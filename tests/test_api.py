"""
Tests for the FastAPI application endpoints.
"""

import json
from typing import Dict, Any
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

# Import from services package
from services import FirmServicesFacade, process_claim
from api import app

# Create test client
client = TestClient(app)

# Mock data
MOCK_CLAIM_REQUEST = {
    "reference_id": "TEST_001",
    "business_ref": "BIZ_001",
    "business_name": "Test Business LLC",
    "tax_id": "12-3456789",
    "organization_crd": "123456",
    "webhook_url": "http://test.webhook.com/endpoint"
}

MOCK_FIRM_DETAILS = {
    "firm_id": "123456",
    "firm_name": "Test Business LLC",
    "crd_number": "123456",
    "sec_number": "801-12345",
    "registration_status": "Approved",
    "business_type": "LLC"
}

MOCK_COMPLIANCE_REPORT = {
    "reference_id": "TEST_001",
    "business_name": "Test Business LLC",
    "compliance_status": "PASS",
    "evaluation_date": "2024-03-14",
    "alerts": []
}

@pytest.fixture
def mock_facade():
    """Create a mock FirmServicesFacade."""
    mock = Mock(spec=FirmServicesFacade)
    mock.search_firm.return_value = [MOCK_FIRM_DETAILS]
    mock.get_firm_details.return_value = MOCK_FIRM_DETAILS
    mock.save_compliance_report.return_value = True
    return mock

@pytest.fixture
def mock_process_claim():
    """Create a mock process_claim function."""
    return Mock(return_value=MOCK_COMPLIANCE_REPORT)

def test_process_claim_basic_success(mock_facade, mock_process_claim):
    """Test successful basic claim processing."""
    with patch('api.facade', mock_facade), \
         patch('api.process_claim', mock_process_claim):
        
        response = client.post("/process-claim-basic", json=MOCK_CLAIM_REQUEST)
        
        assert response.status_code == 200
        assert response.json() == MOCK_COMPLIANCE_REPORT
        
        # Verify process_claim was called with correct parameters
        mock_process_claim.assert_called_once()
        call_args = mock_process_claim.call_args[1]
        assert call_args['business_ref'] == MOCK_CLAIM_REQUEST['business_ref']
        assert call_args['skip_financials'] is True
        assert call_args['skip_legal'] is True

def test_process_claim_basic_failure(mock_facade, mock_process_claim):
    """Test failed claim processing."""
    mock_process_claim.side_effect = Exception("Processing failed")
    
    with patch('api.facade', mock_facade), \
         patch('api.process_claim', mock_process_claim):
        
        response = client.post("/process-claim-basic", json=MOCK_CLAIM_REQUEST)
        
        assert response.status_code == 500
        assert "Processing failed" in response.json()['detail']

def test_get_processing_modes():
    """Test retrieving available processing modes."""
    response = client.get("/processing-modes")
    
    assert response.status_code == 200
    assert "basic" in response.json()
    assert response.json()["basic"]["skip_disciplinary"] is True
    assert response.json()["basic"]["skip_regulatory"] is True

@pytest.mark.asyncio
async def test_cache_operations():
    """Test cache management endpoints."""
    # Test clear cache
    response = client.post("/cache/clear/BIZ_001")
    assert response.status_code == 200
    
    # Test list cache
    response = client.get("/cache/list")
    assert response.status_code == 200
    
    # Test cleanup stale cache
    response = client.post("/cache/cleanup-stale")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_compliance_retrieval():
    """Test compliance report retrieval endpoints."""
    # Test get latest compliance
    response = client.get("/compliance/latest/BIZ_001")
    assert response.status_code == 200
    
    # Test get compliance by reference
    response = client.get("/compliance/by-ref/BIZ_001/TEST_001")
    assert response.status_code == 200
    
    # Test list compliance reports
    response = client.get("/compliance/list")
    assert response.status_code == 200

def test_invalid_claim_request():
    """Test handling of invalid claim request."""
    invalid_request = {
        "reference_id": "TEST_001"  # Missing required fields
    }
    
    response = client.post("/process-claim-basic", json=invalid_request)
    assert response.status_code == 422  # Validation error

def test_missing_webhook_url():
    """Test claim processing without webhook URL."""
    request_data = MOCK_CLAIM_REQUEST.copy()
    del request_data['webhook_url']
    
    with patch('api.facade'), patch('api.process_claim', return_value=MOCK_COMPLIANCE_REPORT):
        response = client.post("/process-claim-basic", json=request_data)
        assert response.status_code == 200
        assert response.json() == MOCK_COMPLIANCE_REPORT

if __name__ == "__main__":
    pytest.main(["-v"])