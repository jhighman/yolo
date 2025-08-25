#!/usr/bin/env python3
"""
Script to generate a full compliance report for a firm with CRD 133763 (Osaic Services, Inc).
This test verifies that the firm is correctly identified as active, addressing the issue
where it's incorrectly flagged as inactive. Note that this firm should have a Disclosure
alert, which is correct, but should not have a Status alert.
"""

import sys
import json
from pathlib import Path
import logging
from datetime import datetime

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent))

from services.firm_services import FirmServicesFacade
from services.firm_business import process_claim
from evaluation.firm_evaluation_processor import evaluate_registration_status

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Generate a full compliance report for firm with CRD 133763 (Osaic Services, Inc)."""
    # Create facade
    facade = FirmServicesFacade()
    
    # Search parameters
    subject_id = "test_subject"
    crd_number = "133763"
    
    # Search for firm by CRD
    logger.info(f"Searching for firm with CRD: {crd_number}")
    firm_details = facade.search_firm_by_crd(subject_id, crd_number)
    
    if firm_details:
        # Create a claim for processing
        claim = {
            "reference_id": f"test-ref-{crd_number}",
            "business_ref": f"BIZ_{crd_number}",
            "business_name": firm_details.get('firm_name', 'Unknown'),
            "organization_crd": crd_number
        }
        
        # Process the claim to generate a compliance report
        logger.info(f"Generating compliance report for {firm_details.get('firm_name', 'Unknown')} (CRD: {crd_number})")
        report = process_claim(
            claim=claim,
            facade=facade,
            business_ref=claim["business_ref"],
            skip_financials=False,
            skip_legal=False
        )
        
        if report:
            # Add the claim to the report
            report["claim"] = claim
            
            # Add timestamp
            report["generated_at"] = datetime.now().isoformat()
            
            # Save the report to a file
            output_file = f"compliance_report_{crd_number}.json"
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"Compliance report saved to {output_file}")
            
            # Verify registration status
            if "business_info" in report:
                business_info = report["business_info"]
                is_compliant, explanation, alerts = evaluate_registration_status(business_info)
                
                # Check if there are any InactiveExpelledFirm or NoActiveRegistration alerts
                status_alerts = [alert for alert in alerts if alert.alert_type in ["InactiveExpelledFirm", "NoActiveRegistration"]]
                
                if status_alerts:
                    logger.error("FAIL: Firm incorrectly flagged with status alerts:")
                    for alert in status_alerts:
                        logger.error(f"  - {alert.alert_type}: {alert.description}")
                    logger.error("Expected: Firm should be identified as active")
                    
                    # Print relevant status fields from the report for debugging
                    logger.info("Status fields in report:")
                    logger.info(f"  - firm_status: {business_info.get('firm_status', 'Not found')}")
                    logger.info(f"  - is_sec_registered: {business_info.get('is_sec_registered', 'Not found')}")
                    logger.info(f"  - is_finra_registered: {business_info.get('is_finra_registered', 'Not found')}")
                    logger.info(f"  - is_state_registered: {business_info.get('is_state_registered', 'Not found')}")
                    logger.info(f"  - registration_status: {business_info.get('registration_status', 'Not found')}")
                    
                    # If SEC search result is available, print it
                    if 'sec_search_result' in business_info:
                        sec_result = business_info.get('sec_search_result', {})
                        logger.info("SEC search result:")
                        logger.info(f"  - registration_status: {sec_result.get('registration_status', 'Not found')}")
                        logger.info(f"  - firm_ia_scope: {sec_result.get('firm_ia_scope', 'Not found')}")
                else:
                    logger.info("PASS: Firm correctly identified as active")
                    logger.info(f"Explanation: {explanation}")
                
                # Check for disclosure alerts - these should be present for this firm
                disclosure_flag = business_info.get('firm_ia_disclosure_fl', '')
                logger.info(f"Disclosure flag: {disclosure_flag}")
                if disclosure_flag and disclosure_flag.upper() in ["Y", "YES"]:
                    logger.info("PASS: Firm correctly has disclosure flag")
                else:
                    logger.warning("NOTE: Expected disclosure flag to be present")
            
            # Print the report
            print(json.dumps(report, indent=2, default=str))
        else:
            logger.error("Failed to generate compliance report")
    else:
        logger.error(f"No firm found with CRD: {crd_number}")

if __name__ == "__main__":
    main()