from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_health_endpoint() -> None:
    app = create_app(
        Settings(
            app_name="Test API",
            app_env="test",
            app_version="0.0.0-test",
            cors_origins=["http://localhost:5173"],
        ),
    )
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "environment": "test",
        "service": "Test API",
        "status": "ok",
        "version": "0.0.0-test",
    }
