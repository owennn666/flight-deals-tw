"""端到端：pipeline 用記憶體儲存 + mock 資料源，驗證偵測與去重。"""
import random
from datetime import date

from flightdeals.detectors.cheap import CheapFareDetector
from flightdeals.detectors.errorfare import ErrorFareDetector
from flightdeals.ingest.base import DataSource
from flightdeals.ingest.mock import DEFAULT_BASELINES, MockDataSource
from flightdeals.models import Cabin, FarePrice, Route
from flightdeals.notify.base import Notifier
from flightdeals.pipeline import Pipeline
from flightdeals.storage.memory import InMemoryStore
from tests._helpers import multi_day_prices

ROUTES = [Route("TPE", "NRT"), Route("TPE", "LHR")]


def _seed_reliable_history(store, routes, n=60, days=8, rng_seed=1):
    """跟 flightdeals.seed.seed_history 邏輯相同（同樣的基準價 + 抖動範圍），
    但把 observed_at 分散到 days 個不同曆日；seed_history 本身只在單一時間點
    寫入、全部落在同一天，滿足不了新的可靠基準線門檻
    （sample_size>=50 且 distinct_days>=7），所以測試改用這個 helper。"""
    rng = random.Random(rng_seed)
    base_map = {Route(*k): v for k, v in DEFAULT_BASELINES.items()}
    total = 0
    for route in routes:
        base = base_map.get(route, 15000)
        prices = [round(base * (1 + rng.uniform(-0.12, 0.15))) for _ in range(n)]
        batch = multi_day_prices(route, prices, days=days)
        store.add_prices(batch)
        total += len(batch)
    return total


class CaptureNotifier(Notifier):
    name = "capture"

    def __init__(self):
        self.deals = []

    def send(self, deal):
        self.deals.append(deal)
        return True


class FixedSource(DataSource):
    """每次都回傳固定的一批報價（測試去重用，不受 RNG 影響）。"""
    name = "fixed"

    def __init__(self, offers):
        self._offers = offers

    def search(self, route, depart=None, ret=None):
        return [o for o in self._offers if o.route == route]


def _pipe(force):
    store = InMemoryStore()
    _seed_reliable_history(store, ROUTES)
    cap = CaptureNotifier()
    pipe = Pipeline(
        sources=[MockDataSource(seed=1, force=force)],
        store=store,
        detectors=[CheapFareDetector(), ErrorFareDetector()],
        notifiers=[cap],
    )
    return pipe, cap


def test_forced_cheap_triggers_deal():
    pipe, cap = _pipe(force="cheap")
    pipe.run_once(ROUTES)
    assert any(d.deal_type.value == "cheap" for d in cap.deals)


def test_forced_error_triggers_verification_deal():
    pipe, cap = _pipe(force="error")
    pipe.run_once(ROUTES)
    errs = [d for d in cap.deals if d.deal_type.value == "error_fare"]
    assert errs and all(d.needs_verification for d in errs)


def test_dedup_no_duplicate_alerts():
    # 用固定報價，兩次 run 得到相同的好康 → 第二次應被去重
    store = InMemoryStore()
    _seed_reliable_history(store, ROUTES)
    cap = CaptureNotifier()
    fixed = FixedSource(
        [FarePrice(route=Route("TPE", "NRT"), price=6000,
                   cabin=Cabin.ECONOMY, depart_date=date(2026, 9, 1))]
    )
    pipe = Pipeline([fixed], store, [CheapFareDetector()], [cap])

    pipe.run_once(ROUTES)
    assert len(cap.deals) == 1        # 第一次推播
    pipe.run_once(ROUTES)
    assert len(cap.deals) == 1        # 同一好康第二次被去重
