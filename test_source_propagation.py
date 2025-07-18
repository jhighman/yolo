#!/usr/bin/env python3
"""
test_source_propagation.py

This script tests that the source field is correctly propagated from the search_evaluation
section to the final_evaluation section in the firm compliance report.
"""

import sys
from pathlib import Path
import json
from datetime import datetime

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent))

from evaluation.firm_evaluation_report_builder import FirmEvaluationReportBuilder
from evaluation.firm_evaluation_report_director import FirmEvaluationReportDirector

def test_source_propagation():
    """Test that the source field is correctly propagated to final_evaluation."""
    print("Testing source field propagation to final_evaluation...")
    
    # Create a reference ID for the test
    reference_id = "TEST-SOURCE-PROP"
    
    # Create a builder and director
    builder = FirmEvaluationReportBuilder(reference_id)
    director = FirmEvaluationReportDirector(builder)
    
    # Create test data with a specific source
    test_source = "TEST_SOURCE"
    
    # Create a claim with minimal required fields
    claim = {
        "business_ref": "TEST-BIZ-REF",
        "business_name": "Test Business",
        "reference_id": reference_id,
        "organization_crd": "123456"
    }
    
    # Create extracted info with search_evaluation containing the test source
    extracted_info = {
        "search_evaluation": {
            "source": test_source,
            "compliance": True,
            "compliance_explanation": "Test compliance",
            "basic_result": {
                "firm_name": "Test Business",
                "crd_number": "123456",
                "registration_status": "ACTIVE"
            }
        }
    }
    
    # Construct the report
    report = director.construct_evaluation_report(claim, extracted_info)
    
    # Check if the source field is correctly propagated to final_evaluation
    if "final_evaluation" in report and "source" in report["final_evaluation"]:
        source_in_final = report["final_evaluation"]["source"]
        if source_in_final == test_source:
            print(f"✅ SUCCESS: Source field '{source_in_final}' correctly propagated to final_evaluation")
        else:
            print(f"❌ FAILURE: Source field in final_evaluation is '{source_in_final}', expected '{test_source}'")
    else:
        print("❌ FAILURE: Source field not found in final_evaluation")
    
    # Print the final_evaluation section for inspection
    print("\nFinal Evaluation Section:")
    print(json.dumps(report["final_evaluation"], indent=2))
    
    return report

if __name__ == "__main__":
    test_source_propagation()