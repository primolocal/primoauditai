"""
Pydantic v2 schemas for API request/response validation.
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# --- Shared base ---

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# --- Audit schemas ---

class AuditCreate(BaseSchema):
    claim_number: str | None = None
    vin: str | None = None
    vehicle_year: int | None = None
    vehicle_make: str | None = None
    vehicle_model: str | None = None
    odometer: int | None = None
    insurance_company: str | None = None
    shop_name: str | None = None
    shop_address: str | None = None
    document_type: str | None = None
    loss_description: str | None = None


class AuditResponse(BaseSchema):
    id: UUID
    claim_number: str | None = None
    vin: str | None = None
    vehicle_year: int | None = None
    vehicle_make: str | None = None
    vehicle_model: str | None = None
    odometer: int | None = None
    insurance_company: str | None = None
    shop_name: str | None = None
    shop_address: str | None = None
    document_type: str | None = None
    loss_description: str | None = None
    status: str
    total_estimate: float | None = None
    total_labor: float | None = None
    total_parts: float | None = None
    findings_count: int
    passed_count: int
    failed_count: int
    parsed_lines: list[dict[str, Any]] | None = None
    parsed_panels: dict[str, list[dict[str, Any]]] | None = None
    parsed_metadata: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class AuditListResponse(BaseSchema):
    items: list[AuditResponse]
    total: int
    page: int
    page_size: int


# --- Finding schemas ---

class FindingResponse(BaseSchema):
    id: UUID
    rule_id: str
    category: str
    severity: str
    description: str
    line_numbers: list[int] = []
    confidence: float = 1.0
    applies: bool = True
    override_reason: str | None = None
    status: str = "unreviewed"
    created_at: datetime


class FindingUpdate(BaseSchema):
    status: str | None = None
    override_reason: str | None = None
    applies: bool | None = None


# --- Document schemas ---

class DocumentResponse(BaseSchema):
    id: UUID
    filename: str
    file_type: str
    file_size: int
    content_hash: str
    extracted_text: str | None = None
    created_at: datetime


class DocumentUpload(BaseSchema):
    filename: str
    file_type: str
    file_size: int


# --- Photo schemas ---

class PhotoResponse(BaseSchema):
    id: UUID
    filename: str
    data_url: str | None = None
    tags: list[str] = []
    vision_result: dict[str, Any] | None = None
    created_at: datetime


class PhotoExtractResponse(BaseSchema):
    photos: list[dict[str, Any]]
    count: int


# --- QC schemas ---

class QCRequest(BaseSchema):
    # Accepts multipart upload — no body fields
    pass


class QCResponse(BaseSchema):
    findings: list[FindingResponse]
    passed: list[dict[str, Any]]
    analytics: dict[str, Any]
    processed_at: datetime


# --- Error schemas ---

class ErrorResponse(BaseSchema):
    detail: str
    error_code: str | None = None
