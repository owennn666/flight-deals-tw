"""LINE 通知（台灣主戰場）：LINE Messaging API broadcast。

設定：環境變數 LINE_CHANNEL_ACCESS_TOKEN。只用標準庫 urllib。
註：broadcast 會推給所有好友；正式版通常改用 push 並依用戶訂閱的航線/預算過濾。
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Optional

from ..models import Deal
from .base import Notifier, format_deal


class LineNotifier(Notifier):
    name = "line"
    ENDPOINT = "https://api.line.me/v2/bot/message/broadcast"

    def __init__(self, token: Optional[str] = None, timeout: int = 15):
        self.token = token or os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        self.timeout = timeout

    def send(self, deal: Deal) -> bool:
        if not self.token:
            raise RuntimeError(
                "缺少 LINE_CHANNEL_ACCESS_TOKEN。請於 LINE Developers 建立 Messaging API 頻道並設定。"
            )
        body = json.dumps(
            {"messages": [{"type": "text", "text": format_deal(deal)}]}
        ).encode("utf-8")
        req = urllib.request.Request(
            self.ENDPOINT,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            },
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return 200 <= resp.status < 300
