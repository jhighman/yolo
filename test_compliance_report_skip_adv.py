#!/usr/bin/env python3
"""
Script to generate a full compliance report with ADV evaluation skipped.
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
    """Generate a full compliance report with ADV evaluation skipped."""
    # Create facade
    facade = FirmServicesFacade()
    
    # Search parameters
    subject_id = "test_subject"
    crd_number = "284175"  # Gordon Dyal & Co., LLC
    
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
        
        # Process the claim to generate a compliance report with ADV evaluation skipped
        logger.info(f"Generating compliance report for {firm_details.get('firm_name', 'Unknown')} (CRD: {crd_number}) with ADV evaluation skipped")
        report = process_claim(
            claim=claim,
            facade=facade,
            business_ref=claim["business_ref"],
            skip_financials=False,
            skip_legal=False,
            skip_adv=True  # Skip ADV evaluation
        )
        
        if report:
            # Add the claim to the report
            report["claim"] = claim
            
            # Add timestamp
            report["generated_at"] = datetime.now().isoformat()
            
            # Save the report to a file
            output_file = f"compliance_report_{crd_number}_skip_adv.json"
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