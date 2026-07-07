"""SQLite 儲存：MVP 落地用，零外部服務。之後可換 Postgres+TimescaleDB。"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Optional

from ..models import Baseline, FarePrice, Route
from ..stats import mad as _mad
from ..stats import median as _median
from .base import PriceStore


class SQLiteStore(PriceStore):
    name = "sqlite"

    def __init__(self, path: str = "flightdeals.db"):
        self._path = path
        self._local = threading.local()  # 每執行緒各自的 connection
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
            CREATE TABLE IF NOT EXISTS prices (
                origin TEXT, destination TEXT, price REAL, currency TEXT,
                cabin TEXT, depart_date TEXT, source TEXT, observed_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_prices_route
                ON prices(origin, destination, observed_at);
            CREATE TABLE IF NOT EXISTS deals_seen (key TEXT PRIMARY KEY, ts TEXT);
            CREATE TABLE IF NOT EXISTS deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT, created_at TEXT, payload TEXT
            );
            """
        )
        self._conn().commit()

    def add_prices(self, prices):
        rows = [
            (
                p.route.origin, p.route.destination, p.price, p.currency,
                p.cabin.value, p.depart_date.isoformat() if p.depart_date else None,
                p.source, p.observed_at.isoformat(),
            )
            for p in prices
        ]
        c = self._conn()
        c.executemany(
            "INSERT INTO prices(origin,destination,price,currency,cabin,depart_date,source,observed_at)"
            " VALUES(?,?,?,?,?,?,?,?)",
            rows,
        )
        c.commit()

    def baseline(self, route, window_days=90):
        since = (datetime.utcnow() - timedelta(days=window_days)).isoformat()
        rows = self._conn().execute(
            "SELECT price FROM prices WHERE origin=? AND destination=? AND observed_at>=?",
            (route.origin, route.destination, since),
        ).fetchall()
        prices = [r[0] for r in rows]
        if len(prices) < 3:
            return None
        med = _median(prices)
        return Baseline(route=route, median=med, mad=_mad(prices, med), sample_size=len(prices))

    def seen_deal(self, key):
        return self._conn().execute(
            "SELECT 1 FROM deals_seen WHERE key=?", (key,)
        ).fetchone() is not None

    def mark_deal(self, key):
        c = self._conn()
        c.execute(
            "INSERT OR IGNORE INTO deals_seen(key, ts) VALUES(?, ?)",
            (key, datetime.utcnow().isoformat()),
        )
        c.commit()

    def save_deal(self, deal_dict):
        c = self._conn()
        cur = c.execute(
            "INSERT INTO deals(type, created_at, payload) VALUES(?,?,?)",
            (deal_dict.get("type"), datetime.utcnow().isoformat(),
             json.dumps(deal_dict, ensure_ascii=False)),
        )
        c.commit()
        return cur.lastrowid

    def recent_deals(self, limit=50, deal_type=None):
        q = "SELECT id, created_at, payload FROM deals"
        args: list = []
        if deal_type:
            q += " WHERE type=?"
            args.append(deal_type)
        q += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        rows = self._conn().execute(q, args).fetchall()
        out = []
        for _id, created, payload in rows:
            d = json.loads(payload)
            d["id"] = _id
            d["created_at"] = created
            out.append(d)
        return out

    def close(self):
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None
