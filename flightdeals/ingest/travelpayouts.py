"""真實資料源：Travelpayouts / Aviasales Data API（v3 prices_for_dates）。

為什麼選它（2026 現況）：
- **真正免費**：只需免費註冊 Travelpayouts 拿 token，無付費門檻。
- **有價格資料 + 涵蓋台灣航線**：回傳 Aviasales 用戶近 48 小時搜到的最低票價（快取）。
- **自帶變現**：帶上聯盟 marker，訂票連結就是你的聯盟連結。
- 對照：Amadeus Self-Service 2026/7/17 停用；Kiwi Tequila 需 5 萬 MAU 才給存取 → 皆不適合新專案。

端點：GET https://api.travelpayouts.com/aviasales/v3/prices_for_dates
只用標準庫 urllib，不需額外套件。
設定：環境變數 TRAVELPAYOUTS_TOKEN（必填）、TRAVELPAYOUTS_MARKER（選填，變現用）。
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import date, datetime
from typing import Optional

from ..models import Cabin, FarePrice, Route
from .base import DataSource


def _parse_dt(s: Optional[str]) -> Optional[date]:
    """把 API 的 ISO 時間（可能帶時區）轉成 date。"""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(s[:10])
        except ValueError:
            return None


class TravelpayoutsSource(DataSource):
    name = "travelpayouts"
    BASE = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"
    AVIASALES = "https://www.aviasales.com"

    def __init__(
        self,
        token: Optional[str] = None,
        currency: str = "twd",
        marker: Optional[str] = None,
        limit: int = 30,
        timeout: int = 15,
    ):
        self.token = token or os.getenv("TRAVELPAYOUTS_TOKEN")
        self.marker = marker or os.getenv("TRAVELPAYOUTS_MARKER")  # 聯盟變現
        self.currency = currency
        self.limit = limit
        self.timeout = timeout

    def search(self, route, depart=None, ret=None):
        if not self.token:
            raise RuntimeError(
                "缺少 TRAVELPAYOUTS_TOKEN。免費註冊 travelpayouts.com → Profile 取得 token → 填到 .env。"
            )
        params = {
            "origin": route.origin,
            "destination": route.destination,
            "currency": self.currency,
            "one_way": "false",
            "sorting": "price",
            "limit": self.limit,
            "token": self.token,
        }
        if depart is not None:
            # 可傳 YYYY-MM（整月）或 YYYY-MM-DD（單日）
            params["departure_at"] = depart.strftime("%Y-%m")
        url = f"{self.BASE}?{urllib.parse.urlencode(params)}"
        return self._parse(self._fetch(url), route)

    def _fetch(self, url: str) -> dict:
        """實際發 HTTP 請求（獨立出來，方便測試時注入假回應）。"""
        with urllib.request.urlopen(url, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _parse(self, payload: dict, route: Route) -> list[FarePrice]:
        offers: list[FarePrice] = []
        for item in (payload or {}).get("data", []) or []:
            price = item.get("price")
            if price is None:
                continue
            offers.append(
                FarePrice(
                    route=route,
                    price=float(price),
                    currency=self.currency.upper(),
                    cabin=Cabin.ECONOMY,
                    depart_date=_parse_dt(item.get("departure_at")),
                    return_date=_parse_dt(item.get("return_at")),
                    source=self.name,
                    deep_link=self._deep_link(item.get("link")),
                    raw=item,
                )
            )
        return offers

    def _deep_link(self, link: Optional[str]) -> str:
        """把相對的 Aviasales 連結補成完整（聯盟）連結。"""
        if not link:
            return self.AVIASALES
        url = f"{self.AVIASALES}{link}"
        if self.marker:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}marker={self.marker}"
        return url
