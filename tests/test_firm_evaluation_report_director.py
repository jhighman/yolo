"""
test_firm_evaluation_report_director.py

Unit tests for the FirmEvaluationReportDirector class.
"""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime
import json
from typing import Any, Dict, List, cast, Optional

from evaluation.firm_evaluation_report_director import (
    FirmEvaluationReportDirector,
    InvalidDataError,
    EvaluationProcessError
)
from evaluation.firm_evaluation_processor import Alert, AlertSeverity
from evaluation.firm_evaluation_report_builder import FirmEvaluationReportBuilder

class TestFirmEvaluationReportDirector(unittest.TestCase):
    """Test cases for FirmEvaluationReportDirector class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_builder = Mock(spec=FirmEvaluationReportBuilder)
        self.mock_builder.build.return_value = {
            "registration_status": {},
            "regulatory_oversight": {},
            "disclosures": {},
            "financials": {},
            "legal": {},
            "qualifications": {},
            "data_integrity": {}
        }
        self.director = FirmEvaluationReportDirector(self.mock_builder)
        
        # Sample test data
        self.valid_claim = {
            "business_name": "Test Firm",
            "business_ref": "TEST123"
        }
        
        self.valid_extracted_info = {
            "search_evaluation": {
                "source": "FINRA",
                "compliance": True,
                "compliance_explanation": "Found in database"
            },
            "disclosures": [],
            "accountant_exams": [],
            "legal": {"due_diligence": {}}
        }

    def test_initialization(self):
        """Test director initialization."""
        # Test with valid builder
        director = FirmEvaluationReportDirector(self.mock_builder)
        self.assertIsInstance(director, FirmEvaluationReportDirector)
        
        # Test with invalid builder
        with self.assertRaises(TypeError):
            invalid_builder = cast(FirmEvaluationReportBuilder, "not a builder")
            FirmEvaluationReportDirector(invalid_builder)

    def test_validate_input_data(self):
        """Test input data validation."""
        # Test with valid data
        try:
            self.director._validate_input_data(self.valid_claim, self.valid_extracted_info)
        except InvalidDataError:
            self.fail("_validate_input_data raised InvalidDataError unexpectedly")
        
        # Test with invalid claim
        with self.assertRaises(InvalidDataError):
            invalid_claim = cast(Dict[str, Any], None)
            self.director._validate_input_data(invalid_claim, self.valid_extracted_info)
        
        # Test with missing required claim fields
        invalid_claim = {"business_name": "Test Firm"}
        with self.assertRaises(InvalidDataError):
            self.director._validate_input_data(invalid_claim, self.valid_extracted_info)
        
        # Test with invalid extracted info
        with self.assertRaises(InvalidDataError):
            invalid_info = cast(Dict[str, Any], None)
            self.director._validate_input_data(self.valid_claim, invalid_info)
        
        # Test with missing required extracted info fields
        invalid_extracted_info = {}
        with self.assertRaises(InvalidDataError):
            self.director._validate_input_data(self.valid_claim, invalid_extracted_info)

    def test_create_skip_evaluation(self):
        """Test skip evaluation creation."""
        # Test basic skip evaluation
        result = self.director._create_skip_evaluation("Test skip")
        self.assertTrue(result["compliance"])
        self.assertEqual(result["explanation"], "Test skip")
        self.assertEqual(result["alerts"], [])
        self.assertTrue(result["skipped"])
        self.assertIn("skip_timestamp", result)
        
        # Test with alert
        alert = Alert(
            alert_type="TestAlert",
            severity=AlertSeverity.HIGH,
            metadata={},
            description="Test alert"
        )
        result = self.director._create_skip_evaluation("Test skip", alert)
        self.assertEqual(len(result["alerts"]), 1)
        self.assertEqual(result["alerts"][0]["alert_type"], "TestAlert")
        
        # Test with due diligence
        due_diligence = {"test": "data"}
        result = self.director._create_skip_evaluation("Test skip", None, due_diligence)
        self.assertEqual(result["due_diligence"], due_diligence)
        
        # Test with invalid explanation
        with self.assertRaises(ValueError):
            self.director._create_skip_evaluation("")
        with self.assertRaises(ValueError):
            invalid_explanation = cast(str, None)
            self.director._create_skip_evaluation(invalid_explanation)

    def test_determine_risk_level(self):
        """Test risk level determination."""
        # Create test alerts
        high_alert = Alert(
            alert_type="HIGH",
            severity=AlertSeverity.HIGH,
            metadata={"source": "test"},
            description="High severity alert"
        )
        medium_alert = Alert(
            alert_type="MEDIUM",
            severity=AlertSeverity.MEDIUM,
            metadata={"source": "test"},
            description="Medium severity alert"
        )
        low_alert = Alert(
            alert_type="LOW",
            severity=AlertSeverity.LOW,
            metadata={"source": "test"},
            description="Low severity alert"
        )
        
        # Test with valid alerts
        alerts = [high_alert, medium_alert, low_alert]
        self.assertEqual(self.director._determine_risk_level(alerts), "High")
        
        # Test with only medium alerts
        alerts = [medium_alert]
        self.assertEqual(self.director._determine_risk_level(alerts), "Medium")
        
        # Test with only low alerts
        alerts = [low_alert]
        self.assertEqual(self.director._determine_risk_level(alerts), "Low")
        
        # Test with empty list
        alerts = []
        self.assertEqual(self.director._determine_risk_level(alerts), "Low")
        
        # Test with None in list (should be filtered out)
        alerts = [high_alert, None, low_alert]  # type: ignore
        self.assertEqual(self.director._determine_risk_level(alerts), "High")
        
        # Test with invalid input
        with self.assertRaises(TypeError):
            self.director._determine_risk_level(None)  # type: ignore

    def test_safe_evaluate(self):
        """Test safe evaluation wrapper."""
        # Mock evaluation functions
        def mock_success(*args):
            return True, "Success", [
                Alert(
                    alert_type="INFO",
                    severity=AlertSeverity.LOW,
                    metadata={"source": "test"},
                    description="Info alert"
                )
            ]

        def mock_failure(*args):
            raise Exception("Test error")

        # Test successful evaluation
        result = self.director._safe_evaluate(
            mock_success,
            section_name="registration_status"
        )
        self.assertTrue(result[0])  # compliance
        self.assertEqual(result[1], "Success")  # explanation
        self.assertEqual(len(result[2]), 1)  # alerts

        # Test failed evaluation
        result = self.director._safe_evaluate(
            mock_failure,
            section_name="regulatory_oversight"
        )
        self.assertFalse(result[0])  # compliance
        self.assertIn("Error evaluating regulatory_oversight", result[1])
        self.assertEqual(len(result[2]), 1)  # error alert

    def test_construct_evaluation_report_skip_conditions(self):
        """Test report construction with skip conditions."""
        # Setup skip condition
        extracted_info = self.valid_extracted_info.copy()
        extracted_info["search_evaluation"]["compliance"] = False
        
        # Test skip due to search failure
        report = self.director.construct_evaluation_report(
            self.valid_claim,
            extracted_info
        )
        
        # Verify builder calls for skip condition
        self.mock_builder.set_claim.assert_called_once()
        self.mock_builder.set_search_evaluation.assert_called_once()
        self.assertEqual(self.mock_builder.set_registration_status.call_count, 1)
        
        # Verify skip evaluations were created
        call_args = self.mock_builder.set_registration_status.call_args[0][0]
        self.assertTrue(call_args["skipped"])
        self.assertTrue(call_args["compliance"])

    @patch('evaluation.firm_evaluation_report_director.evaluate_registration_status')
    @patch('evaluation.firm_evaluation_report_director.evaluate_regulatory_oversight')
    @patch('evaluation.firm_evaluation_report_director.evaluate_disclosures')
    @patch('evaluation.firm_evaluation_report_director.evaluate_financials')
    @patch('evaluation.firm_evaluation_report_director.evaluate_legal')
    @patch('evaluation.firm_evaluation_report_director.evaluate_qualifications')
    @patch('evaluation.firm_evaluation_report_director.evaluate_data_integrity')
    def test_construct_evaluation_report_full(
        self, mock_data, mock_qual, mock_legal, mock_fin,
        mock_disc, mock_oversight, mock_reg_status
    ):
        """Test full report construction."""
        # Set up mock return values
        mock_result = (True, "Success", [
            Alert(
                alert_type="INFO",
                severity=AlertSeverity.LOW,
                metadata={"source": "test"},
                description="Info alert"
            )
        ])
        
        # Set return values for all mocks
        mock_reg_status.return_value = mock_result
        mock_oversight.return_value = mock_result
        mock_disc.return_value = mock_result
        mock_fin.return_value = mock_result
        mock_legal.return_value = mock_result
        mock_qual.return_value = mock_result
        mock_data.return_value = mock_result

        # Run full evaluation
        report = self.director.construct_evaluation_report(
            self.valid_claim,
            self.valid_extracted_info
        )
        
        # Verify all evaluation functions were called
        mock_reg_status.assert_called_once_with(self.valid_extracted_info)
        mock_oversight.assert_called_once_with(self.valid_extracted_info, "Test Firm")
        mock_disc.assert_called_once_with([], "Test Firm")  # Empty list from valid_extracted_info
        mock_fin.assert_called_once_with(self.valid_extracted_info, "Test Firm")
        mock_legal.assert_called_once_with(self.valid_extracted_info, "Test Firm", {})
        mock_qual.assert_called_once_with([], "Test Firm")  # Empty list from valid_extracted_info
        mock_data.assert_called_once_with(self.valid_extracted_info)

    def test_error_handling(self):
        """Test error handling in report construction."""
        # Test builder failure
        self.mock_builder.set_claim.side_effect = Exception("Builder error")
        
        with self.assertRaises(EvaluationProcessError):
            self.director.construct_evaluation_report(
                self.valid_claim,
                self.valid_extracted_info
            )
        
        # Test invalid input data
        with self.assertRaises(InvalidDataError):
            self.director.construct_evaluation_report(
                {},  # Invalid claim
                self.valid_extracted_info
            )
        
        # Test unexpected error
        self.mock_builder.set_claim.side_effect = KeyError("Unexpected error")
        
        with self.assertRaises(EvaluationProcessError):
            self.director.construct_evaluation_report(
                self.valid_claim,
                self.valid_extracted_info
            )

if __name__ == '__main__':
    unittest.main() 