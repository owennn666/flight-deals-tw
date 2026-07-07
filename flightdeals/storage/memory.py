"""記憶體儲存：demo 與單元測試用（不落地、最快）。"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Optional

from ..models import Baseline, FarePrice, Route
from ..stats import mad as _mad
from ..stats import median as _median
from .base import PriceStore


class InMemoryStore(PriceStore):
    name = "memory"

    def __init__(self):
        self._prices: dict[Route, list[float]] = defaultdict(list)
        self._seen: set[str] = set()
        self._deals: list[dict] = []
        self._deal_id = 0

    def add_prices(self, prices):
        for p in prices:
            self._prices[p.route].append(p.price)

    def baseline(self, route, window_days=90):
        xs = self._prices.get(route, [])
        if len(xs) < 3:
            return None
        med = _median(xs)
        return Baseline(route=route, median=med, mad=_mad(xs, med), sample_size=len(xs))

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
