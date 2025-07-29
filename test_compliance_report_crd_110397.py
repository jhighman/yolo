#!/usr/bin/env python3
"""
Script to test compliance report generation for a firm with CRD 110397.
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
    """Test compliance report generation for firm with CRD 110397."""
    # First, let's test the direct API calls to see if the firm exists in either API
    crd_number = "110397"
    
    logger.info("Directly testing SEC API for CRD: %s", crd_number)
    sec_agent = SECFirmIAPDAgent(use_mock=False)  # Use real API, not mock data
    sec_result = sec_agent.search_firm_by_crd(crd_number)
    logger.info("SEC API direct result: %s", json.dumps(sec_result, indent=2, default=str) if sec_result else "No result")
    
    logger.info("Directly testing FINRA API for CRD: %s", crd_number)
    finra_agent = FinraFirmBrokerCheckAgent(use_mock=False)  # Use real API, not mock data
    finra_result = finra_agent.search_firm_by_crd(crd_number)
    logger.info("FINRA API direct result: %s", json.dumps(finra_result, indent=2, default=str) if finra_result else "No result")
    
    # Now let's try using the facade to search for the firm
    facade = FirmServicesFacade()
    subject_id = "test_subject"
    
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
            logger.info("✅ SUCCESS: Firm was found and compliance report generated")
        else:
            logger.error("❌ Failed to generate compliance report")
    else:
        logger.error("❌ No firm found with CRD: %s", crd_number)
        logger.error("This is unexpected as the firm should be found")
        
        # If the firm wasn't found, let's check if there might be an issue with the response structure
        logger.info("\nInvestigating potential response structure issues:")
        
        # Check if the direct API calls returned results
        if sec_result:
            logger.info("SEC API returned results, but the facade couldn't process them")
            logger.info("This suggests an issue with the SEC response structure handling")
        elif finra_result:
            logger.info("FINRA API returned results, but the facade couldn't process them")
            logger.info("This suggests an issue with the FINRA response structure handling")
        else:
            logger.info("Neither API returned results, suggesting the firm doesn't exist in either database")
            logger.info("This could be a data issue rather than a code issue")

if __name__ == "__main__":
    main()