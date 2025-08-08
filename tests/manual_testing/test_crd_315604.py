#!/usr/bin/env python3
"""
Test script for the firm_business.py module with CRD 315604.

This script tests the process_claim function in firm_business.py with CRD 315604.
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
logger = loggers.get('test_crd_315604', None)

def print_report_section(title, section):
    """Print a section of the report in a formatted way."""
    print(f"\n=== {title} ===")
    if section is None:
        print("No data available.")
    else:
        print(json.dumps(section, indent=2))
    print("=" * (len(title) + 8))

def test_with_crd(facade, subject_id, crd_number):
    """Test process_claim with CRD number."""
    print(f"\nTesting process_claim with CRD: {crd_number}")
    
    # Create a claim with CRD number
    claim = {
        "organization_crd": crd_number,
        "business_ref": f"TEST_BIZ_{crd_number}",
        "reference_id": f"TEST_REF_{crd_number}"
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
    
    # Test with CRD number "315604"
    crd_number = "315604"
    test_with_crd(facade, subject_id, crd_number)

if __name__ == "__main__":
    main()