#!/usr/bin/env python3
"""
Test script for the updated disclosure evaluation functionality.
This script tests the new format of disclosures with disclosureType and disclosureCount.
"""

import json
import logging
from evaluation.firm_evaluation_processor import evaluate_disclosures, Alert, AlertSeverity
from utils.logging_config import setup_logging

# Initialize logging
loggers = setup_logging(debug=True)
logger = loggers.get('test', logging.getLogger(__name__))

def main():
    """Test the updated disclosure evaluation functionality."""
    print("Testing disclosure evaluation with new format...")
    
    # Test case 1: New format with multiple disclosure types
    test_disclosures_new_format = [
        {
            "disclosureType": "Regulatory Event",
            "disclosureCount": 10
        },
        {
            "disclosureType": "Arbitration",
            "disclosureCount": 3
        },
        {
            "disclosureType": "Bond",
            "disclosureCount": 1
        }
    ]
    
    # Test case 2: Old format for backward compatibility
    test_disclosures_old_format = [
        {
            "status": "RESOLVED",
            "date": "2020-01-15",
            "description": "Regulatory action resolved"
        },
        {
            "status": "PENDING",
            "date": "2023-05-20",
            "description": "Ongoing investigation"
        }
    ]
    
    # Test case 3: Empty disclosures
    test_disclosures_empty = []
    
    # Run tests
    business_name = "TEST FIRM"
    
    print("\n=== Test Case 1: New Format ===")
    compliant, explanation, alerts = evaluate_disclosures(test_disclosures_new_format, business_name)
    print_results(compliant, explanation, alerts)
    
    print("\n=== Test Case 2: Old Format ===")
    compliant, explanation, alerts = evaluate_disclosures(test_disclosures_old_format, business_name)
    print_results(compliant, explanation, alerts)
    
    print("\n=== Test Case 3: Empty Disclosures ===")
    compliant, explanation, alerts = evaluate_disclosures(test_disclosures_empty, business_name)
    print_results(compliant, explanation, alerts)

def print_results(compliant, explanation, alerts):
    """Print the results of the evaluation."""
    print(f"Compliant: {compliant}")
    print(f"Explanation: {explanation}")
    print("Alerts:")
    for alert in alerts:
        print(f"  - [{alert.severity.value}] {alert.alert_type}: {alert.description}")
        print(f"    Metadata: {json.dumps(alert.metadata, indent=2)}")

if __name__ == "__main__":
    main()