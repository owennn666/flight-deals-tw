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


def _parse_time(s: Optional[str]) -> Optional[str]:
    """從 ISO 時間字串（如 "2026-08-20T08:15:00+07:00"）取出當地時間 "HH:MM"。"""
    if not s:
        return None
    t = s[11:16]
    if len(t) == 5 and t[2] == ":" and t[:2].isdigit() and t[3:].isdigit():
        return t
    return None


class TravelpayoutsSource(DataSource):
    name = "travelpayouts"
    BASE = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"
    # 外導：Trip.com 預填搜尋（資料只給航線/日期，導到該航線那些日期的搜尋頁）
    TRIP_BASE = "https://tw.trip.com/flights/showfarefirst"

    def __init__(
        self,
        token: Optional[str] = None,
        currency: str = "twd",
        marker: Optional[str] = None,
        limit: int = 30,
        timeout: int = 15,
        gates: Optional[list[str]] = None,
    ):
        self.token = token or os.getenv("TRAVELPAYOUTS_TOKEN")
        self.marker = marker or os.getenv("TRAVELPAYOUTS_MARKER")  # 聯盟變現
        self.currency = currency
        self.limit = limit
        self.timeout = timeout
        # 只收這些訂票網站（gate）開的價。預設（prod）不設，收全部家；
        # 外導改採分流（Trip.com → Trip 預填頁，其他家 → Aviasales 比價頁），
        # 不再需要靠這個過濾對齊顯示與外導網站。保留參數供向後相容與測試。
        self.gates = gates

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
            if self.gates and item.get("gate") not in self.gates:
                continue
            depart = _parse_dt(item.get("departure_at"))
            ret = _parse_dt(item.get("return_at"))
            flight_number = item.get("flight_number")
            gate = item.get("gate")
            deep_link = (
                self._trip_link(route, depart, ret)
                if gate == "Trip.com"
                else self._aviasales_link(item.get("link"), route, depart)
            )
            offers.append(
                FarePrice(
                    route=route,
                    price=float(price),
                    currency=self.currency.upper(),
                    cabin=Cabin.ECONOMY,
                    depart_date=depart,
                    return_date=ret,
                    source=self.name,
                    deep_link=deep_link,
                    raw=item,
                    airline=item.get("airline"),
                    flight_number=(
                        str(flight_number) if flight_number is not None else None
                    ),
                    transfers=item.get("transfers"),
                    depart_time=_parse_time(item.get("departure_at")),
                    gate=gate,
                )
            )
        return offers

    def _trip_link(self, route: Route, depart, ret) -> str:
        """組 Trip.com 預填搜尋連結（tw.trip.com、繁中、TWD）。

        Trip.com 不提供「確切票面」深連結，這是資料層能做到最貼近的結果：把
        使用者帶到該航線、那些日期的搜尋頁。無出發日則導到機票首頁避免壞連結。
        之後要接 Trip.com 聯盟分潤：URL 尾端加 &Allianceid=xxx&SID=xxx 即可。
        """
        if depart is None:
            return "https://tw.trip.com/flights/"
        params = {
            "dcity": route.origin.lower(),
            "acity": route.destination.lower(),
            "ddate": depart.isoformat(),
            "class": "y",
            "quantity": "1",
            "locale": "zh-TW",
            "curr": "TWD",
        }
        if ret is not None:
            params["rdate"] = ret.isoformat()
            params["triptype"] = "rt"
        else:
            params["triptype"] = "ow"
        return f"{self.TRIP_BASE}?{urllib.parse.urlencode(params)}"

    def _aviasales_link(self, link: Optional[str], route: Route, depart) -> str:
        """組 Aviasales 比價頁連結（非 Trip.com 開的價都導這裡）。

        優先用 API 回傳的 link（去掉會 15 分鐘過期的 t= token query）；
        沒有 link 時退而用航線/日期自組搜尋路徑；都沒有就導首頁。
        有設 marker（聯盟）則附加在最後。
        """
        if link:
            path = link.split("?")[0]
            url = f"https://www.aviasales.com{path}"
        elif depart is not None:
            ddmm = f"{depart.day:02d}{depart.month:02d}"
            url = (
                f"https://www.aviasales.com/search/"
                f"{route.origin.upper()}{ddmm}{route.destination.upper()}1"
            )
        else:
            url = "https://www.aviasales.com"

        if self.marker:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}marker={self.marker}"
        return url
