"""基準線與統計的單元測試（純函式、可重現）。"""
from flightdeals.models import Route
from flightdeals.stats import mad, median, percentile, robust_z
from flightdeals.storage.memory import InMemoryStore
from tests._helpers import multi_day_prices, same_day_prices


def test_median_and_mad():
    xs = [10, 12, 14, 16, 18]
    assert median(xs) == 14
    assert mad(xs, 14) == 2  # 偏差 [4,2,0,2,4] 的中位數 = 2


def test_robust_z_sign():
    # 越便宜（x 越低於中位數）→ z 越正
    assert robust_z(6000, 10000, 500) > 0
    assert robust_z(14000, 10000, 500) < 0
    assert robust_z(10000, 10000, 0) == 0  # mad=0 不除零


def test_percentile_basic():
    xs = [10, 20, 30, 40, 50]  # n=5, pos = q*4
    assert percentile(xs, 0.0) == 10
    assert percentile(xs, 1.0) == 50
    assert percentile(xs, 0.5) == 30
    assert percentile(xs, 0.25) == 20  # pos=1.0 → 剛好第2個


def test_percentile_interpolates():
    xs = [10, 20, 30, 40]  # n=4, pos = q*3
    # q=0.1 → pos=0.3 → 10 + 0.3*(20-10) = 13
    assert percentile(xs, 0.1) == 13


def test_percentile_edge_cases():
    assert percentile([], 0.5) == 0.0
    assert percentile([42], 0.1) == 42
    assert percentile([42], 0.9) == 42


def test_baseline_needs_min_samples():
    store = InMemoryStore()
    r = Route("TPE", "NRT")
    store.add_prices(multi_day_prices(r, [12000] * 49, days=8))
    # 49 筆 < 50 → 無基準線（樣本數不足，不論橫跨幾天）
    assert store.baseline(r) is None


def test_baseline_reliability_threshold():
    store = InMemoryStore()
    r = Route("TPE", "NRT")
    store.add_prices(multi_day_prices(r, [12000] * 60, days=8))
    b = store.baseline(r)
    assert b is not None
    assert b.sample_size == 60
    assert b.distinct_days == 8
    assert b.is_reliable is True
    assert b.median == 12000


def test_baseline_unreliable_when_single_day():
    store = InMemoryStore()
    r = Route("TPE", "OSA")
    # 60 筆樣本數夠，但全擠在同一天 → 不算「跟平常比」，不可靠
    store.add_prices(same_day_prices(r, [12000] * 60))
    b = store.baseline(r)
    assert b is not None
    assert b.sample_size == 60
    assert b.distinct_days == 1
    assert b.is_reliable is False


def test_baseline_has_percentiles():
    store = InMemoryStore()
    r = Route("TPE", "BKK")
    # 50 筆、橫跨 8 天，其中 40 筆是 6000（廉航常態價）、10 筆是 3800（歷史特價）
    prices = [6000] * 40 + [3800] * 10
    store.add_prices(multi_day_prices(r, prices, days=8))
    b = store.baseline(r)
    assert b is not None
    assert b.sample_size == 50
    assert b.is_reliable is True
    # p10/p05 應落在歷史特價附近，而不是等於混合中位數
    assert b.p10 < b.median
    assert b.p05 <= b.p10
