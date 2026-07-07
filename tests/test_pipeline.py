"""端到端：pipeline 用記憶體儲存 + mock 資料源，驗證偵測與去重。"""
from datetime import date

from flightdeals.detectors.cheap import CheapFareDetector
from flightdeals.detectors.errorfare import ErrorFareDetector
from flightdeals.ingest.base import DataSource
from flightdeals.ingest.mock import MockDataSource
from flightdeals.models import Cabin, FarePrice, Route
from flightdeals.notify.base import Notifier
from flightdeals.pipeline import Pipeline
from flightdeals.seed import seed_history
from flightdeals.storage.memory import InMemoryStore

ROUTES = [Route("TPE", "NRT"), Route("TPE", "LHR")]


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
    seed_history(store, ROUTES)
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
    seed_history(store, ROUTES)
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
