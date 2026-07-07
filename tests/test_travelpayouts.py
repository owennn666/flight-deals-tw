"""Travelpayouts v3 資料源解析測試（注入假回應，不觸網）。"""
from datetime import date

from flightdeals.ingest.travelpayouts import TravelpayoutsSource
from flightdeals.models import Route

# 仿 v3 prices_for_dates 的回應
SAMPLE = {
    "success": True,
    "data": [
        {
            "origin": "TPE", "destination": "NRT", "price": 8200, "airline": "JX",
            "flight_number": 395,
            "departure_at": "2026-08-15T10:00:00+08:00",
            "return_at": "2026-08-22T18:00:00+09:00",
            "transfers": 0, "link": "/search/TPE1508NRT2208",
        },
        {
            "origin": "TPE", "destination": "NRT", "price": 9100, "airline": "BR",
            "departure_at": "2026-09-01T09:00:00+08:00",
            "link": "/search/xyz?foo=1",
        },
        {"origin": "TPE", "destination": "NRT", "price": None},  # 應被略過
    ],
    "currency": "twd",
}


class _StubSource(TravelpayoutsSource):
    """覆寫 _fetch，回傳固定假資料，測試真正的解析路徑。"""
    def _fetch(self, url):
        return SAMPLE


def test_parse_v3_prices():
    src = _StubSource(token="t", marker="12345", currency="twd")
    offers = src.search(Route("TPE", "NRT"))

    assert [o.price for o in offers] == [8200.0, 9100.0]  # None 被略過
    assert offers[0].currency == "TWD"
    assert offers[0].depart_date == date(2026, 8, 15)
    assert offers[0].return_date == date(2026, 8, 22)
    # 外導：Trip.com 預填搜尋連結（航線 + 日期）
    dl0 = offers[0].deep_link
    assert dl0.startswith("https://tw.trip.com/flights/showfarefirst")
    assert "dcity=tpe" in dl0 and "acity=nrt" in dl0
    assert "ddate=2026-08-15" in dl0 and "rdate=2026-08-22" in dl0 and "triptype=rt" in dl0
    # 第二筆無回程日 → 單程，不帶 rdate
    dl1 = offers[1].deep_link
    assert "ddate=2026-09-01" in dl1 and "triptype=ow" in dl1
    assert "rdate=" not in dl1

    # 航空公司 / 航班號 / 轉機 / 出發時間
    assert offers[0].airline == "JX"
    assert offers[0].flight_number == "395"  # int 395 轉字串
    assert offers[0].transfers == 0
    assert offers[0].depart_time == "10:00"

    assert offers[1].airline == "BR"
    assert offers[1].flight_number is None  # SAMPLE 第二筆無 flight_number
    assert offers[1].transfers is None  # SAMPLE 第二筆無 transfers
    assert offers[1].depart_time == "09:00"


def test_missing_token_raises():
    src = TravelpayoutsSource(token=None)
    src.token = None
    try:
        src.search(Route("TPE", "NRT"))
        assert False, "應該要因缺 token 而拋錯"
    except RuntimeError as e:
        assert "TRAVELPAYOUTS_TOKEN" in str(e)
