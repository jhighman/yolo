#!/usr/bin/env python3
"""
test_adv_processing.py

This script tests the ADV PDF processing functionality for firm compliance reports.
"""

import sys
import os
from pathlib import Path
import json
from datetime import datetime

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent))

from agents.adv_processing_agent import process_adv, ADVProcessingAgent
from evaluation.firm_evaluation_report_builder import FirmEvaluationReportBuilder
from evaluation.firm_evaluation_report_director import FirmEvaluationReportDirector

def test_adv_processing():
    """Test ADV PDF processing for a firm with has_adv_pdf=true."""
    print("Testing ADV PDF processing...")
    
    # Create a test entity with has_adv_pdf=true
    # Using UBS FINANCIAL SERVICES INC. (CRD: 8174) as an example
    entity_data = {
        "firm_name": "UBS FINANCIAL SERVICES INC.",
        "crd_number": "8174",
        "sec_number": "801-7163",
        "registration_status": "Approved",
        "address": {
            "street": "1200 HARBOR BLVD",
            "city": "WEEHAWKEN",
            "state": "NJ",
            "zip": "07086",
            "country": "United States"
        },
        "has_adv_pdf": True,
        "adv_filing_date": "2025-01-15"
    }
    
    # Create a test subject ID
    subject_id = "TEST-ADV-PROCESSING"
    
    # Process the ADV PDF
    adv_evaluation = process_adv(subject_id, entity_data["crd_number"], entity_data)
    
    # Print the ADV evaluation results
    print("\nADV Evaluation Results:")
    print(json.dumps(adv_evaluation, indent=2))
    
    # Check if the ADV PDF was downloaded
    agent = ADVProcessingAgent()
    cache_path = agent.get_cache_path(subject_id, entity_data["crd_number"])
    pdf_path = os.path.join(cache_path, "adv.pdf")
    
    if os.path.exists(pdf_path):
        print(f"\n✅ SUCCESS: ADV PDF downloaded to {pdf_path}")
        print(f"File size: {os.path.getsize(pdf_path)} bytes")
    else:
        print(f"\n❌ FAILURE: ADV PDF not downloaded to {pdf_path}")
    
    # Test the full evaluation process
    # Create a reference ID for the test
    reference_id = f"TEST-CRD-{entity_data['crd_number']}"
    
    # Create a builder and director
    builder = FirmEvaluationReportBuilder(reference_id)
    director = FirmEvaluationReportDirector(builder)
    
    # Create a claim with minimal required fields
    claim = {
        "business_ref": f"TEST-BIZ-{entity_data['crd_number']}",
        "business_name": entity_data["firm_name"],
        "reference_id": reference_id,
        "organization_crd": entity_data["crd_number"]
    }
    
    # Create a minimal search_evaluation
    search_evaluation = {
        "source": "SEC",
        "compliance": True,
        "compliance_explanation": f"Found firm with CRD {entity_data['crd_number']}",
        "basic_result": {
            "firm_name": entity_data["firm_name"],
            "crd_number": entity_data["crd_number"],
            "source": "SEC"
        }
    }
    
    # Create extracted_info with the search_evaluation and entity_data
    extracted_info = {
        "search_evaluation": search_evaluation
    }
    extracted_info.update(entity_data)
    
    # Construct the report
    try:
        report = director.construct_evaluation_report(claim, extracted_info)
        
        # Check if the ADV evaluation section is in the report
        if "adv_evaluation" in report:
            print("\n✅ SUCCESS: ADV evaluation section found in report")
            print("\nADV Evaluation Section:")
            print(json.dumps(report["adv_evaluation"], indent=2))
        else:
            print("\n❌ FAILURE: ADV evaluation section not found in report")
        
        # Check if the ADV evaluation results are included in the final evaluation
        if "final_evaluation" in report:
            print("\nFinal Evaluation Section:")
            print(json.dumps(report["final_evaluation"], indent=2))
            
            # Check if any ADV-related alerts are in the final evaluation
            adv_alerts = [alert for alert in report["final_evaluation"].get("alerts", []) 
                         if "ADV" in alert.get("alert_type", "")]
            
            if adv_alerts:
                print(f"\n✅ SUCCESS: {len(adv_alerts)} ADV-related alerts found in final evaluation")
            else:
                print("\nℹ️ INFO: No ADV-related alerts found in final evaluation")
        else:
            print("\n❌ FAILURE: Final evaluation section not found in report")
    except Exception as e:
        print(f"\n❌ ERROR: Failed to construct evaluation report: {str(e)}")
    
    return adv_evaluation

if __name__ == "__main__":
    test_adv_processing()