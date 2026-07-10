"""儲存介面。可從 SQLite 無痛換成 Postgres/TimescaleDB，只要實作這個 ABC。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from ..models import Baseline, FarePrice, Route


class PriceStore(ABC):
    name: str = "base"

    @abstractmethod
    def add_prices(self, prices: list[FarePrice]) -> None:
        """寫入一批票價觀測值。"""

    @abstractmethod
    def baseline(self, route: Route, window_days: int = 90) -> Optional[Baseline]:
        """用近 window_days 的歷史計算基準線；樣本不足回傳 None。"""

    @abstractmethod
    def seen_deal(self, key: str) -> bool:
        """該好康是否已推播過（去重）。"""

    @abstractmethod
    def mark_deal(self, key: str) -> None:
        """標記好康已推播。"""

    # --- deals 持久化：供 API 查詢（App 首頁列表 / 詳情）---

    @abstractmethod
    def save_deal(self, deal_dict: dict) -> int:
        """存一筆已成局的好康（dict 見 serializers.deal_to_dict），回傳 id。"""

    @abstractmethod
    def recent_deals(self, limit: int = 50, deal_type: Optional[str] = None) -> list[dict]:
        """回傳近期好康（新到舊），可依票種篩選；每筆含 id 與 created_at。"""

    def close(self) -> None:
        return None

    def prune(self, days: int = 95) -> int:
        """清除 days 天前的舊報價，避免 prices 表無限增長。

        預設 no-op（回 0）；需要落地保存空間的實作（Postgres/SQLite）應覆寫。
        回傳實際刪除筆數。
        """
        return 0
