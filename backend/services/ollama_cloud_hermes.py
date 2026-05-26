# Ollama Cloud Hermes Provider
# Provides live LLM reasoning via Ollama Cloud Pro (OpenAI-compatible endpoint)
# Designed to be a drop-in replacement for MockHermesProvider

import os
import json
import hashlib
import urllib.request
import urllib.error
from typing import Optional
from datetime import datetime

from database.database import SessionLocal
from database.models import HermesLog
from schemas import HermesResponsePayload, HermesVisionResponse, ActionPlaybook
from logging_config import get_logger
from services.hermes_provider import HermesProvider

logger = get_logger("primoaudit.hermes.ollama_cloud")


class OllamaCloudHermesProvider(HermesProvider):
    """
    Hermes Provider backed by Ollama Cloud Pro.
    Uses the OpenAI-compatible chat completions API with JSON mode.
    """

    def __init__(self):
        self.api_key = os.environ.get("OLLAMA_CLOUD_API_KEY")
        self.base_url = os.environ.get("OLLAMA_CLOUD_BASE_URL", "https://ollama.com/v1")
        self.model = os.environ.get("OLLAMA_CLOUD_MODEL", "kimi-k2.6")
        self.vision_model = os.environ.get("OLLAMA_CLOUD_VISION_MODEL", "qwen3-vl:235b")
        self.timeout = float(os.environ.get("OLLAMA_CLOUD_TIMEOUT", "30.0"))
        self.temperature = float(os.environ.get("OLLAMA_CLOUD_TEMPERATURE", "0.2"))

        if not self.api_key:
            raise RuntimeError("OLLAMA_CLOUD_API_KEY environment variable is required for OllamaCloudHermesProvider")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _call_chat(self, messages: list, model: str, json_mode: bool = True, max_tokens: int = 4000) -> dict:
        """
        Core HTTP call to Ollama Cloud chat completions endpoint.
        Returns the raw parsed JSON dict.
        """
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read()
            parsed = json.loads(body)
            return parsed
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama Cloud API error {e.code}: {error_body}")
        except Exception as e:
            raise RuntimeError(f"Ollama Cloud request failed: {e}")

    def _ensure_valid(self, raw_text: str, model_class) -> dict:
        """
        Parse JSON text and validate against Pydantic schema.
        """
        try:
            # Strip markdown code fences if present
            cleaned = raw_text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3].strip()
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from LLM: {e}. Raw text: {raw_text[:500]}")

        # Pydantic v2 strict validation
        validated = model_class.model_validate(data)
        return validated.model_dump()

    # ------------------------------------------------------------------
    # Prompt builders
    # ------------------------------------------------------------------
    def _build_system_prompt(self) -> str:
        return (
            "You are Hermes, an expert automotive claims damages auditor AI. "
            "You analyze deterministic rule findings and claim context to produce structured audit intelligence. "
            "You NEVER alter financial amounts or override structural rule logic. "
            "Your role is purely advisory: recommend whether the human auditor should APPROVE, DISMISS, or REVIEW each finding. "
            "Always return valid JSON matching the schema exactly."
        )

    def _build_evaluate_prompt(self, hermes_payload: dict) -> str:
        carrier = hermes_payload.get("carrier", "Unknown Carrier")
        findings = hermes_payload.get("findings", [])
        claim_context = hermes_payload.get("claim_context", {})
        guideline_citations = hermes_payload.get("guideline_citations", [])

        # Build concise context string
        context_str = json.dumps({
            "carrier": carrier,
            "vehicle": claim_context.get("vehicle", {}),
            "shop": claim_context.get("shop", {}),
            "total_lines": claim_context.get("total_lines", 0),
            "claim_flags": claim_context.get("flags", []),
        }, indent=2)

        findings_brief = []
        for i, f in enumerate(findings):
            findings_brief.append({
                "index": i,
                "finding_id": f.get("finding_id"),
                "rule_id": f.get("rule_id"),
                "title": f.get("title", f.get("summary", "")),
                "severity": f.get("severity", "medium"),
                "affected_lines": f.get("affected_lines", []),
                "recommendation_strength": f.get("recommendation_strength", "request_support"),
                "suggested_action_type": f.get("suggested_action_type", ""),
                "financial_impact": f.get("financial_impact", 0.0),
                "calibration_reasons": f.get("calibration_reasons", []),
                "carrier_guideline_citation": f.get("carrier_guideline_citation"),
            })

        findings_str = json.dumps(findings_brief, indent=2)
        guideline_str = json.dumps(guideline_citations, indent=2) if guideline_citations else "[]"

        # Concise prompt — the system prompt already sets context
        brief = []
        for f in findings:
            brief.append({
                "finding_id": f.get("finding_id"),
                "rule_id": f.get("rule_id"),
                "severity": f.get("severity", "medium"),
                "strength": f.get("recommendation_strength", "request_support"),
                "financial_impact": f.get("financial_impact", 0.0),
            })
        
        return (
            f"Carrier: {carrier}. Review these {len(findings)} findings and return JSON\n"
            f"Findings: {json.dumps(brief)}\n"
            "Rules: strong_challenge→approve,firm | review_required→review,cautionary | "
            "request_support→review,advisory. Return findings dict + advisory_banners array + top_triage_items array."
        )

    def _build_vision_prompt(self, vision_payload: dict) -> list:
        question = vision_payload.get("question", "Does this photo support the claimed damage?")
        image_urls = vision_payload.get("image_urls", [])
        ctx = vision_payload.get("context", {})

        content = [
            {"type": "text", "text": (
                f"You are analyzing automotive damage evidence for claim audit.\n"
                f"Operation: {ctx.get('operation_type', 'Unknown')}\n"
                f"Part: {ctx.get('part_type', 'Unknown')}\n"
                f"Question: {question}\n\n"
                "Respond with JSON: {\"supports_damage\": bool, \"confidence\": float (0-1), \"notes\": string}"
            )}
        ]

        for url in image_urls[:3]:  # Cap at 3 images for token limits
            content.append({
                "type": "image_url",
                "image_url": {"url": url}
            })

        return [{"role": "user", "content": content}]

    # ------------------------------------------------------------------
    # HermesProvider interface
    # ------------------------------------------------------------------
    def evaluate(self, hermes_payload: dict) -> dict:
        logger.info(f"[Hermes] Using Ollama Cloud Provider — model={self.model}")

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": self._build_evaluate_prompt(hermes_payload)}
        ]

        try:
            response = self._call_chat(messages, self.model, json_mode=False, max_tokens=4000)
            raw_text = response["choices"][0]["message"]["content"]
            if not raw_text or not raw_text.strip():
                raise ValueError(f"Empty response from LLM model {self.model}. Model may not support json_object format.")
            # Parse JSON leniently — strict schema validation is too brittle for LLM output
            cleaned = raw_text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3].strip()
            import json as _json
            return _json.loads(cleaned)
        except Exception as e:
            logger.error(f"[Hermes] Ollama Cloud evaluation failed: {e}")
            raise

    def evaluate_vision(self, vision_payload: dict) -> dict:
        logger.info(f"[Hermes Vision] Using Ollama Cloud Provider — model={self.vision_model}")

        messages = self._build_vision_prompt(vision_payload)

        try:
            response = self._call_chat(messages, self.vision_model, json_mode=True, max_tokens=800)
            raw_text = response["choices"][0]["message"]["content"]
            validated = self._ensure_valid(raw_text, HermesVisionResponse)
            return validated
        except Exception as e:
            logger.error(f"[Hermes Vision] Ollama Cloud vision failed: {e}. Returning None.")
            return None


def patch_hermes_orchestrator():
    """
    Patches the hermes_orchestrator module in-memory to register the Ollama Cloud provider.
    Call this at app startup, or integrate the class directly into hermes_orchestrator.py.
    """
    import services.hermes_orchestrator as ho_module

    # Inject the new class into the module namespace
    ho_module.OllamaCloudHermesProvider = OllamaCloudHermesProvider

    # Wrap the original factory to support the new provider
    _orig_get_provider = ho_module.get_hermes_provider

    def _patched_get_hermes_provider():
        provider_type = os.environ.get("HERMES_PROVIDER", "simulator").lower()
        if provider_type == "ollama_cloud":
            return OllamaCloudHermesProvider()
        return _orig_get_provider()

    ho_module.get_hermes_provider = _patched_get_hermes_provider
