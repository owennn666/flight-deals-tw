"""Postgres 儲存（Supabase）：GitHub Actions 抓票時把 prices/deals 寫進 Supabase。

- 前端不透過這裡讀，而是直接打 Supabase 的 PostgREST 自動 API（見 apps/mobile）。
- 連線字串由環境變數 DATABASE_URL 提供（Supabase 的 connection string）。
- psycopg 延遲載入：沒安裝也不影響其他模組（本機 SQLite / 測試不需要）。
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from ..models import Baseline
from ..stats import mad as _mad
from ..stats import median as _median
from ..stats import percentile as _percentile
from .base import PriceStore


class PostgresStore(PriceStore):
    name = "postgres"

    def __init__(self, dsn: Optional[str] = None):
        import psycopg  # 延遲載入，避免其他情境非得裝 psycopg
        self.dsn = dsn or os.getenv("DATABASE_URL")
        if not self.dsn:
            raise RuntimeError("缺少 DATABASE_URL（Supabase 連線字串）。")
        self._conn = psycopg.connect(self.dsn, autocommit=True)

    def add_prices(self, prices):
        rows = [
            (p.route.origin, p.route.destination, p.price, p.currency,
             p.cabin.value, p.depart_date, p.source, p.observed_at, p.airline)
            for p in prices
        ]
        with self._conn.cursor() as cur:
            cur.executemany(
                "insert into prices(origin,destination,price,currency,cabin,depart_date,source,observed_at,airline)"
                " values (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                rows,
            )

    def baseline(self, route, window_days=90):
        since = datetime.now(timezone.utc) - timedelta(days=window_days)
        with self._conn.cursor() as cur:
            cur.execute(
                "select price, observed_at from prices"
                " where origin=%s and destination=%s and observed_at>=%s",
                (route.origin, route.destination, since),
            )
            rows = cur.fetchall()
        if len(rows) < 50:
            return None
        xs = [r[0] for r in rows]
        distinct_days = len({r[1].date() for r in rows})
        m = _median(xs)
        return Baseline(
            route=route,
            median=m,
            mad=_mad(xs, m),
            sample_size=len(xs),
            p10=_percentile(xs, 0.10),
            p05=_percentile(xs, 0.05),
            distinct_days=distinct_days,
        )

    def seen_deal(self, key):
        with self._conn.cursor() as cur:
            cur.execute("select 1 from deals_seen where key=%s", (key,))
            return cur.fetchone() is not None

    def mark_deal(self, key):
        with self._conn.cursor() as cur:
            cur.execute("insert into deals_seen(key) values (%s) on conflict do nothing", (key,))

    def save_deal(self, d):
        with self._conn.cursor() as cur:
            cur.execute(
                """
                insert into deals
                  (type, route_str, origin, destination, price, currency, cabin,
                   depart_date, return_date, baseline_median, discount_pct, tier,
                   needs_verification, reasons, deep_link, source,
                   airline, flight_number, transfers, depart_time, gate, dedupe_key)
                values
                  (%s,%s,%s,%s,%s,%s,%s,%s::date,%s::date,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s,%s,%s)
                on conflict (dedupe_key) do nothing
                returning id
                """,
                (
                    d["type"], d["route_str"], d["route"]["origin"], d["route"]["destination"],
                    d["price"], d["currency"], d["cabin"], d.get("depart_date"), d.get("return_date"),
                    d["baseline_median"], d["discount_pct"], d["tier"], d["needs_verification"],
                    json.dumps(d["reasons"]), d.get("deep_link"), d.get("source"),
                    d.get("airline"), d.get("flight_number"), d.get("transfers"), d.get("depart_time"),
                    d.get("gate"), d["dedupe_key"],
                ),
            )
            row = cur.fetchone()
            return row[0] if row else -1

    def recent_deals(self, limit=50, deal_type=None):
        q = ("select id, created_at, type, route_str, origin, destination, price, currency, cabin,"
             " depart_date, return_date, baseline_median, discount_pct, tier, needs_verification,"
             " reasons, deep_link, source, airline, flight_number, transfers, depart_time, gate from deals")
        args: list = []
        if deal_type:
            q += " where type=%s"
            args.append(deal_type)
        q += " order by id desc limit %s"
        args.append(limit)
        with self._conn.cursor() as cur:
            cur.execute(q, args)
            cols = [c.name for c in cur.description]
            rows = cur.fetchall()
        out = []
        for r in rows:
            dct = dict(zip(cols, r))
            for k in ("created_at", "depart_date", "return_date"):
                if dct.get(k) is not None:
                    dct[k] = dct[k].isoformat()
            dct["route"] = {"origin": dct.pop("origin"), "destination": dct.pop("destination")}
            out.append(dct)
        return out

    def prune(self, days: int = 95) -> int:
        """刪除 days 天前的舊報價，避免 prices 表無限增長撞 Supabase 免費額度。"""
        with self._conn.cursor() as cur:
            cur.execute(
                "delete from prices where observed_at < now() - make_interval(days => %s)",
                (days,),
            )
            return cur.rowcount

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass
