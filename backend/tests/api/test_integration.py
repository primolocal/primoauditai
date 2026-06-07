"""
Integration tests for API routes with file parsing.
"""
import io

import fitz
import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def _make_test_pdf() -> bytes:
    """Generate a minimal synthetic PDF estimate for testing."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Claim Number: TEST-12345")
    page.insert_text((50, 70), "VIN: 1HGCM82633A123456")
    page.insert_text((50, 90), "1")
    page.insert_text((100, 90), "Repl")
    page.insert_text((150, 90), "Replace fender")
    page.insert_text((50, 110), "2")
    page.insert_text((100, 110), "Blend")
    page.insert_text((150, 110), "Blend door")
    page.insert_text((250, 110), "1")
    page.insert_text((300, 110), "0")
    page.insert_text((350, 110), "1.0")
    page.insert_text((50, 130), "FENDER")
    page.insert_text((50, 150), "DOOR")
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


class TestQCIntegration:
    def test_qc_with_pdf(self, client) -> None:
        """Upload a PDF and get real findings back."""
        pdf_bytes = _make_test_pdf()
        response = client.post(
            "/api/qc",
            files={"estimate_pdf": ("test_estimate.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "findings" in data
        assert "passed" in data
        assert "analytics" in data
        assert data["analytics"]["lines_parsed"] == 2

    def test_qc_no_file(self, client) -> None:
        response = client.post("/api/qc")
        assert response.status_code == 400

    def test_extract_photos_empty_pdf(self, client) -> None:
        """Extract photos from PDF with no embedded images."""
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "No photos here")
        buf = io.BytesIO()
        doc.save(buf)
        doc.close()

        response = client.post(
            "/api/extract-photos",
            files={"photos": ("empty.pdf", io.BytesIO(buf.getvalue()), "application/pdf")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["photos"] == []
