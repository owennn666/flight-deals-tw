"""API 請求/回應型別（與 App 端 apps/mobile/src/api/types.ts 對齊）。"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class DeviceIn(BaseModel):
    token: str                 # Expo push token
    platform: str = "expo"     # ios / android / expo


class SubscriptionIn(BaseModel):
    device: str                       # 以 push token 或裝置 id 當 key
    routes: List[str] = []            # 例：["TPE->NRT", "TPE->KIX"]
    max_price: Optional[float] = None
    cabin: Optional[str] = None


class RouteOut(BaseModel):
    origin: str
    destination: str
    label: str
