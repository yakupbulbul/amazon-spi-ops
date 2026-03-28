from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_login_rejects_invalid_credentials() -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": "missing@example.com", "password": "incorrect-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"
