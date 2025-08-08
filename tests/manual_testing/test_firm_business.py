#!/usr/bin/env python3
"""
Test script for the firm_business.py module.

This script tests the process_claim function in firm_business.py with different search strategies:
1. CRD_ONLY - Search by CRD number
2. NAME_ONLY - Search by business name

The script will help verify that the firm_business.py module correctly handles the "Search unavailable"
condition from the FINRA API and falls back to the SEC agent appropriately.
"""

import sys
import json
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from services.firm_services import FirmServicesFacade
from services.firm_business import process_claim
from utils.logging_config import setup_logging

# Initialize logging
loggers = setup_logging(debug=True)
logger = loggers.get('test_firm_business', None)

def print_report_section(title, section):
    """Print a section of the report in a formatted way."""
    print(f"\n=== {title} ===")
    if section is None:
        print("No data available.")
    else:
        print(json.dumps(section, indent=2))
    print("=" * (len(title) + 8))

def test_with_crd(facade, subject_id, crd_number, business_name=None):
    """Test process_claim with CRD number."""
    print(f"\nTesting process_claim with CRD: {crd_number}")
    
    # Create a claim with CRD number
    claim = {
        "organization_crd": crd_number,
        "business_ref": f"TEST_BIZ_{crd_number}",
        "reference_id": f"TEST_REF_{crd_number}"
    }
    
    if business_name:
        claim["business_name"] = business_name
    
    # Process the claim
    try:
        report = process_claim(claim, facade, business_ref=claim["business_ref"])
        
        # Print the report sections
        print_report_section("Search Evaluation", report.get("search_evaluation"))
        print_report_section("Registration Status", report.get("registration_status"))
        print_report_section("Regulatory Oversight", report.get("regulatory_oversight"))
        print_report_section("Disclosures", report.get("disclosures"))
        print_report_section("Data Integrity", report.get("data_integrity"))
        
        return report
    except Exception as e:
        print(f"Error processing claim: {e}")
        return None

def test_with_name(facade, subject_id, business_name):
    """Test process_claim with business name."""
    print(f"\nTesting process_claim with business name: {business_name}")
    
    # Create a claim with business name
    claim = {
        "business_name": business_name,
        "business_ref": f"TEST_BIZ_{business_name.replace(' ', '_')}",
        "reference_id": f"TEST_REF_{business_name.replace(' ', '_')}"
    }
    
    # Process the claim
    try:
        report = process_claim(claim, facade, business_ref=claim["business_ref"])
        
        # Print the report sections
        print_report_section("Search Evaluation", report.get("search_evaluation"))
        print_report_section("Registration Status", report.get("registration_status"))
        print_report_section("Regulatory Oversight", report.get("regulatory_oversight"))
        print_report_section("Disclosures", report.get("disclosures"))
        print_report_section("Data Integrity", report.get("data_integrity"))
        
        return report
    except Exception as e:
        print(f"Error processing claim: {e}")
        return None

def main():
    """Main entry point for the script."""
    # Create the facade
    facade = FirmServicesFacade()
    
    # Use a test subject ID
    subject_id = "test_user"
    
    # Example 1: Test with CRD number "131940" (Baker Avenue Asset Management)
    crd_number = "131940"
    test_with_crd(facade, subject_id, crd_number)
    
    # Example 2: Test with business name "Baker Avenue Asset Management"
    business_name = "Baker Avenue Asset Management"
    test_with_name(facade, subject_id, business_name)
    
    # Example 3: Test with CRD number "8361" (ALLIANCE GLOBAL PARTNERS)
    crd_number = "8361"
    test_with_crd(facade, subject_id, crd_number)
    
    # Example 4: Test with business name "ALLIANCE GLOBAL PARTNERS"
    business_name = "ALLIANCE GLOBAL PARTNERS"
    test_with_name(facade, subject_id, business_name)

if __name__ == "__main__":
    main()