"""
SQLAlchemy 2.0 async models for PrimoAuditAI v2.
All tables use UUID primary keys, JSONB for structured data.
"""
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Async declarative base."""
    pass


def now_utc() -> datetime:
    return datetime.now(UTC)


class AuditRun(Base):
    """A single audit execution — the parent record for all findings, docs, photos."""
    __tablename__ = "audit_runs"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    vin: Mapped[str | None] = mapped_column(String(50), nullable=True)
    vehicle_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vehicle_make: Mapped[str | None] = mapped_column(String(100), nullable=True)
    vehicle_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    odometer: Mapped[int | None] = mapped_column(Integer, nullable=True)
    insurance_company: Mapped[str | None] = mapped_column(String(200), nullable=True)
    shop_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    shop_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    loss_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="pending")
    total_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_labor: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_parts: Mapped[float | None] = mapped_column(Float, nullable=True)
    findings_count: Mapped[int] = mapped_column(Integer, default=0)
    passed_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    # Relationships
    findings: Mapped[list["Finding"]] = relationship(back_populates="audit_run", cascade="all, delete-orphan")
    documents: Mapped[list["Document"]] = relationship(back_populates="audit_run", cascade="all, delete-orphan")
    photos: Mapped[list["Photo"]] = relationship(back_populates="audit_run", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<AuditRun {self.id} claim={self.claim_number} status={self.status}>"


class Finding(Base):
    """A single rule finding from the rules engine."""
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_run_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("audit_runs.id", ondelete="CASCADE"))

    rule_id: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    line_numbers: Mapped[list[int]] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    applies: Mapped[bool] = mapped_column(Boolean, default=True)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="unreviewed")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    # Relationship
    audit_run: Mapped["AuditRun"] = relationship(back_populates="findings")

    def __repr__(self) -> str:
        return f"<Finding {self.rule_id} {self.severity} lines={self.line_numbers}>"


class Document(Base):
    """An uploaded document (estimate PDF, supporting file)."""
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_run_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("audit_runs.id", ondelete="CASCADE"))

    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    # Relationship
    audit_run: Mapped["AuditRun"] = relationship(back_populates="documents")

    def __repr__(self) -> str:
        return f"<Document {self.filename} {self.file_type}>"


class Photo(Base):
    """An extracted or uploaded photo with optional vision analysis."""
    __tablename__ = "photos"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_run_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("audit_runs.id", ondelete="CASCADE"))

    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    data_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    vision_result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    # Relationship
    audit_run: Mapped["AuditRun"] = relationship(back_populates="photos")

    def __repr__(self) -> str:
        return f"<Photo {self.filename} tags={len(self.tags)}>"
