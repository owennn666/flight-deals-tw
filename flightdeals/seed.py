"""為儲存注入合成歷史資料，讓基準線一開始就可用（demo / 首次啟動暖機）。"""
from __future__ import annotations

import random

from .ingest.mock import DEFAULT_BASELINES
from .models import Cabin, FarePrice, Route
from .storage.base import PriceStore


def seed_history(store: PriceStore, routes, n: int = 60, rng_seed: int = 1) -> int:
    """對每條航線寫入 n 筆基準價附近的歷史觀測。回傳寫入總筆數。"""
    rng = random.Random(rng_seed)
    base_map = {Route(*k): v for k, v in DEFAULT_BASELINES.items()}
    total = 0
    for route in routes:
        base = base_map.get(route, 15000)
        batch = [
            FarePrice(
                route=route,
                price=round(base * (1 + rng.uniform(-0.12, 0.15))),
                currency="TWD",
                cabin=Cabin.ECONOMY,
                source="seed",
            )
            for _ in range(n)
        ]
        store.add_prices(batch)
        total += len(batch)
    return total
