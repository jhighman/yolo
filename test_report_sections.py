#!/usr/bin/env python3
"""
Test script to verify that Arbitration, ADV, and Disciplinary sections 
are properly removed from the final compliance report.
"""

import sys
import json
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent))

from evaluation.firm_evaluation_report_builder import FirmEvaluationReportBuilder

def main():
    """Test the removal of specified sections from the compliance report."""
    # Create a builder with a test reference ID
    builder = FirmEvaluationReportBuilder("TEST-12345")
    
    # Set data for all sections
    builder.set_claim({
        "reference_id": "TEST-12345",
        "organization_crd": "12345",
        "business_name": "Test Company"
    })
    
    builder.set_search_evaluation({
        "compliance": True,
        "basic_result": {
            "firm_name": "Test Company",
            "crd_number": "12345",
            "source": "SEC"
        }
    })
    
    builder.set_status_evaluation({
        "source": "SEC",
        "compliance": True,
        "compliance_explanation": "All status checks passed",
        "alerts": []
    })
    
    builder.set_disclosure_review({
        "source": "SEC",
        "compliance": True,
        "compliance_explanation": "No disclosure issues found",
        "alerts": []
    })
    
    # Set data for sections that should be excluded
    builder.set_disciplinary_evaluation({
        "source": "SEC",
        "compliance": True,
        "compliance_explanation": "No disciplinary actions found",
        "alerts": []
    })
    
    builder.set_arbitration_review({
        "source": "SEC",
        "compliance": True,
        "compliance_explanation": "No arbitration cases found",
        "alerts": []
    })
    
    builder.set_adv_evaluation({
        "source": "SEC",
        "compliance": True,
        "compliance_explanation": "ADV evaluation completed",
        "alerts": []
    })
    
    builder.set_final_evaluation({
        "source": "SEC",
        "overall_compliance": True,
        "overall_risk_level": "Low",
        "recommendations": "No action required",
        "description": "All compliance checks passed",
        "alerts": []
    })
    
    # Build the final report
    report = builder.build()
    
    # Check if the excluded sections are not in the final report
    sections_to_exclude = ["arbitration_review", "adv_evaluation", "disciplinary_evaluation"]
    excluded_sections = [section for section in sections_to_exclude if section in report]
    
    if excluded_sections:
        print(f"ERROR: The following sections were not properly excluded: {', '.join(excluded_sections)}")
    else:
        print("SUCCESS: All specified sections were properly excluded from the final report")
    
    # Print the final report structure
    print("\nFinal report sections:")
    for section in report.keys():
        print(f"- {section}")
    
    # Save the report to a file for inspection
    with open("test_report_output.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print("\nFull report saved to test_report_output.json for inspection")

if __name__ == "__main__":
    main()