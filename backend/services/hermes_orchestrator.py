import os
import hashlib
import json
import urllib.request
import urllib.error
import requests
from datetime import datetime
from database.database import SessionLocal
from database.models import HermesLog, CarrierGuideline
from schemas import HermesResponsePayload, HermesVisionResponse
from services.hermes_provider import HermesProvider
from services.ollama_cloud_hermes import OllamaCloudHermesProvider
from logging_config import get_logger

logger = get_logger("primoaudit.hermes")

CURRENT_HERMES_VERSION = "v2.0"

class MockHermesProvider(HermesProvider):
    def evaluate_vision(self, vision_payload: dict) -> dict:
        logger.info("[Hermes Vision] Using Mock Simulator Visual Analysis.")
        return {
            "supports_damage": False,
            "confidence": 0.85,
            "notes": "[Mock] Evidence does not clearly support the requested operation. Photo obscures the specified area and lacks required measurement indexing."
        }

    def evaluate(self, hermes_payload: dict) -> dict:
        logger.info("[Hermes] Using Mock Simulator Provider.")
        carrier = hermes_payload.get("carrier", "Unknown")
        findings = hermes_payload.get("findings", [])
        
        response = {
            "findings": {},
            "advisory_banners": []
        }
        
        has_strong_challenges = False
        
        for f in findings:
            fid = f.get("finding_id")
            strength = f.get("recommendation_strength", "request_support")
            actions = f.get("suggested_action_type", "")
            reasons = f.get("calibration_reasons", [])
            
            f_resp = {
                "advisory_tone": "soft",
                "template_family": "bypass_warning",
                "wording_variant": "C_high_overturn_rate",
                "escalation_hint": "None.",
                "hermes_rationale_summary": "Low confidence or highly rejected historically.",
                "final_recommendation_text": f"Hermes Context: Soft warning only. The logic identified variance but historically this operation is overturned cleanly. Check estimator notes and bypass.",
                "strength_label": strength,
                "primary_reason_code": "HISTORICAL_TELEMETRY" if len(reasons) > 0 else "BASELINE_RULE",
                "action_playbook": {
                    "primary_action": "Bypass Rule",
                    "steps": ["Review estimator notes for operational exceptions.", "Mark finding as Overturned if documentation matches carrier trends."],
                    "escalate_if": ["No estimator notes exist and cost exceeds $100."],
                    "do_not_do": ["Do not automatically fail the file without reading the notes."]
                },
                "recommended_action": "dismiss",
                "confidence_level": "low",
                "short_reason": "High overturn rate for this logic.",
                "pattern_detection_flags": [],
                "pattern_related_lines": []
            }
            
            if strength == "strong_challenge":
                has_strong_challenges = True
                f_resp["advisory_tone"] = "firm"
                f_resp["template_family"] = "strict_enforcement"
                f_resp["wording_variant"] = "A_carrier_history_led"
                f_resp["escalation_hint"] = "Immediate management review supported."
                f_resp["hermes_rationale_summary"] = "High confidence combined with historically robust behavior warrants strict challenge."
                f_resp["final_recommendation_text"] = f"Hermes Context: Given carrier {carrier}'s history and the {actions} marker, immediately challenge this point. Telemetry confirms {' and '.join(reasons)}."
                f_resp["action_playbook"] = {
                    "primary_action": "Confirm Challenge",
                    "steps": ["Review parts catalog.", "Verify vendor overlap.", "Click 'Confirm' on finding immediately."],
                    "escalate_if": ["Vendor refuses alternative part matches physically."],
                    "do_not_do": ["Do not bypass. This carrier tracks strong challenges strictly."]
                }
                f_resp["recommended_action"] = "approve"
                f_resp["confidence_level"] = "high"
                f_resp["short_reason"] = "Strict guidance violation detected."
                f_resp["pattern_detection_flags"] = ["Identical vendor exceptions on lines 4, 5"]
                f_resp["pattern_related_lines"] = [4, 5]
            elif strength == "review_required":
                f_resp["advisory_tone"] = "cautionary"
                f_resp["template_family"] = "auditor_intervention_req"
                f_resp["wording_variant"] = "B_evidence_gap"
                f_resp["escalation_hint"] = "Standard line item override check."
                f_resp["hermes_rationale_summary"] = "Evidence gap paired with telemetry signals necessitate manual review."
                f_resp["final_recommendation_text"] = f"Hermes Context: Telemetry highlights overlapping issues ({', '.join(reasons)}). Recommend auditing this manually against standard shop profiles rather than failing instantly."
                f_resp["action_playbook"] = {
                    "primary_action": "Manual Profile Check",
                    "steps": ["Open shop profile history.", "Validate average labor rates historically."],
                    "escalate_if": ["Rate variance exceeds 10% tolerance."],
                    "do_not_do": ["Do not click 'Confirm' blindly. Verify actual rate agreements first."]
                }
                f_resp["recommended_action"] = "review"
                f_resp["confidence_level"] = "medium"
                f_resp["short_reason"] = "Labor variance exceeds tolerance."
                f_resp["pattern_detection_flags"] = ["Labor overlap across body panels"]
                f_resp["pattern_related_lines"] = [12, 14]
            elif strength == "request_support":
                f_resp["advisory_tone"] = "advisory"
                f_resp["template_family"] = "doc_request_soft"
                f_resp["wording_variant"] = "A_standard_request"
                f_resp["escalation_hint"] = "None."
                f_resp["hermes_rationale_summary"] = "Weak signal, standard doc request."
                f_resp["final_recommendation_text"] = f"Hermes Context: {actions.replace('_', ' ').capitalize()} to shore up documentation. This carrier frequently rejects this logic, so proceed manually."
                f_resp["action_playbook"] = {
                    "primary_action": "Request Documentation",
                    "steps": ["Draft request to estimator for additional photos."],
                    "escalate_if": ["Estimator refuses contact."],
                    "do_not_do": []
                }
                f_resp["recommended_action"] = "review"
                f_resp["confidence_level"] = "low"
                f_resp["short_reason"] = "Documentation appears incomplete."
                f_resp["pattern_detection_flags"] = []
                f_resp["pattern_related_lines"] = []

            # Phase 21 Mock Guideline Simulation
            citation = f.get("carrier_guideline_citation")
            if citation:
                f_resp["template_family"] = "llm_live_context"
                f_resp["wording_variant"] = f"LLM_Snippet_Mapped_to_{strength}"
                f_resp["hermes_rationale_summary"] = f"Live Carrier Guideline {citation['version_label']} ({citation['citation_reference']}) strictly grounds this recommendation."
                f_resp["final_recommendation_text"] = f"Hermes Context: {citation['carrier']} Guideline {citation['version_label']} directly dictates in {citation['citation_reference']}: \"{citation['excerpt']}\". Therefore, {actions.replace('_', ' ')} is supported and required by carrier policy."

            response["findings"][fid] = f_resp
            
        # Claim Level Banners
        if has_strong_challenges:
            response["advisory_banners"].append({
                "type": "warning",
                "title": "High Resistance Claim",
                "message": f"Hermes Warning: {carrier} frequently rejects recommendations matching these exact patterns. Ensure all hard challenges are backed by unquestionable photo documentation before processing."
            })
            
        if len(findings) > 5:
            response["advisory_banners"].append({
                "type": "secondary",
                "title": "Volume Alert",
                "message": f"This claim generated {len(findings)} distinct flags. Recommend focusing on structural/safety issues rather than minor overlaps."
            })
            
        return response

