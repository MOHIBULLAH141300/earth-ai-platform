from fastapi.testclient import TestClient

from api.main_api import app


client = TestClient(app)


def test_root_endpoint():
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "EarthAI Platform"
    assert "endpoints" in body


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"


def test_models_endpoint():
    resp = client.get("/api/v1/models")
    assert resp.status_code == 200
    body = resp.json()
    assert "models" in body
    assert "count" in body
