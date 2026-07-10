"""訂閱比對 + Expo 推播閉環測試（不觸網、不落地）。"""
from flightdeals.models import Cabin, Deal, DealType, FarePrice, Route
from flightdeals.notify.expo_push import ExpoPushNotifier
from flightdeals.subscribers import InMemorySubscriberRepo, PostgresSubscriberRepo, matches


def test_matches_route_filter():
    deal = {"route_str": "TPE->NRT", "price": 7000, "cabin": "economy"}
    assert matches({"routes": ["TPE->NRT"], "max_price": None}, deal)
    assert not matches({"routes": ["TPE->LHR"], "max_price": None}, deal)
    assert matches({"routes": [], "max_price": None}, deal)  # 空清單 = 全航線


def test_matches_price_and_cabin():
    deal = {"route_str": "TPE->NRT", "price": 9000, "cabin": "business"}
    assert not matches({"routes": [], "max_price": 8000}, deal)
    assert matches({"routes": [], "max_price": 10000}, deal)
    assert not matches({"routes": [], "cabin": "economy"}, deal)
    assert matches({"routes": [], "cabin": "business"}, deal)


class FakeSender:
    def __init__(self):
        self.calls = []

    def send(self, tokens, title, body, extra=None):
        self.calls.append((tokens, title, body, extra))
        return len(tokens)


def _cheap_deal():
    return Deal(
        fare=FarePrice(route=Route("TPE", "NRT"), price=7000, cabin=Cabin.ECONOMY),
        deal_type=DealType.CHEAP,
        baseline_median=12000,
        discount_pct=0.42,
        score=3.0,
        tier="strong",
    )


def test_expo_push_only_to_matching_devices():
    repo = InMemorySubscriberRepo()
    repo.upsert_device("ExponentPushToken[a]", "ios")
    repo.set_subscription("ExponentPushToken[a]", {"routes": ["TPE->NRT"], "max_price": 8000})
    repo.upsert_device("ExponentPushToken[b]", "android")
    repo.set_subscription("ExponentPushToken[b]", {"routes": ["TPE->LHR"], "max_price": None})

    fake = FakeSender()
    notifier = ExpoPushNotifier(repo=repo, sender=fake)
    assert notifier.send(_cheap_deal()) is True

    # 只有訂閱 TPE->NRT 的裝置 a 該收到
    assert len(fake.calls) == 1
    assert fake.calls[0][0] == ["ExponentPushToken[a]"]
    # extra 帶了整筆 deal（App 點通知可直接開詳情）
    assert fake.calls[0][3]["route_str"] == "TPE->NRT"


def test_expo_push_no_subscribers_is_noop():
    fake = FakeSender()
    notifier = ExpoPushNotifier(repo=InMemorySubscriberRepo(), sender=fake)
    assert notifier.send(_cheap_deal()) is True
    assert fake.calls == []  # 沒有訂閱者 → 不發送


class FakePostgresSubscriberRepo(PostgresSubscriberRepo):
    """PostgresSubscriberRepo 測試替身：不連真 Postgres，覆寫兩個查詢方法餵假資料。

    subscriptions 存前端 UUID（device_id），token 要靠 devices 表另外 join 出來——
    這裡用 dict 模擬那張表：{device_id: token}。
    """

    def __init__(self, subscriptions: list[dict], devices: dict[str, str]):
        # 故意不呼叫 super().__init__()：測試不連真 DB，也不需要 DATABASE_URL。
        self._subs = subscriptions
        self._devices = devices

    def _fetch_subscriptions(self):
        return self._subs

    def _fetch_tokens(self, device_ids):
        return [
            token
            for device_id, token in self._devices.items()
            if device_id in device_ids and token.startswith("ExponentPushToken")
        ]


def _nrt_deal():
    return {"route_str": "TPE->NRT", "price": 7000, "cabin": "economy"}


def test_postgres_repo_matches_and_joins_device_id_to_token():
    repo = FakePostgresSubscriberRepo(
        subscriptions=[
            {"device": "uuid-a", "routes": ["TPE->NRT"], "max_price": 8000, "cabin": None},
            {"device": "uuid-b", "routes": ["TPE->LHR"], "max_price": None, "cabin": None},
        ],
        devices={"uuid-a": "ExponentPushToken[a]", "uuid-b": "ExponentPushToken[b]"},
    )
    # 只有 uuid-a 的訂閱命中航線；uuid-b 訂閱的是別條航線，不該被推
    assert repo.tokens_for_deal(_nrt_deal()) == ["ExponentPushToken[a]"]


def test_postgres_repo_matched_sub_without_matching_device_row_returns_empty():
    repo = FakePostgresSubscriberRepo(
        subscriptions=[
            {"device": "uuid-orphan", "routes": ["TPE->NRT"], "max_price": None, "cabin": None},
        ],
        devices={},  # devices 表查無此 device_id（例如裝置從沒註冊過 token）
    )
    assert repo.tokens_for_deal(_nrt_deal()) == []


def test_postgres_repo_max_price_below_deal_price_excluded():
    repo = FakePostgresSubscriberRepo(
        subscriptions=[
            {"device": "uuid-a", "routes": ["TPE->NRT"], "max_price": 5000, "cabin": None},
        ],
        devices={"uuid-a": "ExponentPushToken[a]"},
    )
    # deal 價格 7000 > max_price 5000 → 不推
    assert repo.tokens_for_deal(_nrt_deal()) == []
