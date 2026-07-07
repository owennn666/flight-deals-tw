"""異常便宜票偵測：低於基準線一定比例即成局（誤報成本低，可自動推播）。"""
from __future__ import annotations

from typing import Optional

from ..models import Baseline, Deal, DealType, FarePrice
from ..stats import robust_z
from .base import Detector


class CheapFareDetector(Detector):
    deal_type = DealType.CHEAP

    def __init__(self, threshold: float = 0.25, strong: float = 0.40):
        # threshold：便宜多少才算好康；strong：便宜多少算「強力推薦」
        self.threshold = threshold
        self.strong = strong

    def evaluate(self, fare, baseline):
        if baseline is None or not baseline.is_reliable:
            return None
        med = baseline.median
        if med <= 0:
            return None
        discount = (med - fare.price) / med
        if discount < self.threshold:
            return None
        tier = "strong" if discount >= self.strong else "good"
        return Deal(
            fare=fare,
            deal_type=self.deal_type,
            baseline_median=med,
            discount_pct=discount,
            score=robust_z(fare.price, med, baseline.mad),
            tier=tier,
            reasons=[f"比基準線便宜 {discount * 100:.0f}%（基準 {med:.0f} {fare.currency}）"],
        )
