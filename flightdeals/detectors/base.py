"""偵測器介面。新增票種只要實作這個 ABC，再到 registry 註冊即可。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from ..models import Baseline, Deal, FarePrice


class Detector(ABC):
    deal_type: str = "base"

    @abstractmethod
    def evaluate(self, fare: FarePrice, baseline: Optional[Baseline]) -> Optional[Deal]:
        """判斷單筆票價是否成局；不成局回傳 None。"""
        raise NotImplementedError
