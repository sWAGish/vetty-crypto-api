
import pytest
from fastapi.testclient import TestClient

import app.main as main

client = TestClient(main.app)


def fake_coingecko_get(url, params=None, timeout=10):
    class FakeResponse:
        def __init__(self, json_data, status_code=200):
            self._json_data = json_data
            self.status_code = status_code

        def json(self):
            return self._json_data

    if url.endswith("/coins/list"):
        return FakeResponse(
            [
                {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"},
                {"id": "ethereum", "symbol": "eth", "name": "Ethereum"},
            ]
        )

    if url.endswith("/coins/categories/list"):
        return FakeResponse(
            [
                {"category_id": "layer-1", "name": "Layer 1"},
                {"category_id": "defi", "name": "DeFi"},
            ]
        )

    if url.endswith("/coins/markets"):
        vs = params.get("vs_currency")
        if vs == "inr":
            return FakeResponse(
                [
                    {
                        "id": "bitcoin",
                        "symbol": "btc",
                        "name": "Bitcoin",
                        "current_price": 100.0,
                        "market_cap": 1000000.0,
                        "price_change_percentage_24h": 1.5,
                    }
                ]
            )
        if vs == "cad":
            return FakeResponse(
                [
                    {
                        "id": "bitcoin",
                        "symbol": "btc",
                        "name": "Bitcoin",
                        "current_price": 2.0,
                        "market_cap": 20000.0,
                        "price_change_percentage_24h": 1.0,
                    }
                ]
            )

    return FakeResponse([], 404)


@pytest.fixture(autouse=True)
def mock_requests(monkeypatch):
    monkeypatch.setattr(main.requests, "get", fake_coingecko_get)


def get_token():
    response = client.post(
        "/auth/token",
        data={"username": main.API_USERNAME, "password": main.API_PASSWORD},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_auth_success():
    token = get_token()
    assert isinstance(token, str)


def test_auth_failure():
    response = client.post(
        "/auth/token",
        data={"username": "wrong", "password": "wrong"},
    )
    assert response.status_code == 401


def test_list_coins_requires_auth():
    response = client.get("/coins")
    assert response.status_code == 401


def test_list_coins_ok():
    token = get_token()
    response = client.get(
        "/coins?page_num=1&per_page=1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["page_num"] == 1
    assert data["per_page"] == 1
    assert data["total_items"] == 2
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == "bitcoin"


def test_list_categories_ok():
    token = get_token()
    response = client.get(
        "/categories",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_items"] == 2
    assert data["items"][0]["category_id"] == "layer-1"


def test_markets_requires_params():
    token = get_token()
    response = client.get(
        "/markets",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400


def test_markets_with_ids_ok():
    token = get_token()
    response = client.get(
        "/markets?coin_ids=bitcoin",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_items"] == 1
    item = data["items"][0]
    assert item["id"] == "bitcoin"
    assert item["inr"]["price"] == 100.0
    assert item["cad"]["price"] == 2.0
