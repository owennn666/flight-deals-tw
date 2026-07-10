"""端到端：pipeline 用記憶體儲存 + mock 資料源，驗證偵測與去重。"""
import random
from datetime import date, datetime, timedelta

from flightdeals.detectors.base import Detector
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


class BrokenDetector(Detector):
    """對特定航線的報價一律 raise，用來驗證單一航線失敗（非來源層級）不拖垮整批。

    刻意不用「來源 search() 炸掉」當測試情境，因為那條容錯路徑既有的
    per-source try/except 就已經接住了；這裡要驗證的是新加的
    route（航線）層級 try/except，所以讓例外發生在偵測器這一步
    （既有程式碼完全沒包 try/except 的地方）。
    """
    name = "broken"

    def __init__(self, broken_route: Route):
        self._broken_route = broken_route

    def evaluate(self, fare, baseline):
        if fare.route == self._broken_route:
            raise RuntimeError("boom")
        return CheapFareDetector().evaluate(fare, baseline)


def test_route_failure_does_not_abort_other_routes():
    broken = Route("TPE", "NRT")
    ok = Route("TPE", "LHR")
    store = InMemoryStore()
    _seed_reliable_history(store, [broken, ok])
    cap = CaptureNotifier()
    fixed = FixedSource(
        [
            FarePrice(route=broken, price=6000, cabin=Cabin.ECONOMY, depart_date=date(2026, 9, 1)),
            FarePrice(route=ok, price=6000, cabin=Cabin.ECONOMY, depart_date=date(2026, 9, 1)),
        ]
    )
    pipe = Pipeline(
        sources=[fixed],
        store=store,
        detectors=[BrokenDetector(broken)],
        notifiers=[cap],
    )

    deals = pipe.run_once([broken, ok])

    # 壞航線的偵測器炸掉，沒有讓整批 run_once 中斷；正常航線照常出好康
    assert deals
    assert all(d.fare.route == ok for d in deals)


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


class RecordingStore(InMemoryStore):
    """包一層 InMemoryStore，記錄每次 baseline() 實際收到的 window_days 與結果，
    用來驗證 Pipeline.window_days 真的有從設定一路傳到 store.baseline()。"""

    def __init__(self):
        super().__init__()
        self.baseline_calls: list[int] = []
        self.baseline_results = []

    def baseline(self, route, window_days=90):
        self.baseline_calls.append(window_days)
        result = super().baseline(route, window_days=window_days)
        self.baseline_results.append(result)
        return result


def _prices_days_ago(route, prices, days_ago, cabin=Cabin.ECONOMY, source="seed"):
    """把一串價格包成『固定落在 days_ago 天前』的 FarePrice 清單，
    用來測試 window_days 邊界（是否被正確排除在基準線之外）。"""
    obs = datetime.utcnow() - timedelta(days=days_ago)
    return [
        FarePrice(route=route, price=p, cabin=cabin, source=source, observed_at=obs)
        for p in prices
    ]


def test_window_days_from_config_excludes_older_samples():
    route = Route("TPE", "NRT")
    store = RecordingStore()
    # 30 天內、可靠基準線（sample_size>=50、distinct_days>=7）：60 筆、價格 12000
    store.add_prices(multi_day_prices(route, [12000] * 60, days=8))
    # 31~38 天前（超出 window_days=30）：60 筆、價格 3000。
    # 若沒被正確排除，median 會被這批便宜的舊樣本大幅拉低。
    for offset in range(31, 39):
        store.add_prices(_prices_days_ago(route, [3000] * 8, days_ago=offset))

    cap = CaptureNotifier()
    fixed = FixedSource(
        [FarePrice(route=route, price=11000, cabin=Cabin.ECONOMY, depart_date=date(2026, 9, 1))]
    )
    pipe = Pipeline(
        sources=[fixed],
        store=store,
        detectors=[CheapFareDetector()],
        notifiers=[cap],
        window_days=30,
    )

    pipe.run_once([route])

    assert store.baseline_calls == [30]  # Pipeline 把 window_days=30 傳給 store.baseline()
    baseline = store.baseline_results[0]
    assert baseline is not None
    assert baseline.sample_size == 60          # 31 天前那批（共 64 筆）被排除，只剩 30 天內的 60 筆
    assert baseline.median == 12000            # 沒被舊的便宜樣本拉低
