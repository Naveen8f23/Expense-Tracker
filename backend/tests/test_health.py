from fastapi.testclient import TestClient

from app.presentation.main import app

client = TestClient(app)


def test_health_returns_200_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_allows_cross_origin_requests_from_the_dashboard():
    # The dashboard runs on a different dev port (Vite), so this is a cross-origin request
    # from the browser's point of view — must not be silently blocked (see session notes:
    # this exact gap caused a real "Failed to fetch" in the browser during A3 verification).
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
