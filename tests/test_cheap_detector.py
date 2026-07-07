"""異常便宜票偵測器測試。"""
from flightdeals.detectors.cheap import CheapFareDetector
from flightdeals.models import Baseline, Cabin, FarePrice, Route

R = Route("TPE", "NRT")


def _baseline(median=10000, mad=800, n=30):
    return Baseline(route=R, median=median, mad=mad, sample_size=n)


def _fare(price):
    return FarePrice(route=R, price=price, cabin=Cabin.ECONOMY)


def test_not_cheap_enough_returns_none():
    det = CheapFareDetector(threshold=0.25)
    assert det.evaluate(_fare(9000), _baseline()) is None  # 只便宜 10%


def test_good_tier():
    det = CheapFareDetector(threshold=0.25, strong=0.40)
    deal = det.evaluate(_fare(7000), _baseline())  # 便宜 30%
    assert deal is not None
    assert deal.tier == "good"
    assert 0.29 < deal.discount_pct < 0.31


def test_strong_tier():
    det = CheapFareDetector(threshold=0.25, strong=0.40)
    deal = det.evaluate(_fare(5500), _baseline())  # 便宜 45%
    assert deal is not None
    assert deal.tier == "strong"


def test_unreliable_baseline_returns_none():
    det = CheapFareDetector()
    assert det.evaluate(_fare(5000), _baseline(n=3)) is None  # 樣本太少不判
