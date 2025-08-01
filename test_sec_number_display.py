#!/usr/bin/env python3
"""
Test script to verify SEC number display for entities with Status alerts.
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

def test_entity(crd_number, entity_name):
    """Generate a compliance report for a firm with the given CRD number and verify SEC number display."""
    # Create facade
    facade = FirmServicesFacade()
    
    # Search parameters
    subject_id = f"test_subject_{crd_number}"
    
    # Search for firm by CRD
    logger.info(f"Searching for firm with CRD: {crd_number} ({entity_name})")
    firm_details = facade.search_firm_by_crd(subject_id, crd_number)
    
    if firm_details:
        # Create a claim for processing
        claim = {
            "reference_id": f"test-ref-{crd_number}",
            "business_ref": f"BIZ_{crd_number}",
            "business_name": entity_name,
            "organization_crd": crd_number
        }
        
        # Process the claim to generate a compliance report
        logger.info(f"Generating compliance report for {entity_name} (CRD: {crd_number})")
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
            
            # Check if SEC number is present in the entity section
            entity_section = report.get("entity", {})
            sec_number = entity_section.get("sec_number", "")
            
            # Check if there's a NoActiveRegistration alert
            status_evaluation = report.get("status_evaluation", {})
            alerts = status_evaluation.get("alerts", [])
            has_no_active_registration_alert = any(
                alert.get("alert_type") == "NoActiveRegistration" for alert in alerts
            )
            
            logger.info(f"Entity: {entity_name}")
            logger.info(f"CRD: {crd_number}")
            logger.info(f"SEC Number: {sec_number}")
            logger.info(f"Has NoActiveRegistration Alert: {has_no_active_registration_alert}")
            
            return {
                "entity_name": entity_name,
                "crd_number": crd_number,
                "sec_number": sec_number,
                "has_no_active_registration_alert": has_no_active_registration_alert
            }
        else:
            logger.error("Failed to generate compliance report")
    else:
        logger.error(f"No firm found with CRD: {crd_number}")
    
    return None

def main():
    """Test SEC number display for specific entities."""
    # List of entities to test
    entities = [
        {"crd": "10863", "name": "GATE US LLC"},
        {"crd": "8605", "name": "WALLACH FX OPTIONS INC."},
        {"crd": "110397", "name": "ZWJ INVESTMENT COUNSEL INC"},
        {"crd": "16688", "name": "ADAMS SECURITIES, INC."}
    ]
    
    results = []
    for entity in entities:
        result = test_entity(entity["crd"], entity["name"])
        if result:
            results.append(result)
    
    # Print summary
    print("\nTest Results Summary:")
    print("-" * 80)
    for result in results:
        print(f"Entity: {result['entity_name']}")
        print(f"CRD: {result['crd_number']}")
        print(f"SEC Number: {result['sec_number']}")
        print(f"Has NoActiveRegistration Alert: {result['has_no_active_registration_alert']}")
        print("-" * 80)

if __name__ == "__main__":
    main()