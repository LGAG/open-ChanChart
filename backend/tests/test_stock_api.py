"""Integration tests for the /api/stock endpoints."""
import pytest


# ---------------------------------------------------------------------------
# /api/stock/search
# ---------------------------------------------------------------------------

def test_search_by_name_returns_matching_stocks(client):
    response = client.get("/api/stock/search", params={"keyword": "平安"})
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert isinstance(body["data"], list)
    assert any("平安" in s["name"] for s in body["data"])


def test_search_by_code_returns_matching_stocks(client):
    response = client.get("/api/stock/search", params={"keyword": "000001"})
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert any(s["code"] == "000001" for s in body["data"])


def test_search_with_market_filter_returns_only_that_market(client):
    response = client.get("/api/stock/search", params={"keyword": "银行", "market": "sh"})
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert isinstance(body["data"], list)
    assert len(body["data"]) > 0
    for stock in body["data"]:
        assert stock["market"] == "sh"


def test_search_no_results_returns_empty_list(client):
    response = client.get("/api/stock/search", params={"keyword": "XYZNONEXISTENT"})
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"] == []


def test_search_missing_keyword_returns_validation_error(client):
    response = client.get("/api/stock/search")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# /api/stock/kline
# ---------------------------------------------------------------------------

def test_kline_returns_data_structure(client):
    response = client.get("/api/stock/kline", params={"code": "000001", "market": "sz"})
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    data = body["data"]
    assert data["code"] == "000001"
    assert data["market"] == "sz"
    assert "klines" in data
    assert isinstance(data["klines"], list)
    assert len(data["klines"]) > 0


def test_kline_entry_has_required_fields(client):
    response = client.get("/api/stock/kline", params={"code": "600519", "market": "sh"})
    assert response.status_code == 200
    klines = response.json()["data"]["klines"]
    assert len(klines) > 0
    for entry in klines:
        assert "date" in entry
        assert "open" in entry
        assert "high" in entry
        assert "low" in entry
        assert "close" in entry
        assert "volume" in entry


def test_kline_with_date_range_respects_boundaries(client):
    params = {
        "code": "000001",
        "market": "sz",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
    }
    response = client.get("/api/stock/kline", params=params)
    assert response.status_code == 200
    klines = response.json()["data"]["klines"]
    for k in klines:
        assert k["date"] >= "2024-01-01"
        assert k["date"] <= "2024-01-31"


def test_kline_period_is_reflected_in_response(client):
    response = client.get("/api/stock/kline", params={"code": "000001", "period": "30F"})
    assert response.status_code == 200
    assert response.json()["data"]["period"] == "30F"


def test_kline_missing_code_returns_validation_error(client):
    response = client.get("/api/stock/kline")
    assert response.status_code == 422
