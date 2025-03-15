"""Director for firm evaluation report construction.

This module will coordinate the building of firm evaluation reports
using the builder pattern.
"""

from typing import Dict, Any
from .firm_evaluation_report_builder import FirmEvaluationReportBuilder

class FirmEvaluationReportDirector:
    """Director for orchestrating the construction of firm evaluation reports."""
    
    def construct_evaluation_report(
        self,
        claim: Dict[str, Any],
        extracted_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Construct a firm evaluation report using the provided data.
        
        Args:
            claim: Original claim data
            extracted_info: Information extracted from search results
            
        Returns:
            Constructed report dictionary
        """
        builder = FirmEvaluationReportBuilder(claim.get('reference_id', 'UNKNOWN'))
        
        # Build summary
        summary = {
            "business_name": extracted_info.get("business_name", ""),
            "search_source": extracted_info["search_evaluation"]["source"],
            "compliance": extracted_info["search_evaluation"]["compliance"],
            "compliance_explanation": extracted_info["search_evaluation"]["compliance_explanation"]
        }
        builder.add_summary(summary)
        
        # Build compliance status
        compliance_status = {
            "is_compliant": extracted_info["search_evaluation"]["compliance"],
            "explanation": extracted_info["search_evaluation"]["compliance_explanation"],
            "error": extracted_info["search_evaluation"].get("error")
        }
        builder.add_compliance_status(compliance_status)
        
        # Build due diligence
        due_diligence = {
            "business_details": extracted_info.get("business", {}),
            "financials": extracted_info.get("financials_evaluation", {"status": "Skipped"}),
            "legal": extracted_info.get("legal_evaluation", {"status": "Skipped"})
        }
        builder.add_due_diligence(due_diligence)
        
        # Add risks
        if not extracted_info["search_evaluation"]["compliance"]:
            builder.add_risk({
                "type": "VERIFICATION",
                "severity": "HIGH",
                "description": "Unable to verify business information",
                "details": extracted_info["search_evaluation"].get("error", "No data found")
            })
            
        if extracted_info.get("financials_evaluation", {}).get("status") == "Skipped":
            builder.add_risk({
                "type": "FINANCIAL",
                "severity": "MEDIUM",
                "description": "Financial evaluation was skipped",
                "details": "No financial due diligence performed"
            })
            
        if extracted_info.get("legal_evaluation", {}).get("status") == "Skipped":
            builder.add_risk({
                "type": "LEGAL",
                "severity": "MEDIUM",
                "description": "Legal evaluation was skipped",
                "details": "No legal due diligence performed"
            })
        
        return builder.get_report()

# TODO: Implement firm evaluation report director logic