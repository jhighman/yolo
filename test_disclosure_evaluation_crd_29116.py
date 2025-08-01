#!/usr/bin/env python3
"""
Script to test disclosure evaluation for BROOKSTONE SECURITIES, INC. (CRD 29116).
This script investigates why disclosures are not being properly flagged in the evaluation report.
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
from evaluation.firm_evaluation_processor import evaluate_disclosures

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Test disclosure evaluation for BROOKSTONE SECURITIES, INC. (CRD 29116)."""
    # Create facade
    facade = FirmServicesFacade()
    
    # Search parameters
    subject_id = "test_subject_29116"
    crd_number = "29116"
    
    # Search for firm by CRD
    logger.info(f"Searching for firm with CRD: {crd_number}")
    firm_details = facade.search_firm_by_crd(subject_id, crd_number)
    
    if firm_details:
        # Log disclosure flag from raw data
        disclosure_flag = None
        if 'raw_data' in firm_details and 'iaDisclosureFlag' in firm_details['raw_data']:
            disclosure_flag = firm_details['raw_data']['iaDisclosureFlag']
            logger.info(f"Disclosure flag from raw data: {disclosure_flag}")
        elif 'raw_data' in firm_details and 'basicInformation' in firm_details['raw_data'] and 'iaDisclosureFlag' in firm_details['raw_data']['basicInformation']:
            disclosure_flag = firm_details['raw_data']['basicInformation']['iaDisclosureFlag']
            logger.info(f"Disclosure flag from raw data: {disclosure_flag}")
        
        # Check SEC search result for disclosure flag
        if 'sec_search_result' in firm_details and 'firm_ia_disclosure_fl' in firm_details['sec_search_result']:
            sec_disclosure_flag = firm_details['sec_search_result']['firm_ia_disclosure_fl']
            logger.info(f"Disclosure flag from SEC search result: {sec_disclosure_flag}")
            if disclosure_flag is None:
                disclosure_flag = sec_disclosure_flag
        
        # Check if disclosures are present in the firm details
        if 'disclosures' in firm_details:
            logger.info(f"Disclosures in firm_details: {json.dumps(firm_details['disclosures'], indent=2)}")
        else:
            logger.warning("No disclosures field in firm_details")
            
        # If disclosure flag is 'Y' but no disclosures field, this is an issue
        if (disclosure_flag == 'Y' or disclosure_flag == 'YES') and 'disclosures' not in firm_details:
            logger.error("ISSUE DETECTED: Disclosure flag is 'Y' but no disclosures field is present in firm_details")
        
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
            
            # Check disclosure evaluation in the report
            if 'disclosure_review' in report:
                logger.info(f"Disclosure review in report: {json.dumps(report['disclosure_review'], indent=2)}")
                
                # Manually evaluate disclosures to compare
                logger.info("Manually evaluating disclosures...")
                firm_data = report.get('entity', {})
                business_name = report.get('entity', {}).get('firm_name', 'Unknown')
                
                # Check if disclosure flag is present but disclosures are missing
                disclosure_flag = None
                if 'sec_search_result' in report['search_evaluation'] and 'firm_ia_disclosure_fl' in report['search_evaluation']['sec_search_result']:
                    disclosure_flag = report['search_evaluation']['sec_search_result']['firm_ia_disclosure_fl']
                    logger.info(f"Disclosure flag in report: {disclosure_flag}")
                
                # Get disclosures from firm data
                disclosures = firm_data.get('disclosures', [])
                
                # Create mock FINRA disclosures for testing the fallback
                finra_disclosures = None
                if disclosure_flag == 'Y' and not disclosures:
                    logger.info("Creating mock FINRA disclosures for testing fallback")
                    finra_disclosures = [
                        {
                            "type": "Regulatory",
                            "date": datetime.now().strftime("%Y-%m-%d"),
                            "status": "UNRESOLVED",
                            "description": "Mock FINRA disclosure for testing"
                        }
                    ]
                
                # Use the updated evaluate_disclosures function with disclosure_flag and finra_disclosures parameters
                is_compliant, explanation, alerts = evaluate_disclosures(disclosures, business_name, disclosure_flag, finra_disclosures)
                
                # Convert to a format that can be logged as JSON
                manual_evaluation_result = {
                    "compliance": is_compliant,
                    "explanation": explanation,
                    "alerts": [alert.to_dict() for alert in alerts]
                }
                logger.info(f"Manual disclosure evaluation: {json.dumps(manual_evaluation_result, indent=2)}")
                
                # Compare with the report's evaluation
                if report['disclosure_review']['compliance'] != is_compliant:
                    logger.error(f"Discrepancy in disclosure evaluation: report={report['disclosure_review']['compliance']}, manual={is_compliant}")
                else:
                    logger.info("Disclosure evaluation matches between report and manual check")
            else:
                logger.warning("No disclosure_review in report")
            
            # Save the report to a file
            output_file = f"compliance_report_{crd_number}.json"
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"Compliance report saved to {output_file}")
            
            # Print the report
            print(json.dumps(report, indent=2, default=str))
        else:
            logger.error("Failed to generate compliance report")
    else:
        logger.error(f"No firm found with CRD: {crd_number}")

if __name__ == "__main__":
    main()