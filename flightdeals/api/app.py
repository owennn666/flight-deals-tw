"""FastAPI 應用：App / Web 客戶端透過這層讀好康、管訂閱、註冊 push token。

用 create_app(store=..., subscribers=...) 工廠，方便測試注入記憶體版；
預設用 config 的 SQLite（與 CLI 的 run/seed 及 ExpoPushNotifier 共用同一個 db，
這樣 App 註冊的裝置/訂閱，推播服務才讀得到）。
"""
from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from ..config import DEFAULT_CONFIG
from ..storage.base import PriceStore
from ..subscribers import SQLiteSubscriberRepo, SubscriberRepo
from .schemas import DeviceIn, SubscriptionIn

_DB_PATH = DEFAULT_CONFIG["store"]["params"]["path"]


def _default_store() -> PriceStore:
    from ..storage.sqlite_store import SQLiteStore
    return SQLiteStore(_DB_PATH)


def _default_subscribers() -> SubscriberRepo:
    return SQLiteSubscriberRepo(_DB_PATH)


def _dump(model) -> dict:
    # 相容 pydantic v2 (model_dump) 與 v1 (dict)
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


def create_app(
    store: Optional[PriceStore] = None,
    subscribers: Optional[SubscriberRepo] = None,
) -> FastAPI:
    store = store or _default_store()
    subs = subscribers or _default_subscribers()

    app = FastAPI(title="便宜機票 API", version="0.2.0")
    # 允許 App / Web 前端跨網域呼叫（開發階段全開；上線請鎖定網域）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/routes")
    def routes():
        return [
            {"origin": o, "destination": d, "label": f"{o}→{d}"}
            for o, d in DEFAULT_CONFIG["routes"]
        ]

    @app.get("/api/deals")
    def deals(limit: int = Query(50, ge=1, le=200),
              type: Optional[str] = Query(None, description="cheap / error_fare / nested")):
        return store.recent_deals(limit=limit, deal_type=type)

    @app.get("/api/deals/{deal_id}")
    def deal_detail(deal_id: int):
        for d in store.recent_deals(limit=1000):
            if d.get("id") == deal_id:
                return d
        raise HTTPException(status_code=404, detail="deal not found")

    @app.post("/api/devices")
    def register_device(body: DeviceIn):
        subs.upsert_device(body.token, body.platform)
        return {"ok": True, "devices": subs.device_count()}

    @app.get("/api/subscriptions")
    def get_subscription(device: str):
        return subs.get_subscription(device) or {
            "device": device, "routes": [], "max_price": None, "cabin": None,
        }

    @app.post("/api/subscriptions")
    def set_subscription(body: SubscriptionIn):
        subs.set_subscription(body.device, _dump(body))
        return {"ok": True}

    return app
