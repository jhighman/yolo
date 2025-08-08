import logging
import sys
from pathlib import Path

# Add parent directory to Python path to import evaluation module
sys.path.append(str(Path(__file__).parent))

from evaluation.firm_evaluation_processor import evaluate_registration_status

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_registration_status')

def test_with_mock_data():
    """Test the evaluate_registration_status function with mock data."""
    
    # Test cases to verify the function correctly finds firm_ia_scope in different locations
    test_cases = [
        {
            "name": "Case 1: firm_ia_scope in main business_info",
            "data": {
                "is_sec_registered": True,
                "is_finra_registered": False,
                "is_state_registered": False,
                "registration_status": "APPROVED",
                "firm_ia_scope": "ACTIVE",
                "last_updated": "2025-01-01T00:00:00Z",
                "data_sources": ["SEC", "FINRA"]
            },
            "expected_result": True,
            "expected_location": "main business_info"
        },
        {
            "name": "Case 2: firm_ia_scope in sec_search_result",
            "data": {
                "is_sec_registered": True,
                "is_finra_registered": False,
                "is_state_registered": False,
                "registration_status": "APPROVED",
                "sec_search_result": {
                    "firm_ia_scope": "ACTIVE"
                },
                "last_updated": "2025-01-01T00:00:00Z",
                "data_sources": ["SEC", "FINRA"]
            },
            "expected_result": True,
            "expected_location": "sec_search_result"
        },
        {
            "name": "Case 3: firm_ia_scope in finra_search_result",
            "data": {
                "is_sec_registered": True,
                "is_finra_registered": False,
                "is_state_registered": False,
                "registration_status": "APPROVED",
                "finra_search_result": {
                    "status": "found",
                    "firm_ia_scope": "ACTIVE"
                },
                "last_updated": "2025-01-01T00:00:00Z",
                "data_sources": ["SEC", "FINRA"]
            },
            "expected_result": True,
            "expected_location": "finra_search_result"
        },
        {
            "name": "Case 4: firm_ia_scope is INACTIVE",
            "data": {
                "is_sec_registered": True,
                "is_finra_registered": False,
                "is_state_registered": False,
                "registration_status": "APPROVED",
                "firm_ia_scope": "INACTIVE",
                "last_updated": "2025-01-01T00:00:00Z",
                "data_sources": ["SEC", "FINRA"]
            },
            "expected_result": True,  # Still compliant because registration_status is APPROVED
            "expected_location": "main business_info"
        },
        {
            "name": "Case 5: firm_ia_scope not found anywhere",
            "data": {
                "is_sec_registered": True,
                "is_finra_registered": False,
                "is_state_registered": False,
                "registration_status": "APPROVED",
                "last_updated": "2025-01-01T00:00:00Z",
                "data_sources": ["SEC", "FINRA"]
            },
            "expected_result": True,  # Still compliant because registration_status is APPROVED
            "expected_location": "not found"
        },
        {
            "name": "Case 6: registration_status is not APPROVED but firm_ia_scope is ACTIVE",
            "data": {
                "is_sec_registered": False,
                "is_finra_registered": False,
                "is_state_registered": False,
                "registration_status": "PENDING",
                "sec_search_result": {
                    "firm_ia_scope": "ACTIVE"
                },
                "last_updated": "2025-01-01T00:00:00Z",
                "data_sources": ["SEC", "FINRA"]
            },
            "expected_result": False,  # Not compliant because registration_status is PENDING
            "expected_location": "sec_search_result"
        },
        {
            "name": "Case 7: registration_status is TERMINATED",
            "data": {
                "is_sec_registered": False,
                "is_finra_registered": False,
                "is_state_registered": False,
                "registration_status": "TERMINATED",
                "firm_ia_scope": "ACTIVE",  # Even with ACTIVE scope, TERMINATED status should fail
                "last_updated": "2025-01-01T00:00:00Z",
                "data_sources": ["SEC", "FINRA"]
            },
            "expected_result": False,  # Not compliant because registration_status is TERMINATED
            "expected_location": "main business_info"
        }
    ]
    
    # Run each test case
    for i, case in enumerate(test_cases):
        logger.info(f"Running {case['name']}")
        
        # Call the function
        is_compliant, explanation, alerts = evaluate_registration_status(case['data'])
        
        # Check if the result matches the expected result
        result_matches = is_compliant == case['expected_result']
        
        # Log the results
        logger.info(f"Expected result: {case['expected_result']}")
        logger.info(f"Actual result: {is_compliant}")
        logger.info(f"Explanation: {explanation}")
        
        # Check where firm_ia_scope was found
        if case['expected_location'] == "main business_info":
            found = "firm_ia_scope" in case['data']
            logger.info(f"firm_ia_scope found in main business_info: {found}")
        elif case['expected_location'] == "sec_search_result":
            found = "sec_search_result" in case['data'] and "firm_ia_scope" in case['data']['sec_search_result']
            logger.info(f"firm_ia_scope found in sec_search_result: {found}")
        elif case['expected_location'] == "finra_search_result":
            found = "finra_search_result" in case['data'] and "firm_ia_scope" in case['data']['finra_search_result']
            logger.info(f"firm_ia_scope found in finra_search_result: {found}")
        else:
            logger.info("firm_ia_scope not expected to be found")
        
        # Log any alerts
        if alerts:
            logger.info(f"Alerts ({len(alerts)}):")
            for alert in alerts:
                logger.info(f"  - [{alert.severity.value}] {alert.alert_type}: {alert.description}")
        else:
            logger.info("No alerts generated")
        
        # Log the test result
        if result_matches:
            logger.info("TEST PASSED ✓")
        else:
            logger.error("TEST FAILED ✗")
        
        logger.info("-" * 50)

if __name__ == "__main__":
    test_with_mock_data()