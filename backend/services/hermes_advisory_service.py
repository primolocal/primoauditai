import json
import urllib.request
from typing import Dict, Any

class HermesAdvisoryService:
    @staticmethod
    def fetch_audit_advisory(audit_run: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts structured deterministic context from the completed AuditRun 
        and hits the external decoupled Hermes Advisory endpoint.
        Returns the raw structural Advisory payload without mutating the run.
        """
        try:
            # 1. Structure the strict Read-Only payload
            findings_payload = []
            for f in audit_run.get("findings", []):
                
                # Check for severity format depending on engine phase mapped 
                sev_raw = f.get("severity", "low")
                if isinstance(sev_raw, str):
                    sev_num = {"critical": 40, "major": 25, "high": 25, "medium": 10, "minor": 0, "low": 0}.get(sev_raw.lower(), 0)
                else:
                    sev_num = sev_raw
                    
                finding_block = {
                    "id": f.get("id"),
                    "category": f.get("category", "General"),
                    "severity": sev_num, 
                    "rule_id": f.get("rule_id", "Unknown"),
                    "description": f.get("message", "No description"),
                    "evidence": {
                        "photos_present": any(e.get("type") == "photo" for e in f.get("evidence_refs", [])),
                        "docs_present": any(e.get("type") == "doc" for e in f.get("evidence_refs", [])),
                        "estimate_lines": f.get("affected_lines", [])
                    }
                }
                findings_payload.append(finding_block)

            payload = {
                "audit_id": audit_run.get("audit_id", audit_run.get("run_id", "unknown")),
                "carrier": audit_run.get("claim_package", {}).get("carrier", "Unknown"),
                "claim_meta": {
                    "status": audit_run.get("claim_package", {}).get("status", "unknown")
                },
                "findings": findings_payload,
                "category_scores": audit_run.get("scorecard", {}).get("category_scores", {}),
                "historical_patterns": {
                    # Future integration wrapper mapping global metric deltas
                },
                "auditor_context": {
                    "id": audit_run.get("auditor_id", "unassigned")
                }
            }

            # 2. Dispatch using built-in urllib
            req = urllib.request.Request(
                "http://127.0.0.1:8000/api/hermes/advisory",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=4.0) as response:
                res_body = response.read()
            
            # The strict JSON structure guaranteed by the API endpoint contract
            return json.loads(res_body)

        except Exception as e:
            print(f"[Hermes Advisory Service] Fetch failed or timed out: {e}")
            # Fallback wrapper that perfectly aligns with UI without blocking
            return {
                "audit_summary": "Advisory unavailable.",
                "findings": [],
                "fallback_active": True
            }