class RemoteHermesProvider(HermesProvider):
    def evaluate_vision(self, vision_payload: dict) -> dict:
        vps_url = os.environ.get("HERMES_VPS_URL")
        logger.info(f"[Hermes Vision] Hitting target remote vision API at {vps_url}/vision")
        if not vps_url:
            return None
            
        try:
            req = urllib.request.Request(
                f"{vps_url}/vision",
                data=json.dumps(vision_payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=8.0) as response:
                res_body = response.read()
            
            validated_payload = HermesVisionResponse.model_validate(json.loads(res_body))
            return validated_payload.model_dump()
        except Exception as e:
            logger.warning(f"[Hermes Vision] VPS Visual Request failed: {e}. Falling back to text-only logic.")
            return None

    def evaluate(self, hermes_payload: dict) -> dict:
        vps_url = os.environ.get("HERMES_VPS_URL")
        logger.info(f"[Hermes] Using Remote VPS Provider at {vps_url}")
        if not vps_url:
            logger.error("[Hermes] HERMES_VPS_URL missing. Cannot connect.")
            raise Exception("HERMES_VPS_URL is missing")
            
        try:
            req = urllib.request.Request(
                vps_url,
                data=json.dumps(hermes_payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=4.0) as response:
                res_body = response.read()
            
            # Phase 11 Constrained Validation
            # Automatically throws ValidationError if payload breaks JSON bounds or drops required keys
            validated_payload = HermesResponsePayload.model_validate(json.loads(res_body))
            return validated_payload.model_dump()
            
        except Exception as e:
            # Native requests timeout, or Pydantic ValidationError bounds tripped
            logger.warning(f"[Hermes] VPS Request/Validation failed: {e}. Falling back to simulator.")
            raise

class GoogleGenAIHermesProvider(HermesProvider):
    def evaluate_vision(self, vision_payload: dict) -> dict:
        return None
        
    def evaluate(self, hermes_payload: dict) -> dict:
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            logger.error("[Hermes] google-genai package not found. Falling back to simulator.")
            raise Exception("google-genai not installed")

        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            logger.error("[Hermes] GOOGLE_API_KEY missing. Falling back to simulator.")
            raise Exception("GOOGLE_API_KEY missing")

        logger.info("[Hermes] Hitting live Google Gemini 2.5 Flash via google-genai SDK.")

        client = genai.Client(api_key=api_key)
        
        system_instruction = (
            "You are Hermes, an expert automated automotive claims damages auditor. "
            "You receive an internal payload of deterministic rules that have failed, and you must review "
            "the context (claim package, historical data, and guideline citations) and output an intelligent "
            "structured response dictating whether the reviewer should actively APPROVE, DISMISS, or REVIEW the anomalies."
        )

        prompt = (
            f"Review the following strict deterministic rule findings and claim context. "
            f"Analyze the rule ID string, recommended action, baseline evidence strength, and carrier guideline mapping. "
            f"If there is a carrier pattern of identical issues, flag them. "
            f"Context: {json.dumps(hermes_payload, indent=2)}\n\n"
            f"Generate the exact structured output mapping your assessment to each finding_id inside the payload."
        )

        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=HermesResponsePayload,
                    temperature=0.2,
                )
            )
            
            res_body = response.text
            validated_payload = HermesResponsePayload.model_validate(json.loads(res_body))
            return validated_payload.model_dump()
            
        except Exception as e:
            logger.error(f"[Hermes] Gemini execution failed: {e}. Falling back.")
            raise

