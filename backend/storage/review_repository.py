import os
from typing import Optional, Dict

class ReviewRepository:
    """Abstract interface to prepare the backend for a formalized SQLite migration."""
    
    def get_review_state(self, audit_id: str) -> dict:
        raise NotImplementedError

    def set_finding_review(self, audit_id: str, finding_id: str, note: Optional[str], health_status: Optional[str], health_explanation: Optional[str], evidence_exists: Optional[str] = None, evidence_uploaded: Optional[str] = None, linked_asset_ids: Optional[list] = None, missing_upload_reason: Optional[str] = None, hermes_critique: Optional[str] = None, auditor_outcome: Optional[str] = None, auditor_reason_code: Optional[str] = None, guideline_citation: Optional[str] = None) -> dict:
        raise NotImplementedError

    def set_asset_verdict(self, audit_id: str, state_key: str, verdict: Optional[str]) -> dict:
        raise NotImplementedError

class MockReviewRepository(ReviewRepository):
    """In-memory dictionary MVP implementation of the ReviewRepository."""

    def __init__(self):
        self.store = {}
    
    def _ensure_audit(self, audit_id: str) -> dict:
        if audit_id not in self.store:
            self.store[audit_id] = {
                "asset_verdicts": {},
                "reviewer_notes": {},
                "finding_health": {},
                "claim_readiness": "Not Evaluated"
            }
        return self.store[audit_id]

    def get_review_state(self, audit_id: str) -> dict:
        return self._ensure_audit(audit_id)

    def set_finding_review(self, audit_id: str, finding_id: str, note: Optional[str], health_status: Optional[str], health_explanation: Optional[str], evidence_exists: Optional[str] = None, evidence_uploaded: Optional[str] = None, linked_asset_ids: Optional[list] = None, missing_upload_reason: Optional[str] = None, hermes_critique: Optional[str] = None, auditor_outcome: Optional[str] = None, auditor_reason_code: Optional[str] = None, guideline_citation: Optional[str] = None) -> dict:
        state = self._ensure_audit(audit_id)
        
        # Strict validation rule for reviewer notes
        if note is not None:
            trimmed_note = note.strip()
            if len(trimmed_note) > 0:
                state["reviewer_notes"][finding_id] = trimmed_note
            else:
                state["reviewer_notes"].pop(finding_id, None)
                
        if health_status:
            state["finding_health"][finding_id] = {
                "status": health_status,
                "explanation": health_explanation
            }
            
        self._recompute_readiness(audit_id)
        return state["reviewer_notes"]

    def set_asset_verdict(self, audit_id: str, state_key: str, verdict: Optional[str]) -> dict:
        state = self._ensure_audit(audit_id)
        
        if verdict:
            state["asset_verdicts"][state_key] = verdict
        else:
            state["asset_verdicts"].pop(state_key, None)
            
        self._recompute_readiness(audit_id)
        return state["asset_verdicts"]

    def _recompute_readiness(self, audit_id: str):
        state = self._ensure_audit(audit_id)
        health_dict = state.get("finding_health", {})
        notes_dict = state.get("reviewer_notes", {})

        has_error = False
        has_risk = False

        for fid, health in health_dict.items():
            status = health.get("status")
            is_unresolved = (status == "Reviewer Overrode System" and fid not in notes_dict)

            if status in ["Missing Required Evidence", "Invalid Support"] or is_unresolved:
                has_error = True
            elif status == "Weak Support" or (status == "Reviewer Overrode System" and not is_unresolved):
                has_risk = True

        if has_error:
            state["claim_readiness"] = "Not Ready"
        elif has_risk:
            state["claim_readiness"] = "Risky"
        else:
            state["claim_readiness"] = "Ready"

from database.database import SessionLocal
from database.models import AuditRun, FindingReview, AssetVerdict
import json

