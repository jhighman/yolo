"""
firm_evaluation_report_builder.py

This module defines the FirmEvaluationReportBuilder class for constructing comprehensive
compliance reports for business entities. It supports incremental assembly of evaluation
results through method chaining and produces a structured output for downstream processing.
"""

from collections import OrderedDict
from typing import Dict, Any, cast

class FirmEvaluationReportBuilder:
    """Constructs compliance reports for business entities by collecting sub-evaluations."""
    
    def __init__(self, reference_id: str):
        """Initialize the builder with a reference ID and set up the report structure.
        
        Args:
            reference_id: String identifier for the claim (e.g., "B123-45678")
        """
        self.report = OrderedDict([
            ("reference_id", reference_id),
            ("claim", {}),
            ("entity", {}),
            ("search_evaluation", {}),
            ("status_evaluation", {}),
            ("disclosure_review", {}),
            ("disciplinary_evaluation", {}),
            ("arbitration_review", {}),
            ("adv_evaluation", {}),  # New section for ADV PDF evaluation
            ("final_evaluation", {})
        ])

    def set_claim(self, claim: Dict[str, Any]) -> "FirmEvaluationReportBuilder":
        """Set the simplified claim data in the report.
        
        Args:
            claim: Dictionary containing claim data
            
        Returns:
            self for method chaining
        """
        # Extract only the required fields for the simplified claim structure
        simplified_claim = {
            "referenceId": claim.get("reference_id") or claim.get("referenceId", ""),
            "crdNumber": claim.get("organization_crd") or claim.get("crdNumber", ""),
            "entityName": claim.get("business_name") or claim.get("entityName", "")
        }
        
        self.report["claim"] = simplified_claim
        return self

    def set_entity(self, entity_data: Dict[str, Any]) -> "FirmEvaluationReportBuilder":
        """Set the entity information in the report.
        
        Args:
            entity_data: Dictionary containing entity information
            
        Returns:
            self for method chaining
        """
        self.report["entity"] = entity_data
        return self

    def set_search_evaluation(self, search_evaluation: Dict[str, Any]) -> "FirmEvaluationReportBuilder":
        """Set the simplified search evaluation results from upstream processing.
        
        Args:
            search_evaluation: Dictionary containing search results and compliance status
            
        Returns:
            self for method chaining
        """
        # Get the source from basic_result
        basic_result = search_evaluation.get("basic_result", {})
        source = basic_result.get("source", search_evaluation.get("source", "UNKNOWN"))
        
        # Remove redundant source from basic_result if it exists
        if basic_result and "source" in basic_result:
            basic_result = {k: v for k, v in basic_result.items() if k != "source"}
        
        # Extract entity information from basic_result and set it
        if basic_result:
            entity_data = {
                "firm_name": basic_result.get("firm_name", ""),
                "crd_number": basic_result.get("crd_number", ""),
                "sec_number": basic_result.get("sec_number", ""),
                "registration_status": basic_result.get("registration_status", ""),
                "address": basic_result.get("address", {}),
                "registration_date": basic_result.get("registration_date", ""),
                "other_names": basic_result.get("other_names", []),
                "is_sec_registered": basic_result.get("is_sec_registered", False),
                "is_state_registered": basic_result.get("is_state_registered", False),
                "is_era_registered": basic_result.get("is_era_registered", False),
                "is_sec_era_registered": basic_result.get("is_sec_era_registered", False),
                "is_state_era_registered": basic_result.get("is_state_era_registered", False),
                "adv_filing_date": basic_result.get("adv_filing_date", ""),
                "has_adv_pdf": basic_result.get("has_adv_pdf", False)
            }
            self.set_entity(entity_data)
        
        # Extract only the required fields for the simplified search_evaluation structure
        simplified_search_evaluation = {
            "source": source,  # Use the source from basic_result
            "compliance": search_evaluation.get("compliance", False),
            "compliance_explanation": f"Search completed successfully with {source} data, individual found."
                if search_evaluation.get("compliance", False)
                else f"Search failed to find entity in {source}.",
            "basic_result": basic_result
        }
        
        # Always include raw search results
        simplified_search_evaluation["sec_search_result"] = search_evaluation.get("sec_search_result", {
            "status": "not_found",
            "details": {}
        })
        
        simplified_search_evaluation["finra_search_result"] = search_evaluation.get("finra_search_result", {
            "status": "not_found",
            "details": {}
        })
        
        self.report["search_evaluation"] = simplified_search_evaluation
        return self

    def set_status_evaluation(self, status_evaluation: Dict[str, Any]) -> "FirmEvaluationReportBuilder":
        """Set the status evaluation (replaces registration_status).
        
        Args:
            status_evaluation: Dictionary containing registration status compliance evaluation
            
        Returns:
            self for method chaining
        """
        self.report["status_evaluation"] = status_evaluation
        return self

    def set_disclosure_review(self, disclosure_review: Dict[str, Any]) -> "FirmEvaluationReportBuilder":
        """Set the disclosure review (replaces disclosures).
        
        Args:
            disclosure_review: Dictionary containing disclosure compliance evaluation
            
        Returns:
            self for method chaining
        """
        self.report["disclosure_review"] = disclosure_review
        return self

    def set_disciplinary_evaluation(self, disciplinary_evaluation: Dict[str, Any]) -> "FirmEvaluationReportBuilder":
        """Set the disciplinary evaluation.
        
        Args:
            disciplinary_evaluation: Dictionary containing disciplinary action evaluation
            
        Returns:
            self for method chaining
        """
        self.report["disciplinary_evaluation"] = disciplinary_evaluation
        return self

    def set_arbitration_review(self, arbitration_review: Dict[str, Any]) -> "FirmEvaluationReportBuilder":
        """Set the arbitration review.
        
        Args:
            arbitration_review: Dictionary containing arbitration data evaluation
            
        Returns:
            self for method chaining
        """
        self.report["arbitration_review"] = arbitration_review
        return self
        
    def set_adv_evaluation(self, adv_evaluation: Dict[str, Any]) -> "FirmEvaluationReportBuilder":
        """Set the ADV evaluation results.
        
        Args:
            adv_evaluation: Dictionary containing ADV PDF evaluation results
            
        Returns:
            self for method chaining
        """
        self.report["adv_evaluation"] = adv_evaluation
        return self

    def set_final_evaluation(self, final_evaluation: Dict[str, Any]) -> "FirmEvaluationReportBuilder":
        """Set the final overall evaluation, summarizing compliance and risk.
        
        Args:
            final_evaluation: Dictionary containing overall compliance and risk assessment
            
        Returns:
            self for method chaining
        """
        self.report["final_evaluation"] = final_evaluation
        return self

    def build(self) -> Dict[str, Any]:
        """Finalize and return the fully constructed report.
        
        Returns:
            Dictionary containing all report sections in the specified order,
            excluding Arbitration, ADV, and Disciplinary sections which are
            preserved in the builder but not included in the final report.
        """
        # Create a copy of the report without the excluded sections
        filtered_report = OrderedDict()
        sections_to_exclude = ["arbitration_review", "adv_evaluation", "disciplinary_evaluation"]
        
        for key, value in self.report.items():
            if key not in sections_to_exclude:
                filtered_report[key] = value
        
        return cast(Dict[str, Any], dict(filtered_report))  # Cast OrderedDict to Dict[str, Any]

# TODO: Implement firm evaluation report builder logic