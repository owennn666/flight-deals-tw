"""訂閱者（裝置 + 訂閱條件）儲存 + 好康比對。

API 端寫入（裝置註冊、設定訂閱條件）；推播服務讀取（命中好康時找出該推給誰）。
兩邊指向同一個 SQLite 檔即可共享資料，這就是「命中 → 只推給有訂閱的人」的關鍵。
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional


def matches(subscription: dict, deal: dict) -> bool:
    """一筆好康是否符合某訂閱條件（純函式、好測試）。

    規則：
    - 有指定航線時，好康航線要在清單內（沒指定 = 全航線）。
    - 有預算上限時，價格不能超過。
    - 有指定艙等時，要一致。
    """
    routes = subscription.get("routes") or []
    if routes and deal.get("route_str") not in routes:
        return False
    max_price = subscription.get("max_price")
    if max_price is not None and deal.get("price", 0) > max_price:
        return False
    cabin = subscription.get("cabin")
    if cabin and deal.get("cabin") != cabin:
        return False
    return True


class SubscriberRepo(ABC):
    @abstractmethod
    def upsert_device(self, token: str, platform: str) -> None: ...

    @abstractmethod
    def set_subscription(self, device: str, sub: dict) -> None: ...

    @abstractmethod
    def get_subscription(self, device: str) -> Optional[dict]: ...

    @abstractmethod
    def all_subscriptions(self) -> list[dict]: ...

    @abstractmethod
    def device_count(self) -> int: ...

    def tokens_for_deal(self, deal: dict) -> list[str]:
        """回傳所有訂閱條件命中此好康的裝置 token（= 訂閱的 device 鍵）。"""
        return [s["device"] for s in self.all_subscriptions() if matches(s, deal)]


class InMemorySubscriberRepo(SubscriberRepo):
    def __init__(self):
        self._devices: dict[str, dict] = {}
        self._subs: dict[str, dict] = {}

    def upsert_device(self, token, platform):
        self._devices[token] = {"platform": platform, "updated_at": datetime.utcnow().isoformat()}

    def set_subscription(self, device, sub):
        self._subs[device] = {**sub, "device": device}

    def get_subscription(self, device):
        return self._subs.get(device)

    def all_subscriptions(self):
        return list(self._subs.values())

    def device_count(self):
        return len(self._devices)


class SQLiteSubscriberRepo(SubscriberRepo):
    def __init__(self, path: str = "flightdeals.db"):
        self._path = path
        self._local = threading.local()
        self._init()

    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self._path)
            self._local.conn = conn
        return conn

    def _init(self):
        self._conn().executescript(
            """
            CREATE TABLE IF NOT EXISTS devices (
                token TEXT PRIMARY KEY, platform TEXT, updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS subscriptions (
                device TEXT PRIMARY KEY, payload TEXT
            );
            """
        )
        self._conn().commit()

    def upsert_device(self, token, platform):
        c = self._conn()
        c.execute(
            "INSERT OR REPLACE INTO devices(token, platform, updated_at) VALUES(?,?,?)",
            (token, platform, datetime.utcnow().isoformat()),
        )
        c.commit()

    def set_subscription(self, device, sub):
        payload = json.dumps({**sub, "device": device}, ensure_ascii=False)
        c = self._conn()
        c.execute(
            "INSERT OR REPLACE INTO subscriptions(device, payload) VALUES(?,?)",
            (device, payload),
        )
        c.commit()

    def get_subscription(self, device):
        row = self._conn().execute(
            "SELECT payload FROM subscriptions WHERE device=?", (device,)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def all_subscriptions(self):
        rows = self._conn().execute("SELECT payload FROM subscriptions").fetchall()
        return [json.loads(r[0]) for r in rows]

    def device_count(self):
        return self._conn().execute("SELECT COUNT(*) FROM devices").fetchone()[0]


class PostgresSubscriberRepo(SubscriberRepo):
    """Postgres（Supabase）版訂閱者儲存：推播服務讀這裡找出好康該推給誰。

    前端直接寫 Supabase（PostgREST），不經過這支程式的 upsert_device / set_subscription
    —— 那三個方法只是滿足抽象類介面，引擎推播路徑實際只會呼叫 tokens_for_deal。

    關鍵 join：subscriptions.device 存的是前端持久化的裝置 UUID（device_id），不是
    Expo push token；devices 表另有 token 欄。要送推播得先用 device_id 換出 token。
    """

    def __init__(self, dsn: Optional[str] = None):
        import psycopg  # 延遲載入，避免其他情境非得裝 psycopg
        self.dsn = dsn or os.getenv("DATABASE_URL")
        if not self.dsn:
            raise RuntimeError("缺少 DATABASE_URL（Supabase 連線字串）。")
        self._conn = psycopg.connect(self.dsn, autocommit=True)

    def upsert_device(self, token, platform):
        with self._conn.cursor() as cur:
            cur.execute(
                """
                insert into devices(token, platform, updated_at)
                values (%s, %s, now())
                on conflict (token) do update
                  set platform = excluded.platform,
                      updated_at = now()
                """,
                (token, platform),
            )

    def set_subscription(self, device, sub):
        with self._conn.cursor() as cur:
            cur.execute(
                """
                insert into subscriptions(device, routes, max_price, cabin, updated_at)
                values (%s, %s::jsonb, %s, %s, now())
                on conflict (device) do update
                  set routes = excluded.routes,
                      max_price = excluded.max_price,
                      cabin = excluded.cabin,
                      updated_at = now()
                """,
                (device, json.dumps(sub.get("routes") or []), sub.get("max_price"), sub.get("cabin")),
            )

    def get_subscription(self, device):
        with self._conn.cursor() as cur:
            cur.execute(
                "select device, routes, max_price, cabin from subscriptions where device=%s",
                (device,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return {"device": row[0], "routes": row[1], "max_price": row[2], "cabin": row[3]}

    def device_count(self):
        with self._conn.cursor() as cur:
            cur.execute("select count(*) from devices")
            return cur.fetchone()[0]

    def _fetch_subscriptions(self) -> list[dict]:
        """查全部訂閱條件；抽成獨立方法方便測試用假資料覆寫、不必真連 DB。"""
        with self._conn.cursor() as cur:
            cur.execute("select device, routes, max_price, cabin from subscriptions")
            rows = cur.fetchall()
        return [
            {"device": r[0], "routes": r[1], "max_price": r[2], "cabin": r[3]}
            for r in rows
        ]

    def _fetch_tokens(self, device_ids: list[str]) -> list[str]:
        """把命中的 device（前端 UUID）join devices.device_id 換成 Expo push token。

        只回傳格式正確（'ExponentPushToken' 開頭）的 token；抽成獨立方法方便測試覆寫。
        """
        if not device_ids:
            return []
        with self._conn.cursor() as cur:
            cur.execute(
                "select token from devices"
                " where device_id = any(%s) and token like 'ExponentPushToken%%'",
                (device_ids,),
            )
            rows = cur.fetchall()
        return [r[0] for r in rows]

    def all_subscriptions(self):
        return self._fetch_subscriptions()

    def tokens_for_deal(self, deal: dict) -> list[str]:
        matched_device_ids = [
            s["device"] for s in self._fetch_subscriptions() if matches(s, deal)
        ]
        if not matched_device_ids:
            return []
        return self._fetch_tokens(matched_device_ids)
