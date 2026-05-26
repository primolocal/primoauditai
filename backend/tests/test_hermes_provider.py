import pytest
from unittest.mock import patch, MagicMock
from requests.exceptions import Timeout
from datetime import datetime

# Adjust Python path for tests
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from schemas import HermesResponsePayload, HermesFindingResponse, HermesClaimLevelBanner, HermesVisionResponse
from services.hermes_orchestrator import RemoteHermesProvider, finalize_audit_advisory
from pydantic import ValidationError

@pytest.fixture
def mock_hermes_payload():
    return {
        "audit_id": "test_audit_1",
        "claim_id": "test_claim_1",
        "carrier": "TestCarrier",
        "claim_risk_flags": [],
        "findings": [
            {
                "finding_id": "test_finding_1",
                "rule_id": "rule_01",
                "category": "parts",
                "determinism": "deterministic",
                "operation_type": "replace",
                "part_type": "fender",
                "evidence_strength": "strong",
                "history_validation_rate": 0.9,
                "guideline_snippet": ""
            }
        ]
    }

@patch('requests.post')
@patch.dict(os.environ, {"HERMES_VPS_URL": "http://mock-vps.local"})
def test_remote_schema_valid_routing(mock_post, mock_hermes_payload):
    provider = RemoteHermesProvider()
    
    mock_res = MagicMock()
    mock_res.json.return_value = {
        "findings": {
            "test_finding_1": {
                "final_recommendation_text": "Mocked test.",
                "advisory_tone": "firm",
                "strength_label": "review_required",
                "escalation_hint": "Check notes.",
                "hermes_rationale_summary": "Logic dictates review.",
                "template_family": "base",
                "wording_variant": "A",
                "primary_reason_code": "TEST_REASON"
            }
        },
        "advisory_banners": []
    }
    mock_post.return_value = mock_res
    
    result = provider.evaluate(mock_hermes_payload)
    
    assert "test_finding_1" in result["findings"]
    assert result["findings"]["test_finding_1"]["advisory_tone"] == "firm"
    mock_post.assert_called_once()

@patch('requests.post')
@patch.dict(os.environ, {"HERMES_VPS_URL": "http://mock-vps.local"})
def test_remote_timeout_fallback(mock_post, mock_hermes_payload):
    provider = RemoteHermesProvider()
    mock_post.side_effect = Timeout("VPS unreachable")
    
    with pytest.raises(Timeout):
        provider.evaluate(mock_hermes_payload)
        
@patch('requests.post')
@patch.dict(os.environ, {"HERMES_VPS_URL": "http://mock-vps.local"})
def test_remote_invalid_schema(mock_post, mock_hermes_payload):
    provider = RemoteHermesProvider()
    
    mock_res = MagicMock()
    # Missing required 'final_recommendation_text' will trip Pydantic
    mock_res.json.return_value = {
        "findings": {
            "test_finding_1": {
                "advisory_tone": "firm"
            }
        },
        "advisory_banners": []
    }
    mock_post.return_value = mock_res
    
    with pytest.raises(ValidationError):
        provider.evaluate(mock_hermes_payload)

@patch('requests.post')
@patch.dict(os.environ, {"HERMES_VPS_URL": "http://mock-vps.local"})
def test_remote_vision_timeout_fallback(mock_post):
    provider = RemoteHermesProvider()
    mock_post.side_effect = Timeout("Vision VPS unreachable")
    
    # Should not raise exception, but return None gracefully
    vision_payload = {
        "question": "Is this damaged?",
        "image_urls": ["http://test.jpg"],
        "context": {}
    }
    
    result = provider.evaluate_vision(vision_payload)
    assert result is None

@patch('requests.post')
@patch.dict(os.environ, {"HERMES_VPS_URL": "http://mock-vps.local"})
def test_remote_vision_success(mock_post):
    provider = RemoteHermesProvider()
    mock_res = MagicMock()
    mock_res.json.return_value = {
        "supports_damage": True,
        "confidence": 0.95,
        "notes": "Clear scratch visible.",
        "error": None
    }
    mock_post.return_value = mock_res
    
    result = provider.evaluate_vision({"q": "test", "image_urls": [], "context": {}})
    assert result is not None
    assert result["supports_damage"] is True
    assert result["confidence"] == 0.95
