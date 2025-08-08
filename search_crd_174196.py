#!/usr/bin/env python3
"""
Script to search for a firm with CRD 174196 and evaluate its registration status.
"""

import sys
import json
from pathlib import Path
import logging

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent))

from services.firm_services import FirmServicesFacade
from evaluation.firm_evaluation_processor import evaluate_registration_status

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Search for firm with CRD 174196 and evaluate its registration status."""
    # Create facade
    facade = FirmServicesFacade()
    
    # Search parameters
    subject_id = "test_subject"
    crd_number = "174196"
    
    # Search for firm by CRD
    logger.info(f"Searching for firm with CRD: {crd_number}")
    firm_details = facade.search_firm_by_crd(subject_id, crd_number)
    
    if firm_details:
        # Print firm details
        logger.info(f"Found firm: {firm_details.get('firm_name', 'Unknown')}")
        logger.info(f"CRD: {firm_details.get('crd_number', 'Unknown')}")
        logger.info(f"Source: {firm_details.get('source', 'Unknown')}")
        logger.info(f"Firm status: {firm_details.get('firm_status', 'Unknown')}")
        logger.info(f"is_finra_registered: {firm_details.get('is_finra_registered', False)}")
        logger.info(f"is_sec_registered: {firm_details.get('is_sec_registered', False)}")
        
        # Evaluate registration status
        is_compliant, explanation, alerts = evaluate_registration_status(firm_details)
        
        # Print evaluation results
        logger.info(f"Registration status compliant: {is_compliant}")
        logger.info(f"Explanation: {explanation}")
        logger.info("Alerts:")
        for alert in alerts:
            logger.info(f"  - {alert.alert_type}: {alert.description} (Severity: {alert.severity.value})")
        
        # Print full details for debugging
        logger.debug(f"Full firm details: {json.dumps(firm_details, indent=2, default=str)}")
    else:
        logger.error(f"No firm found with CRD: {crd_number}")

if __name__ == "__main__":
    main()