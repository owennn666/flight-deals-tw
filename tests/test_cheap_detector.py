"""異常便宜票偵測器測試（方案 C：跟航線自己的歷史分位數比，不跟混合中位數比）。"""
from flightdeals.detectors.cheap import CheapFareDetector
from flightdeals.models import Baseline, Cabin, FarePrice, Route

R = Route("TPE", "NRT")


def _baseline(median=10000, mad=800, p10=8500, p05=8000, n=30):
    return Baseline(route=R, median=median, mad=mad, sample_size=n, p10=p10, p05=p05)


def _fare(price):
    return FarePrice(route=R, price=price, cabin=Cabin.ECONOMY)


def test_above_p10_not_cheap_enough_returns_none():
    det = CheapFareDetector()
    # 9000 >= p10(8500) → 沒跌破航線歷史地板，即使比中位數低也不成局
    assert det.evaluate(_fare(9000), _baseline()) is None


def test_at_p10_returns_none():
    det = CheapFareDetector()
    # 剛好等於 p10 → 依 spec「>= p10 → None」，邊界不成局
    assert det.evaluate(_fare(8500), _baseline()) is None


def test_between_p05_and_p10_is_good_tier():
    det = CheapFareDetector()
    deal = det.evaluate(_fare(8200), _baseline())  # 介於 p05(8000)/p10(8500) 之間
    assert deal is not None
    assert deal.tier == "good"


def test_below_p05_is_strong_tier():
    det = CheapFareDetector()
    deal = det.evaluate(_fare(7000), _baseline())  # 低於 p05(8000)
    assert deal is not None
    assert deal.tier == "strong"


def test_discount_pct_is_display_only_and_nonnegative():
    det = CheapFareDetector()
    deal = det.evaluate(_fare(7000), _baseline(median=10000))
    assert deal is not None
    assert abs(deal.discount_pct - 0.30) < 1e-9  # (10000-7000)/10000


def test_unreliable_baseline_returns_none():
    det = CheapFareDetector()
    # 樣本太少（<20）時上游 baseline() 本該回 None；這裡直接構造
    # sample_size=3 的 Baseline 確認 is_reliable 擋下判定，不成局。
    assert det.evaluate(_fare(5000), _baseline(n=3)) is None


def test_budget_carrier_normal_price_not_flagged():
    # 對應真實 bug 場景：廉航正常價落在歷史地板附近（等於 p10），不該被誤判成好康。
    det = CheapFareDetector()
    baseline = _baseline(median=6000, p10=5800, p05=5500, n=25)
    assert det.evaluate(_fare(5900), baseline) is None  # 5900 >= p10(5800)
