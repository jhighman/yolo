#!/usr/bin/env python3
"""
Script to generate a full compliance report for a firm with CRD 112694.
This script is used to investigate connection reset issues and search failures for
CONSOLIDATED PORTFOLIO REVIEW CORP.
"""

import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent))

from services.firm_services import FirmServicesFacade
from services.firm_business import process_claim
from services.firm_marshaller import fetch_sec_firm_by_crd, fetch_finra_firm_by_crd, ResponseStatus

# Set up logging
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Generate a full compliance report for firm with CRD 112694."""
    # Create facade with increased service delay to handle potential rate limiting
    facade = FirmServicesFacade()
    facade.service_delay = 6  # Increase delay between API calls to 6 seconds
    
    # Search parameters
    subject_id = "test_subject_112694"
    crd_number = "112694"
    
    # Search for firm by CRD
    logger.info(f"Searching for firm with CRD: {crd_number}")
    
    # First try direct search with marshaller functions to diagnose connection issues
    try:
        logger.info("Attempting direct search with marshaller functions first...")
        search_firm_id = f"search_crd_{crd_number}"
        
        # Search SEC
        logger.info("Searching SEC IAPD for firm by CRD...")
        max_retries = 3
        sec_response = None
        
        for attempt in range(max_retries):
            try:
                sec_response = fetch_sec_firm_by_crd(subject_id, search_firm_id, {"crd_number": crd_number})
                if sec_response.status == ResponseStatus.SUCCESS and sec_response.data:
                    logger.info(f"SEC search successful on attempt {attempt+1}")
                    logger.info(f"SEC search result: {json.dumps(sec_response.data, indent=2, default=str)}")
                    break
                else:
                    logger.warning(f"SEC search attempt {attempt+1} failed with status: {sec_response.status}")
            except Exception as e:
                logger.error(f"SEC search attempt {attempt+1} error: {str(e)}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5  # Exponential backoff
                    logger.info(f"Waiting {wait_time} seconds before retrying SEC search...")
                    time.sleep(wait_time)
        
        # Search FINRA
        logger.info("Searching FINRA BrokerCheck for firm by CRD...")
        finra_response = None
        
        for attempt in range(max_retries):
            try:
                finra_response = fetch_finra_firm_by_crd(subject_id, search_firm_id, {"crd_number": crd_number})
                if finra_response.status == ResponseStatus.SUCCESS and finra_response.data:
                    logger.info(f"FINRA search successful on attempt {attempt+1}")
                    logger.info(f"FINRA search result: {json.dumps(finra_response.data, indent=2, default=str)}")
                    break
                else:
                    logger.warning(f"FINRA search attempt {attempt+1} failed with status: {finra_response.status}")
            except Exception as e:
                logger.error(f"FINRA search attempt {attempt+1} error: {str(e)}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5  # Exponential backoff
                    logger.info(f"Waiting {wait_time} seconds before retrying FINRA search...")
                    time.sleep(wait_time)
    
    except Exception as e:
        logger.error(f"Error during direct search: {str(e)}")
    
    # Now proceed with the regular search using the facade
    logger.info("Now proceeding with regular search using FirmServicesFacade...")
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