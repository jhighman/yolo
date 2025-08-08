#!/usr/bin/env python3
"""
Test script for the FirmServicesFacade class with the three examples used in the agents.

This script tests the three main methods of the FirmServicesFacade class:
1. search_firm - Search for a firm by name
2. search_firm_by_crd - Search for a firm by CRD number
3. get_firm_details - Get detailed information about a firm by CRD number

The script uses the following examples:
1. "Baker Avenue Asset Management" (search by name)
2. "131940" (search by CRD number for Baker Avenue Asset Management)
3. "128066" (get firm details for BAKER STREET ADVISORS, LLC)
"""

import sys
import json
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from services.firm_services import FirmServicesFacade
from utils.logging_config import setup_logging

# Initialize logging
loggers = setup_logging(debug=True)
logger = loggers.get('test_firm_services', None)

def print_results(title, results):
    """Print results in a formatted way."""
    print(f"\n=== {title} ===")
    if results is None:
        print("No results found.")
    elif isinstance(results, list) and len(results) == 0:
        print("No results found.")
    else:
        print(json.dumps(results, indent=2))
    print("=" * (len(title) + 8))

def test_search_firm(facade, subject_id, firm_name):
    """Test searching for a firm by name."""
    print(f"\nSearching for firm: {firm_name}")
    results = facade.search_firm(subject_id, firm_name)
    print_results(f"Search Results for '{firm_name}'", results)
    return results

def test_search_firm_by_crd(facade, subject_id, crd_number):
    """Test searching for a firm by CRD number."""
    print(f"\nSearching for firm by CRD: {crd_number}")
    result = facade.search_firm_by_crd(subject_id, crd_number)
    print_results(f"Search Results for CRD '{crd_number}'", result)
    return result

def test_get_firm_details(facade, subject_id, crd_number):
    """Test getting detailed information about a firm by CRD number."""
    print(f"\nGetting firm details for CRD: {crd_number}")
    result = facade.get_firm_details(subject_id, crd_number)
    print_results(f"Firm Details for CRD '{crd_number}'", result)
    return result

def main():
    """Main entry point for the script."""
    # Create the facade
    facade = FirmServicesFacade()
    
    # Use a test subject ID
    subject_id = "test_user"
    
    # Example 1: Search for "Baker Avenue Asset Management"
    firm_name = "Baker Avenue Asset Management"
    test_search_firm(facade, subject_id, firm_name)
    
    # Example 2: Search for firm by CRD number "131940" (Baker Avenue Asset Management)
    crd_number = "131940"
    test_search_firm_by_crd(facade, subject_id, crd_number)
    
    # Example 3: Get firm details for CRD number "128066" (BAKER STREET ADVISORS, LLC)
    crd_number = "128066"
    test_get_firm_details(facade, subject_id, crd_number)
    
    # Additional examples from test_data.json
    print("\n\n=== Additional Examples from test_data.json ===")
    
    # Able Wealth Management, LLC (CRD: 298085)
    crd_number = "298085"
    test_get_firm_details(facade, subject_id, crd_number)
    
    # Adell, Harriman & Carpenter, Inc. (CRD: 107488)
    crd_number = "107488"
    test_get_firm_details(facade, subject_id, crd_number)
    
    # ALLIANCE GLOBAL PARTNERS, LLC (CRD: 8361)
    crd_number = "8361"
    test_get_firm_details(facade, subject_id, crd_number)

if __name__ == "__main__":
    main()