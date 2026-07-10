"""storage 層測試：SQLite baseline 的 p10/p05（原本永遠 0.0 的 bug）與
prices 保留期 prune()（memory / sqlite）。"""
from datetime import datetime, timedelta

from flightdeals.models import Cabin, FarePrice, Route
from flightdeals.storage.memory import InMemoryStore
from flightdeals.storage.sqlite_store import SQLiteStore
from tests._helpers import multi_day_prices

R = Route("TPE", "NRT")


def _old_price(route, price, days_ago):
    return FarePrice(
        route=route, price=price, cabin=Cabin.ECONOMY, source="test",
        observed_at=datetime.utcnow() - timedelta(days=days_ago),
    )


def test_sqlite_baseline_has_nonzero_percentiles():
    store = SQLiteStore(path=":memory:")
    try:
        # 50 筆、橫跨 8 天，其中 40 筆是 6000、10 筆是 3800（歷史特價）
        prices = [6000] * 40 + [3800] * 10
        store.add_prices(multi_day_prices(R, prices, days=8))
        b = store.baseline(R)
        assert b is not None
        assert b.sample_size == 50
        assert b.distinct_days == 8
        # 原本 SQLiteStore.baseline 沒算 p10/p05，永遠是 0.0；修正後應 > 0。
        assert b.p10 > 0
        assert b.p05 > 0
        assert b.p05 <= b.p10 < b.median
    finally:
        store.close()


def test_memory_prune_keeps_recent_drops_old():
    store = InMemoryStore()
    store.add_prices([_old_price(R, 9000, 60), _old_price(R, 9500, 100)])
    removed = store.prune(95)
    assert removed == 1
    remaining = store._prices[R]
    assert len(remaining) == 1
    assert remaining[0][0] == 9000  # 只剩 60 天前那筆，100 天前的被刪掉


def test_sqlite_prune_keeps_recent_drops_old():
    store = SQLiteStore(path=":memory:")
    try:
        store.add_prices([_old_price(R, 9000, 60), _old_price(R, 9500, 100)])
        removed = store.prune(95)
        assert removed == 1
        rows = store._conn().execute("SELECT price FROM prices").fetchall()
        assert [r[0] for r in rows] == [9000]
    finally:
        store.close()
