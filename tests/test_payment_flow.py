from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_missing_token_returns_402_challenge():
    resp = client.post("/v1/enrich", json={"domain": "acme.io"})
    assert resp.status_code == 402
    assert resp.headers["X-Payment-Required"] == "true"
    assert resp.headers["X-Price"] == "10"
    body = resp.json()
    assert body["endpoint"] == "/v1/enrich"
    assert body["cost"] == 10


def test_funded_token_succeeds_with_billing_envelope():
    resp = client.post(
        "/v1/enrich",
        json={"domain": "acme.io"},
        headers={"X-Payment-Token": "funded-1"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "apollo"
    assert body["data"]["domain"] == "acme.io"
    assert body["billing"]["amount_deducted"] == 10
    assert body["billing"]["remaining_credits"] == 90  # 100 default - 10


def test_distinct_providers_and_costs():
    resp = client.post(
        "/v1/scrape",
        json={"url": "https://acme.io"},
        headers={"X-Payment-Token": "funded-2"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "scrapegraph"
    assert body["data"]["url"] == "https://acme.io"
    assert body["billing"]["amount_deducted"] == 5
    assert body["billing"]["remaining_credits"] == 95  # 100 default - 5


def test_drained_balance_returns_402():
    token = "drainme"
    # Default balance 100, enrich costs 10 -> 10 succeed, 11th is rejected.
    for _ in range(10):
        ok = client.post("/v1/enrich", json={}, headers={"X-Payment-Token": token})
        assert ok.status_code == 200
    broke = client.post("/v1/enrich", json={}, headers={"X-Payment-Token": token})
    assert broke.status_code == 402
    assert broke.json()["balance"] == 0
