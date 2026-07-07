"""四腳票 / 隱藏城市票偵測（構票）— 介面骨架。

與另外兩種本質不同：不是「等便宜出現」，而是「主動組合航段」壓低票價，
需要 multi-city 搜尋資料（Kiwi Tequila / Amadeus multi-city）。
單筆票價無法判斷構票效益，故 evaluate() 一律回傳 None；
真正的比較邏輯放在 compare_itineraries()，Phase 3 接上構票資料源後啟用。
"""
from __future__ import annotations

from typing import Optional

from ..models import Baseline, Deal, DealType, FarePrice
from .base import Detector


class NestedTicketDetector(Detector):
    deal_type = DealType.NESTED

    def __init__(self, threshold: float = 0.20):
        self.threshold = threshold  # 構票要比直購便宜多少才值得

    def evaluate(self, fare, baseline):
        # 單筆報價無法判斷「構票 vs 直購」，需成對比較 → 交給 compare_itineraries()
        return None

    def compare_itineraries(self, constructed_total: float, direct_price: float) -> Optional[float]:
        """給定『構出來的多段總價』與『直購價』，回傳節省比例（達標才回傳，否則 None）。

        Phase 3：由構票資料源產生候選組合後呼叫此方法，達標者再包成 Deal 推播，
        並務必附上風險標註（航段順序性、行李、改簽限制等）。
        """
        if direct_price <= 0:
            return None
        saving = (direct_price - constructed_total) / direct_price
        return saving if saving >= self.threshold else None
