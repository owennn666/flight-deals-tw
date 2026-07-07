"""異常便宜票偵測：跟這條航線自己的歷史價分位數比，跌破歷史低價才成局。

方案 C：不跟「混合廉航+傳統航空」的中位數比（廉航結構性便宜、正常價也會
天然低於混合中位數，形成循環邏輯），改跟航線自己的歷史 p10/p05 比，對齊
Google Flights / Hopper 的「跟航線歷史比」邏輯。
"""
from __future__ import annotations

from typing import Optional

from ..models import Baseline, Deal, DealType, FarePrice
from ..stats import robust_z
from .base import Detector


class CheapFareDetector(Detector):
    deal_type = DealType.CHEAP

    def __init__(self, **_):
        # 不再吃 threshold/strong：門檻改為固定的歷史分位數（p10/p05）。
        # **_ 吞掉任何殘留的 config 參數，避免舊 config 沒清乾淨時炸掉。
        pass

    def evaluate(self, fare, baseline):
        if baseline is None or not baseline.is_reliable:
            return None
        med = baseline.median
        if med <= 0:
            return None
        if fare.price >= baseline.p10:
            return None  # 沒跌破航線歷史地板，不夠便宜
        tier = "strong" if fare.price < baseline.p05 else "good"
        discount = max(0.0, (med - fare.price) / med)  # 僅作顯示用
        return Deal(
            fare=fare,
            deal_type=self.deal_type,
            baseline_median=med,
            discount_pct=discount,
            score=robust_z(fare.price, med, baseline.mad),
            tier=tier,
            reasons=[f"比這條航線平常便宜 {discount * 100:.0f}%（平常約 {med:.0f} {fare.currency}）"],
        )
