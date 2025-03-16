"""Unit tests for the FirmServicesFacade class."""

import unittest
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List
import argparse
from io import StringIO
import sys

from services.firm_services import FirmServicesFacade

class TestFirmServices(unittest.TestCase):
    """Test cases for the FirmServices class."""
    
    def setUp(self):
        self.facade = FirmServicesFacade()
        self.subject_id = "test_subject"
        
        # Sample test data
        self.mock_finra_data = {
            "organization_crd": "12345",
            "firm_name": "Test Firm",
            "address": "123 Test St",
            "city": "Test City",
            "state": "TS",
            "zip": "12345"
        }
        
        self.mock_sec_data = {
            "organization_crd": "12345",
            "firm_name": "Test Firm",
            "address": "123 Test St",
            "city": "Test City",
            "state": "TS",
            "zip": "12345"
        }

    @patch('services.firm_services.fetch_finra_firm_details')
    @patch('services.firm_services.fetch_sec_firm_details')
    def test_get_firm_details(self, mock_sec_details, mock_finra_details):
        """Test getting firm details."""
        mock_finra_details.return_value = self.mock_finra_data
        mock_sec_details.return_value = self.mock_sec_data
        
        results = self.facade.get_firm_details(self.subject_id, "12345")
        self.assertEqual(results, self.mock_finra_data)
        mock_finra_details.assert_called_once_with(self.subject_id, "details_12345", {"organization_crd": "12345"})
        mock_sec_details.assert_not_called()

    @patch('services.firm_services.fetch_finra_firm_search')
    @patch('services.firm_services.fetch_sec_firm_search')
    def test_search_firm(self, mock_sec_search, mock_finra_search):
        """Test searching firm by name."""
        mock_finra_search.return_value = [self.mock_finra_data]
        mock_sec_search.return_value = [self.mock_sec_data]
        
        results = self.facade.search_firm(self.subject_id, "Test Firm")
        self.assertEqual(results, [self.mock_finra_data, self.mock_sec_data])
        mock_finra_search.assert_called_once_with(self.subject_id, "search_Test Firm", {"firm_name": "Test Firm"})
        mock_sec_search.assert_called_once_with(self.subject_id, "search_Test Firm", {"firm_name": "Test Firm"})

    @patch('services.firm_services.fetch_finra_firm_by_crd')
    @patch('services.firm_services.fetch_sec_firm_by_crd')
    def test_search_firm_by_crd(self, mock_sec_search, mock_finra_search):
        """Test searching firm by CRD."""
        mock_finra_search.return_value = self.mock_finra_data
        mock_sec_search.return_value = self.mock_sec_data
        
        results = self.facade.search_firm_by_crd(self.subject_id, "12345")
        self.assertEqual(results, self.mock_finra_data)
        mock_finra_search.assert_called_once_with(self.subject_id, "search_crd_12345", {"organization_crd": "12345"})
        mock_sec_search.assert_not_called()

    @patch('services.firm_services.save_compliance_report')
    def test_save_compliance_report(self, mock_save):
        """Test saving compliance report."""
        mock_save.return_value = True
        report = {"test": "data"}
        
        result = self.facade.save_compliance_report(report, "EMP123")
        self.assertTrue(result)
        mock_save.assert_called_once_with(report, "EMP123")

    @patch('services.firm_services.save_business_report')
    def test_save_business_report(self, mock_save):
        """Test saving business report."""
        report = {"test": "data"}
        
        self.facade.save_business_report(report, "BIZ123")
        mock_save.assert_called_once_with(report, "BIZ123")

if __name__ == '__main__':
    unittest.main() 