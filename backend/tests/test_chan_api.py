"""Integration tests for the /api/chan/analysis endpoint."""
import pytest


def test_chan_analysis_returns_success(client):
    params = {
        "code": "000001",
        "market": "sz",
        "start_date": "2024-01-01",
        "end_date": "2024-06-30",
    }
    response = client.get("/api/chan/analysis", params=params)
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["message"] == "Success"


def test_chan_analysis_response_structure(client):
    params = {
        "code": "600519",
        "market": "sh",
        "start_date": "2024-01-01",
        "end_date": "2024-06-30",
    }
    response = client.get("/api/chan/analysis", params=params)
    assert response.status_code == 200
    data = response.json()["data"]

    assert "code" in data
    assert "market" in data
    assert "period" in data
    assert "klines" in data
    assert "chan" in data

    chan = data["chan"]
    assert "fractals" in chan
    assert "pens" in chan
    assert "segments" in chan
    assert "zhongshus" in chan

    assert isinstance(chan["fractals"], list)
    assert isinstance(chan["pens"], list)
    assert isinstance(chan["segments"], list)
    assert isinstance(chan["zhongshus"], list)


def test_chan_analysis_fractal_fields(client):
    params = {
        "code": "000001",
        "market": "sz",
        "start_date": "2024-01-01",
        "end_date": "2024-06-30",
    }
    response = client.get("/api/chan/analysis", params=params)
    assert response.status_code == 200
    fractals = response.json()["data"]["chan"]["fractals"]
    for f in fractals:
        assert "index" in f
        assert "date" in f
        assert "price" in f
        assert f["type"] in ("top", "bottom")


def test_chan_analysis_pen_fields(client):
    params = {
        "code": "000001",
        "market": "sz",
        "start_date": "2024-01-01",
        "end_date": "2024-06-30",
    }
    response = client.get("/api/chan/analysis", params=params)
    assert response.status_code == 200
    pens = response.json()["data"]["chan"]["pens"]
    for pen in pens:
        assert "start_index" in pen
        assert "end_index" in pen
        assert "start_date" in pen
        assert "end_date" in pen
        assert "start_price" in pen
        assert "end_price" in pen
        assert pen["direction"] in ("up", "down")


def test_chan_analysis_without_inclusion_processing(client):
    params = {
        "code": "000001",
        "market": "sz",
        "process_include": "false",
        "start_date": "2024-01-01",
        "end_date": "2024-06-30",
    }
    response = client.get("/api/chan/analysis", params=params)
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert "chan" in body["data"]


def test_chan_analysis_missing_code_returns_validation_error(client):
    response = client.get("/api/chan/analysis")
    assert response.status_code == 422


def test_chan_analysis_default_period_is_daily(client):
    params = {
        "code": "000001",
        "start_date": "2024-01-01",
        "end_date": "2024-03-31",
    }
    response = client.get("/api/chan/analysis", params=params)
    assert response.status_code == 200
    assert response.json()["data"]["period"] == "D"
