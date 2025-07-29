#!/usr/bin/env python3
"""
Script to generate a full compliance report for a firm with CRD 172089.
This script tests if the firm is found and has a Status alert as expected.
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
from agents.finra_firm_broker_check_agent import FinraFirmBrokerCheckAgent
from agents.sec_firm_iapd_agent import SECFirmIAPDAgent

# Set up logging
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Generate a full compliance report for firm with CRD 172089 and verify Status alert."""
    # Create facade
    facade = FirmServicesFacade()
    
    # Search parameters
    subject_id = "test_subject"
    crd_number = "172089"
    
    # Search for firm by CRD using the facade
    logger.info("Searching for firm with CRD: %s using facade", crd_number)
    firm_details = facade.search_firm_by_crd(subject_id, crd_number)
    
    if firm_details:
        logger.info("Firm details found: %s", json.dumps(firm_details, indent=2, default=str))
        
        # Create a claim for processing
        claim = {
            "reference_id": f"test-ref-{crd_number}",
            "business_ref": f"BIZ_{crd_number}",
            "business_name": firm_details.get('firm_name', 'Unknown'),
            "organization_crd": crd_number
        }
        
        # Process the claim to generate a compliance report
        logger.info("Generating compliance report for %s (CRD: %s)", firm_details.get('firm_name', 'Unknown'), crd_number)
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
            output_file = f"compliance_report_crd_{crd_number}.json"
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info("Compliance report saved to %s", output_file)
            
            # Check for Status alert
            status_alerts = []
            if 'status_evaluation' in report and 'alerts' in report['status_evaluation']:
                status_alerts = report['status_evaluation']['alerts']
            
            if status_alerts:
                logger.info("✅ SUCCESS: Status alerts found as expected:")
                for alert in status_alerts:
                    logger.info("  - %s: %s", alert.get('alert_type', 'Unknown'), alert.get('description', 'No description'))
            else:
                logger.error("❌ FAILURE: No Status alerts found, but they were expected")
            
            # Evaluate registration status
            logger.info("Evaluating registration status")
            business_info = report.get('entity', {})
            if 'basic_result' in report.get('search_evaluation', {}):
                basic_result = report['search_evaluation']['basic_result']
                business_info['source'] = report.get('search_evaluation', {}).get('source')
                if 'raw_data' in basic_result:
                    business_info['raw_data'] = basic_result['raw_data']
            
            is_compliant, explanation, alerts = evaluate_registration_status(business_info)
            
            logger.info("Registration status: %s", "Compliant" if is_compliant else "Non-compliant")
            logger.info("Explanation: %s", explanation)
            
            # Print success message
            logger.info("\n✅ SUCCESS: Compliance report generated for CRD 172089")
            logger.info("The firm was found and Status alerts were checked")
        else:
            logger.error("❌ Failed to generate compliance report")
    else:
        logger.error("❌ No firm found with CRD: %s", crd_number)
        logger.error("This is unexpected as the firm should be found")
        
        # Direct API calls to diagnose the issue
        logger.info("\nDiagnosing the issue with direct API calls:")
        
        logger.info("Directly testing SEC API for CRD: %s", crd_number)
        sec_agent = SECFirmIAPDAgent(use_mock=False)
        sec_result = sec_agent.search_firm_by_crd(crd_number)
        logger.info("SEC API direct result: %s", json.dumps(sec_result, indent=2, default=str) if sec_result else "No result")
        
        logger.info("Directly testing FINRA API for CRD: %s", crd_number)
        finra_agent = FinraFirmBrokerCheckAgent(use_mock=False)
        finra_result = finra_agent.search_firm_by_crd(crd_number)
        logger.info("FINRA API direct result: %s", json.dumps(finra_result, indent=2, default=str) if finra_result else "No result")

if __name__ == "__main__":
    main()