"""API 層測試（FastAPI TestClient，注入記憶體版 store 與 subscribers）。

需要選用依賴：pip install fastapi httpx
若未安裝，pytest 會自動略過本檔。
"""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from flightdeals.api.app import create_app  # noqa: E402
from flightdeals.detectors.cheap import CheapFareDetector  # noqa: E402
from flightdeals.ingest.mock import MockDataSource  # noqa: E402
from flightdeals.models import Route  # noqa: E402
from flightdeals.notify.repository import RepositoryNotifier  # noqa: E402
from flightdeals.pipeline import Pipeline  # noqa: E402
from flightdeals.seed import seed_history  # noqa: E402
from flightdeals.storage.memory import InMemoryStore  # noqa: E402
from flightdeals.subscribers import InMemorySubscriberRepo  # noqa: E402


def _client(store=None):
    # 一律注入記憶體版，避免測試碰到 SQLite 檔
    return TestClient(create_app(store=store or InMemoryStore(),
                                 subscribers=InMemorySubscriberRepo()))


def _store_with_deals():
    store = InMemoryStore()
    routes = [Route("TPE", "NRT")]
    seed_history(store, routes)
    Pipeline(
        [MockDataSource(seed=1, force="cheap")],
        store,
        [CheapFareDetector()],
        [RepositoryNotifier(store)],
    ).run_once(routes)
    return store


def test_health():
    assert _client().get("/api/health").json() == {"status": "ok"}


def test_routes_endpoint():
    data = _client().get("/api/routes").json()
    assert len(data) > 0
    assert {"origin", "destination", "label"} <= set(data[0].keys())


def test_deals_list_and_detail():
    client = _client(store=_store_with_deals())
    deals = client.get("/api/deals").json()
    assert len(deals) >= 1
    assert deals[0]["type"] == "cheap"

    did = deals[0]["id"]
    assert client.get(f"/api/deals/{did}").status_code == 200
    assert client.get("/api/deals/99999999").status_code == 404


def test_deals_type_filter():
    client = _client(store=_store_with_deals())
    assert client.get("/api/deals", params={"type": "error_fare"}).json() == []


def test_device_and_subscription_roundtrip():
    client = _client()
    tok = "ExponentPushToken[abc123]"
    assert client.post("/api/devices", json={"token": tok, "platform": "ios"}).json()["ok"]
    assert client.post(
        "/api/subscriptions",
        json={"device": tok, "routes": ["TPE->NRT"], "max_price": 8000},
    ).json()["ok"]
    got = client.get("/api/subscriptions", params={"device": tok}).json()
    assert got["max_price"] == 8000
    assert got["routes"] == ["TPE->NRT"]
