"""訂閱者（裝置 + 訂閱條件）儲存 + 好康比對。

API 端寫入（裝置註冊、設定訂閱條件）；推播服務讀取（命中好康時找出該推給誰）。
兩邊指向同一個 SQLite 檔即可共享資料，這就是「命中 → 只推給有訂閱的人」的關鍵。
"""
from __future__ import annotations

import json
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
