"""共用資料模型（所有模組都依賴這裡，不依賴任何實作）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional


class Cabin(str, Enum):
    ECONOMY = "economy"
    PREMIUM = "premium"
    BUSINESS = "business"
    FIRST = "first"


@dataclass(frozen=True)
class Route:
    """航線（以 IATA 代碼表示），frozen 以便當 dict key / 放入 set。"""
    origin: str        # 例：TPE
    destination: str   # 例：NRT

    def __str__(self) -> str:
        return f"{self.origin}->{self.destination}"


@dataclass
class FarePrice:
    """一筆票價觀測值（某來源、某時間點抓到的一個報價）。"""
    route: Route
    price: float
    currency: str = "TWD"
    cabin: Cabin = Cabin.ECONOMY
    depart_date: Optional[date] = None
    return_date: Optional[date] = None
    source: str = "unknown"
    observed_at: datetime = field(default_factory=datetime.utcnow)
    deep_link: Optional[str] = None          # 訂票（聯盟）連結
    raw: dict = field(default_factory=dict)  # 原始回應，除錯用


@dataclass
class Baseline:
    """某航線的價格基準線（偵測的參照點）。"""
    route: Route
    median: float
    mad: float                 # median absolute deviation，抗離群值的離散度
    sample_size: int
    currency: str = "TWD"

    @property
    def is_reliable(self) -> bool:
        """樣本太少的基準線不可信，避免暖機期誤報。"""
        return self.sample_size >= 8


class DealType(str, Enum):
    CHEAP = "cheap"            # 異常便宜票
    ERROR_FARE = "error_fare"  # bug 票 / 標錯價
    NESTED = "nested"          # 四腳票 / 隱藏城市（構票）


@dataclass
class Deal:
    """偵測到的好康（偵測器的輸出、通知的輸入）。"""
    fare: FarePrice
    deal_type: DealType
    baseline_median: float
    discount_pct: float               # 相對基準線便宜幾成（0~1）
    score: float                      # 異常分數（穩健 z）
    tier: str                         # good / strong / insane
    needs_verification: bool = False  # True = 推播前需人工複核（bug 票）
    reasons: list[str] = field(default_factory=list)

    def dedupe_key(self) -> str:
        """去重鍵：同票種、同航線、同出發日、同價位只推一次。"""
        f = self.fare
        d = f.depart_date.isoformat() if f.depart_date else "-"
        return f"{self.deal_type.value}|{f.route}|{d}|{round(f.price)}"
