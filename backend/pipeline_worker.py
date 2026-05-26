import sys
import os
import io
import uuid
from typing import List, Tuple
from datetime import datetime
import traceback
import httpx

from logging_config import get_logger

logger = get_logger("primoaudit.pipeline")

from storage_service import StorageService
from storage.review_repository import SQLReviewRepository

repo = SQLReviewRepository()

def process_audit_pipeline(
    job_id: str, 
    audit_id: str, 
    ems_zip_bytes: bytes, 
    supporting_files: List[Tuple[str, bytes]], 
    evidence_mode: str, 
    base_url: str
):
    try:
        repo.update_job(job_id, status="processing", progress=10, audit_id=audit_id, message="Starting EMS Extraction...")

        # Run the 3-stage pipeline
        from parser.ems_parser import EmsParser
        parser = EmsParser()
        parsed_data = parser.analyze_zip(io.BytesIO(ems_zip_bytes))
        
        repo.update_job(job_id, status="processing", progress=30, message="Annotating Delta...")
        from delta_service import DeltaService
        parsed_data = DeltaService.annotate(parsed_data)
        
        repo.update_job(job_id, status="processing", progress=50, message="Processing Evidence...")
        from parser.evidence_parser import EvidenceParser
        
        if evidence_mode == "mock":
            raw_assets = EvidenceParser.extract_assets(io.BytesIO(ems_zip_bytes))
            for asset in raw_assets:
                asset["is_mock"] = True
                asset["source_kind"] = "generated_fixture"
                asset["processing_status"] = "preview_ready"
                asset["ingested_at"] = datetime.utcnow().isoformat() + "Z"
                asset["extraction_method"] = "mock_generator"
        elif evidence_mode == "live_with_fixtures":
            raw_assets = EvidenceParser.extract_assets_live(io.BytesIO(ems_zip_bytes), base_url, with_fixtures=True, supporting_files=supporting_files, audit_id=audit_id)
        else:
            raw_assets = EvidenceParser.extract_assets_live(io.BytesIO(ems_zip_bytes), base_url, with_fixtures=False, supporting_files=supporting_files, audit_id=audit_id)
            
        if evidence_mode != "mock":
            for asset in raw_assets:
                ext = asset.get("storage_key", "").lower()
                a_type = "pdf" if ext.endswith(".pdf") else "image"
                
                # Use abstracted DB persistence instead of RAM Asset Registry
                repo.save_asset_record(
                    audit_id=audit_id,
                    asset_id=asset["id"],
                    role="supporting_evidence",
                    storage_key=asset.get("storage_key", ""),
                    original_filename=asset["filename"],
                    content_type="application/octet-stream",
                    byte_size=0
                )
        
        from evidence_service import EvidenceMappingService
        parsed_data = EvidenceMappingService.classify_and_map(parsed_data, raw_assets)
        
        # 4. Generate Core AuditRun base (normalize parsed_data without findings)
        from adapter import build_audit_run
        strict_result = build_audit_run(parsed_data, audit_id=audit_id)
        
        repo.update_job(job_id, status="processing", progress=75, message="Calling Hermes Audit Service...")
        
        # 5. Call Hermes Intelligence — route by provider type
        import os
        provider_type = os.getenv("HERMES_PROVIDER", "simulator").lower()

        strict_result["ingestion_status"] = "normalized"
        strict_result["hermes_status"] = "processing"

        # Use local provider (ollama_cloud, simulator, google_genai) instead of webhook
        if provider_type in ("ollama_cloud", "simulator", "google_genai"):
            from services.hermes_orchestrator import finalize_audit_advisory

            # Build findings from rules engine
            from rules_engine import RulesEngine
            engine = RulesEngine()
            evaluated = engine.evaluate_estimate(parsed_data)
            findings = (
                evaluated.get("audit", {}).get("base_findings", []) +
                evaluated.get("audit", {}).get("carrier_overlays", {}).get("natgen", {}).get("findings", [])
            )

            strict_result["findings"] = findings
            strict_result["scorecard"] = evaluated.get("audit", {}).get("scorecard", {})
            strict_result["narrative"] = evaluated.get("narrative", {})

            # Run Hermes advisory (local provider)
            try:
                repo.update_job(job_id, status="processing", progress=80, message="Running AI vision & advisory...")
                finalize_audit_advisory(strict_result, findings)
                strict_result["hermes_status"] = "success"
                strict_result["hermes_finalized"] = True
                strict_result["hermes_version_applied"] = "v2.0"
                strict_result["manual_review_mode"] = False
                logger.info(f"Hermes advisory completed via {provider_type}")
            except Exception as e:
                logger.error(f"Hermes advisory failed: {e}")
                strict_result["hermes_status"] = "failed"
                strict_result["manual_review_mode"] = True

            repo.update_job(job_id, status="completed", progress=100, message="Audit Pipeline Complete (local provider)")
            # Persist
            claim_meta = strict_result.get("claim_package", {})
            claim_number = claim_meta.get("claim_number")
            if claim_number:
                repo.save_claim_record(claim_number, carrier=claim_meta.get("carrier"), loss_date=claim_meta.get("loss_date"))
                repo.link_audit_to_claim(claim_number, audit_id)
            repo.save_audit_run(audit_id, strict_result)
            return

        # Use remote webhook for remote_hermes provider
        elif provider_type == "remote_hermes":
            base_vps_url = os.getenv("HERMES_VPS_URL", "").rstrip('/')
            if not base_vps_url:
                raise RuntimeError("HERMES_VPS_URL environment variable is required for remote_hermes")
            hermes_url = f"{base_vps_url}/webhooks/audit_trigger"
        
        try:
            claim_pkg = strict_result.get("claim_package", {})
            est_summary = strict_result.get("estimate_lines", {}).get("summary", {})
            ev_matrix = strict_result.get("evidence_matrix", {})
            
            photos = ev_matrix.get("photos", [])
            documents = ev_matrix.get("documents", [])
            mappings = ev_matrix.get("line_mappings", {})
            
            photos_count = len(photos)
            pdf_count = len(documents)
            
            shop_pkg = strict_result.get("shop_profile", {})
            req_payload = {
                "claim_id": claim_pkg.get("claim_number", "UNKNOWN"),
                "event_type": "audit_start",
                "audit_id": audit_id,
                "estimate_type": "supplement" if "-S" in (strict_result.get("active_supplement") or "") else "original",
                "carrier": claim_pkg.get("carrier", "UNKNOWN"),
                "state": shop_pkg.get("state") or claim_pkg.get("state", "UNKNOWN"),
                "scope": strict_result.get("active_supplement") or "E01",
                "data": {
                    "facts_of_loss": claim_pkg.get("facts_of_loss", "Not provided."),
                    "estimate_summary": {
                        "gross_total": float(est_summary.get("gross_total", 0.0) or 0.0),
                        "labor_hours": float(est_summary.get("total_labor_hours", 0.0) or 0.0),
                        "labor_days": int(est_summary.get("repair_days", 0) or 0)
                    },
                    "estimate_lines": strict_result.get("estimate_lines", {}).get("items", []),
                    "evidence": {
                        "photos_count": photos_count,
                        "pdf_count": pdf_count,
                        "photo_metadata": photos,
                        "document_metadata": documents,
                        "photo_line_mappings": mappings
                    },
                    "validation_signals": {
                        "ems_verified": True,
                        "evidence_mapped": (photos_count + pdf_count) > 0
                    },
                    "deterministic_findings": strict_result.get("findings", [])
                }
            }
            
            import logging
            import time
            from datetime import datetime
            import logging as _logging
            _logging.basicConfig(level=_logging.INFO)
            _logger = _logging.getLogger("hermes_pipeline")
            
            hermes_run_id = f"hrun_{uuid.uuid4().hex[:8]}"
            started_at = datetime.utcnow()
            
            _logger.info("=== PREPARING HERMES EXECUTION ===")
            _logger.info(f"Target Webhook: {hermes_url}")
            _logger.info(f"Audit ID: {audit_id}")
            _logger.info(f"Run ID: {hermes_run_id}")
            
            import json
            
            # 1. Explicitly serialize the JSON with no spaces so we control it
            payload_bytes = json.dumps(req_payload, separators=(',', ':')).encode('utf-8')
            
            # 2. Hash those exact bytes using the secure function
            from security import sign_webhook_payload
            signature = sign_webhook_payload(payload_bytes)
            
            # 3. Set headers explicitly
            headers = {
                "x-hermes-event": "audit_start",
                "Content-Type": "application/json",
                "Content-Length": str(len(payload_bytes)),
                "x-hub-signature-256": signature
            }
                
            # 4. Send the physical bytes natively via httpx
            with httpx.Client() as client:
                resp = client.post(hermes_url, content=payload_bytes, headers=headers, timeout=180.0)
            
            completed_at = datetime.utcnow()
            elapsed_ms = int((completed_at - started_at).total_seconds() * 1000)
            
            _logger.info(f"=== HERMES RESPONSE: HTTP {resp.status_code} ===")
            resp.raise_for_status()
            
            h_data = resp.json()
            
            # DEBUG: Dump the exact payload Hermes returned to a file
            try:
                with open(os.path.join(os.path.dirname(__file__), 'hermes_last_response.json'), 'w') as f:
                    import json as _json
                    _json.dump(h_data, f, indent=2)
            except Exception as e:
                _logger.error(f"Failed to dump debug json: {e}")
                
            # 6. Apply Hermes feedback
            tasks = h_data.get("tasks", {})
            tasks_list = tasks if isinstance(tasks, list) else tasks.get("tasks", []) if isinstance(tasks, dict) else []
            
            if len(tasks_list) == 0:
                 raise ValueError("Hermes payload returned 0 executable tasks.")
                 
            for t in tasks_list:
                if 'message' not in t:
                    t['message'] = t.get('reason', 'Generated by Hermes')
                if 'rule_id' not in t:
                    t['rule_id'] = t.get('label', 'HERMES_LIVE')
                if 'category' not in t:
                    t['category'] = 'hermes_live'
            
            strict_result["hermes_tasks"] = tasks_list
            strict_result["findings"] = tasks_list + h_data.get("findings", [])
            strict_result["rule_results"] = h_data.get("rule_results", [])
            herm_sum = h_data.get("summary", {})
            if isinstance(herm_sum, dict):
                if "recommendation" in herm_sum and "decision" not in herm_sum: herm_sum["decision"] = herm_sum.pop("recommendation")
                if "estimated_score_impact" in herm_sum and "net_score_impact" not in herm_sum: herm_sum["net_score_impact"] = herm_sum.pop("estimated_score_impact")
                if "determinism" in herm_sum and "confidence_override" not in herm_sum: herm_sum["confidence_override"] = herm_sum.pop("determinism")
                if "total_findings" not in herm_sum: herm_sum["total_findings"] = herm_sum.pop("findings_count", len(tasks_list))
            elif isinstance(herm_sum, str):
                herm_sum = {"decision": herm_sum, "total_findings": len(tasks_list)}
            strict_result["summary"] = herm_sum
            strict_result["scorecard"] = h_data.get("scorecard", {})
            strict_result["narrative"] = h_data.get("narrative", {})
            strict_result["hermes_advisory"] = h_data.get("hermes_advisory", {})
            strict_result["hermes_status"] = "success"
            strict_result["manual_review_mode"] = False
            
            strict_result["hermes_run_metadata"] = {
                "hermes_run_id": hermes_run_id,
                "hermes_status": "success",
                "hermes_started_at": started_at.isoformat() + "Z",
                "hermes_completed_at": completed_at.isoformat() + "Z",
                "hermes_elapsed_ms": elapsed_ms,
                "hermes_error_code": None,
                "hermes_error_message": None
            }
            
            _logger.info(f"Hermes execution SUCCESS in {elapsed_ms}ms. Returned {len(strict_result['findings'])} findings and {len(tasks_list)} tasks.")
            
        except Exception as e:
            completed_at = datetime.utcnow()
            # If started_at hasn't been instantiated correctly somehow, fallback
            safe_started = locals().get('started_at', datetime.utcnow())
            elapsed_ms = int((completed_at - safe_started).total_seconds() * 1000)
            
            error_code = "unknown_error"
            message = str(e)
            
            import logging as _logging2
            _logger = _logging2.getLogger("hermes_pipeline")
            _logger.error(f"=== HERMES EXECUTION FAILED ===")
            _logger.error(f"Exception Type: {type(e).__name__}")
            _logger.error(f"Stacktrace:\n{traceback.format_exc()}")
            
            if isinstance(e, httpx.TimeoutException):
                error_code = "timeout"
                message = "The intelligence engine timed out."
            elif isinstance(e, httpx.RequestError):
                error_code = "connection_error"
                message = "Could not connect to the intelligence engine."
            elif isinstance(e, httpx.HTTPStatusError):
                status_code = getattr(e.response, "status_code", 500) if hasattr(e, "response") else 500
                error_code = "5xx" if status_code >= 500 else "invalid_request"
                message = f"Hermes returned HTTP {status_code}."
            elif getattr(e, "__class__", None).__name__ == "JSONDecodeError" or isinstance(e, ValueError):
                error_code = "invalid_response_schema"
                message = "Hermes returned an invalid or empty payload structure."
                
            _logger.error(f"Hermes Call Failed: {error_code} - {message}")
            _logger.error(f"Resolved Error: {error_code} - {message}")
            
            hr_id = locals().get('hermes_run_id', f"hrun_{uuid.uuid4().hex[:8]}")
            
            strict_result["hermes_status"] = "failed"
            strict_result["status"] = "needs_review"
            strict_result["manual_review_mode"] = True
            
            strict_result["hermes_run_metadata"] = {
                "hermes_run_id": hr_id,
                "hermes_status": "failed",
                "hermes_started_at": safe_started.isoformat() + "Z",
                "hermes_completed_at": completed_at.isoformat() + "Z",
                "hermes_elapsed_ms": elapsed_ms,
                "hermes_error_code": error_code,
                "hermes_error_message": message
            }
            
            # Ensure valid empty response shapes
            strict_result["hermes_tasks"] = {"tasks": [], "total_tasks": 0, "resolved_tasks": 0}
            strict_result["findings"] = []
            strict_result["scorecard"] = {"overall_score": 100, "verdict": "Pass", "category_scores": {}}
            
            strict_result["activity_log"].append({
                "id": f"evt_{uuid.uuid4().hex[:6]}",
                "timestamp": completed_at.isoformat() + "Z",
                "actor": "system",
                "event_type": "hermes_failure",
                "description": f"Hermes Intelligence Engine failed ({error_code}). Fallback to manual review mode enforced."
            })
                
        # Handle Claim Continuity
        claim_meta = strict_result.get("claim_package", {})
        claim_number = claim_meta.get("claim_number")
        if claim_number:
            repo.save_claim_record(claim_number, carrier=claim_meta.get("carrier"), loss_date=claim_meta.get("loss_date"))
            repo.link_audit_to_claim(claim_number, audit_id)
            
        # Persist structured payload via repo instead of main RAM block
        repo.save_audit_run(audit_id, strict_result)
        
        repo.update_job(job_id, status="completed", progress=100, message="Audit Pipeline Complete")
            
    except Exception as e:
        traceback.print_exc()
        repo.update_job(job_id, status="failed", progress=0, message=str(e))
