#!/usr/bin/env python3
"""
Test script for the FINRA BrokerCheck agent.
This script tests the agent's ability to search for firms by CRD number
and handle connection errors with retry logic.
"""

import sys
import os
import time
from agents.finra_firm_broker_check_agent import FinraFirmBrokerCheckAgent

def test_search_firm_by_crd():
    """Test searching for a firm by CRD number."""
    print("Testing search_firm_by_crd method...")
    
    # Create an agent with real API access (not mock)
    agent = FinraFirmBrokerCheckAgent(use_mock=False)
    
    # Test with a known CRD number (Gordon Dyal & Co., LLC - CRD: 165308)
    crd_number = "165308"
    print(f"Searching for firm with CRD: {crd_number}")
    
    try:
        results = agent.search_firm_by_crd(crd_number)
        if results:
            print(f"Success! Found firm: {results[0].get('firm_name', 'Unknown')}")
            return True
        else:
            print(f"No results found for CRD: {crd_number}")
            return False
    except Exception as e:
        print(f"Error searching for firm by CRD: {e}")
        return False

def test_search_entity():
    """Test searching for an entity by CRD number."""
    print("\nTesting search_entity method...")
    
    # Create an agent with real API access (not mock)
    agent = FinraFirmBrokerCheckAgent(use_mock=False)
    
    # Test with a known CRD number (Gordon Dyal & Co., LLC - CRD: 165308)
    crd_number = "165308"
    print(f"Searching for entity with CRD: {crd_number}")
    
    try:
        result = agent.search_entity(crd_number, entity_type="firm")
        if result:
            print(f"Success! Found entity data for CRD: {crd_number}")
            return True
        else:
            print(f"No entity data found for CRD: {crd_number}")
            return False
    except Exception as e:
        print(f"Error searching for entity by CRD: {e}")
        return False

def test_get_firm_details():
    """Test getting firm details by CRD number."""
    print("\nTesting get_firm_details method...")
    
    # Create an agent with real API access (not mock)
    agent = FinraFirmBrokerCheckAgent(use_mock=False)
    
    # Test with a known CRD number (Gordon Dyal & Co., LLC - CRD: 165308)
    crd_number = "165308"
    print(f"Getting details for firm with CRD: {crd_number}")
    
    try:
        details = agent.get_firm_details(crd_number)
        if details:
            print(f"Success! Got firm details for CRD: {crd_number}")
            return True
        else:
            print(f"No firm details found for CRD: {crd_number}")
            return False
    except Exception as e:
        print(f"Error getting firm details by CRD: {e}")
        return False

def main():
    """Run all tests."""
    print("Starting FINRA BrokerCheck Agent tests...")
    
    success_count = 0
    total_tests = 3
    
    if test_search_firm_by_crd():
        success_count += 1
    
    if test_search_entity():
        success_count += 1
    
    if test_get_firm_details():
        success_count += 1
    
    print(f"\nTest results: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("All tests passed! The FINRA BrokerCheck agent is working correctly.")
        return 0
    else:
        print("Some tests failed. Please check the logs for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())