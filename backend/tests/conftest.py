"""Shared pytest fixtures for the backend test suite."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.stock_model import KlineData


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient shared across a test module."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_klines():
    """A minimal list of KlineData objects useful for unit tests."""
    return [
        KlineData(date="2024-01-01", open=100.0, high=105.0, low=98.0, close=103.0, volume=10000),
        KlineData(date="2024-01-02", open=103.0, high=108.0, low=101.0, close=106.0, volume=12000),
        KlineData(date="2024-01-03", open=106.0, high=110.0, low=104.0, close=109.0, volume=11000),
        KlineData(date="2024-01-04", open=109.0, high=112.0, low=106.0, close=108.0, volume=9000),
        KlineData(date="2024-01-05", open=108.0, high=109.0, low=103.0, close=104.0, volume=8000),
        KlineData(date="2024-01-06", open=104.0, high=105.0, low=99.0, close=100.0, volume=7500),
        KlineData(date="2024-01-07", open=100.0, high=101.0, low=95.0, close=97.0, volume=8500),
        KlineData(date="2024-01-08", open=97.0, high=98.0, low=93.0, close=96.0, volume=9000),
        KlineData(date="2024-01-09", open=96.0, high=100.0, low=94.0, close=99.0, volume=10500),
        KlineData(date="2024-01-10", open=99.0, high=104.0, low=97.0, close=103.0, volume=11000),
    ]
