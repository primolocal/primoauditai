import pytest
from unittest.mock import patch, MagicMock
import requests
from fastapi.testclient import TestClient

from api.main import app
import storage.review_repository

# Sample AuditRun to be loaded by repo.get_audit_run
MOCK_AUDIT_RUN = {
    "run_id": "test_run_123",
    "ingestion_status": "normalized",
    "hermes_status": "pending",
    "claim_package": {},
    "vehicle_profile": {},
    "shop_profile": {},
    "estimate_lines": {},
    "evidence_matrix": {}
}

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_repo():
    with patch("api.main.repo.get_audit_run", return_value=MOCK_AUDIT_RUN.copy()) as mock_get, \
         patch("api.main.repo.save_audit_run") as mock_save:
         yield {"get": mock_get, "save": mock_save}

@patch("requests.post")
def test_hermes_success(mock_post, client, mock_repo):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "tasks": {"tasks": [{"id": "t1"}], "total_tasks": 1, "resolved_tasks": 0},
        "findings": [{"id": "f1"}],
        "scorecard": {},
        "narrative": {}
    }
    mock_post.return_value = mock_resp
    
    response = client.post("/api/audits/A123/retry-hermes")
    assert response.status_code == 200
    
    saved = mock_repo["save"].call_args_list[-1][0][1]
    assert saved["hermes_status"] == "success"
    assert saved["manual_review_mode"] is False
    assert saved["hermes_run_metadata"]["hermes_status"] == "success"

@patch("requests.post")
def test_hermes_timeout(mock_post, client, mock_repo):
    mock_post.side_effect = requests.exceptions.Timeout("Read timeout")
    
    response = client.post("/api/audits/A123/retry-hermes")
    assert response.status_code == 500
    
    saved = mock_repo["save"].call_args_list[-1][0][1]
    assert saved["hermes_status"] == "failed"
    assert saved["manual_review_mode"] is True
    assert saved["hermes_run_metadata"]["hermes_error_code"] == "timeout"

@patch("requests.post")
def test_hermes_connection_error(mock_post, client, mock_repo):
    mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")
    
    response = client.post("/api/audits/A123/retry-hermes")
    assert response.status_code == 500
    
    saved = mock_repo["save"].call_args_list[-1][0][1]
    assert saved["hermes_status"] == "failed"
    assert saved["manual_review_mode"] is True
    assert saved["hermes_run_metadata"]["hermes_error_code"] == "connection_error"

@patch("requests.post")
def test_hermes_500_error(mock_post, client, mock_repo):
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    # Provide the HTTPError from raise_for_status
    mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error", response=mock_resp)
    mock_post.return_value = mock_resp
    
    response = client.post("/api/audits/A123/retry-hermes")
    assert response.status_code == 500
    
    saved = mock_repo["save"].call_args_list[-1][0][1]
    assert saved["hermes_status"] == "failed"
    assert saved["manual_review_mode"] is True
    assert saved["hermes_run_metadata"]["hermes_error_code"] == "5xx"

@patch("requests.post")
def test_hermes_invalid_schema(mock_post, client, mock_repo):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    # Simulate valid HTTP but missing tasks payload
    mock_resp.json.return_value = {
        "tasks": {"tasks": [], "total_tasks": 0, "resolved_tasks": 0}
    }
    mock_post.return_value = mock_resp
    
    response = client.post("/api/audits/A123/retry-hermes")
    assert response.status_code == 500
    
    saved = mock_repo["save"].call_args_list[-1][0][1]
    assert saved["hermes_status"] == "failed"
    assert saved["manual_review_mode"] is True
    assert saved["hermes_run_metadata"]["hermes_error_code"] == "invalid_response_schema"
