#!/usr/bin/env python3
"""
Test script to investigate status alerts for FINRA-regulated entities.
This script checks why entities that are regulated by FINRA and have 'Approved' SEC Registration Status
are still showing status alerts in compliance reports.
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
    """Generate a compliance report for a firm with the given CRD number and analyze status alerts."""
    # Create facade
    facade = FirmServicesFacade()
    
    # Search parameters
    subject_id = f"test_subject_{crd_number}"
    
    # Search for firm by CRD
    logger.info(f"Searching for firm with CRD: {crd_number} ({entity_name})")
    firm_details = facade.search_firm_by_crd(subject_id, crd_number)
    
    if firm_details:
        # Log the raw FINRA search result if available
        if 'finra_search_result' in firm_details:
            finra_result = firm_details.get('finra_search_result', {})
            logger.info("FINRA search result:")
            logger.info(f"  - firm_name: {finra_result.get('firm_name', 'Not found')}")
            logger.info(f"  - crd_number: {finra_result.get('crd_number', 'Not found')}")
            logger.info(f"  - registration_status: {finra_result.get('registration_status', 'Not found')}")
            logger.info(f"  - firm_status: {finra_result.get('firm_status', 'Not found')}")
        
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
            
            # Check for status alerts
            status_evaluation = report.get("status_evaluation", {})
            compliance = status_evaluation.get("compliance", True)
            compliance_explanation = status_evaluation.get("compliance_explanation", "")
            alerts = status_evaluation.get("alerts", [])
            
            # Extract registration information
            entity_section = report.get("entity", {})
            registration_status = entity_section.get("registration_status", "")
            firm_status = entity_section.get("firm_status", "")
            is_finra_registered = entity_section.get("is_finra_registered", False)
            is_sec_registered = entity_section.get("is_sec_registered", False)
            
            # Log detailed information
            logger.info(f"Entity: {entity_name}")
            logger.info(f"CRD: {crd_number}")
            logger.info(f"Registration Status: {registration_status}")
            logger.info(f"Firm Status: {firm_status}")
            logger.info(f"Is FINRA Registered: {is_finra_registered}")
            logger.info(f"Is SEC Registered: {is_sec_registered}")
            logger.info(f"Status Compliance: {compliance}")
            logger.info(f"Status Compliance Explanation: {compliance_explanation}")
            logger.info(f"Has Status Alerts: {len(alerts) > 0}")
            
            # Log detailed alert information
            if alerts:
                logger.info("Status Alerts:")
                for i, alert in enumerate(alerts, 1):
                    logger.info(f"  Alert {i}:")
                    logger.info(f"    Type: {alert.get('alert_type', 'Unknown')}")
                    logger.info(f"    Severity: {alert.get('severity', 'Unknown')}")
                    logger.info(f"    Description: {alert.get('description', 'No description')}")
                    logger.info(f"    Category: {alert.get('alert_category', 'Unknown')}")
                    
                    # Log metadata if available
                    metadata = alert.get('metadata', {})
                    if metadata:
                        logger.info(f"    Metadata:")
                        for key, value in metadata.items():
                            logger.info(f"      {key}: {value}")
            
            # Check raw data for registration information
            basic_result = report.get("search_evaluation", {}).get("basic_result", {})
            raw_data = basic_result.get("raw_data", {})
            if raw_data:
                basic_info = raw_data.get("basicInformation", {})
                logger.info("Raw Registration Data:")
                logger.info(f"  FINRA Registered: {basic_info.get('finraRegistered', 'N/A')}")
                logger.info(f"  Firm Status: {basic_info.get('firmStatus', 'N/A')}")
                logger.info(f"  Regulator: {basic_info.get('regulator', 'N/A')}")
                logger.info(f"  BC Scope: {basic_info.get('bcScope', 'N/A')}")
                logger.info(f"  IA Scope: {basic_info.get('iaScope', 'N/A')}")
            
            return {
                "entity_name": entity_name,
                "crd_number": crd_number,
                "registration_status": registration_status,
                "firm_status": firm_status,
                "is_finra_registered": is_finra_registered,
                "is_sec_registered": is_sec_registered,
                "has_status_alerts": len(alerts) > 0,
                "status_alerts": alerts,
                "compliance_explanation": compliance_explanation
            }
        else:
            logger.error("Failed to generate compliance report")
    else:
        logger.error(f"No firm found with CRD: {crd_number}")
    
    return None

def main():
    """Test status alerts for specific FINRA-regulated entities."""
    # List of entities to test
    entities = [
        {"crd": "40290", "name": "GREENHILL & CO., LLC"},
        {"crd": "47936", "name": "Martinwolf"},
        {"crd": "17409", "name": "Martinson & Company, LTD."},
        {"crd": "100960", "name": "OUTCOME CAPITAL, LLC"},
        {"crd": "284175", "name": "Gordon Dyal & Co., LLC"}
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
        print(f"Registration Status: {result['registration_status']}")
        print(f"Firm Status: {result['firm_status']}")
        print(f"Is FINRA Registered: {result['is_finra_registered']}")
        print(f"Is SEC Registered: {result['is_sec_registered']}")
        print(f"Has Status Alerts: {result['has_status_alerts']}")
        if result['has_status_alerts']:
            print(f"Compliance Explanation: {result['compliance_explanation']}")
            print("Status Alerts:")
            for alert in result['status_alerts']:
                print(f"  - {alert.get('alert_type', 'Unknown')}: {alert.get('description', 'No description')}")
        print("-" * 80)

if __name__ == "__main__":
    main()