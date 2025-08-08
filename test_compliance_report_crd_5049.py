#!/usr/bin/env python3
"""
Script to generate a full compliance report for a firm with CRD 5049.
This script tests how the SEC number is populated in the compliance report.
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
    """Generate a full compliance report for firm with CRD 5049 with focus on SEC number."""
    # Create facade
    facade = FirmServicesFacade()
    
    # Search parameters
    subject_id = "test_subject"
    crd_number = "5049"
    
    # Direct API calls to diagnose the issue
    logger.info("Directly testing SEC API for CRD: %s", crd_number)
    sec_agent = SECFirmIAPDAgent(use_mock=False)
    sec_result = sec_agent.search_firm_by_crd(crd_number)
    logger.info("SEC API direct result: %s", json.dumps(sec_result, indent=2, default=str) if sec_result else "No result")
    
    logger.info("Directly testing FINRA API for CRD: %s", crd_number)
    finra_agent = FinraFirmBrokerCheckAgent(use_mock=False)
    finra_result = finra_agent.search_firm_by_crd(crd_number)
    logger.info("FINRA API direct result: %s", json.dumps(finra_result, indent=2, default=str) if finra_result else "No result")
    
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
            
            # Examine SEC number in the report
            entity_sec_number = report.get('entity', {}).get('sec_number', 'Not found')
            logger.info("SEC number in entity section: %s", entity_sec_number)
            
            basic_result_sec_number = report.get('search_evaluation', {}).get('basic_result', {}).get('sec_number', 'Not found')
            logger.info("SEC number in basic_result section: %s", basic_result_sec_number)
            
            # Check if SEC number is in raw data
            raw_data = report.get('search_evaluation', {}).get('basic_result', {}).get('raw_data', {})
            if raw_data:
                basic_info = raw_data.get('basicInformation', {})
                if basic_info:
                    ia_sec_number = basic_info.get('iaSECNumber', 'Not found')
                    ia_sec_number_type = basic_info.get('iaSECNumberType', 'Not found')
                    bd_sec_number = basic_info.get('bdSECNumber', 'Not found')
                    
                    logger.info("Raw data SEC numbers:")
                    logger.info("  IA SEC Number: %s", ia_sec_number)
                    logger.info("  IA SEC Number Type: %s", ia_sec_number_type)
                    logger.info("  BD SEC Number: %s", bd_sec_number)
                    
                    # Check if full SEC number is constructed correctly
                    if ia_sec_number != 'Not found' and ia_sec_number_type != 'Not found':
                        expected_full_sec = f"{ia_sec_number_type}-{ia_sec_number}"
                        logger.info("Expected full SEC number: %s", expected_full_sec)
                        
                        if expected_full_sec == entity_sec_number:
                            logger.info("✅ SEC number is correctly formatted in entity section")
                        else:
                            logger.error("❌ SEC number format mismatch in entity section")
            
            # Evaluate registration status
            logger.info("Evaluating registration status")
            # Extract the entity information from the report for evaluation
            business_info = report.get('entity', {})
            # Add additional fields that might be in basic_result
            if 'basic_result' in report.get('search_evaluation', {}):
                basic_result = report['search_evaluation']['basic_result']
                # Add source information
                business_info['source'] = report.get('search_evaluation', {}).get('source')
                # Add raw_data if available
                if 'raw_data' in basic_result:
                    business_info['raw_data'] = basic_result['raw_data']
            
            is_compliant, explanation, alerts = evaluate_registration_status(business_info)
            
            logger.info("Registration status: %s", "Compliant" if is_compliant else "Non-compliant")
            logger.info("Explanation: %s", explanation)
            
            # Print the report
            print(json.dumps(report, indent=2, default=str))
        else:
            logger.error("Failed to generate compliance report")
    else:
        logger.error("No firm found with CRD: %s", crd_number)

if __name__ == "__main__":
    main()