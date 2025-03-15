"""
Unit tests for firm_evaluation_processor.py

Tests the evaluation functions for firm compliance and risk assessment.
"""

import unittest
from datetime import datetime, timedelta
from evaluation.firm_evaluation_processor import (
    AlertSeverity,
    Alert,
    evaluate_registration_status,
    evaluate_regulatory_oversight,
    evaluate_disclosures,
    evaluate_financials,
    evaluate_legal,
    evaluate_qualifications,
    evaluate_data_integrity
)

def create_iso_date(days_ago: int) -> str:
    """Helper function to create ISO format dates relative to today."""
    date = datetime.now() - timedelta(days=days_ago)
    return date.isoformat()  # Return naive datetime string

class TestFirmEvaluationProcessor(unittest.TestCase):
    def test_registration_status_active(self):
        """Test evaluation of an actively registered firm."""
        business_info = {
            "is_sec_registered": True,
            "is_finra_registered": True,
            "is_state_registered": False,
            "registration_status": "APPROVED",
            "registration_date": create_iso_date(365)
        }
        
        compliant, explanation, alerts = evaluate_registration_status(business_info)
        self.assertTrue(compliant)
        self.assertIn("SEC", explanation)
        self.assertIn("FINRA", explanation)
        self.assertEqual(len(alerts), 0)

    def test_registration_status_terminated(self):
        """Test evaluation of a terminated registration."""
        business_info = {
            "is_sec_registered": False,
            "is_finra_registered": False,
            "is_state_registered": False,
            "registration_status": "TERMINATED",
            "registration_date": create_iso_date(730)
        }
        
        compliant, explanation, alerts = evaluate_registration_status(business_info)
        self.assertFalse(compliant)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].severity, AlertSeverity.HIGH)
        self.assertEqual(alerts[0].alert_type, "TerminatedRegistration")

    def test_regulatory_oversight_active(self):
        """Test evaluation of active regulatory oversight."""
        business_info = {
            "regulatory_authorities": ["SEC", "FINRA"],
            "notice_filings": [
                {
                    "state": "CA",
                    "status": "ACTIVE",
                    "effective_date": create_iso_date(180),
                    "termination_date": None
                }
            ]
        }
        business_name = "Test Firm"
        
        compliant, explanation, alerts = evaluate_regulatory_oversight(business_info, business_name)
        self.assertTrue(compliant)
        self.assertIn("CA", explanation)
        self.assertEqual(len(alerts), 0)

    def test_disclosures_clean(self):
        """Test evaluation of a firm with no disclosures."""
        disclosures = []
        business_name = "Test Firm"
        
        compliant, explanation, alerts = evaluate_disclosures(disclosures, business_name)
        self.assertTrue(compliant)
        self.assertEqual(len(alerts), 0)
        self.assertIn("No disclosures", explanation)

    def test_disclosures_with_issues(self):
        """Test evaluation of a firm with active disclosures."""
        disclosures = [
            {
                "status": "PENDING",
                "date": create_iso_date(30),
                "description": "Regulatory investigation",
                "sanctions": ["Fine"]
            }
        ]
        business_name = "Test Firm"
        
        compliant, explanation, alerts = evaluate_disclosures(disclosures, business_name)
        self.assertFalse(compliant)
        self.assertTrue(any(a.severity == AlertSeverity.HIGH for a in alerts))

    def test_disclosures_unresolved(self):
        """Test evaluation with unresolved disclosures."""
        disclosures = [
            {
                "status": "PENDING",
                "date": create_iso_date(90),
                "description": "Regulatory investigation"
            }
        ]
        business_name = "Test Firm"
        
        compliant, explanation, alerts = evaluate_disclosures(disclosures, business_name)
        self.assertFalse(compliant)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].severity, AlertSeverity.HIGH)
        self.assertEqual(alerts[0].alert_type, "UnresolvedDisclosure")

    def test_disclosures_recent_resolved(self):
        """Test evaluation with recently resolved disclosures."""
        disclosures = [
            {
                "status": "RESOLVED",
                "date": create_iso_date(180),
                "description": "Minor violation - resolved"
            }
        ]
        business_name = "Test Firm"
        
        compliant, explanation, alerts = evaluate_disclosures(disclosures, business_name)
        self.assertTrue(compliant)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].severity, AlertSeverity.MEDIUM)
        self.assertEqual(alerts[0].alert_type, "RecentDisclosure")

    def test_disclosures_missing_date(self):
        """Test evaluation with missing disclosure date."""
        disclosures = [
            {
                "status": "RESOLVED",
                "date": None,
                "description": "Historical disclosure"
            }
        ]
        business_name = "Test Firm"
        
        compliant, explanation, alerts = evaluate_disclosures(disclosures, business_name)
        self.assertTrue(compliant)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].severity, AlertSeverity.MEDIUM)
        self.assertEqual(alerts[0].alert_type, "MissingDisclosureDate")

    def test_financials_current(self):
        """Test evaluation of current financial filings."""
        business_info = {
            "adv_filing_date": create_iso_date(180),
            "has_adv_pdf": True,
            "disclosures": []
        }
        business_name = "Test Firm"
        
        compliant, explanation, alerts = evaluate_financials(business_info, business_name)
        self.assertTrue(compliant)
        self.assertEqual(len(alerts), 0)

    def test_financials_outdated(self):
        """Test evaluation of outdated financial filings."""
        business_info = {
            "adv_filing_date": create_iso_date(400),
            "has_adv_pdf": False,
            "disclosures": []
        }
        business_name = "Test Firm"
        
        compliant, explanation, alerts = evaluate_financials(business_info, business_name)
        self.assertFalse(compliant)
        self.assertTrue(any(a.alert_type == "OutdatedFinancialFiling" for a in alerts))

    def test_financials_no_adv(self):
        """Test evaluation with no ADV filing."""
        business_info = {
            "adv_filing_date": None,
            "has_adv_pdf": False
        }
        business_name = "Test Firm"
        
        compliant, explanation, alerts = evaluate_financials(business_info, business_name)
        self.assertFalse(compliant)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].severity, AlertSeverity.HIGH)
        self.assertEqual(alerts[0].alert_type, "NoADVFiling")

    def test_financials_outdated_adv(self):
        """Test evaluation with outdated ADV filing."""
        business_info = {
            "adv_filing_date": create_iso_date(400),  # More than 1 year old
            "has_adv_pdf": True,
            "disclosures": []
        }
        business_name = "Test Firm"
        
        compliant, explanation, alerts = evaluate_financials(business_info, business_name)
        self.assertTrue(compliant)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].severity, AlertSeverity.MEDIUM)
        self.assertEqual(alerts[0].alert_type, "OutdatedFinancialFiling")

    def test_financials_missing_pdf(self):
        """Test evaluation with missing ADV PDF."""
        business_info = {
            "adv_filing_date": create_iso_date(30),
            "has_adv_pdf": False,
            "disclosures": []
        }
        business_name = "Test Firm"
        
        compliant, explanation, alerts = evaluate_financials(business_info, business_name)
        self.assertTrue(compliant)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].severity, AlertSeverity.MEDIUM)
        self.assertEqual(alerts[0].alert_type, "MissingADVDocument")

    def test_financials_with_distress(self):
        """Test evaluation with financial distress disclosure."""
        business_info = {
            "adv_filing_date": create_iso_date(30),
            "has_adv_pdf": True,
            "disclosures": [
                {
                    "type": "FINANCIAL_DISTRESS",
                    "date": create_iso_date(60),
                    "status": "PENDING"
                }
            ]
        }
        business_name = "Test Firm"
        
        compliant, explanation, alerts = evaluate_financials(business_info, business_name)
        self.assertFalse(compliant)
        self.assertTrue(any(a.alert_type == "FinancialDisclosure" for a in alerts))

    def test_legal_clean(self):
        """Test evaluation of a firm with no legal issues."""
        business_info = {
            "headquarters": {"country": "UNITED STATES", "state": "CA"},
            "is_sec_registered": True,
            "disclosures": []
        }
        business_name = "Test Firm"
        
        compliant, explanation, alerts = evaluate_legal(business_info, business_name)
        self.assertTrue(compliant)
        self.assertEqual(len(alerts), 0)

    def test_legal_with_issues(self):
        """Test evaluation of a firm with legal issues."""
        business_info = {
            "headquarters": {"country": "CANADA", "state": "ON"},
            "is_sec_registered": True,
            "disclosures": [
                {
                    "type": "CIVIL",
                    "status": "PENDING",
                    "date": create_iso_date(30),
                    "description": "Civil litigation"
                }
            ]
        }
        business_name = "Test Firm"
        
        compliant, explanation, alerts = evaluate_legal(business_info, business_name)
        self.assertFalse(compliant)
        self.assertTrue(any(a.alert_type == "JurisdictionMismatch" for a in alerts))
        self.assertTrue(any(a.alert_type == "PendingLegalAction" for a in alerts))

    def test_qualifications_current(self):
        """Test evaluation of current qualifications."""
        accountant_exams = [
            {
                "exam_type": "Series 65",
                "status": "PASSED",
                "date": create_iso_date(365)
            }
        ]
        business_name = "Test Firm"
        
        compliant, explanation, alerts = evaluate_qualifications(accountant_exams, business_name)
        self.assertTrue(compliant)
        self.assertIn("Series 65", explanation)
        self.assertEqual(len(alerts), 0)

    def test_qualifications_failed(self):
        """Test evaluation of failed qualifications."""
        accountant_exams = [
            {
                "exam_type": "Series 66",
                "status": "FAILED",
                "date": create_iso_date(30)
            }
        ]
        business_name = "Test Firm"
        
        compliant, explanation, alerts = evaluate_qualifications(accountant_exams, business_name)
        self.assertFalse(compliant)
        self.assertTrue(any(a.alert_type == "FailedAccountantExam" for a in alerts))

    def test_data_integrity_current(self):
        """Test evaluation of current data."""
        business_info = {
            "last_updated": create_iso_date(1),  # 1 day old
            "data_sources": ["FINRA", "SEC"],
            "cache_status": {
                "is_cached": True,
                "cache_date": create_iso_date(0),  # Today
                "ttl": 86400  # 1 day in seconds
            }
        }
        
        compliant, explanation, alerts = evaluate_data_integrity(business_info)
        self.assertTrue(compliant)
        self.assertEqual(len(alerts), 0)
        self.assertEqual(explanation, "Data is current and reliable")

    def test_data_integrity_outdated(self):
        """Test evaluation of outdated data."""
        business_info = {
            "last_updated": create_iso_date(200),  # More than 6 months old
            "data_sources": [],  # No data sources - HIGH severity
            "cache_status": {
                "is_cached": True,
                "cache_date": create_iso_date(2),
                "ttl": 3600  # 1 hour in seconds
            }
        }
        
        compliant, explanation, alerts = evaluate_data_integrity(business_info)
        self.assertFalse(compliant)
        self.assertTrue(any(a.alert_type == "NoDataSources" for a in alerts))
        self.assertTrue(any(a.severity == AlertSeverity.HIGH for a in alerts))
        self.assertEqual(explanation, "No data sources specified")

    def test_registration_status_pending(self):
        """Test evaluation of a pending registration."""
        business_info = {
            "is_sec_registered": False,
            "is_finra_registered": False,
            "is_state_registered": False,
            "registration_status": "PENDING",
            "registration_date": create_iso_date(30)
        }
        
        compliant, explanation, alerts = evaluate_registration_status(business_info)
        self.assertFalse(compliant)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].severity, AlertSeverity.MEDIUM)
        self.assertEqual(alerts[0].alert_type, "PendingRegistration")

    def test_registration_status_invalid_date(self):
        """Test evaluation with an invalid registration date."""
        business_info = {
            "is_sec_registered": True,
            "is_finra_registered": True,
            "registration_status": "APPROVED",
            "registration_date": "invalid-date"
        }
        
        compliant, explanation, alerts = evaluate_registration_status(business_info)
        self.assertTrue(compliant)  # Still compliant because registration is active
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].severity, AlertSeverity.MEDIUM)
        self.assertEqual(alerts[0].alert_type, "InvalidDateFormat")

    def test_registration_status_future_date(self):
        """Test evaluation with a future registration date."""
        future_date = (datetime.now() + timedelta(days=30)).isoformat()
        business_info = {
            "is_sec_registered": True,
            "registration_status": "APPROVED",
            "registration_date": future_date
        }
        
        compliant, explanation, alerts = evaluate_registration_status(business_info)
        self.assertFalse(compliant)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].severity, AlertSeverity.HIGH)
        self.assertEqual(alerts[0].alert_type, "InvalidRegistrationDate")

    def test_registration_status_old(self):
        """Test evaluation with a very old registration."""
        business_info = {
            "is_sec_registered": True,
            "registration_status": "APPROVED",
            "registration_date": create_iso_date(365 * 21)  # 21 years old
        }
        
        compliant, explanation, alerts = evaluate_registration_status(business_info)
        self.assertTrue(compliant)  # Still compliant because registration is active
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].severity, AlertSeverity.LOW)
        self.assertEqual(alerts[0].alert_type, "OldRegistration")

    def test_regulatory_oversight_no_authorities(self):
        """Test evaluation with no regulatory authorities."""
        business_info = {
            "regulatory_authorities": [],
            "notice_filings": [
                {
                    "state": "CA",
                    "status": "ACTIVE",
                    "effective_date": create_iso_date(180)
                }
            ]
        }
        business_name = "Test Firm"
        
        compliant, explanation, alerts = evaluate_regulatory_oversight(business_info, business_name)
        self.assertFalse(compliant)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].severity, AlertSeverity.HIGH)
        self.assertEqual(alerts[0].alert_type, "NoRegulatoryOversight")

    def test_regulatory_oversight_missing_dates(self):
        """Test evaluation with missing dates in notice filings."""
        business_info = {
            "regulatory_authorities": ["SEC"],
            "notice_filings": [
                {
                    "state": "CA",
                    "status": "ACTIVE",
                    "effective_date": None
                }
            ]
        }
        business_name = "Test Firm"
        
        compliant, explanation, alerts = evaluate_regulatory_oversight(business_info, business_name)
        self.assertTrue(compliant)  # Still compliant because has SEC authority
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].severity, AlertSeverity.MEDIUM)
        self.assertEqual(alerts[0].alert_type, "MissingFilingDate")

    def test_regulatory_oversight_terminated_filing(self):
        """Test evaluation with terminated notice filing."""
        business_info = {
            "regulatory_authorities": ["SEC"],
            "notice_filings": [
                {
                    "state": "CA",
                    "status": "TERMINATED",
                    "effective_date": create_iso_date(365),
                    "termination_date": create_iso_date(30)
                }
            ]
        }
        business_name = "Test Firm"
        
        compliant, explanation, alerts = evaluate_regulatory_oversight(business_info, business_name)
        self.assertTrue(compliant)  # Still compliant because has SEC authority
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].severity, AlertSeverity.MEDIUM)
        self.assertEqual(alerts[0].alert_type, "TerminatedNoticeFiling")

    def test_regulatory_oversight_old_filing(self):
        """Test evaluation with old notice filing."""
        business_info = {
            "regulatory_authorities": ["SEC"],
            "notice_filings": [
                {
                    "state": "CA",
                    "status": "ACTIVE",
                    "effective_date": create_iso_date(365 * 6)  # 6 years old
                }
            ]
        }
        business_name = "Test Firm"
        
        compliant, explanation, alerts = evaluate_regulatory_oversight(business_info, business_name)
        self.assertTrue(compliant)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].severity, AlertSeverity.LOW)
        self.assertEqual(alerts[0].alert_type, "OldNoticeFiling")

    def test_qualifications_missing_date(self):
        """Test evaluation with missing exam date."""
        accountant_exams = [
            {
                "exam_type": "Series 7",
                "status": "PASSED",
                "date": None
            }
        ]
        business_name = "Test Firm"
        
        compliant, explanation, alerts = evaluate_qualifications(accountant_exams, business_name)
        self.assertTrue(compliant)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].severity, AlertSeverity.MEDIUM)
        self.assertEqual(alerts[0].alert_type, "MissingExamDate")

    def test_qualifications_multiple_failures(self):
        """Test evaluation with multiple failed exams."""
        accountant_exams = [
            {
                "exam_type": "Series 7",
                "status": "FAILED",
                "date": create_iso_date(90)
            },
            {
                "exam_type": "Series 66",
                "status": "FAILED",
                "date": create_iso_date(60)
            }
        ]
        business_name = "Test Firm"
        
        compliant, explanation, alerts = evaluate_qualifications(accountant_exams, business_name)
        self.assertFalse(compliant)
        self.assertEqual(len(alerts), 2)
        self.assertTrue(all(a.alert_type == "FailedAccountantExam" for a in alerts))

    def test_qualifications_outdated(self):
        """Test evaluation with outdated qualifications."""
        accountant_exams = [
            {
                "exam_type": "Series 7",
                "status": "PASSED",
                "date": create_iso_date(365 * 12)  # 12 years old
            }
        ]
        business_name = "Test Firm"
        
        compliant, explanation, alerts = evaluate_qualifications(accountant_exams, business_name)
        self.assertTrue(compliant)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].severity, AlertSeverity.LOW)
        self.assertEqual(alerts[0].alert_type, "OutdatedQualification")

    def test_data_integrity_invalid_dates(self):
        """Test evaluation with invalid date formats."""
        business_info = {
            "last_updated": "invalid-date",
            "data_sources": ["FINRA"],
            "cache_status": {
                "is_cached": True,
                "cache_date": "also-invalid",
                "ttl": 3600
            }
        }
        
        compliant, explanation, alerts = evaluate_data_integrity(business_info)
        self.assertFalse(compliant)
        self.assertTrue(any(a.alert_type == "InvalidLastUpdateDate" for a in alerts))
        self.assertTrue(any(a.alert_type == "InvalidCacheDate" for a in alerts))

    def test_data_integrity_expired_cache(self):
        """Test evaluation with expired cache."""
        business_info = {
            "last_updated": create_iso_date(30),
            "data_sources": ["FINRA"],
            "cache_status": {
                "is_cached": True,
                "cache_date": create_iso_date(2),
                "ttl": 3600  # 1 hour in seconds
            }
        }
        
        compliant, explanation, alerts = evaluate_data_integrity(business_info)
        self.assertTrue(compliant)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].severity, AlertSeverity.LOW)
        self.assertEqual(alerts[0].alert_type, "ExpiredCache")

    def test_data_integrity_no_cache_info(self):
        """Test evaluation with missing cache information."""
        business_info = {
            "last_updated": create_iso_date(30),
            "data_sources": ["FINRA"],
            "cache_status": {
                "is_cached": False
            }
        }
        
        compliant, explanation, alerts = evaluate_data_integrity(business_info)
        self.assertTrue(compliant)
        self.assertEqual(len(alerts), 0)

if __name__ == '__main__':
    unittest.main() 