class SQLReviewRepository(ReviewRepository):
    """SQLite implementation mapping mutations logically via SQLAlchemy ORM."""
    
    def _ensure_audit_run(self, session, audit_id: str) -> AuditRun:
        run = session.query(AuditRun).filter_by(audit_id=audit_id).first()
        if not run:
            run = AuditRun(audit_id=audit_id, claim_readiness="Not Evaluated")
            session.add(run)
            session.flush()
        return run

    def save_audit_run(self, audit_id: str, summary_json: dict) -> AuditRun:
        with SessionLocal() as session:
            run = self._ensure_audit_run(session, audit_id)
            run.summary_json = summary_json
            session.commit()
            session.refresh(run)
            return run

    def get_audit_run(self, audit_id: str) -> dict:
        with SessionLocal() as session:
            run = session.query(AuditRun).filter_by(audit_id=audit_id).first()
            if run and run.summary_json:
                return run.summary_json
            return None

    def create_job(self, job_id: str, audit_id: str = None) -> dict:
        from database.models import ProcessingJob
        with SessionLocal() as session:
            job = ProcessingJob(job_id=job_id, audit_id=audit_id)
            session.add(job)
            session.commit()
            return {"job_id": job.job_id, "status": job.status, "progress": job.progress_percentage}

    def update_job(self, job_id: str, status: str, progress: int, audit_id: str = None, message: str = None) -> dict:
        from database.models import ProcessingJob
        with SessionLocal() as session:
            job = session.query(ProcessingJob).filter_by(job_id=job_id).first()
            if job:
                job.status = status
                job.progress_percentage = progress
                if audit_id:
                    job.audit_id = audit_id
                if message:
                    job.message = message
                session.commit()
                return {"job_id": job.job_id, "status": job.status, "progress": job.progress_percentage, "message": job.message}
            return None

    def get_job_status(self, job_id: str) -> dict:
        from database.models import ProcessingJob
        with SessionLocal() as session:
            job = session.query(ProcessingJob).filter_by(job_id=job_id).first()
            if job:
                return {"job_id": job.job_id, "status": job.status, "progress": job.progress_percentage, "audit_id": job.audit_id, "message": job.message}
            return None

    def save_claim_record(self, claim_number: str, carrier: Optional[str] = None, loss_date: Optional[str] = None):
        from database.models import ClaimRecord
        from datetime import datetime
        parsed_date = None
        if loss_date:
            try:
                # Basic string format fallback if it is ISO
                clean_date = loss_date.replace("Z", "+00:00")
                parsed_date = datetime.fromisoformat(clean_date)
            except Exception:
                pass
                
        with SessionLocal() as session:
            record = session.query(ClaimRecord).filter_by(claim_number=claim_number).first()
            if not record:
                record = ClaimRecord(claim_number=claim_number, carrier=carrier, loss_date=parsed_date)
                session.add(record)
            else:
                if carrier: record.carrier = carrier
                if parsed_date: record.loss_date = parsed_date
            session.commit()
            
    def link_audit_to_claim(self, claim_number: str, audit_id: str):
        from database.models import ClaimAuditRecord
        with SessionLocal() as session:
            link = session.query(ClaimAuditRecord).filter_by(audit_id=audit_id).first()
            if not link:
                link = ClaimAuditRecord(claim_number=claim_number, audit_id=audit_id)
                session.add(link)
                session.commit()

    def save_asset_record(self, audit_id: str, asset_id: str, role: str, storage_key: str, original_filename: str, content_type: str, byte_size: int = None):
        from database.models import AssetRecordModel
        with SessionLocal() as session:
            record = session.query(AssetRecordModel).filter_by(asset_id=asset_id).first()
            if not record:
                record = AssetRecordModel(
                    audit_id=audit_id,
                    asset_id=asset_id,
                    role=role,
                    storage_key=storage_key,
                    original_filename=original_filename,
                    content_type=content_type,
                    byte_size=byte_size
                )
                session.add(record)
            else:
                record.role = role
                record.storage_key = storage_key
            session.commit()

    def get_asset_record(self, asset_id: str) -> dict:
        from database.models import AssetRecordModel
        with SessionLocal() as session:
            r = session.query(AssetRecordModel).filter_by(asset_id=asset_id).first()
            if r:
                return {
                    "audit_id": r.audit_id,
                    "asset_id": r.asset_id,
                    "role": r.role,
                    "storage_key": r.storage_key,
                    "original_filename": r.original_filename,
                    "content_type": r.content_type,
                    "byte_size": r.byte_size
                }
            return None

    def get_review_state(self, audit_id: str) -> dict:
        with SessionLocal() as session:
            run = self._ensure_audit_run(session, audit_id)
            readiness = run.claim_readiness
            
            reviews = session.query(FindingReview).filter_by(audit_id=audit_id).all()
            verdicts = session.query(AssetVerdict).filter_by(audit_id=audit_id).all()
            
            finding_health = {}
            reviewer_notes = {}
            finding_confirmations = {}
            for r in reviews:
                if r.health_status:
                    finding_health[r.finding_id] = {
                        "status": r.health_status,
                        "explanation": r.health_explanation
                    }
                if r.reviewer_note:
                    reviewer_notes[r.finding_id] = r.reviewer_note

                # Parse finding_confirmations
                if r.evidence_exists or r.evidence_uploaded or r.linked_asset_ids or r.missing_upload_reason or r.hermes_critique or r.auditor_outcome or r.recommendation_outcome:
                    finding_confirmations[r.finding_id] = {
                        "hermes_critique": r.hermes_critique,
                        "auditor_outcome": r.auditor_outcome,
                        "auditor_reason_code": r.auditor_reason_code,
                        "evidence_exists": r.evidence_exists,
                        "evidence_uploaded": r.evidence_uploaded,
                        "linked_asset_ids": json.loads(r.linked_asset_ids) if r.linked_asset_ids else [],
                        "missing_upload_reason": r.missing_upload_reason,
                        "recommendation_outcome": r.recommendation_outcome,
                        "recommendation_reason_code": r.recommendation_reason_code
                    }

            asset_verdicts = {}
            for v in verdicts:
                if v.auditor_verdict:
                    state_key = f"{v.finding_id}_{v.asset_id}"
                    asset_verdicts[state_key] = v.auditor_verdict

            return {
                "asset_verdicts": asset_verdicts,
                "reviewer_notes": reviewer_notes,
                "finding_health": finding_health,
                "finding_confirmations": finding_confirmations,
                "claim_readiness": readiness
            }

    def set_finding_review(self, audit_id: str, finding_id: str, note: Optional[str] = None, health_status: Optional[str] = None, health_explanation: Optional[str] = None, evidence_exists: Optional[str] = None, evidence_uploaded: Optional[str] = None, linked_asset_ids: Optional[list] = None, missing_upload_reason: Optional[str] = None, hermes_critique: Optional[str] = None, auditor_outcome: Optional[str] = None, auditor_reason_code: Optional[str] = None, guideline_citation: Optional[str] = None, suggested_action_type: Optional[str] = None, suggested_revision: Optional[dict] = None, requires_manual_confirmation: Optional[bool] = None, supporting_reason: Optional[str] = None, recommendation_outcome: Optional[str] = None, recommendation_reason_code: Optional[str] = None) -> dict:
        with SessionLocal() as session:
            self._ensure_audit_run(session, audit_id)
            review = session.query(FindingReview).filter_by(audit_id=audit_id, finding_id=finding_id).first()
            if not review:
                review = FindingReview(audit_id=audit_id, finding_id=finding_id)
                session.add(review)

            if note is not None:
                trimmed_note = (note or "").strip()
                review.reviewer_note = trimmed_note if len(trimmed_note) > 0 else None
            
            if health_status is not None:
                review.health_status = health_status
                review.health_explanation = health_explanation

            if evidence_exists is not None:
                review.evidence_exists = evidence_exists
            if evidence_uploaded is not None:
                review.evidence_uploaded = evidence_uploaded
            if linked_asset_ids is not None:
                review.linked_asset_ids = json.dumps(linked_asset_ids)
            if missing_upload_reason is not None:
                review.missing_upload_reason = missing_upload_reason
            if hermes_critique is not None:
                review.hermes_critique = hermes_critique
            if auditor_outcome is not None:
                review.auditor_outcome = auditor_outcome
            if auditor_reason_code is not None:
                review.auditor_reason_code = auditor_reason_code
            if guideline_citation is not None:
                review.guideline_citation = guideline_citation
            if suggested_action_type is not None:
                review.suggested_action_type = suggested_action_type
            if suggested_revision is not None:
                review.suggested_revision = suggested_revision
            if requires_manual_confirmation is not None:
                review.requires_manual_confirmation = requires_manual_confirmation    
            if supporting_reason is not None:
                review.supporting_reason = supporting_reason
            if recommendation_outcome is not None:
                review.recommendation_outcome = recommendation_outcome
            if recommendation_reason_code is not None:
                review.recommendation_reason_code = recommendation_reason_code

            session.flush()
            self._recompute_readiness(session, audit_id)
            session.commit()

            all_reviews = session.query(FindingReview).filter_by(audit_id=audit_id).all()
            return {r.finding_id: r.reviewer_note for r in all_reviews if r.reviewer_note}

    def set_asset_verdict(self, audit_id: str, state_key: str, verdict: Optional[str]) -> dict:
        with SessionLocal() as session:
            self._ensure_audit_run(session, audit_id)
            try:
                finding_id, asset_id = state_key.split('_', 1)
            except ValueError:
                finding_id = state_key
                asset_id = "unknown"

            asset = session.query(AssetVerdict).filter_by(audit_id=audit_id, finding_id=finding_id, asset_id=asset_id).first()
            if not asset:
                asset = AssetVerdict(audit_id=audit_id, finding_id=finding_id, asset_id=asset_id)
                session.add(asset)

            asset.auditor_verdict = verdict if verdict else None
            
            session.flush()
            self._recompute_readiness(session, audit_id)
            session.commit()

            all_verdicts = session.query(AssetVerdict).filter_by(audit_id=audit_id).all()
            return {f"{v.finding_id}_{v.asset_id}": v.auditor_verdict for v in all_verdicts if v.auditor_verdict}

    def _recompute_readiness(self, session, audit_id: str):
        run = session.query(AuditRun).filter_by(audit_id=audit_id).first()
        if not run: return
        
        reviews = session.query(FindingReview).filter_by(audit_id=audit_id).all()
        has_error = False
        has_risk = False

        for r in reviews:
            status = r.health_status
            is_unresolved = (status == "Reviewer Overrode System" and not r.reviewer_note)

            r.is_unresolved_override = is_unresolved

            if status in ["Missing Required Evidence", "Invalid Support"] or is_unresolved:
                has_error = True
            elif status == "Weak Support" or (status == "Reviewer Overrode System" and not is_unresolved):
                has_risk = True

        if has_error:
            run.claim_readiness = "Not Ready"
        elif has_risk:
            run.claim_readiness = "Risky"
        else:
            run.claim_readiness = "Ready"
