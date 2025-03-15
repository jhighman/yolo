"""Unit tests for the firm business module."""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime
import json
from typing import Dict, Any

from services.firm_business import (
    SearchStrategy,
    determine_search_strategy,
    search_with_tax_id_and_org_crd,
    search_with_crd_only,
    search_with_name_only,
    search_with_default,
    process_claim,
    SearchImplementationStatus
)
from evaluation.firm_evaluation_processor import Alert, AlertSeverity
from evaluation.firm_evaluation_report_director import InvalidDataError, EvaluationProcessError

class TestFirmBusiness(unittest.TestCase):
    """Test cases for firm business module."""

    def setUp(self):
        """Set up test fixtures."""
        self.facade = Mock()
        self.business_ref = "TEST_REF"
        
        # Register implemented strategies
        SearchImplementationStatus.register_implementation(SearchStrategy.TAX_ID_AND_CRD.value)
        SearchImplementationStatus.register_implementation(SearchStrategy.CRD_ONLY.value)
        SearchImplementationStatus.register_implementation(SearchStrategy.NAME_ONLY.value)
        SearchImplementationStatus.register_implementation(SearchStrategy.DEFAULT.value)

    def test_determine_search_strategy(self):
        """Test search strategy determination based on claim data."""
        # Test tax_id and CRD
        claim = {
            "tax_id": "123456789",
            "organization_crd": "987654",
            "business_name": "Test Firm"
        }
        self.assertEqual(
            determine_search_strategy(claim),
            SearchStrategy.TAX_ID_AND_CRD
        )

        # Test CRD only
        claim = {
            "organization_crd": "987654",
            "business_name": "Test Firm"
        }
        self.assertEqual(
            determine_search_strategy(claim),
            SearchStrategy.CRD_ONLY
        )

        # Test name only
        claim = {
            "business_name": "Test Firm"
        }
        self.assertEqual(
            determine_search_strategy(claim),
            SearchStrategy.NAME_ONLY
        )

        # Test empty claim
        claim = {}
        self.assertEqual(
            determine_search_strategy(claim),
            SearchStrategy.DEFAULT
        )

    def test_search_with_tax_id_and_org_crd(self):
        """Test search using tax ID and CRD."""
        claim = {
            "tax_id": "123456789",
            "organization_crd": "987654"
        }

        # Test successful search
        self.facade.search_firm_by_crd.return_value = {
            "organization_crd": "987654",
            "business_name": "Test Firm"
        }
        self.facade.get_firm_details.return_value = {
            "disclosures": [],
            "accountant_exams": []
        }

        result = search_with_tax_id_and_org_crd(claim, self.facade, self.business_ref)
        self.assertTrue(result["compliance"])
        self.assertEqual(result["source"], "FINRA")
        self.assertTrue("basic_result" in result)
        self.assertTrue("detailed_result" in result)

        # Test failed search
        self.facade.search_firm_by_crd.return_value = None
        result = search_with_tax_id_and_org_crd(claim, self.facade, self.business_ref)
        self.assertFalse(result["compliance"])

    def test_search_with_crd_only(self):
        """Test search using CRD only."""
        claim = {
            "organization_crd": "987654"
        }

        # Test successful search
        self.facade.search_firm_by_crd.return_value = {
            "organization_crd": "987654",
            "business_name": "Test Firm"
        }
        self.facade.get_firm_details.return_value = {
            "disclosures": [],
            "accountant_exams": []
        }

        result = search_with_crd_only(claim, self.facade, self.business_ref)
        self.assertTrue(result["compliance"])
        self.assertEqual(result["source"], "FINRA")

        # Test failed search
        self.facade.search_firm_by_crd.return_value = None
        result = search_with_crd_only(claim, self.facade, self.business_ref)
        self.assertFalse(result["compliance"])

    def test_search_with_name_only(self):
        """Test search using business name only."""
        claim = {
            "business_name": "Test Firm"
        }

        # Test successful search
        self.facade.search_firm.return_value = [{
            "organization_crd": "987654",
            "business_name": "Test Firm"
        }]
        self.facade.get_firm_details.return_value = {
            "disclosures": [],
            "accountant_exams": []
        }

        result = search_with_name_only(claim, self.facade, self.business_ref)
        self.assertTrue(result["compliance"])
        self.assertEqual(result["source"], "FINRA")

        # Test failed search
        self.facade.search_firm.return_value = []
        result = search_with_name_only(claim, self.facade, self.business_ref)
        self.assertFalse(result["compliance"])

    def test_search_with_default(self):
        """Test default search strategy."""
        # Test with business name
        claim = {
            "business_name": "Test Firm"
        }
        self.facade.search_firm.return_value = [{
            "organization_crd": "987654",
            "business_name": "Test Firm"
        }]
        self.facade.get_firm_details.return_value = {
            "disclosures": [],
            "accountant_exams": []
        }

        result = search_with_default(claim, self.facade, self.business_ref)
        self.assertTrue(result["compliance"])

        # Test without business name
        claim = {}
        result = search_with_default(claim, self.facade, self.business_ref)
        self.assertFalse(result["compliance"])
        self.assertEqual(result["compliance_explanation"], "Insufficient search criteria")

    @patch('services.firm_business.FirmEvaluationReportBuilder')
    @patch('services.firm_business.FirmEvaluationReportDirector')
    def test_process_claim(self, mock_director_class, mock_builder_class):
        """Test claim processing end-to-end."""
        # Set up mocks
        mock_builder = Mock()
        mock_director = Mock()
        mock_builder_class.return_value = mock_builder
        mock_director_class.return_value = mock_director

        # Create test data
        claim = {
            "reference_id": "TEST123",
            "business_name": "Test Firm",
            "organization_crd": "987654"
        }

        # Mock successful search
        self.facade.search_firm_by_crd.return_value = {
            "organization_crd": "987654",
            "business_name": "Test Firm"
        }
        self.facade.get_firm_details.return_value = {
            "disclosures": [],
            "accountant_exams": []
        }

        # Mock report generation
        mock_report = {
            "reference_id": "TEST123",
            "final_evaluation": {
                "overall_compliance": True,
                "risk_level": "Low"
            }
        }
        mock_director.construct_evaluation_report.return_value = mock_report

        # Test successful processing
        result = process_claim(claim, self.facade, self.business_ref)
        self.assertEqual(result, mock_report)
        self.facade.save_business_report.assert_called_once()

        # Test with invalid data
        mock_director.construct_evaluation_report.side_effect = InvalidDataError("Invalid data")
        with self.assertRaises(InvalidDataError):
            process_claim(claim, self.facade, self.business_ref)

        # Test with evaluation error
        mock_director.construct_evaluation_report.side_effect = EvaluationProcessError("Process failed")
        with self.assertRaises(EvaluationProcessError):
            process_claim(claim, self.facade, self.business_ref)

        # Test with save error
        mock_director.construct_evaluation_report.side_effect = None
        self.facade.save_business_report.side_effect = Exception("Save failed")
        with self.assertRaises(EvaluationProcessError):
            process_claim(claim, self.facade, self.business_ref)

    def test_process_claim_with_skip_flags(self):
        """Test claim processing with skip flags."""
        claim = {
            "reference_id": "TEST123",
            "business_name": "Test Firm",
            "organization_crd": "987654"
        }

        # Set up mocks
        self.facade.search_firm_by_crd.return_value = {
            "organization_crd": "987654",
            "business_name": "Test Firm"
        }
        self.facade.get_firm_details.return_value = {
            "disclosures": [],
            "accountant_exams": []
        }

        # Test with skip flags
        with patch('services.firm_business.FirmEvaluationReportBuilder') as mock_builder_class:
            with patch('services.firm_business.FirmEvaluationReportDirector') as mock_director_class:
                mock_builder = Mock()
                mock_director = Mock()
                mock_builder_class.return_value = mock_builder
                mock_director_class.return_value = mock_director

                mock_report = {
                    "reference_id": "TEST123",
                    "final_evaluation": {
                        "overall_compliance": True,
                        "risk_level": "Low"
                    }
                }
                mock_director.construct_evaluation_report.return_value = mock_report

                result = process_claim(
                    claim,
                    self.facade,
                    self.business_ref,
                    skip_financials=True,
                    skip_legal=True
                )

                # Verify skip flags were passed correctly
                call_args = mock_director.construct_evaluation_report.call_args[0]
                extracted_info = call_args[1]
                self.assertTrue(extracted_info.get("skip_financials"))
                self.assertTrue(extracted_info.get("skip_legal"))

if __name__ == '__main__':
    unittest.main() 