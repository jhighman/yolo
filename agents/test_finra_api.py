#!/usr/bin/env python3
"""
Test script for FINRA BrokerCheck API.
This script runs a specific test case with the real API and logs the results.
"""

import sys
import os
import json
import logging
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from agents.finra_firm_broker_check_agent import FinraFirmBrokerCheckAgent
from agents.exceptions import RateLimitExceeded

# Configure logging
def setup_logging():
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'agents')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'finra_api_test.log')
    
    logger = logging.getLogger('finra_api_test')
    logger.setLevel(logging.DEBUG)
    
    # Create file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

# Sample entities for testing
SAMPLE_ENTITIES = [
    {
        "_id": {"$oid":"67bcdac22e749a352e23befe"},
        "type": "Thing/Other",
        "workProduct": "WP24-0037036",
        "entity": "EN-114236",
        "entityName": "Able Wealth Management, LLC",
        "name": "Able Wealth Management, LLC",
        "normalizedName": "ablewealthmanagementllc",
        "principal": "Able Wealth Management, LLC,",
        "street1": "695 Cross Street",
        "city": "Lakewood",
        "state": "New Jersey",
        "zip": "8701",
        "taxID": "",
        "organizationCRD": "298085",
        "status": "",
        "notes": "",
        "reference_id": "test-ref-001",
        "business_ref": "BIZ_001",
        "business_name": "Able Wealth Management, LLC",
        "tax_id": "123456789"
    },
    {
        "_id": {"$oid":"67bcdac22e749a352e23beff"},
        "type": "Thing/Other",
        "workProduct": "WP24-0037424",
        "entity": "EN-017252",
        "entityName": "Adell, Harriman & Carpenter, Inc.",
        "name": "Adell, Harriman & Carpenter, Inc.",
        "normalizedName": "adellharrimancarpenterinc",
        "principal": "Adell, Harriman & Carpenter, Inc.,",
        "street1": "2700 Post Oak Blvd. Suite 1200",
        "city": "Houston",
        "state": "Texas",
        "zip": "77056",
        "taxID": "",
        "organizationCRD": "107488",
        "status": "",
        "notes": "",
        "reference_id": "test-ref-002",
        "business_ref": "BIZ_002",
        "business_name": "Adell, Harriman & Carpenter, Inc.",
        "tax_id": "987654321"
    },
    {
        "_id": {"$oid":"67bcdac22e749a352e23bf00"},
        "type": "Thing/Other",
        "workProduct": "WP24-0036284",
        "entity": "EN-109946",
        "entityName": "ALLIANCE GLOBAL PARTNERS, LLC",
        "name": "ALLIANCE GLOBAL PARTNERS, LLC",
        "normalizedName": "allianceglobalpartnersllc",
        "principal": "ALLIANCE GLOBAL PARTNERS, LLC,",
        "street1": "88 Post Road West",
        "city": "Westport",
        "state": "Connecticut",
        "zip": "6880",
        "taxID": "",
        "organizationCRD": "8361",
        "status": "",
        "notes": "",
        "reference_id": "test-ref-003",
        "business_ref": "BIZ_003",
        "business_name": "ALLIANCE GLOBAL PARTNERS, LLC",
        "tax_id": "456789123"
    }
]

def run_tests():
    """Run tests for all sample entities using the real API."""
    logger.info("Starting FINRA BrokerCheck API tests with real API")
    
    # Create an agent with real API calls
    agent = FinraFirmBrokerCheckAgent(use_mock=False)
    logger.info("Created FINRA BrokerCheck agent with real API")
    
    employee_number = "EMP001"
    
    for i, entity in enumerate(SAMPLE_ENTITIES, 1):
        logger.info(f"Testing entity {i}: {entity['name']} (CRD: {entity['organizationCRD']})")
        
        try:
            # Test 1: Search firm by name
            logger.info(f"Test 1: Search firm by name: {entity['name']}")
            try:
                # Get the raw response first
                from agents.finra_firm_broker_check_agent import BROKERCHECK_CONFIG
                url = BROKERCHECK_CONFIG["firm_search_url"]
                params = {**BROKERCHECK_CONFIG["default_params"], "query": entity['name']}
                response = agent.session.get(url, params=params, timeout=(10, 30))
                
                if response.status_code == 200:
                    raw_data = response.json()
                    logger.info(f"Raw API response: {json.dumps(raw_data, indent=2)}")
                else:
                    logger.error(f"API returned status code: {response.status_code}")
                
                # Now try the actual method
                results = agent.search_firm(entity['name'])
                logger.info(f"Search results: {json.dumps(results, indent=2)}")
            except Exception as e:
                logger.error(f"Error in raw API call: {e}")
            
            # Test 2: Search firm by CRD
            logger.info(f"Test 2: Search firm by CRD: {entity['organizationCRD']}")
            results = agent.search_firm_by_crd(entity['organizationCRD'], employee_number)
            logger.info(f"Search results: {json.dumps(results, indent=2)}")
            
            # Test 3: Get firm details
            logger.info(f"Test 3: Get firm details for CRD: {entity['organizationCRD']}")
            details = agent.get_firm_details(entity['organizationCRD'], employee_number)
            logger.info(f"Firm details: {json.dumps(details, indent=2)}")
            
            # Test 4: Search entity (firm)
            logger.info(f"Test 4: Search entity (firm) for CRD: {entity['organizationCRD']}")
            data = agent.search_entity(entity['organizationCRD'], entity_type="firm", employee_number=employee_number)
            logger.info(f"Entity data: {json.dumps(data, indent=2)}")
            
            # Test 5: Get detailed entity info
            logger.info(f"Test 5: Get detailed entity info for CRD: {entity['organizationCRD']}")
            data = agent.search_entity_detailed_info(entity['organizationCRD'], entity_type="firm", employee_number=employee_number)
            logger.info(f"Detailed entity data: {json.dumps(data, indent=2)}")
            
        except RateLimitExceeded as e:
            logger.error(f"Rate limit error: {e}")
            break
        except Exception as e:
            logger.error(f"Error testing entity {entity['name']}: {e}")
        
        logger.info(f"Completed tests for entity {i}: {entity['name']}")
        logger.info("-" * 80)

if __name__ == "__main__":
    run_tests()
    logger.info("All tests completed")