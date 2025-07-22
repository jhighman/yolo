#!/usr/bin/env python3
"""
Test script to generate a compliance report for CRD 133763.
This will test the updated disclosure evaluation functionality with a real firm.
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent))

from utils.logging_config import setup_logging
from services.firm_business import process_claim
from services.firm_services import FirmServicesFacade

# Initialize logging
loggers = setup_logging(debug=True)
logger = logging.getLogger(__name__)

def main():
    """Generate a compliance report for CRD 133763."""
    logger.info("Generating compliance report for CRD 133763")
    
    # Create a claim for the firm
    claim = {
        "reference_id": "test-ref-133763",
        "business_ref": "BIZ_133763",
        "business_name": "FIRM CRD 133763",
        "organization_crd": "133763"
    }
    
    # Create a facade for data retrieval
    facade = FirmServicesFacade()
    
    # Process the claim to generate a compliance report
    # We'll set skip_adv=True to use our new default setting
    report = process_claim(claim, facade, skip_adv=True)
    
    # Save the report to a file for inspection
    output_file = f"compliance_report_crd_133763_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Compliance report saved to {output_file}")
    
    # Print a summary of the report
    print("\nCompliance Report Summary:")
    print(f"Firm: {report.get('entity', {}).get('firm_name', 'Unknown')}")
    print(f"CRD: {report.get('entity', {}).get('crd_number', 'Unknown')}")
    print(f"Overall Compliance: {report.get('final_evaluation', {}).get('overall_compliance', False)}")
    print(f"Risk Level: {report.get('final_evaluation', {}).get('overall_risk_level', 'Unknown')}")
    
    # Print disclosure evaluation details
    disclosure_review = report.get('disclosure_review', {})
    print("\nDisclosure Evaluation:")
    print(f"Compliance: {disclosure_review.get('compliance', False)}")
    print(f"Explanation: {disclosure_review.get('compliance_explanation', 'Unknown')}")
    
    # Print alerts from disclosure evaluation
    alerts = disclosure_review.get('alerts', [])
    if alerts:
        print("\nDisclosure Alerts:")
        for alert in alerts:
            print(f"  - [{alert.get('severity', 'UNKNOWN')}] {alert.get('alert_type', 'Unknown')}: {alert.get('description', 'No description')}")
    else:
        print("\nNo disclosure alerts found.")

if __name__ == "__main__":
    main()