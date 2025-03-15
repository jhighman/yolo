"""
firm_evaluation_report_builder.py

This module defines the FirmEvaluationReportBuilder class for constructing comprehensive
compliance reports for business entities. It supports incremental assembly of evaluation
results through method chaining and produces a structured output for downstream processing.
"""

from collections import OrderedDict
from typing import Dict, Any, cast
import copy  # Add import for deepcopy

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
            ("search_evaluation", {}),
            ("registration_status", {}),
            ("regulatory_oversight", {}),
            ("disclosures", {}),
            ("financials", {}),
            ("legal", {}),
            ("qualifications", {}),
            ("data_integrity", {}),
            ("final_evaluation", {})
        ])

    def set_claim(self, claim: Dict[str, Any]) -> "FirmEvaluationReportBuilder":
        """Set the original claim data in the report.
        
        Args:
            claim: Dictionary containing claim data (e.g., business name, tax ID)
            
        Returns:
            self for method chaining
        """
        self.report["claim"] = claim
        return self

    def set_search_evaluation(self, search_evaluation: Dict[str, Any]) -> "FirmEvaluationReportBuilder":
        """Set the search evaluation results from upstream processing.
        
        Args:
            search_evaluation: Dictionary containing search results and compliance status
            
        Returns:
            self for method chaining
        """
        self.report["search_evaluation"] = search_evaluation
        return self

    def set_registration_status(self, registration_status: Dict[str, Any]) -> "FirmEvaluationReportBuilder":
        """Set the registration status evaluation.
        
        Args:
            registration_status: Dictionary containing registration compliance evaluation
            
        Returns:
            self for method chaining
        """
        self.report["registration_status"] = registration_status
        return self

    def set_regulatory_oversight(self, regulatory_oversight: Dict[str, Any]) -> "FirmEvaluationReportBuilder":
        """Set the regulatory oversight evaluation.
        
        Args:
            regulatory_oversight: Dictionary containing oversight compliance evaluation
            
        Returns:
            self for method chaining
        """
        self.report["regulatory_oversight"] = regulatory_oversight
        return self

    def set_disclosures(self, disclosures: Dict[str, Any]) -> "FirmEvaluationReportBuilder":
        """Set the disclosure evaluation.
        
        Args:
            disclosures: Dictionary containing disclosure compliance evaluation
            
        Returns:
            self for method chaining
        """
        self.report["disclosures"] = disclosures
        return self

    def set_financials(self, financials: Dict[str, Any]) -> "FirmEvaluationReportBuilder":
        """Set the financial stability evaluation.
        
        Args:
            financials: Dictionary containing financial compliance evaluation
            
        Returns:
            self for method chaining
        """
        self.report["financials"] = financials
        return self

    def set_legal(self, legal: Dict[str, Any]) -> "FirmEvaluationReportBuilder":
        """Set the legal compliance evaluation.
        
        Args:
            legal: Dictionary containing legal compliance evaluation
            
        Returns:
            self for method chaining
        """
        self.report["legal"] = legal
        return self

    def set_qualifications(self, qualifications: Dict[str, Any]) -> "FirmEvaluationReportBuilder":
        """Set the professional qualifications evaluation.
        
        Args:
            qualifications: Dictionary containing qualifications compliance evaluation
            
        Returns:
            self for method chaining
        """
        self.report["qualifications"] = qualifications
        return self

    def set_data_integrity(self, data_integrity: Dict[str, Any]) -> "FirmEvaluationReportBuilder":
        """Set the data integrity evaluation.
        
        Args:
            data_integrity: Dictionary containing data reliability evaluation
            
        Returns:
            self for method chaining
        """
        self.report["data_integrity"] = data_integrity
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
            Dictionary containing all report sections in the specified order
        """
        return cast(Dict[str, Any], copy.deepcopy(dict(self.report)))  # Create deep copy

# TODO: Implement firm evaluation report builder logic