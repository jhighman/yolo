"""
test_firm_evaluation_report_builder.py

Unit tests for the FirmEvaluationReportBuilder class.
"""

import unittest
from typing import Dict, Any
from evaluation.firm_evaluation_report_builder import FirmEvaluationReportBuilder

class TestFirmEvaluationReportBuilder(unittest.TestCase):
    """Test cases for FirmEvaluationReportBuilder."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.reference_id = "B123-45678"
        self.builder = FirmEvaluationReportBuilder(self.reference_id)
        
        # Sample data for testing
        self.sample_claim = {
            "business_name": "Acme Corp",
            "tax_id": "12-3456789",
            "organization_crd": "123456",
            "business_ref": "ACME001"
        }
        
        self.sample_search = {
            "compliance": True,
            "source": "SEC",
            "match_score": 0.95
        }
        
        self.sample_registration = {
            "compliance": True,
            "explanation": "Firm is actively registered",
            "alerts": []
        }
        
        self.sample_oversight = {
            "compliance": True,
            "explanation": "Under SEC oversight",
            "alerts": []
        }
        
        self.sample_disclosures = {
            "compliance": True,
            "explanation": "No issues found",
            "alerts": []
        }
        
        self.sample_financials = {
            "compliance": True,
            "explanation": "Recent ADV filing",
            "alerts": []
        }
        
        self.sample_legal = {
            "compliance": True,
            "explanation": "No legal issues",
            "alerts": []
        }
        
        self.sample_qualifications = {
            "compliance": True,
            "explanation": "All required exams passed",
            "alerts": []
        }
        
        self.sample_data_integrity = {
            "compliance": True,
            "explanation": "Data is current",
            "alerts": []
        }
        
        self.sample_final = {
            "overall_compliance": True,
            "overall_risk_level": "Low",
            "alerts": []
        }

    def test_initialization(self):
        """Test builder initialization with reference ID."""
        report = self.builder.build()
        
        # Check reference ID
        self.assertEqual(report["reference_id"], self.reference_id)
        
        # Check all sections are initialized as empty dicts
        sections = [
            "claim", "search_evaluation", "registration_status",
            "regulatory_oversight", "disclosures", "financials",
            "legal", "qualifications", "data_integrity",
            "final_evaluation"
        ]
        for section in sections:
            self.assertEqual(report[section], {})

    def test_set_claim(self):
        """Test setting claim data."""
        report = self.builder.set_claim(self.sample_claim).build()
        self.assertEqual(report["claim"], self.sample_claim)

    def test_set_search_evaluation(self):
        """Test setting search evaluation data."""
        report = self.builder.set_search_evaluation(self.sample_search).build()
        self.assertEqual(report["search_evaluation"], self.sample_search)

    def test_set_registration_status(self):
        """Test setting registration status data."""
        report = self.builder.set_registration_status(self.sample_registration).build()
        self.assertEqual(report["registration_status"], self.sample_registration)

    def test_set_regulatory_oversight(self):
        """Test setting regulatory oversight data."""
        report = self.builder.set_regulatory_oversight(self.sample_oversight).build()
        self.assertEqual(report["regulatory_oversight"], self.sample_oversight)

    def test_set_disclosures(self):
        """Test setting disclosures data."""
        report = self.builder.set_disclosures(self.sample_disclosures).build()
        self.assertEqual(report["disclosures"], self.sample_disclosures)

    def test_set_financials(self):
        """Test setting financials data."""
        report = self.builder.set_financials(self.sample_financials).build()
        self.assertEqual(report["financials"], self.sample_financials)

    def test_set_legal(self):
        """Test setting legal data."""
        report = self.builder.set_legal(self.sample_legal).build()
        self.assertEqual(report["legal"], self.sample_legal)

    def test_set_qualifications(self):
        """Test setting qualifications data."""
        report = self.builder.set_qualifications(self.sample_qualifications).build()
        self.assertEqual(report["qualifications"], self.sample_qualifications)

    def test_set_data_integrity(self):
        """Test setting data integrity data."""
        report = self.builder.set_data_integrity(self.sample_data_integrity).build()
        self.assertEqual(report["data_integrity"], self.sample_data_integrity)

    def test_set_final_evaluation(self):
        """Test setting final evaluation data."""
        report = self.builder.set_final_evaluation(self.sample_final).build()
        self.assertEqual(report["final_evaluation"], self.sample_final)

    def test_method_chaining(self):
        """Test method chaining for building complete report."""
        report = (self.builder
            .set_claim(self.sample_claim)
            .set_search_evaluation(self.sample_search)
            .set_registration_status(self.sample_registration)
            .set_regulatory_oversight(self.sample_oversight)
            .set_disclosures(self.sample_disclosures)
            .set_financials(self.sample_financials)
            .set_legal(self.sample_legal)
            .set_qualifications(self.sample_qualifications)
            .set_data_integrity(self.sample_data_integrity)
            .set_final_evaluation(self.sample_final)
            .build())
        
        # Verify all sections
        self.assertEqual(report["reference_id"], self.reference_id)
        self.assertEqual(report["claim"], self.sample_claim)
        self.assertEqual(report["search_evaluation"], self.sample_search)
        self.assertEqual(report["registration_status"], self.sample_registration)
        self.assertEqual(report["regulatory_oversight"], self.sample_oversight)
        self.assertEqual(report["disclosures"], self.sample_disclosures)
        self.assertEqual(report["financials"], self.sample_financials)
        self.assertEqual(report["legal"], self.sample_legal)
        self.assertEqual(report["qualifications"], self.sample_qualifications)
        self.assertEqual(report["data_integrity"], self.sample_data_integrity)
        self.assertEqual(report["final_evaluation"], self.sample_final)

    def test_section_order(self):
        """Test that report sections maintain the specified order."""
        expected_order = [
            "reference_id",
            "claim",
            "search_evaluation",
            "registration_status",
            "regulatory_oversight",
            "disclosures",
            "financials",
            "legal",
            "qualifications",
            "data_integrity",
            "final_evaluation"
        ]
        
        report = self.builder.build()
        actual_order = list(report.keys())
        self.assertEqual(actual_order, expected_order)

    def test_immutable_report(self):
        """Test that building report doesn't affect builder state."""
        # Build initial report
        first_report = self.builder.set_claim(self.sample_claim).build()
        
        # Modify the report
        first_report["claim"]["new_field"] = "test"
        
        # Build second report
        second_report = self.builder.build()
        
        # Verify second report is unaffected by modifications to first
        self.assertNotEqual(first_report["claim"], second_report["claim"])
        self.assertNotIn("new_field", second_report["claim"])

if __name__ == '__main__':
    unittest.main() 