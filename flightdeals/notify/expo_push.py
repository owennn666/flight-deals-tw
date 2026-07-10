"""Expo 原生推播：命中好康 → 讀訂閱找出該推的裝置 → 打 Expo Push API。

Expo Push API：POST https://exp.host/--/api/v2/push/send
以標準庫 urllib 實作，不需額外套件。這一支把「偵測 → 推播」的閉環補完。
"""
from __future__ import annotations

import json
import urllib.request
from typing import Optional

from ..models import Deal
from ..serializers import deal_to_dict
from ..subscribers import SQLiteSubscriberRepo, SubscriberRepo
from .base import Notifier, format_deal


class ExpoPushSender:
    """低階 Expo Push API 客戶端。"""
    ENDPOINT = "https://exp.host/--/api/v2/push/send"

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    def send(self, tokens: list[str], title: str, body: str, extra: Optional[dict] = None) -> int:
        """送出推播，回傳實際送出的訊息數。只送格式正確的 Expo token。

        extra：附在通知 data 欄位的酬載（App 點通知時讀它 → 直接跳該筆好康詳情）。
        """
        base = {"title": title, "body": body, "sound": "default"}
        if extra:
            base["data"] = extra
        messages = [
            {"to": t, **base}
            for t in tokens
            if isinstance(t, str) and t.startswith("ExponentPushToken")
        ]
        if not messages:
            return 0
        payload = json.dumps(messages).encode("utf-8")
        req = urllib.request.Request(
            self.ENDPOINT,
            data=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return len(messages) if 200 <= resp.status < 300 else 0


class ExpoPushNotifier(Notifier):
    """Notifier：每筆好康 → 找出符合訂閱條件的裝置 → 發原生推播。

    subscriber_db 指向與 API 相同的 SQLite 檔，才能讀到 App 註冊的裝置/訂閱。
    （repo / sender 可注入，方便測試。）
    """
    name = "expo_push"

    def __init__(
        self,
        subscriber_db: str = "flightdeals.db",
        repo: Optional[SubscriberRepo] = None,
        sender: Optional[ExpoPushSender] = None,
        backend: str = "sqlite",
    ):
        if repo is not None:
            self.repo = repo
        elif backend == "postgres":
            from ..subscribers import PostgresSubscriberRepo  # 延遲 import，避免沒裝 psycopg 的環境炸掉

            self.repo = PostgresSubscriberRepo()
        else:
            self.repo = SQLiteSubscriberRepo(subscriber_db)
        self.sender = sender or ExpoPushSender()

    def send(self, deal: Deal) -> bool:
        d = deal_to_dict(deal)
        tokens = self.repo.tokens_for_deal(d)
        if not tokens:
            return True  # 沒有符合條件的訂閱者 → 沒事做，視為成功
        title = f"{d['route_str']}　{d['price']:.0f} {d['currency']}（省 {round(d['discount_pct'] * 100)}%）"
        # extra 帶整筆 deal → App 點通知就能直接開詳情，不必再打 API
        self.sender.send(tokens, title, format_deal(deal), extra=d)
        return True
