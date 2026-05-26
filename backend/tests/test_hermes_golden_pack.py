import pytest
import os
import glob
import json

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.hermes_orchestrator import RemoteHermesProvider, finalize_audit_advisory
from unittest.mock import patch, MagicMock

GOLDEN_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'golden_claims')

def load_golden_claim(filename):
    with open(os.path.join(GOLDEN_DIR, filename), 'r') as f:
        return json.load(f)

@pytest.fixture
def clean_claim():
    return load_golden_claim("clean_claim.json")

@pytest.fixture
def weak_photo_claim():
    return load_golden_claim("weak_photo_claim.json")

@pytest.fixture
def high_overturn_claim():
    return load_golden_claim("high_overturn_claim.json")

@patch('requests.post')
@patch.dict(os.environ, {"HERMES_VPS_URL": "http://mock-vps.local"})
def test_clean_claim_regression(mock_post, clean_claim):
    provider = RemoteHermesProvider()
    mock_post.return_value = MagicMock(
        json=lambda: {
            "findings": {
                "fnd_cln_1": {
                    "final_recommendation_text": "Clean",
                    "advisory_tone": "soft",
                    "strength_label": "advisory",
                    "escalation_hint": "",
                    "hermes_rationale_summary": "Standard repair logic.",
                    "template_family": "A",
                    "wording_variant": "A_firm",
                    "primary_reason_code": "CLEAN"
                }
            },
            "advisory_banners": []
        }
    )
    result = provider.evaluate(clean_claim)
    assert "fnd_cln_1" in result["findings"]
    assert result["findings"]["fnd_cln_1"]["advisory_tone"] == "soft"

@patch('requests.post')
@patch.dict(os.environ, {"HERMES_VPS_URL": "http://mock-vps.local"})
def test_weak_photo_claim_triggers_vision(mock_post, weak_photo_claim):
    # This primarily tests the orchestrator mapping for vision
    # since RemoteHermesProvider only handles the external execution
    from services.hermes_orchestrator import build_hermes_payload
    
    # We mock the db and provider
    provider_mock = MagicMock()
    provider_mock.evaluate_vision.return_value = {"supports_damage": True, "confidence": 0.99, "notes": "visible dent", "error": None}
    
    # Needs valid evidence ref for vision trigger that evaluates specifically to weak
    weak_photo_claim["findings"][0]["evidence_refs"] = [{"url": "http://photo.jpg", "type": "photo", "support_status": "missing"}]
    
    # Not checking DB snippets here, assume empty
    db_mock = MagicMock()
    
    payload = build_hermes_payload(weak_photo_claim, weak_photo_claim["findings"], db_mock, provider_mock)
    
    # Because evidence is weak and it has a photo, vision should have triggered
    provider_mock.evaluate_vision.assert_called_once()
    assert weak_photo_claim["findings"][0]["vision_result"]["confidence"] == 0.99
