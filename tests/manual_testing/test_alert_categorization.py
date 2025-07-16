#!/usr/bin/env python3
"""
Test script to verify alert categorization for inactive/expelled firms.
This script tests that the InactiveExpelledFirm alert is properly categorized
as "Registration Issue" in the final compliance report.

Usage:
    python test_alert_categorization.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from services.firm_services import FirmServicesFacade
from services.firm_business import process_claim
from evaluation.firm_evaluation_report_builder import FirmEvaluationReportBuilder
from evaluation.firm_evaluation_report_director import FirmEvaluationReportDirector

def print_report_section(title, section):
    """Print a section of the report in a formatted way."""
    print(f"\n=== {title} ===")
    if section is None:
        print("No data available.")
    else:
        print(json.dumps(section, indent=2))
    print("=" * (len(title) + 8))

def test_inactive_expelled_firm_categorization():
    """Test that InactiveExpelledFirm alerts are properly categorized as Registration Issue."""
    print("\n=== Testing Alert Categorization for Inactive/Expelled Firms ===\n")
    
    # Initialize the services
    firm_services = FirmServicesFacade()
    
    # Test with BROOKSTONE SECURITIES, INC (CRD #29116)
    crd_number = "29116"
    firm_name = "BROOKSTONE SECURITIES, INC"
    subject_id = f"TEST_{crd_number}"
    
    # Create a claim with CRD number
    claim = {
        "organization_crd": crd_number,
        "business_ref": f"TEST_BIZ_{crd_number}",
        "reference_id": f"TEST_REF_{crd_number}",
        "business_name": firm_name,
        "entityName": firm_name
    }
    
    # Process the claim
    print(f"Processing claim for {firm_name} (CRD #{crd_number})...")
    report = process_claim(claim, firm_services, business_ref=claim["business_ref"])
    
    # Print the report sections
    print_report_section("Search Evaluation", report.get("search_evaluation"))
    print_report_section("Status Evaluation", report.get("status_evaluation"))
    print_report_section("Final Evaluation", report.get("final_evaluation"))
    
    # Check if the report contains the InactiveExpelledFirm alert
    # and if it's properly categorized as "Registration Issue"
    found_alert = False
    correct_category = False
    
    # Check in final_evaluation alerts
    if "final_evaluation" in report and "alerts" in report["final_evaluation"]:
        for alert in report["final_evaluation"]["alerts"]:
            if alert.get("alert_type") == "InactiveExpelledFirm":
                found_alert = True
                print(f"\nFound InactiveExpelledFirm alert in final_evaluation:")
                print(f"  Alert type: {alert.get('alert_type')}")
                print(f"  Alert category: {alert.get('alert_category')}")
                print(f"  Description: {alert.get('description')}")
                
                if alert.get("alert_category") == "REGISTRATION":
                    correct_category = True
                    print("✅ Alert is correctly categorized as 'Registration Issue'")
                else:
                    print(f"❌ Alert is incorrectly categorized as '{alert.get('alert_category')}' instead of 'Registration Issue'")
    
    # Also check in status_evaluation alerts as a fallback
    if not found_alert and "status_evaluation" in report and "alerts" in report["status_evaluation"]:
        for alert in report["status_evaluation"]["alerts"]:
            if alert.get("alert_type") == "InactiveExpelledFirm":
                found_alert = True
                print(f"\nFound InactiveExpelledFirm alert in status_evaluation:")
                print(f"  Alert type: {alert.get('alert_type')}")
                print(f"  Alert category: {alert.get('alert_category')}")
                print(f"  Description: {alert.get('description')}")
                
                # The category might be different in status_evaluation vs final_evaluation
                if alert.get("alert_category") == "REGISTRATION":
                    correct_category = True
                    print("✅ Alert is correctly categorized as 'Registration Issue'")
                else:
                    print(f"❌ Alert is incorrectly categorized as '{alert.get('alert_category')}' instead of 'Registration Issue'")
    
    if not found_alert:
        print("\n❌ InactiveExpelledFirm alert was not found in the report")
        return False
    
    if not correct_category:
        print("\n❌ InactiveExpelledFirm alert was found but has incorrect category")
        return False
    
    print("\n✅ Test passed: InactiveExpelledFirm alert is properly categorized as 'Registration Issue'")
    return True

def main():
    """Main entry point for the script."""
    success = test_inactive_expelled_firm_categorization()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()