"""bug 票 / error fare 偵測器測試。"""
from flightdeals.detectors.errorfare import ErrorFareDetector
from flightdeals.models import Baseline, Cabin, FarePrice, Route

R = Route("TPE", "LHR")


def _baseline(median=30000, mad=2500, n=60, days=8):
    return Baseline(route=R, median=median, mad=mad, sample_size=n, distinct_days=days)


def test_extreme_low_price_flagged():
    det = ErrorFareDetector(threshold=0.70)
    deal = det.evaluate(FarePrice(route=R, price=6000, cabin=Cabin.ECONOMY), _baseline())
    assert deal is not None
    assert deal.needs_verification is True  # 一律進人工複核
    assert deal.tier == "insane"


def test_moderate_discount_not_flagged():
    det = ErrorFareDetector(threshold=0.70)
    # 只便宜 30%，屬「便宜票」而非「疑似標錯價」
    assert det.evaluate(FarePrice(route=R, price=21000), _baseline()) is None


def test_high_cabin_structural_rule():
    det = ErrorFareDetector(threshold=0.70, high_cabin_ratio=0.60)
    # 商務艙卻只有基準線 50% 的價 → 即使沒到 70% 門檻也該被結構性規則抓到
    deal = det.evaluate(
        FarePrice(route=R, price=15000, cabin=Cabin.BUSINESS), _baseline()
    )
    assert deal is not None
    assert deal.needs_verification is True
