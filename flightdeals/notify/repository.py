"""把好康持久化到儲存，讓 FastAPI 能查詢（App 首頁列表/詳情的資料來源）。

這其實是「用 Notifier 介面做持久化」——pipeline 每次推播，順手把 deal 存起來。
所以它需要一個 store 實例，不走 registry（registry 只認得無狀態、由 config 建構的實作）。
"""
from __future__ import annotations

from ..models import Deal
from ..serializers import deal_to_dict
from ..storage.base import PriceStore
from .base import Notifier


class RepositoryNotifier(Notifier):
    name = "repository"

    def __init__(self, store: PriceStore):
        self.store = store

    def send(self, deal: Deal) -> bool:
        self.store.save_deal(deal_to_dict(deal))
        return True
