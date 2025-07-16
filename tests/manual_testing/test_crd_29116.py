#!/usr/bin/env python3
"""
Test script for the firm_business.py module with CRD 29116.

This script tests the process_claim function in firm_business.py with CRD 29116
(BROOKSTONE SECURITIES, INC), which is an inactive/expelled firm.
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
logger = loggers.get('test_crd_29116', None)

def print_report_section(title, section):
    """Print a section of the report in a formatted way."""
    print(f"\n=== {title} ===")
    if section is None:
        print("No data available.")
    else:
        print(json.dumps(section, indent=2))
    print("=" * (len(title) + 8))

def test_with_crd(facade, subject_id, crd_number, entity_name=None):
    """Test process_claim with CRD number."""
    print(f"\nTesting process_claim with CRD: {crd_number}")
    
    # Create a claim with CRD number
    claim = {
        "organization_crd": crd_number,
        "business_ref": f"TEST_BIZ_{crd_number}",
        "reference_id": f"TEST_REF_{crd_number}"
    }
    
    # Add entity name if provided
    if entity_name:
        claim["entityName"] = entity_name
    
    # Process the claim
    try:
        report = process_claim(claim, facade, business_ref=claim["business_ref"])
        
        # Print the report sections
        print_report_section("Search Evaluation", report.get("search_evaluation"))
        print_report_section("Status Evaluation", report.get("status_evaluation"))
        print_report_section("Disclosure Review", report.get("disclosure_review"))
        print_report_section("Disciplinary Evaluation", report.get("disciplinary_evaluation"))
        print_report_section("Arbitration Review", report.get("arbitration_review"))
        print_report_section("Final Evaluation", report.get("final_evaluation"))
        
        # Print firm status information from search_evaluation
        if "search_evaluation" in report and "basic_result" in report["search_evaluation"]:
            basic_result = report["search_evaluation"]["basic_result"]
            print("\nFirm Status Information from Search Evaluation:")
            print(f"Status: {basic_result.get('firm_status', 'N/A')}")
            print(f"Message: {basic_result.get('status_message', 'N/A')}")
        
        # Print firm status information from status_evaluation
        if "status_evaluation" in report and "alerts" in report["status_evaluation"]:
            print("\nFirm Status Information from Status Evaluation:")
            for i, alert in enumerate(report["status_evaluation"]["alerts"]):
                print(f"Alert {i+1}:")
                print(f"  Type: {alert.get('alert_type', 'N/A')}")
                print(f"  Description: {alert.get('description', 'N/A')}")
                if "metadata" in alert:
                    print(f"  Metadata: {json.dumps(alert['metadata'], indent=4)}")
        
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
    
    # Test with CRD number "29116" (BROOKSTONE SECURITIES, INC)
    crd_number = "29116"
    entity_name = "BROOKSTONE SECURITIES, INC"
    test_with_crd(facade, subject_id, crd_number, entity_name)

if __name__ == "__main__":
    main()