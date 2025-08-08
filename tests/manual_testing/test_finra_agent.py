#!/usr/bin/env python3
"""
Test script specifically for the FINRA BrokerCheck API agent.
This script isolates the FINRA agent to test it directly without the facade.
"""

import sys
import json
import logging
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from agents.finra_firm_broker_check_agent import FinraFirmBrokerCheckAgent, BROKERCHECK_CONFIG
from utils.logging_config import setup_logging

# Initialize logging
loggers = setup_logging(debug=True)
logger = loggers.get('test_finra_agent', None)

def test_search_firm(agent, firm_name, use_mock=False):
    """Test searching for a firm by name with detailed logging of the raw API response."""
    print(f"\nTesting search_firm with {'MOCK' if use_mock else 'REAL'} API: {firm_name}")
    
    try:
        # First, get the raw response to examine what the API is returning
        if not use_mock:
            url = BROKERCHECK_CONFIG["firm_search_url"]
            params = {**BROKERCHECK_CONFIG["default_params"], "query": firm_name}
            print(f"Making direct API request to: {url}")
            print(f"With parameters: {params}")
            
            response = agent.session.get(url, params=params, timeout=(10, 30))
            print(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                raw_data = response.json()
                print("Raw API response:")
                print(json.dumps(raw_data, indent=2))
                
                # Check for API error messages
                if "errorCode" in raw_data and raw_data["errorCode"] != 0:
                    error_msg = raw_data.get("errorMessage", "Unknown API error")
                    print(f"API returned error: {error_msg} (Code: {raw_data['errorCode']})")
            else:
                print(f"API returned non-200 status code: {response.status_code}")
        
        # Now use the agent's method
        print("\nUsing agent.search_firm method:")
        results = agent.search_firm(firm_name)
        print(f"Results from agent.search_firm:")
        print(json.dumps(results, indent=2))
        return results
        
    except Exception as e:
        print(f"Error during test: {e}")
        return None

def test_search_firm_by_crd(agent, crd_number, use_mock=False):
    """Test searching for a firm by CRD number."""
    print(f"\nTesting search_firm_by_crd with {'MOCK' if use_mock else 'REAL'} API: {crd_number}")
    
    try:
        results = agent.search_firm_by_crd(crd_number)
        print(f"Results from agent.search_firm_by_crd:")
        print(json.dumps(results, indent=2))
        return results
    except Exception as e:
        print(f"Error during test: {e}")
        return None

def test_get_firm_details(agent, crd_number, use_mock=False):
    """Test getting detailed information about a firm by CRD number."""
    print(f"\nTesting get_firm_details with {'MOCK' if use_mock else 'REAL'} API: {crd_number}")
    
    try:
        details = agent.get_firm_details(crd_number)
        print(f"Results from agent.get_firm_details:")
        print(json.dumps(details, indent=2))
        return details
    except Exception as e:
        print(f"Error during test: {e}")
        return None

def main():
    """Main entry point for the script."""
    # Test data
    firm_name = "Baker Avenue Asset Management"
    crd_number = "131940"  # Baker Avenue Asset Management
    
    # Test with real API
    print("\n=== TESTING WITH REAL API ===")
    real_agent = FinraFirmBrokerCheckAgent(use_mock=False)
    test_search_firm(real_agent, firm_name)
    test_search_firm_by_crd(real_agent, crd_number)
    test_get_firm_details(real_agent, crd_number)
    
    # Test with mock API
    print("\n=== TESTING WITH MOCK API ===")
    mock_agent = FinraFirmBrokerCheckAgent(use_mock=True)
    test_search_firm(mock_agent, firm_name, use_mock=True)
    test_search_firm_by_crd(mock_agent, crd_number, use_mock=True)
    test_get_firm_details(mock_agent, crd_number, use_mock=True)
    
    # Test with a different firm name to see if the issue is specific to "Baker Avenue Asset Management"
    alt_firm_name = "ALLIANCE GLOBAL PARTNERS"
    alt_crd_number = "8361"
    
    print("\n=== TESTING WITH ALTERNATIVE FIRM (REAL API) ===")
    test_search_firm(real_agent, alt_firm_name)
    test_search_firm_by_crd(real_agent, alt_crd_number)
    test_get_firm_details(real_agent, alt_crd_number)

if __name__ == "__main__":
    main()