def get_hermes_provider() -> HermesProvider:
    provider_type = os.environ.get("HERMES_PROVIDER", "simulator").lower()
    
    if provider_type == "remote_hermes":
        return RemoteHermesProvider()
    elif provider_type == "google_genai":
        return GoogleGenAIHermesProvider()
    elif provider_type == "ollama_cloud":
        return OllamaCloudHermesProvider()
    else:
        return MockHermesProvider()

def extract_guideline_snippets(carrier: str, keywords: list, db) -> dict:
    # Phase 21 Structured Citation Mock/DB fetch
    # Case insensitive DB match
    cg = db.query(CarrierGuideline).filter(CarrierGuideline.carrier.ilike(f"%{carrier}%")).first()
    
    # If no DB policy exists for this specific carrier, provide a robust mock for UI validation
    if not cg or not cg.extracted_text:
        return {
            "carrier": carrier,
            "version_label": "2024 Q1 Auto Guidelines",
            "section_title": "Parts & Sourcing Hierarchy",
            "excerpt": f"Estimators must explicitly photo-document and justify any standard labor deviations exceeding 0.5 hours or manual parts selection bypassing the automated vendor cascade.",
            "citation_reference": "Section 4.1.2 - Labor Tolerances & Parts Cascade"
        }
    
    text = cg.extracted_text.lower()
    snippets = []
    
    primary_kw = keywords[0] if keywords else "policy"
    
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower in text:
            idx = text.find(kw_lower)
            start = max(0, idx - 150)
            end = min(len(text), idx + 150)
            snippets.append(cg.extracted_text[start:end].strip().replace("\n", " "))
            primary_kw = kw
            
    if not snippets:
        return None
        
    combined_excerpt = "... " + " ... ".join(snippets[:2]) + " ..."
    return {
        "carrier": cg.carrier,
        "version_label": cg.version_label or "Active Policy",
        "section_title": f"Derived Match: {primary_kw.capitalize()}",
        "excerpt": combined_excerpt,
        "citation_reference": f"Document Match: Line {text.find(primary_kw.lower()) if primary_kw else 0}"
    }


