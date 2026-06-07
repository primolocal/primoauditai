"""Tests for SQLAlchemy models."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.models import AuditRun, Base, Document, Finding, Photo


@pytest.fixture
def db_session():
    """Create an in-memory SQLite session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)  # noqa: N806
    session = SessionLocal()
    yield session
    session.close()


class TestAuditRun:
    def test_create_audit_run(self, db_session) -> None:
        run = AuditRun(claim_number="CLM-12345", vin="1HGCM82633A123456")
        db_session.add(run)
        db_session.commit()
        assert run.id is not None
        assert run.claim_number == "CLM-12345"
        assert run.status == "pending"
        assert run.findings_count == 0

    def test_audit_run_with_totals(self, db_session) -> None:
        run = AuditRun(
            total_estimate=12500.50,
            total_labor=45.5,
            total_parts=8200.00,
            findings_count=12,
            passed_count=3,
            failed_count=9,
        )
        db_session.add(run)
        db_session.commit()
        assert run.total_estimate == 12500.50
        assert run.total_labor == 45.5
        assert run.total_parts == 8200.00


class TestFinding:
    def test_create_finding(self, db_session) -> None:
        run = AuditRun(claim_number="CLM-12345")
        db_session.add(run)
        db_session.commit()

        finding = Finding(
            audit_run_id=run.id,
            rule_id="AUDIT_001",
            category="AUDIT",
            severity="HIGH",
            description="Labor rate above threshold",
            line_numbers=[42, 43],
            confidence=0.95,
            applies=True,
        )
        db_session.add(finding)
        db_session.commit()

        assert finding.id is not None
        assert finding.rule_id == "AUDIT_001"
        assert finding.severity == "HIGH"
        assert finding.line_numbers == [42, 43]
        assert finding.confidence == 0.95
        assert finding.applies is True
        assert finding.audit_run_id == run.id

    def test_finding_override(self, db_session) -> None:
        run = AuditRun(claim_number="CLM-12345")
        db_session.add(run)
        db_session.commit()

        finding = Finding(
            audit_run_id=run.id,
            rule_id="NATGEN_014",
            category="NATGEN",
            severity="HIGH",
            description="Flex additive present",
            applies=False,
            override_reason="Auditor verified — not present in this estimate",
        )
        db_session.add(finding)
        db_session.commit()
        assert finding.applies is False
        assert finding.override_reason == "Auditor verified — not present in this estimate"


class TestDocument:
    def test_create_document(self, db_session) -> None:
        run = AuditRun(claim_number="CLM-12345")
        db_session.add(run)
        db_session.commit()

        doc = Document(
            audit_run_id=run.id,
            filename="estimate.pdf",
            file_type="application/pdf",
            file_size=245000,
            content_hash="a1b2c3d4e5f6",
            extracted_text="Line 1: Replace fender...",
        )
        db_session.add(doc)
        db_session.commit()

        assert doc.filename == "estimate.pdf"
        assert doc.file_size == 245000
        assert doc.content_hash == "a1b2c3d4e5f6"


class TestPhoto:
    def test_create_photo(self, db_session) -> None:
        run = AuditRun(claim_number="CLM-12345")
        db_session.add(run)
        db_session.commit()

        photo = Photo(
            audit_run_id=run.id,
            filename="photo_001.jpg",
            data_url="data:image/jpeg;base64,/9j/4AAQ...",
            tags=["fender", "damage"],
            vision_result={"has_damage": True, "confidence": 0.88},
        )
        db_session.add(photo)
        db_session.commit()

        assert photo.filename == "photo_001.jpg"
        assert photo.tags == ["fender", "damage"]
        assert photo.vision_result is not None
        assert photo.vision_result["has_damage"] is True


class TestRelationships:
    def test_audit_run_with_findings(self, db_session) -> None:
        run = AuditRun(claim_number="CLM-12345")
        db_session.add(run)
        db_session.commit()

        for i in range(3):
            f = Finding(
                audit_run_id=run.id,
                rule_id=f"RULE_{i:03d}",
                category="AUDIT",
                severity="HIGH",
                description=f"Finding {i}",
            )
            db_session.add(f)
        db_session.commit()

        run = db_session.query(AuditRun).filter_by(claim_number="CLM-12345").first()
        assert len(run.findings) == 3
