"""Tests for the root and health-check endpoints in app.main."""


def test_root_returns_welcome_message(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Welcome to ChanChart API"
    assert body["version"] == "1.0.0"
    assert "docs" in body


def test_health_check_returns_healthy(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