def build_hermes_payload(run_json: dict, findings: list, db, provider: HermesProvider) -> dict:
    audit_id = run_json.get("audit_id", "unknown")
    claim_pkg = run_json.get("claim_package", {})
    claim_id = claim_pkg.get("claim_number", "none")
    carrier = claim_pkg.get("carrier", "Unknown")
    
    payload = {
        "audit_id": audit_id,
        "claim_id": claim_id,
        "carrier": carrier,
        "claim_risk_flags": run_json.get("risk_flags", []),
        "findings": []
    }
    
    for f in findings:
        rule_id = f.get("rule_id", "UNKNOWN_RULE")
        keywords = [rule_id.split("_")[0], "photo", "labor", "replace", "oem"]
        citation_dict = extract_guideline_snippets(carrier, keywords, db)
        
        ev_refs = f.get("evidence_refs", [])
        evidence_strength = "strong" if not any(e.get("support_status") == "missing" for e in ev_refs) else "weak"
        
        # Phase 8: Hermes Vision Trigger — collect all tasks, run in parallel
        vision_tasks = []
        requires_vision = False
        
        if "visual" in rule_id or "photo" in rule_id or "PHOTO_VERIFY" in rule_id:
            requires_vision = True
        elif evidence_strength == "weak":
            requires_vision = True
            
        if requires_vision:
            img_urls = [e.get("url") for e in ev_refs if e.get("type") == "photo" and e.get("url")]
            if img_urls:
                import base64 as _b64
                from storage_service import StorageService as _ss
                data_urls = []
                for url in img_urls[:1]:  # 1 photo per finding
                    try:
                        storage_key = url.split("/assets/")[-1] if "/assets/" in url else None
                        if storage_key:
                            img_bytes = _ss.read_file_bytes(storage_key)
                            if img_bytes:
                                data_urls.append(f"data:image/jpeg;base64,{_b64.b64encode(img_bytes).decode()}")
                                continue
                    except Exception:
                        pass
                    data_urls.append(url)
                
                if data_urls:
                    vision_tasks.append((
                        f, data_urls,
                        f.get("operation_type", ""),
                        f.get("part_type", ""),
                        f.get("id", "")
                    ))

        # Collect per-finding data for the payload after vision
        fd = {
            "finding_id": f.get("id"),
            "rule_id": rule_id,
            "category": f.get("category", ""),
            "determinism": f.get("determinism", "deterministic"),
            "operation_type": f.get("operation_type"),
            "part_type": f.get("part_type"),
            "evidence_strength": evidence_strength,
            "vision_task": vision_tasks[0] if vision_tasks else None,  # deferred
            "historical_signals": f.get("historical_signals", []),
            "recommendation_strength": f.get("recommendation_strength", "request_support"),
            "calibration_reasons": f.get("calibration_reasons", []),
            "suggested_action_type": f.get("suggested_action_type", ""),
            "requires_manual_confirmation": True,
            "carrier_guideline_citation": citation_dict
        }
        payload["findings"].append(fd)
        
    # --- Run all vision calls in parallel ---
    all_vision_tasks = []
    for fd in payload["findings"]:
        vt = fd.pop("vision_task", None)
        if vt:
            all_vision_tasks.append((fd["finding_id"], vt))
    
    if all_vision_tasks:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        logger.info(f"Running {len(all_vision_tasks)} vision calls in parallel...")
        
        def _run_vision(task_data):
            f_ref, data_urls, op_type, part_type, fid = task_data
            v_payload = {
                "question": f"Please verify if the photo supports the {op_type} operation on {part_type}.",
                "image_urls": data_urls,
                "context": {"part_type": part_type, "operation_type": op_type, "finding_id": fid}
            }
            result = provider.evaluate_vision(v_payload)
            if result:
                f_ref["vision_result"] = result  # Store directly on the finding dict
            return result
        
        with ThreadPoolExecutor(max_workers=4) as ex:
            futures = [ex.submit(_run_vision, vt) for _, vt in all_vision_tasks]
            for future in as_completed(futures):
                try:
                    future.result(timeout=60)
                except Exception as e:
                    logger.warning(f"Vision call failed: {e}")
        
        logger.info(f"Vision complete: {len(all_vision_tasks)} calls")
    
    return payload


