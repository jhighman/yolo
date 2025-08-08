#!/usr/bin/env python3
"""
Script to generate a full compliance report for a firm with CRD 17409.
This script is used to investigate an unexpected search failure for MARTINSON & COMPANY, LTD.
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
    """Generate a full compliance report for firm with CRD 17409."""
    # Create facade
    facade = FirmServicesFacade()
    
    # Search parameters
    subject_id = "test_subject_17409"
    crd_number = "17409"
    
    # Search for firm by CRD
    logger.info(f"Searching for firm with CRD: {crd_number}")
    firm_details = facade.search_firm_by_crd(subject_id, crd_number)
    
    # Log the raw response for debugging
    logger.info(f"Raw firm details: {json.dumps(firm_details, indent=2, default=str)}")
    
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
            
            # Print the report
            print(json.dumps(report, indent=2, default=str))
        else:
            logger.error("Failed to generate compliance report")
    else:
        logger.error(f"No firm found with CRD: {crd_number}")
        
        # Try to get more information about the failure
        try:
            # Try to search directly using the marshaller functions
            from services.firm_marshaller import fetch_sec_firm_by_crd, fetch_finra_firm_by_crd
            
            logger.info("Attempting direct search with marshaller functions...")
            search_firm_id = f"search_crd_{crd_number}"
            
            # Search SEC
            sec_response = fetch_sec_firm_by_crd(subject_id, search_firm_id, {"crd_number": crd_number})
            if hasattr(sec_response, 'data') and sec_response.data:
                logger.info(f"SEC search result: {json.dumps(sec_response.data, indent=2, default=str)}")
            else:
                logger.info("No SEC search result found")
            
            # Search FINRA
            finra_response = fetch_finra_firm_by_crd(subject_id, search_firm_id, {"crd_number": crd_number})
            if hasattr(finra_response, 'data') and finra_response.data:
                logger.info(f"FINRA search result: {json.dumps(finra_response.data, indent=2, default=str)}")
            else:
                logger.info("No FINRA search result found")
        except Exception as e:
            logger.error(f"Error during direct search: {str(e)}")

if __name__ == "__main__":
    main()