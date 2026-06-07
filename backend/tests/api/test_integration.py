"""
Integration tests for wired audit endpoint with real file parsing.
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


# Default API key for test requests
TEST_API_KEY = "pa_dev_key"


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


class TestAuditCreate:
    def test_create_audit_with_pdf(self, client) -> None:
        """POST /api/audits with PDF — parsed, persisted, findings generated."""
        pdf_bytes = _make_test_pdf()
        response = client.post(
            "/api/audits",
            files={"estimate_pdf": ("test_estimate.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            headers={"X-API-Key": TEST_API_KEY},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["claim_number"] == "TEST-12345"
        assert data["vin"] == "1HGCM82633A123456"
        assert data["document_type"] == "pdf_estimate"
        assert data["status"] == "completed"
        assert data["parsed_lines"] is not None
        assert len(data["parsed_lines"]) > 0
        assert data["parsed_metadata"] is not None
        assert data["parsed_metadata"]["claim_number"] == "TEST-12345"

    def test_create_audit_with_pdf_and_form_override(self, client) -> None:
        """Form fields override parsed metadata."""
        pdf_bytes = _make_test_pdf()
        response = client.post(
            "/api/audits",
            files={"estimate_pdf": ("test_estimate.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            data={
                "claim_number": "OVERRIDE-999",
                "vehicle_year": "2025",
                "vehicle_make": "FORD",
            },
            headers={"X-API-Key": TEST_API_KEY},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["claim_number"] == "OVERRIDE-999"
        assert data["vehicle_year"] == 2025
        assert data["vehicle_make"] == "FORD"
        # VIN comes from PDF since not overridden
        assert data["vin"] == "1HGCM82633A123456"

    def test_create_audit_no_file(self, client) -> None:
        """No file returns 400."""
        response = client.post(
            "/api/audits",
            headers={"X-API-Key": TEST_API_KEY},
        )
        assert response.status_code == 400
        assert "No file uploaded" in response.json()["detail"]

    def test_create_audit_with_real_pdf(self, client) -> None:
        """Parse the real TestEstimate.pdf and verify full pipeline."""
        with open("tests/testfiles/TestEstimate.pdf", "rb") as f:
            pdf_bytes = f.read()
        response = client.post(
            "/api/audits",
            files={"estimate_pdf": ("TestEstimate.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            headers={"X-API-Key": TEST_API_KEY},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["claim_number"] == "260479295-1"
        assert data["vin"] == "5TFKB5DB1TX376956"
        assert data["vehicle_year"] == 2026
        assert data["vehicle_make"] == "TOYO"
        assert data["document_type"] == "pdf_estimate"
        assert data["status"] == "completed"
        assert data["total_estimate"] > 0
        assert data["total_labor"] > 0
        assert data["parsed_lines"] is not None
        assert len(data["parsed_lines"]) > 0
        assert data["parsed_panels"] is not None
        assert "FRONT BUMPER" in data["parsed_panels"]
        assert data["findings_count"] >= 0
        assert data["passed_count"] >= 0


class TestAuditListGet:
    def test_list_audits(self, client) -> None:
        """GET /api/audits returns paginated list."""
        response = client.get(
            "/api/audits",
            headers={"X-API-Key": TEST_API_KEY},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    def test_get_audit_not_found(self, client) -> None:
        """GET /api/audits/{id} with bad ID returns 404."""
        response = client.get(
            "/api/audits/00000000-0000-0000-0000-000000000000",
            headers={"X-API-Key": TEST_API_KEY},
        )
        assert response.status_code == 404


class TestAuditFindings:
    def test_get_audit_findings(self, client) -> None:
        """Create audit then fetch its findings."""
        # Create audit first
        pdf_bytes = _make_test_pdf()
        create_resp = client.post(
            "/api/audits",
            files={"estimate_pdf": ("test_estimate.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            headers={"X-API-Key": TEST_API_KEY},
        )
        assert create_resp.status_code == 201
        audit_id = create_resp.json()["id"]

        # Fetch findings
        response = client.get(
            f"/api/audits/{audit_id}/findings",
            headers={"X-API-Key": TEST_API_KEY},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_audit_with_findings_count(self, client) -> None:
        """Create audit with real PDF and verify findings generated."""
        with open("tests/testfiles/TestEstimate.pdf", "rb") as f:
            pdf_bytes = f.read()
        create_resp = client.post(
            "/api/audits",
            files={"estimate_pdf": ("TestEstimate.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            headers={"X-API-Key": TEST_API_KEY},
        )
        assert create_resp.status_code == 201
        audit = create_resp.json()

        response = client.get(
            f"/api/audits/{audit['id']}/findings",
            headers={"X-API-Key": TEST_API_KEY},
        )
        assert response.status_code == 200
        findings = response.json()
        assert isinstance(findings, list)
        assert len(findings) == audit["findings_count"]


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
