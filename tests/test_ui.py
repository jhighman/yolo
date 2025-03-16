"""
Tests for the Firm Compliance API UI.
"""

import json
import pytest
import requests_mock
from typing import Dict, Any, Tuple

from ui import (
    api_call,
    render_claim_report,
    process_claim,
    clear_cache,
    clear_all_cache,
    clear_agent_cache,
    list_cache,
    cleanup_stale_cache,
    get_latest_compliance,
    get_compliance_by_ref,
    list_compliance_reports,
    API_BASE_URL
)

# Test data
MOCK_CLAIM_REQUEST = {
    "reference_id": "TEST_001",
    "business_ref": "BIZ_001",
    "business_name": "Test Business LLC",
    "tax_id": "12-3456789",
    "organization_crd": "123456",
    "webhook_url": "http://test.webhook.com/endpoint"
}

MOCK_CLAIM_RESPONSE = {
    "reference_id": "TEST_001",
    "claim": {
        "business_ref": "BIZ_001",
        "business_name": "Test Business LLC",
        "tax_id": "12-3456789",
        "organization_crd": "123456"
    },
    "final_evaluation": {
        "overall_compliance": True,
        "overall_risk_level": "LOW",
        "compliance_explanation": "All checks passed",
        "alerts": []
    },
    "search_evaluation": {
        "compliance": True,
        "compliance_explanation": "Found by CRD"
    },
    "registration_status": {
        "compliance": True,
        "compliance_explanation": "Active registration"
    }
}

MOCK_CACHE_LIST = {
    "status": "success",
    "cache": {
        "businesses": ["BIZ_001"],
        "files": ["cache/BIZ_001/report.json"]
    },
    "pagination": {
        "total_items": 1,
        "total_pages": 1,
        "current_page": 1,
        "page_size": 10
    }
}

@pytest.fixture
def mock_api():
    """Fixture to set up requests_mock for API calls."""
    with requests_mock.Mocker() as m:
        yield m

def test_api_call_get(mock_api):
    """Test GET request with api_call function."""
    mock_api.get(f"{API_BASE_URL}/test", json={"status": "success"})
    
    response = api_call("get", "/test")
    assert "success" in response
    assert mock_api.call_count == 1

def test_api_call_post(mock_api):
    """Test POST request with api_call function."""
    mock_api.post(f"{API_BASE_URL}/test", json={"status": "success"})
    
    response = api_call("post", "/test", {"key": "value"})
    assert "success" in response
    assert mock_api.call_count == 1

def test_api_call_error(mock_api):
    """Test error handling in api_call function."""
    mock_api.get(f"{API_BASE_URL}/test", status_code=500)
    
    response = api_call("get", "/test")
    assert "Error" in response
    assert "500" in response

def test_render_claim_report():
    """Test report rendering function."""
    report_json = json.dumps(MOCK_CLAIM_RESPONSE)
    html, json_output = render_claim_report(report_json)
    
    # Check HTML output
    assert "Compliance Report" in html
    assert "Test Business LLC" in html
    assert "BIZ_001" in html
    assert "LOW" in html
    
    # Check JSON output
    assert "TEST_001" in json_output
    assert "overall_compliance" in json_output

def test_render_claim_report_invalid_json():
    """Test report rendering with invalid JSON."""
    html, json_output = render_claim_report("invalid json")
    assert "Invalid report format" in html
    assert "invalid json" in json_output

def test_process_claim(mock_api):
    """Test claim processing function."""
    mock_api.post(f"{API_BASE_URL}/process-claim-basic", json=MOCK_CLAIM_RESPONSE)
    
    html, json_output = process_claim(
        reference_id="TEST_001",
        business_ref="BIZ_001",
        business_name="Test Business LLC",
        tax_id="12-3456789",
        organization_crd="123456",
        webhook_url="http://test.webhook.com/endpoint"
    )
    
    assert "Test Business LLC" in html
    assert "overall_compliance" in json_output
    assert mock_api.call_count == 1

def test_process_claim_missing_required(mock_api):
    """Test claim processing with missing required fields."""
    html, json_output = process_claim(
        reference_id="",
        business_ref="BIZ_001",
        business_name="Test Business LLC",
        tax_id="12-3456789",
        organization_crd="123456",
        webhook_url=""
    )
    
    assert "Please fill in all required fields" in html
    assert not json_output
    assert mock_api.call_count == 0

def test_cache_operations(mock_api):
    """Test cache management functions."""
    # Setup mock responses
    mock_api.post(f"{API_BASE_URL}/cache/clear/BIZ_001", json={"status": "success"})
    mock_api.post(f"{API_BASE_URL}/cache/clear-all", json={"status": "success"})
    mock_api.post(f"{API_BASE_URL}/cache/clear-agent/BIZ_001/SEC_Agent", json={"status": "success"})
    mock_api.get(f"{API_BASE_URL}/cache/list", json=MOCK_CACHE_LIST)
    mock_api.post(f"{API_BASE_URL}/cache/cleanup-stale", json={"status": "success"})
    
    # Test each cache operation
    assert "success" in clear_cache("BIZ_001")
    assert "success" in clear_all_cache()
    assert "success" in clear_agent_cache("BIZ_001", "SEC_Agent")
    assert "BIZ_001" in list_cache("BIZ_001", 1, 10)
    assert "success" in cleanup_stale_cache()
    
    assert mock_api.call_count == 5

def test_compliance_report_operations(mock_api):
    """Test compliance report retrieval functions."""
    mock_response = {"status": "success", "report": MOCK_CLAIM_RESPONSE}
    
    # Setup mock responses
    mock_api.get(f"{API_BASE_URL}/compliance/latest/BIZ_001", json=mock_response)
    mock_api.get(f"{API_BASE_URL}/compliance/by-ref/BIZ_001/TEST_001", json=mock_response)
    mock_api.get(f"{API_BASE_URL}/compliance/list", json={"status": "success", "reports": [mock_response]})
    
    # Test each compliance operation
    assert "success" in get_latest_compliance("BIZ_001")
    assert "success" in get_compliance_by_ref("BIZ_001", "TEST_001")
    assert "success" in list_compliance_reports("BIZ_001", 1, 10)
    
    assert mock_api.call_count == 3

def test_validation_errors():
    """Test input validation error handling."""
    # Test missing business ref
    assert "Error: Business Ref is required" in clear_cache("")
    assert "Error: Business Ref is required" in get_latest_compliance("")
    
    # Test missing reference ID
    assert "Error: Business Ref and Reference ID are required" in get_compliance_by_ref("BIZ_001", "")
    assert "Error: Business Ref and Reference ID are required" in get_compliance_by_ref("", "TEST_001")
    
    # Test missing agent name
    assert "Error: Business Ref and Agent Name are required" in clear_agent_cache("BIZ_001", "")
    assert "Error: Business Ref and Agent Name are required" in clear_agent_cache("", "SEC_Agent") 