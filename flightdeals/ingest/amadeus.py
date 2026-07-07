"""資料源骨架：Amadeus Self-Service。

⚠️ 已淘汰：Amadeus Self-Service 於 2026/7/17 停用（新註冊已關閉、金鑰將失效），
   不建議新專案採用。保留此骨架僅供了解「多來源交叉驗證」的介面長相。
   免費首選請改用 travelpayouts.py。
設定（若仍有既有金鑰）：AMADEUS_CLIENT_ID / AMADEUS_CLIENT_SECRET。
"""
from __future__ import annotations

import os
from typing import Optional

from .base import DataSource


class AmadeusSource(DataSource):
    name = "amadeus"

    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        self.client_id = client_id or os.getenv("AMADEUS_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("AMADEUS_CLIENT_SECRET")

    def search(self, route, depart=None, ret=None):
        raise NotImplementedError(
            "AmadeusSource 尚未實作。請參考 README『新增資料源』："
            "先用 client_id/secret 取得 OAuth token，再呼叫 Flight Offers Search。"
        )
