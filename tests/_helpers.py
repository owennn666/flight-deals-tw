"""共用測試工具：產生「樣本數足夠、橫跨多個曆日」的合成歷史報價。

新版可靠基準線門檻是 sample_size>=50 且 distinct_days>=7（見 models.Baseline.is_reliable）。
用這裡的 helper 產生 fixture，避免每個測試各自兜資料、忘記把 observed_at 分散到不同天。
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Sequence

from flightdeals.models import Cabin, FarePrice, Route


def spread_observed_at(n: int, days: int = 8, base: Optional[datetime] = None) -> list[datetime]:
    """產生 n 個 observed_at，平均分散在 days 個不同曆日（往回推，含今天）。

    只用整天位移（不加小時抖動）：加小時偏移在「now」接近午夜時會把時間戳
    推過日期邊界，讓 distinct_days 隨執行當下的時刻變動、測試變 flaky。
    """
    now = base or datetime.utcnow()
    return [now - timedelta(days=i % days) for i in range(n)]


def multi_day_prices(
    route: Route,
    prices: Sequence[float],
    days: int = 8,
    cabin: Cabin = Cabin.ECONOMY,
    source: str = "seed",
) -> list[FarePrice]:
    """把一串價格包成橫跨 days 個曆日的 FarePrice 清單（可靠基準線 fixture）。"""
    obs = spread_observed_at(len(prices), days=days)
    return [
        FarePrice(route=route, price=p, cabin=cabin, source=source, observed_at=o)
        for p, o in zip(prices, obs)
    ]


def same_day_prices(
    route: Route,
    prices: Sequence[float],
    cabin: Cabin = Cabin.ECONOMY,
    source: str = "seed",
) -> list[FarePrice]:
    """全部集中在同一天（用來測『樣本數夠但天數不夠』應判定不可靠）。"""
    now = datetime.utcnow()
    return [
        FarePrice(route=route, price=p, cabin=cabin, source=source, observed_at=now)
        for p in prices
    ]
