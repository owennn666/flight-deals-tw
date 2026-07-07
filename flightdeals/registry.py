"""模組註冊表：設定檔以「名稱」選用實作，這是可插拔架構的樞紐。

新增模組的最後一步就是在這裡登記一個名字。
"""
from __future__ import annotations

from .detectors.cheap import CheapFareDetector
from .detectors.errorfare import ErrorFareDetector
from .detectors.nested import NestedTicketDetector
from .ingest.amadeus import AmadeusSource
from .ingest.mock import MockDataSource
from .ingest.travelpayouts import TravelpayoutsSource
from .notify.console import ConsoleNotifier
from .notify.expo_push import ExpoPushNotifier
from .notify.line import LineNotifier
from .storage.memory import InMemoryStore
from .storage.postgres_store import PostgresStore
from .storage.sqlite_store import SQLiteStore

SOURCES = {
    "mock": MockDataSource,
    "travelpayouts": TravelpayoutsSource,
    "amadeus": AmadeusSource,
}

STORES = {
    "sqlite": SQLiteStore,
    "memory": InMemoryStore,
    "postgres": PostgresStore,
}

DETECTORS = {
    "cheap": CheapFareDetector,
    "error_fare": ErrorFareDetector,
    "nested": NestedTicketDetector,
}

NOTIFIERS = {
    "console": ConsoleNotifier,
    "line": LineNotifier,
    "expo_push": ExpoPushNotifier,
}
