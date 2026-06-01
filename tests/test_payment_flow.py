"""Payment flow integration tests.

Each test registers a fresh user to get a real API key, ensuring isolation.
"""

import pytest
from fastapi.testclient import TestClient

AUTH_HEADER = "X-OneAPI-Key"


@pytest.fixture(scope="session")
def client(isolated_user_store):
    """TestClient created after the user store is patched to a temp path."""
    from app.main import create_app
    return TestClient(create_app())


def _register(client: TestClient, email: str, password: str = "test1234") -> str:
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["api_key"]


def test_missing_token_returns_402_challenge(client):
    resp = client.post("/v1/enrich", json={"domain": "acme.io"})
    assert resp.status_code == 402
    assert resp.headers["X-Payment-Required"] == "true"
    assert resp.headers["X-Price"] == "10"
    body = resp.json()
    assert body["endpoint"] == "/v1/enrich"
    assert body["cost"] == 10


def test_unknown_token_returns_401(client):
    resp = client.post(
        "/v1/scrape",
        json={"url": "https://example.com"},
        headers={AUTH_HEADER: "sk-notavalidkey"},
    )
    assert resp.status_code == 401


def test_funded_token_succeeds_with_billing_envelope(client):
    key = _register(client, "funded1@test.example")
    resp = client.post(
        "/v1/scrape",
        json={"url": "https://acme.io"},
        headers={AUTH_HEADER: key},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "scrapegraph"
    assert body["billing"]["amount_deducted"] == 5
    assert body["billing"]["remaining_credits"] == 95  # 100 - 5


def test_distinct_providers_and_costs(client):
    key = _register(client, "funded2@test.example")
    resp = client.post(
        "/v1/scrape",
        json={"url": "https://acme.io"},
        headers={AUTH_HEADER: key},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["billing"]["amount_deducted"] == 5
    assert body["billing"]["remaining_credits"] == 95


def test_drained_balance_returns_402(client):
    key = _register(client, "drain@test.example")
    for _ in range(20):
        ok = client.post(
            "/v1/scrape",
            json={"url": "https://example.com"},
            headers={AUTH_HEADER: key},
        )
        assert ok.status_code == 200
    broke = client.post(
        "/v1/scrape",
        json={"url": "https://example.com"},
        headers={AUTH_HEADER: key},
    )
    assert broke.status_code == 402
    assert broke.json()["balance"] == 0


def test_topup_increases_balance(client):
    key = _register(client, "topup@test.example")
    resp = client.post(
        "/api/v1/wallet/topup",
        json={"amount": 50},
        headers={AUTH_HEADER: key},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["amount_added"] == 50
    assert body["new_balance"] == 150


def test_wallet_activity_requires_valid_key(client):
    resp = client.get(
        "/api/v1/wallet/activity",
        headers={AUTH_HEADER: "sk-invalid"},
    )
    assert resp.status_code == 401


def test_duplicate_email_rejected(client):
    _register(client, "dup@test.example")
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "dup@test.example", "password": "test1234"},
    )
    assert resp.status_code == 409
