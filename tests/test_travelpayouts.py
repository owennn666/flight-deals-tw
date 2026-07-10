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
            "gate": "Trip.com",
        },
        {
            "origin": "TPE", "destination": "NRT", "price": 9100, "airline": "BR",
            "departure_at": "2026-09-01T09:00:00+08:00",
            "link": "/search/xyz?foo=1",
            "gate": "Kiwi.com",
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
    # 外導分流：第一筆 gate=Trip.com → Trip 預填搜尋連結（航線 + 日期）
    dl0 = offers[0].deep_link
    assert dl0.startswith("https://tw.trip.com/flights/showfarefirst")
    assert "dcity=tpe" in dl0 and "acity=nrt" in dl0
    assert "ddate=2026-08-15" in dl0 and "rdate=2026-08-22" in dl0 and "triptype=rt" in dl0
    # 第二筆 gate=Kiwi.com（非 Trip.com）→ 導 Aviasales，去掉會過期的 t= token query，
    # 帶 marker（_StubSource marker="12345"）
    dl1 = offers[1].deep_link
    assert dl1.startswith("https://www.aviasales.com/search/xyz")
    assert "t=" not in dl1
    assert "foo=1" not in dl1
    assert "marker=12345" in dl1

    # 航空公司 / 航班號 / 轉機 / 出發時間
    assert offers[0].airline == "JX"
    assert offers[0].flight_number == "395"  # int 395 轉字串
    assert offers[0].transfers == 0
    assert offers[0].depart_time == "10:00"
    assert offers[0].gate == "Trip.com"

    assert offers[1].airline == "BR"
    assert offers[1].flight_number is None  # SAMPLE 第二筆無 flight_number
    assert offers[1].transfers is None  # SAMPLE 第二筆無 transfers
    assert offers[1].depart_time == "09:00"
    assert offers[1].gate == "Kiwi.com"


def test_trip_link_alliance_params(monkeypatch):
    """設了 Trip.com 聯盟環境變數 → Trip 連結帶 Allianceid/SID；Aviasales 連結不受影響。"""
    monkeypatch.setenv("TRIP_ALLIANCE_ID", "5743816")
    monkeypatch.setenv("TRIP_SID", "146111470")
    src = _StubSource(token="t", currency="twd")
    offers = src.search(Route("TPE", "NRT"))
    dl0 = offers[0].deep_link  # gate=Trip.com → Trip 預填連結
    assert "Allianceid=5743816" in dl0 and "SID=146111470" in dl0
    dl1 = offers[1].deep_link  # gate=Kiwi.com → Aviasales，不帶 Trip 聯盟參數
    assert "Allianceid" not in dl1


def test_trip_link_no_alliance_when_unset(monkeypatch):
    monkeypatch.delenv("TRIP_ALLIANCE_ID", raising=False)
    monkeypatch.delenv("TRIP_SID", raising=False)
    src = _StubSource(token="t", currency="twd")
    offers = src.search(Route("TPE", "NRT"))
    assert "Allianceid" not in offers[0].deep_link


def test_gate_filter_keeps_only_listed_gates():
    src = _StubSource(token="t", currency="twd", gates=["Trip.com"])
    offers = src.search(Route("TPE", "NRT"))
    # SAMPLE 三筆：Trip.com / Kiwi.com / price=None → 只留 Trip.com 那筆
    assert [o.price for o in offers] == [8200.0]
    assert offers[0].airline == "JX"


def test_no_gate_filter_keeps_all():
    src = _StubSource(token="t", currency="twd")  # gates 未設 = 不過濾
    offers = src.search(Route("TPE", "NRT"))
    assert [o.price for o in offers] == [8200.0, 9100.0]


def test_missing_token_raises():
    src = TravelpayoutsSource(token=None)
    src.token = None
    try:
        src.search(Route("TPE", "NRT"))
        assert False, "應該要因缺 token 而拋錯"
    except RuntimeError as e:
        assert "TRAVELPAYOUTS_TOKEN" in str(e)
