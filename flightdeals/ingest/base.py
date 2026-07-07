"""資料源介面。新增任何來源只要實作這個 ABC，再到 registry 註冊即可。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from ..models import FarePrice, Route


class DataSource(ABC):
    name: str = "base"

    @abstractmethod
    def search(
        self,
        route: Route,
        depart: Optional[date] = None,
        ret: Optional[date] = None,
    ) -> list[FarePrice]:
        """回傳某航線目前的一批票價觀測值（可能多筆報價）。"""
        raise NotImplementedError

    def close(self) -> None:
        """釋放資源（HTTP session 等）。預設不做事。"""
        return None
