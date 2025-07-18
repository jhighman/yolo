#!/usr/bin/env python3
"""
test_real_crd_source_propagation.py

This script tests that the source field is correctly propagated from the search_evaluation
section to the final_evaluation section in the firm compliance report using a real CRD number.
"""

import sys
from pathlib import Path
import json
from datetime import datetime

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent))

from services.firm_services import FirmServicesFacade
from evaluation.firm_evaluation_report_builder import FirmEvaluationReportBuilder
from evaluation.firm_evaluation_report_director import FirmEvaluationReportDirector

def test_real_crd_source_propagation(crd_number="174196"):
    """Test source field propagation with a real CRD number."""
    print(f"Testing source field propagation with CRD {crd_number}...")
    
    # Create a reference ID for the test
    reference_id = f"TEST-CRD-{crd_number}"
    
    # Create a FirmServicesFacade instance
    facade = FirmServicesFacade()
    
    # Search for the firm by CRD number
    subject_id = f"TEST-{crd_number}"  # Create a test subject ID
    search_result = facade.search_firm_by_crd(subject_id, crd_number)
    
    # Debug output to see what's in the search_result
    print(f"Search result: {search_result}")
    
    if not search_result:
        print(f"❌ FAILURE: Could not find firm with CRD {crd_number}")
        return None
    
    # The search_result might not have a 'compliance' field directly
    # It might be in a different structure or not present at all
    # Let's create a minimal search_evaluation with the source
    
    # Extract the source from the search result
    source = "UNKNOWN"
    if isinstance(search_result, dict):
        # Try to extract source from different possible locations
        if "source" in search_result:
            source = search_result["source"]
        elif "basic_result" in search_result and isinstance(search_result["basic_result"], dict):
            basic_result = search_result["basic_result"]
            if "source" in basic_result:
                source = basic_result["source"]
    
    print(f"Source from search_evaluation: {source}")
    
    # Create a minimal search_evaluation with the source
    search_evaluation = {
        "source": source,
        "compliance": True,
        "compliance_explanation": f"Found firm with CRD {crd_number}",
        "basic_result": {
            "firm_name": search_result.get("firm_name", f"CRD {crd_number}"),
            "crd_number": crd_number,
            "source": source
        }
    }
    
    # Create a builder and director
    builder = FirmEvaluationReportBuilder(reference_id)
    director = FirmEvaluationReportDirector(builder)
    
    # Create a claim with minimal required fields
    claim = {
        "business_ref": f"TEST-BIZ-{crd_number}",
        "business_name": search_result.get("firm_name", f"CRD {crd_number}"),
        "reference_id": reference_id,
        "organization_crd": crd_number
    }
    
    # Construct the report
    report = director.construct_evaluation_report(claim, {"search_evaluation": search_evaluation})
    
    # Check if the source field is correctly propagated to final_evaluation
    if "final_evaluation" in report and "source" in report["final_evaluation"]:
        source_in_final = report["final_evaluation"]["source"]
        if source_in_final == source:
            print(f"✅ SUCCESS: Source field '{source_in_final}' correctly propagated to final_evaluation")
        else:
            print(f"❌ FAILURE: Source field in final_evaluation is '{source_in_final}', expected '{source}'")
    else:
        print("❌ FAILURE: Source field not found in final_evaluation")
    
    # Print the final_evaluation section for inspection
    print("\nFinal Evaluation Section:")
    print(json.dumps(report["final_evaluation"], indent=2))
    
    return report

if __name__ == "__main__":
    # Test with CRD 174196 (GORDON FINANCIAL)
    test_real_crd_source_propagation("174196")