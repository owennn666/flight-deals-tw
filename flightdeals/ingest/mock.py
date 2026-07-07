"""離線假資料源：不需任何 API key 就能跑整條 pipeline，用於 demo 與測試。

- 平常回傳基準價附近的數筆報價（帶雜訊）
- 依機率注入「異常便宜」或「error fare」異常
- force 參數可強制注入某類異常（demo/測試用），配合 seed 可完全可重現
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Optional

from ..models import Cabin, FarePrice, Route
from .base import DataSource

# 每條航線的「正常」來回價（TWD）— 純示範
DEFAULT_BASELINES = {
    ("TPE", "NRT"): 12000,
    ("TPE", "KIX"): 11000,
    ("TPE", "ICN"): 9000,
    ("TPE", "BKK"): 9500,
    ("TPE", "DAD"): 8000,
    ("TPE", "CDG"): 32000,
    ("TPE", "LHR"): 34000,
}


class MockDataSource(DataSource):
    name = "mock"

    def __init__(
        self,
        baselines: Optional[dict] = None,
        seed: Optional[int] = None,
        cheap_prob: float = 0.15,
        error_prob: float = 0.05,
        force: Optional[str] = None,   # None / "cheap" / "error"
    ):
        base = baselines or DEFAULT_BASELINES
        # 允許 tuple 或 Route 當 key，統一轉成 Route
        self._base = {
            (k if isinstance(k, Route) else Route(*k)): v for k, v in base.items()
        }
        self._rng = random.Random(seed)
        self.cheap_prob = cheap_prob
        self.error_prob = error_prob
        self.force = force

    def _baseline_for(self, route: Route) -> float:
        return self._base.get(route, 15000)

    def search(self, route, depart=None, ret=None):
        base = self._baseline_for(route)
        depart = depart or (date.today() + timedelta(days=45))
        offers = [
            self._make(route, base * (1 + self._rng.uniform(-0.12, 0.15)), depart, ret)
            for _ in range(3)
        ]
        roll = self._rng.random()
        if self.force == "error" or (self.force is None and roll < self.error_prob):
            offers.append(
                self._make(route, base * self._rng.uniform(0.12, 0.22), depart, ret, tag="error")
            )
        elif self.force == "cheap" or (self.force is None and roll < self.cheap_prob):
            offers.append(
                self._make(route, base * self._rng.uniform(0.50, 0.68), depart, ret, tag="cheap")
            )
        return offers

    def _make(self, route, price, depart, ret, tag="normal"):
        return FarePrice(
            route=route,
            price=round(price),
            currency="TWD",
            cabin=Cabin.ECONOMY,
            depart_date=depart,
            return_date=ret,
            source=self.name,
            deep_link=f"https://example-ota.test/book?o={route.origin}&d={route.destination}",
            raw={"mock_tag": tag},
        )