def finalize_audit_advisory(run_json: dict, findings: list):
    audit_id = run_json.get("audit_id", "unknown")
    carrier = run_json.get("claim_package", {}).get("carrier", "Unknown")
    
    db = SessionLocal()
    
    try:
        provider = get_hermes_provider()
        provider_used = os.environ.get("HERMES_PROVIDER", "simulator").lower()
        response_mode = "live" if provider_used in ("remote_hermes", "ollama_cloud", "google_genai") else "mock"
        fallback_reason = None
        
        # Build strict JSON payload dynamically hitting vision endpoints if triggered
        payload = build_hermes_payload(run_json, findings, db, provider)
        
        try:
            resp = provider.evaluate(payload)
        except Exception as e:
            # Automatic fallback to simulator if remote fails
            if provider_used != "simulator":
                from pydantic import ValidationError
                if hasattr(requests, 'exceptions') and isinstance(e, requests.exceptions.Timeout):
                    fallback_reason = "timeout"
                elif isinstance(e, ValidationError):
                    fallback_reason = "schema_validation_error"
                elif hasattr(requests, 'exceptions') and isinstance(e, requests.exceptions.RequestException):
                    # res.json() parsing failure triggers JSONDecodeError natively inheriting from ValueError
                    if e.__class__.__name__ == "JSONDecodeError" or isinstance(e, ValueError):
                        fallback_reason = "invalid_json"
                    else:
                        fallback_reason = "http_error"
                else:
                    if getattr(e, "__class__", None).__name__ == "JSONDecodeError" or isinstance(e, ValueError):
                        fallback_reason = "invalid_json"
                    else:
                        fallback_reason = "empty_payload"
                        
                logger.warning(f"[Hermes Orchestrator] Provider failed: {e}. Reason: {fallback_reason}. Falling back to simulator.")
                resp = MockHermesProvider().evaluate(payload)
                response_mode = "fallback_local"
            else:
                resp = {"findings": {}, "advisory_banners": []}
                
        run_json["hermes_provider_used"] = provider_used
        run_json["hermes_response_mode"] = response_mode
        if fallback_reason:
            run_json["hermes_fallback_reason"] = fallback_reason
                
        # 3. Adsorb Response Structure
        f_resp_map = resp.get("findings", {})
        
        for f in findings:
            fid = f.get("id")
            hermes_f = f_resp_map.get(fid, {})
            
            vis_res = f.get("vision_result")
            v_trig = False
            v_succ = False
            v_timeout = False
            v_error = None
            if vis_res:
                v_trig = True
                if vis_res.get("error"):
                    v_error = vis_res.get("error")
                    v_timeout = "timeout" in v_error.lower() or "fail" in v_error.lower()
                else:
                    v_succ = True
            
            f["hermes_version"] = CURRENT_HERMES_VERSION
            f["strength_label"] = hermes_f.get("strength_label", f.get("recommendation_strength"))
            f["carrier"] = carrier
            f["primary_reason_code"] = hermes_f.get("primary_reason_code", "BASELINE_RULE")
            f["reason_codes_json"] = f.get("calibration_reasons", [])
            
            f["advisory_tone"] = hermes_f.get("advisory_tone", "advisory")
            f["template_family"] = hermes_f.get("template_family", "fallback")
            f["wording_variant"] = hermes_f.get("wording_variant", "D_basic")
            f["escalation_hint"] = hermes_f.get("escalation_hint", "")
            f["hermes_rationale_summary"] = hermes_f.get("hermes_rationale_summary", "")
            f["final_recommendation_text"] = hermes_f.get("final_recommendation_text", "Audit logic applied.")
            
            # Phase 25: Enhanced Decision Support Fields
            f["hermes_recommended_action"] = hermes_f.get("recommended_action")
            f["hermes_confidence_level"] = hermes_f.get("confidence_level")
            f["hermes_short_reason"] = hermes_f.get("short_reason")
            f["pattern_detection_flags"] = hermes_f.get("pattern_detection_flags", [])
            f["pattern_related_lines"] = hermes_f.get("pattern_related_lines", [])

            # Phase 15: Action Playbook
            if hermes_f.get("action_playbook"):
                f["action_playbook"] = hermes_f.get("action_playbook")
                
            # Phase 21: Guideline Citation
            # Fetch structured citation out of payload builder
            target_build_finding = next((pf for pf in payload["findings"] if pf["finding_id"] == fid), None)
            if target_build_finding and target_build_finding.get("carrier_guideline_citation"):
                f["carrier_guideline_citation"] = target_build_finding.get("carrier_guideline_citation")
            
            # Phase 13: Triage Calculation
            score = 0.0
            
            # 1. Severity Base
            sev = f.get("severity", "low").lower()
            if sev == "critical": score += 40
            elif sev == "major" or sev == "high": score += 25
            elif sev == "medium": score += 10
            
            # 2. Financial Impact
            fin = float(f.get("financial_impact", 0.0) or 0.0)
            if fin >= 500: score += 20
            elif fin >= 100: score += 10
            
            # 3. Evidence Strength
            ev_refs = f.get("evidence_refs", [])
            evidence_weak = any(e.get("support_status") == "missing" for e in ev_refs) or len(ev_refs) == 0
            if evidence_weak: score += 15
            
            # 4. Vision Context
            if v_succ and vis_res.get("supports_damage") is False:
                score += 20  # AI Vision explicitly contradicts the claim!
                
            # 5. Telemetry & Carrier Flags
            hist = f.get("historical_signals", [])
            has_overturn = any(h.get("type", "") == "historically_overturned" for h in hist)
            has_carrier_conflict = any(h.get("source", "") == "carrier" for h in hist)
            if has_overturn: score += 15
            if has_carrier_conflict: score += 10
            
            # 6. Hermes Confidence
            if f["strength_label"] in ["strong_challenge", "review_required"]:
                score += 10
                
            score = min(max(score, 0.0), 100.0)
            f["triage_priority_score"] = score
            
            if score >= 80:
                bucket = "Address First"
            elif score >= 60:
                bucket = "Needs Review"
            elif score >= 35:
                bucket = "Request Support"
            else:
                bucket = "Low Urgency"
                
            f["triage_bucket"] = bucket
            
            # Log output centrally
            log1 = HermesLog(
                input_hash=hashlib.md5(f"{audit_id}-{fid or 'unknown'}-{CURRENT_HERMES_VERSION}".encode()).hexdigest(),
                target_id=fid or f"unknown_{audit_id}",
                target_type="finding",
                generated_text=f["final_recommendation_text"],
                advisory_tone=f["advisory_tone"],
                escalation_hint=f["escalation_hint"],
                hermes_version=f["hermes_version"],
                template_family=f["template_family"],
                wording_variant=f["wording_variant"],
                strength_label=f["strength_label"],
                primary_reason_code=f["primary_reason_code"],
                reason_codes_json=f["reason_codes_json"],
                carrier=f["carrier"],
                rule_id=f.get("rule_id", "UNKNOWN"),
                provider=os.environ.get("HERMES_PROVIDER", "simulator"),
                vision_triggered=v_trig,
                vision_success=v_succ,
                vision_timeout=v_timeout,
                vision_error=v_error,
                triage_bucket=f["triage_bucket"],
                primary_action=f.get("action_playbook", {}).get("primary_action") if f.get("action_playbook") else None
            )
            try:
                db.add(log1)
            except Exception:
                pass  # Non-critical logging failure — don't block pipeline

        # Phase 13: Hermes claim-level top 3 triage output (legacy mapped alongside tasks)
        sorted_findings = sorted(findings, key=lambda x: x.get("triage_priority_score", 0.0), reverse=True)
        top_3 = sorted_findings[:3]
        top_triage_items = []
        for i, tf in enumerate(top_3):
            if tf.get("triage_priority_score", 0.0) > 0:
                top_triage_items.append({
                    "finding_id": tf.get("id", tf.get("finding_id")),
                    "title": f"[{tf.get('triage_bucket')}] {tf.get('rule_id', 'Unknown')}",
                    "short_reason": tf.get("hermes_rationale_summary", "Review required based on analytical strength and operational severity.")
                })
        run_json["top_triage_items"] = top_triage_items

        # Phase 22: Queue Execution Engine
        tasks = []
        for i, tf in enumerate(sorted_findings):
            score = tf.get("triage_priority_score", 0.0)
            if score == 0.0:
                continue

            line_no = tf.get("affected_lines", [0])[0] if tf.get("affected_lines") else 0
            severity = "BLOCKING" if score >= 80 else "WARNING"
            impact = int(score / 10)
            
            fstat = tf.get("status", "open")
            tstat = "pending" if fstat == "open" else "resolved"
            
            label_base = tf.get("category", tf.get("rule_id", "Unknown Issue"))

            tasks.append({
                "id": f"task_{tf.get('id', 'unknown')}",
                "finding_id": tf.get("id", "unknown"),
                "line_number": line_no,
                "label": label_base,
                "severity": severity,
                "score_impact": impact,
                "status": tstat,
                "allowed_actions": ["request_info", "override", "confirm"]
            })
            
        run_json["hermes_tasks"] = {
            "tasks": tasks,
            "total_tasks": len(tasks),
            "resolved_tasks": len([t for t in tasks if t["status"] == "resolved"])
        }

        # Claim Banners
        # Sort strategically by priority before restricting array length
        all_banners = resp.get("advisory_banners", [])
        
        banner_priority = {"warning": 0, "primary": 1, "secondary": 2, "info": 3}
        all_banners.sort(key=lambda x: banner_priority.get(x.get("type", "info"), 4))
        
        banners = all_banners[:2]
        
        if len(all_banners) > 2:
            run_json["hermes_banner_overflow_truncated"] = True
            run_json["hermes_banner_count_returned"] = len(all_banners)
            
        if banners:
            run_json["advisory_banners"] = banners
            log2 = HermesLog(
                input_hash=hashlib.md5(f"{audit_id}-claim-{len(banners)}".encode()).hexdigest(),
                target_id=audit_id,
                target_type="claim",
                banner_text=banners[0].get("message"),
                provider=os.environ.get("HERMES_PROVIDER", "simulator")
            )
            db.add(log2)

        db.commit()

    except Exception as e:
        import traceback
        logger.error(f"Hermes Mapping Error: {e}")
        logger.error("Hermes Mapping Traceback", exc_info=True)
        db.rollback()
    finally:
        db.close()
        
    run_json["hermes_finalized"] = True
    run_json["hermes_version_applied"] = CURRENT_HERMES_VERSION
