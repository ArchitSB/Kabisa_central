from app.main import app
from fastapi.testclient import TestClient


def test_liveness() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "kabisa-api",
        "environment": "development",
    }
