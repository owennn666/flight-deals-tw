"""bug 票 / error fare 偵測：極端低價 + 結構性規則，一律標記需人工複核。

刻意保守：error fare 誤報一次會嚴重傷害信任，所以門檻拉高並要求覆核。
真實系統還應在此之後做「多來源交叉驗證」（見 README / pipeline 註解）。
"""
from __future__ import annotations

from typing import Optional

from ..models import Baseline, Cabin, Deal, DealType, FarePrice
from ..stats import robust_z
from .base import Detector


class ErrorFareDetector(Detector):
    deal_type = DealType.ERROR_FARE

    def __init__(self, threshold: float = 0.70, high_cabin_ratio: float = 0.60):
        self.threshold = threshold                # 低於基準線幾成算極端
        self.high_cabin_ratio = high_cabin_ratio  # 高艙等卻低於基準此比例 → 可疑

    def evaluate(self, fare, baseline):
        if baseline is None or not baseline.is_reliable:
            return None
        med = baseline.median
        if med <= 0:
            return None
        discount = (med - fare.price) / med
        reasons: list[str] = []

        if discount >= self.threshold:
            reasons.append(f"極端低價：比基準線便宜 {discount * 100:.0f}%")

        # 結構性規則：商務/頭等艙卻是超低價（典型標錯價特徵）
        if fare.cabin in (Cabin.BUSINESS, Cabin.FIRST) and fare.price <= med * self.high_cabin_ratio:
            reasons.append(f"{fare.cabin.value} 艙等卻只有基準線 {fare.price / med * 100:.0f}% 的價格")

        if not reasons:
            return None
        return Deal(
            fare=fare,
            deal_type=self.deal_type,
            baseline_median=med,
            discount_pct=discount,
            score=robust_z(fare.price, med, baseline.mad),
            tier="insane",
            needs_verification=True,  # 一律進人工複核佇列
            reasons=reasons,
        )
