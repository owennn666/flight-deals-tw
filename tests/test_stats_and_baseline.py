"""基準線與統計的單元測試（純函式、可重現）。"""
from flightdeals.models import Cabin, FarePrice, Route
from flightdeals.stats import mad, median, robust_z
from flightdeals.storage.memory import InMemoryStore


def test_median_and_mad():
    xs = [10, 12, 14, 16, 18]
    assert median(xs) == 14
    assert mad(xs, 14) == 2  # 偏差 [4,2,0,2,4] 的中位數 = 2


def test_robust_z_sign():
    # 越便宜（x 越低於中位數）→ z 越正
    assert robust_z(6000, 10000, 500) > 0
    assert robust_z(14000, 10000, 500) < 0
    assert robust_z(10000, 10000, 0) == 0  # mad=0 不除零


def test_baseline_needs_min_samples():
    store = InMemoryStore()
    r = Route("TPE", "NRT")
    store.add_prices([FarePrice(route=r, price=12000, cabin=Cabin.ECONOMY)])
    # 少於 3 筆 → 無基準線
    assert store.baseline(r) is None


def test_baseline_reliability_threshold():
    store = InMemoryStore()
    r = Route("TPE", "NRT")
    store.add_prices([FarePrice(route=r, price=12000) for _ in range(10)])
    b = store.baseline(r)
    assert b is not None
    assert b.sample_size == 10
    assert b.is_reliable is True
    assert b.median == 12000
