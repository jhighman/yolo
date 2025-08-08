#!/usr/bin/env python3
"""
test_adv_processing_no_pdf.py

This script tests the ADV PDF processing functionality for a firm without an ADV PDF.
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

def test_adv_processing_no_pdf():
    """Test ADV PDF processing for a firm with has_adv_pdf=false."""
    print("Testing ADV PDF processing for a firm without an ADV PDF...")
    
    # Create a test entity with has_adv_pdf=false
    entity_data = {
        "firm_name": "TEST FIRM WITHOUT ADV",
        "crd_number": "999999",
        "sec_number": "801-99999",
        "registration_status": "Approved",
        "address": {
            "street": "123 TEST ST",
            "city": "TEST CITY",
            "state": "TS",
            "zip": "12345",
            "country": "United States"
        },
        "has_adv_pdf": False,
        "adv_filing_date": ""
    }
    
    # Create a test subject ID
    subject_id = "TEST-ADV-PROCESSING-NO-PDF"
    
    # Process the ADV PDF
    adv_evaluation = process_adv(subject_id, entity_data["crd_number"], entity_data)
    
    # Print the ADV evaluation results
    print("\nADV Evaluation Results:")
    print(json.dumps(adv_evaluation, indent=2))
    
    # Check if the ADV evaluation has the correct compliance status
    if not adv_evaluation.get("compliance", True):
        print("\n✅ SUCCESS: ADV evaluation correctly shows non-compliance for firm without ADV PDF")
    else:
        print("\n❌ FAILURE: ADV evaluation incorrectly shows compliance for firm without ADV PDF")
    
    # Check if the ADV evaluation has the correct alert
    alerts = adv_evaluation.get("alerts", [])
    if alerts and any(alert.get("alert_type") == "NoADVFiling" for alert in alerts):
        print("\n✅ SUCCESS: ADV evaluation correctly includes NoADVFiling alert")
    else:
        print("\n❌ FAILURE: ADV evaluation does not include NoADVFiling alert")
    
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
                         if "ADV" in alert.get("alert_type", "") or "Filing" in alert.get("alert_type", "")]
            
            if adv_alerts:
                print(f"\n✅ SUCCESS: {len(adv_alerts)} ADV-related alerts found in final evaluation")
                for alert in adv_alerts:
                    print(f"  - {alert.get('alert_type')}: {alert.get('description')}")
            else:
                print("\n❌ FAILURE: No ADV-related alerts found in final evaluation")
                
            # Check if overall compliance is affected
            if not report["final_evaluation"].get("overall_compliance", True):
                print("\n✅ SUCCESS: Overall compliance is correctly affected by missing ADV PDF")
            else:
                print("\n❌ FAILURE: Overall compliance is not affected by missing ADV PDF")
        else:
            print("\n❌ FAILURE: Final evaluation section not found in report")
    except Exception as e:
        print(f"\n❌ ERROR: Failed to construct evaluation report: {str(e)}")
    
    return adv_evaluation

if __name__ == "__main__":
    test_adv_processing_no_pdf()