#!/usr/bin/env python3
"""
Test script to investigate missing SEC numbers for specific firms.
This script checks the SEC number display for firms that are reported to have missing SEC numbers.
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
        # Log the raw SEC search result if available
        if 'sec_search_result' in firm_details:
            sec_result = firm_details.get('sec_search_result', {})
            logger.info("SEC search result:")
            logger.info(f"  - firm_ia_sec_number: {sec_result.get('firm_ia_sec_number', 'Not found')}")
            logger.info(f"  - firm_ia_full_sec_number: {sec_result.get('firm_ia_full_sec_number', 'Not found')}")
        
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
            
            # Check if firm is inactive/expelled
            firm_status = entity_section.get("firm_status", "")
            is_inactive = firm_status.lower() == "inactive"
            
            # Check registration status
            registration_status = entity_section.get("registration_status", "")
            
            logger.info(f"Entity: {entity_name}")
            logger.info(f"CRD: {crd_number}")
            logger.info(f"SEC Number: {sec_number}")
            logger.info(f"Firm Status: {firm_status}")
            logger.info(f"Registration Status: {registration_status}")
            logger.info(f"Has NoActiveRegistration Alert: {has_no_active_registration_alert}")
            
            # Check if SEC number is missing but should be present
            if not sec_number or sec_number == "-":
                logger.warning(f"MISSING SEC NUMBER: {entity_name} (CRD: {crd_number})")
                
                # Check if we can find the SEC number in the raw data
                if 'basic_result' in report and 'raw_data' in report['basic_result']:
                    raw_data = report['basic_result']['raw_data']
                    if 'basicInformation' in raw_data:
                        basic_info = raw_data['basicInformation']
                        ia_sec_number = basic_info.get('iaSECNumber')
                        ia_sec_number_type = basic_info.get('iaSECNumberType')
                        bd_sec_number = basic_info.get('bdSECNumber')
                        
                        logger.info("Raw SEC number data:")
                        logger.info(f"  - iaSECNumber: {ia_sec_number}")
                        logger.info(f"  - iaSECNumberType: {ia_sec_number_type}")
                        logger.info(f"  - bdSECNumber: {bd_sec_number}")
                        
                        # Calculate what the SEC number should be
                        expected_sec_number = ""
                        if ia_sec_number and ia_sec_number_type:
                            expected_sec_number = f"{ia_sec_number_type}-{ia_sec_number}"
                        elif bd_sec_number:
                            expected_sec_number = f"8-{bd_sec_number}"
                            
                        if expected_sec_number:
                            logger.info(f"Expected SEC Number: {expected_sec_number}")
            
            return {
                "entity_name": entity_name,
                "crd_number": crd_number,
                "sec_number": sec_number,
                "firm_status": firm_status,
                "registration_status": registration_status,
                "has_no_active_registration_alert": has_no_active_registration_alert,
                "is_inactive": is_inactive
            }
        else:
            logger.error("Failed to generate compliance report")
    else:
        logger.error(f"No firm found with CRD: {crd_number}")
    
    return None

def main():
    """Test SEC number display for specific entities with reported missing SEC numbers."""
    # List of entities to test
    entities = [
        {"crd": "288357", "name": "QVR ADVISORS"},
        {"crd": "106108", "name": "BNY ADVISORS"},
        {"crd": "29116", "name": "Brookstone Securities, Inc."},
        {"crd": "110181", "name": "BROWN ADVISORY"},
        {"crd": "284175", "name": "GORDON DYAL & CO., LLC"}
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
        print(f"Firm Status: {result['firm_status']}")
        print(f"Registration Status: {result['registration_status']}")
        print(f"Has NoActiveRegistration Alert: {result['has_no_active_registration_alert']}")
        print(f"Is Inactive: {result['is_inactive']}")
        print("-" * 80)

if __name__ == "__main__":
    main()