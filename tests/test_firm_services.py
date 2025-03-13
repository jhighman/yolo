"""Unit tests for the FirmServicesFacade class."""

import unittest
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List

from services.firm_services import FirmServicesFacade

class TestFirmServicesFacade(unittest.TestCase):
    """Test cases for FirmServicesFacade."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.facade = FirmServicesFacade()
        
        # Sample test data
        self.sample_finra_result = {
            "org_name": "Test Firm FINRA",
            "org_source_id": "12345",
            "registration_status": "APPROVED"
        }
        
        self.sample_sec_result = {
            "firm_name": "Test Firm SEC",
            "crd_number": "12345",
            "sec_number": "801-12345",
            "registration_status": "ACTIVE"
        }
        
        # Search results don't include registration_status in normalized form
        self.normalized_finra_search_result = {
            "firm_name": "Test Firm FINRA",
            "crd_number": "12345",
            "source": "FINRA",
            "raw_data": self.sample_finra_result
        }
        
        self.normalized_sec_search_result = {
            "firm_name": "Test Firm SEC",
            "crd_number": "12345",
            "sec_number": "801-12345",
            "source": "SEC",
            "raw_data": self.sample_sec_result
        }
        
        # Details results include registration_status and additional fields
        self.normalized_finra_details = {
            "firm_name": "Test Firm FINRA",
            "crd_number": "12345",
            "registration_status": "APPROVED",
            "source": "FINRA",
            "addresses": [],
            "disclosures": [],
            "raw_data": self.sample_finra_result
        }
        
        self.normalized_sec_details = {
            "firm_name": "Test Firm SEC",
            "crd_number": "12345",
            "sec_number": "801-12345",
            "registration_status": "ACTIVE",
            "source": "SEC",
            "addresses": [],
            "disclosures": [],
            "raw_data": self.sample_sec_result
        }

    @patch('services.firm_services.fetch_finra_firm_search')
    @patch('services.firm_services.fetch_sec_firm_search')
    def test_search_firm_success(self, mock_sec_search, mock_finra_search):
        """Test successful firm search from both FINRA and SEC."""
        # Setup mocks
        mock_finra_search.return_value = [self.sample_finra_result]
        mock_sec_search.return_value = [self.sample_sec_result]
        
        # Execute search
        results = self.facade.search_firm("Test Firm")
        
        # Verify results
        self.assertEqual(len(results), 2)
        self.assertIn(self.normalized_finra_search_result, results)
        self.assertIn(self.normalized_sec_search_result, results)
        
        # Verify mocks called correctly
        mock_finra_search.assert_called_once_with("search_Test Firm", {"firm_name": "Test Firm"})
        mock_sec_search.assert_called_once_with("search_Test Firm", {"firm_name": "Test Firm"})

    @patch('services.firm_services.fetch_finra_firm_search')
    @patch('services.firm_services.fetch_sec_firm_search')
    def test_search_firm_finra_error(self, mock_sec_search, mock_finra_search):
        """Test firm search when FINRA fails but SEC succeeds."""
        # Setup mocks
        mock_finra_search.side_effect = Exception("FINRA API Error")
        mock_sec_search.return_value = [self.sample_sec_result]
        
        # Execute search
        results = self.facade.search_firm("Test Firm")
        
        # Verify results - should only have SEC result
        self.assertEqual(len(results), 1)
        self.assertIn(self.normalized_sec_search_result, results)

    @patch('services.firm_services.fetch_finra_firm_details')
    @patch('services.firm_services.fetch_sec_firm_details')
    def test_get_firm_details_finra_success(self, mock_sec_details, mock_finra_details):
        """Test getting firm details when FINRA succeeds."""
        # Setup mocks
        mock_finra_details.return_value = self.sample_finra_result
        
        # Execute search
        result = self.facade.get_firm_details("12345")
        
        # Verify result
        self.assertEqual(result, self.normalized_finra_details)
        
        # Verify only FINRA was called (SEC shouldn't be called if FINRA succeeds)
        mock_finra_details.assert_called_once_with("details_12345", {"crd_number": "12345"})
        mock_sec_details.assert_not_called()

    @patch('services.firm_services.fetch_finra_firm_details')
    @patch('services.firm_services.fetch_sec_firm_details')
    def test_get_firm_details_finra_fails_sec_success(self, mock_sec_details, mock_finra_details):
        """Test getting firm details when FINRA fails but SEC succeeds."""
        # Setup mocks
        mock_finra_details.side_effect = Exception("FINRA API Error")
        mock_sec_details.return_value = self.sample_sec_result
        
        # Execute search
        result = self.facade.get_firm_details("12345")
        
        # Verify result
        self.assertEqual(result, self.normalized_sec_details)
        
        # Verify both services were called
        mock_finra_details.assert_called_once()
        mock_sec_details.assert_called_once()

    @patch('services.firm_services.fetch_finra_firm_by_crd')
    @patch('services.firm_services.fetch_sec_firm_by_crd')
    def test_search_firm_by_crd_finra_success(self, mock_sec_search, mock_finra_search):
        """Test searching firm by CRD when FINRA succeeds."""
        # Setup mocks
        mock_finra_search.return_value = self.sample_finra_result
        
        # Execute search
        result = self.facade.search_firm_by_crd("12345")
        
        # Verify result
        self.assertEqual(result, self.normalized_finra_search_result)
        
        # Verify only FINRA was called
        mock_finra_search.assert_called_once_with("search_crd_12345", {"crd_number": "12345"})
        mock_sec_search.assert_not_called()

    @patch('services.firm_services.fetch_finra_firm_by_crd')
    @patch('services.firm_services.fetch_sec_firm_by_crd')
    def test_search_firm_by_crd_both_fail(self, mock_sec_search, mock_finra_search):
        """Test searching firm by CRD when both services fail."""
        # Setup mocks
        mock_finra_search.side_effect = Exception("FINRA API Error")
        mock_sec_search.side_effect = Exception("SEC API Error")
        
        # Execute search
        result = self.facade.search_firm_by_crd("12345")
        
        # Verify result is None when both services fail
        self.assertIsNone(result)
        
        # Verify both services were called
        mock_finra_search.assert_called_once()
        mock_sec_search.assert_called_once()

    def test_invalid_response_types(self):
        """Test handling of invalid response types from services."""
        with patch('services.firm_services.fetch_finra_firm_search') as mock_finra:
            with patch('services.firm_services.fetch_sec_firm_search') as mock_sec:
                # Test with None response
                mock_finra.return_value = None
                mock_sec.return_value = None
                results = self.facade.search_firm("Test Firm")
                self.assertEqual(len(results), 0)
                
                # Test with string response instead of list
                mock_finra.return_value = "Invalid Response"
                mock_sec.return_value = "Invalid Response"
                results = self.facade.search_firm("Test Firm")
                self.assertEqual(len(results), 0)
                
                # Test with list containing non-dict items
                mock_finra.return_value = ["not a dict", 123]
                mock_sec.return_value = ["not a dict", 123]
                results = self.facade.search_firm("Test Firm")
                self.assertEqual(len(results), 0)

if __name__ == '__main__':
    unittest.main() 