"""Tests for FastAPI app factory and middleware."""
import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestHealth:
    def test_health_check(self, client) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestMiddleware:
    def test_request_id_header(self, client) -> None:
        response = client.get("/health")
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) == 8

    def test_cors_headers(self, client) -> None:
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )
        assert "access-control-allow-origin" in response.headers

    def test_openapi_without_key(self, client) -> None:
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert "openapi" in response.json()

    def test_docs_without_key(self, client) -> None:
        response = client.get("/docs")
        assert response.status_code == 200

    def test_qc_without_key(self, client) -> None:
        response = client.post("/api/qc")
        assert response.status_code == 400  # no file, but not 401

    def test_audits_require_key(self, client) -> None:
        response = client.get("/api/audits")
        assert response.status_code == 401

    def test_audits_with_valid_key(self, client) -> None:
        response = client.get(
            "/api/audits",
            headers={"X-API-Key": "pa_dev_key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
