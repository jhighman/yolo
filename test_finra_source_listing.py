#!/usr/bin/env python3
"""
Test script to verify source listings for FINRA-regulated entities.
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
    """Generate a compliance report for a firm with the given CRD number and verify source listing."""
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
            
            # Check source in various sections of the report
            search_evaluation = report.get("search_evaluation", {})
            status_evaluation = report.get("status_evaluation", {})
            final_evaluation = report.get("final_evaluation", {})
            
            search_source = search_evaluation.get("source", "")
            status_source = status_evaluation.get("source", "")
            final_source = final_evaluation.get("source", "")
            
            # Check if firm is regulated by FINRA
            basic_result = search_evaluation.get("basic_result", {})
            is_finra_registered = basic_result.get("is_finra_registered", False)
            is_sec_registered = basic_result.get("is_sec_registered", False)
            
            logger.info(f"Entity: {entity_name}")
            logger.info(f"CRD: {crd_number}")
            logger.info(f"Is FINRA Registered: {is_finra_registered}")
            logger.info(f"Is SEC Registered: {is_sec_registered}")
            logger.info(f"Source in search_evaluation: {search_source}")
            logger.info(f"Source in status_evaluation: {status_source}")
            logger.info(f"Source in final_evaluation: {final_source}")
            
            return {
                "entity_name": entity_name,
                "crd_number": crd_number,
                "is_finra_registered": is_finra_registered,
                "is_sec_registered": is_sec_registered,
                "search_source": search_source,
                "status_source": status_source,
                "final_source": final_source
            }
        else:
            logger.error("Failed to generate compliance report")
    else:
        logger.error(f"No firm found with CRD: {crd_number}")
    
    return None

def main():
    """Test source listings for specific FINRA-regulated entities."""
    # List of entities to test
    entities = [
        {"crd": "29116", "name": "BROOKSTONE SECURITIES, INC."},
        {"crd": "47936", "name": "MARTINWOLF"},
        {"crd": "100960", "name": "OUTCOME CAPITAL, LLC"}
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
        print(f"Is FINRA Registered: {result['is_finra_registered']}")
        print(f"Is SEC Registered: {result['is_sec_registered']}")
        print(f"Source in search_evaluation: {result['search_source']}")
        print(f"Source in status_evaluation: {result['status_source']}")
        print(f"Source in final_evaluation: {result['final_source']}")
        print("-" * 80)

if __name__ == "__main__":
    main()