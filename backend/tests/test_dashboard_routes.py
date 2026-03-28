from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_dashboard_summary_requires_authentication() -> None:
    response = client.get("/api/dashboard/summary")

    assert response.status_code == 401


def test_dashboard_summary_returns_metrics_for_authenticated_user() -> None:
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "change-me-admin"},
    )
    token = login.json()["access_token"]

    response = client.get(
        "/api/dashboard/summary",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["metrics"]) == 4
    assert "recent_activity" in body
    assert "inventory_alerts" in body
    assert "slack_delivery" in body
