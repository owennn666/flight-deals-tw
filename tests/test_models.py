"""models.py 的 Deal.dedupe_key 測試（去重鍵維度：gate / return_date / 價格桶）。"""
from datetime import date

from flightdeals.models import Cabin, Deal, DealType, FarePrice, Route

R = Route("TPE", "NRT")


def _deal(price, gate=None, return_date=None, depart_date=None):
    fare = FarePrice(
        route=R,
        price=price,
        cabin=Cabin.ECONOMY,
        depart_date=depart_date or date(2026, 9, 1),
        return_date=return_date,
        gate=gate,
    )
    return Deal(
        fare=fare, deal_type=DealType.CHEAP, baseline_median=10000,
        discount_pct=0.3, score=1.0, tier="good",
    )


def test_dedupe_key_differs_by_gate():
    # 不同訂票網站（gate）開出同價，不該被誤判成同一筆重複 deal 而吞掉。
    a = _deal(6000, gate="Trip.com")
    b = _deal(6000, gate="ezTravel")
    assert a.dedupe_key() != b.dedupe_key()


def test_dedupe_key_differs_by_return_date():
    # 不同回程日的同價 deal 是不同行程，不該共用一個去重鍵。
    a = _deal(6000, return_date=date(2026, 9, 8))
    b = _deal(6000, return_date=date(2026, 9, 15))
    assert a.dedupe_key() != b.dedupe_key()


def test_dedupe_key_same_price_bucket_collapses():
    # 5106 與 5149 同落在百元桶 5100 → key 相同，避免 1 元價格抖動被當新 deal。
    a = _deal(5106)
    b = _deal(5149)
    assert a.dedupe_key() == b.dedupe_key()


def test_dedupe_key_different_price_bucket_differs():
    a = _deal(5106)
    b = _deal(5206)
    assert a.dedupe_key() != b.dedupe_key()
