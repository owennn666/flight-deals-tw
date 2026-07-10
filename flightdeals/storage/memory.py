"""記憶體儲存：demo 與單元測試用（不落地、最快）。"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from ..models import Baseline, FarePrice, Route
from ..stats import mad as _mad
from ..stats import median as _median
from ..stats import percentile as _percentile
from .base import PriceStore


class InMemoryStore(PriceStore):
    name = "memory"

    def __init__(self):
        self._prices: dict[Route, list[tuple[float, datetime]]] = defaultdict(list)
        self._seen: set[str] = set()
        self._deals: list[dict] = []
        self._deal_id = 0

    def add_prices(self, prices):
        for p in prices:
            self._prices[p.route].append((p.price, p.observed_at))

    def baseline(self, route, window_days=90):
        cutoff = datetime.utcnow() - timedelta(days=window_days)
        rows = [(price, obs) for price, obs in self._prices.get(route, []) if obs >= cutoff]
        if len(rows) < 50:
            return None
        xs = [price for price, _ in rows]
        distinct_days = len({obs.date() for _, obs in rows})
        med = _median(xs)
        return Baseline(
            route=route,
            median=med,
            mad=_mad(xs, med),
            sample_size=len(xs),
            p10=_percentile(xs, 0.10),
            p05=_percentile(xs, 0.05),
            distinct_days=distinct_days,
        )

    def prune(self, days: int = 95) -> int:
        cutoff = datetime.utcnow() - timedelta(days=days)
        removed = 0
        for route, rows in self._prices.items():
            kept = [(price, obs) for price, obs in rows if obs >= cutoff]
            removed += len(rows) - len(kept)
            self._prices[route] = kept
        return removed

    def seen_deal(self, key):
        return key in self._seen

    def mark_deal(self, key):
        self._seen.add(key)

    def save_deal(self, deal_dict):
        self._deal_id += 1
        rec = {"id": self._deal_id, "created_at": datetime.utcnow().isoformat(), **deal_dict}
        self._deals.append(rec)
        return self._deal_id

    def recent_deals(self, limit=50, deal_type=None):
        items = list(reversed(self._deals))
        if deal_type:
            items = [d for d in items if d.get("type") == deal_type]
        return items[:limit]
