"""主控台通知：開發/demo 用，直接印出。"""
from __future__ import annotations

from ..models import Deal
from .base import Notifier, format_deal


class ConsoleNotifier(Notifier):
    name = "console"

    def send(self, deal: Deal) -> bool:
        print("─" * 48)
        print(format_deal(deal))
        return True
