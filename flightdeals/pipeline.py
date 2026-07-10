"""編排引擎：把四層串起來。這是唯一知道「流程」的地方，各模組彼此不相依。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .detectors.base import Detector
from .ingest.base import DataSource
from .models import Deal, Route
from .notify.base import Notifier
from .storage.base import PriceStore


@dataclass
class Pipeline:
    sources: list[DataSource]
    store: PriceStore
    detectors: list[Detector]
    notifiers: list[Notifier]
    window_days: int = 90

    def run_once(self, routes: Iterable[Route]) -> list[Deal]:
        found: list[Deal] = []
        for route in routes:
            try:
                found.extend(self._run_route(route))
            except Exception as e:  # 單一航線失敗不該中斷整批
                print(f"[warn] 航線 {route} 失敗：{e}")
        return found

    def _run_route(self, route: Route) -> list[Deal]:
        found: list[Deal] = []
        # 1) 從所有資料源抓當前報價
        offers = []
        for src in self.sources:
            try:
                offers.extend(src.search(route))
            except Exception as e:  # 單一來源失敗不該中斷整批
                print(f"[warn] 來源 {src.name} 於 {route} 失敗：{e}")
        if not offers:
            return found

        # 2) 先用「歷史」算基準線，再把當前報價存入（供未來使用）
        baseline = self.store.baseline(route, window_days=self.window_days)
        self.store.add_prices(offers)
        if baseline is None:
            return found  # 暖機不足，先不偵測

        # 3) 每筆報價 × 每個偵測器
        for fare in offers:
            for det in self.detectors:
                deal = det.evaluate(fare, baseline)
                if deal is None:
                    continue
                key = deal.dedupe_key()
                if self.store.seen_deal(key):
                    continue  # 去重：推過就不再推
                self.store.mark_deal(key)
                self._notify(deal)
                found.append(deal)
        return found

    def _notify(self, deal: Deal) -> None:
        for n in self.notifiers:
            try:
                n.send(deal)
            except Exception as e:
                print(f"[warn] 通知管道 {n.name} 失敗：{e}")

    def close(self) -> None:
        for s in self.sources:
            s.close()
        self.store.close()
