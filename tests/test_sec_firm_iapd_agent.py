"""Unit tests for the SEC IAPD Agent."""

import unittest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime
from pathlib import Path
import sys
import requests

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from agents.sec_firm_iapd_agent import (
    SECFirmIAPDAgent,
    SECAPIError,
    SECResponseError,
    SECRequestError,
    SECRateLimitError,
    IAPD_CONFIG
)

class TestSECFirmIAPDAgent(unittest.TestCase):
    """Test cases for the SEC IAPD Agent."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.agent = SECFirmIAPDAgent()
        
        # Sample response data
        self.sample_search_response = {
            "hits": {
                "total": 1,
                "hits": [{
                    "_source": {
                        "org_name": "Test Investment Advisers",
                        "org_pk": "123456",
                        "sec_number": "801-12345",
                        "firm_type": "Investment Adviser",
                        "registration_status": "Approved"
                    },
                    "highlight": {
                        "org_name": ["<em>Test</em> Investment Advisers"]
                    }
                }]
            }
        }
        
        self.sample_details_response = {
            "hits": {
                "hits": [{
                    "_source": {
                        "org_name": "Test Investment Advisers",
                        "org_pk": "123456",
                        "sec_number": "801-12345",
                        "firm_type": "Investment Adviser",
                        "registration_status": "Approved",
                        "firm_website": "www.testfirm.com",
                        "firm_crd_reg_start_date": "2000-01-01"
                    }
                }]
            }
        }

    @patch('requests.Session')
    def test_search_firm_success(self, mock_session):
        """Test successful firm search by name."""
        # Configure mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.sample_search_response
        mock_session.return_value.get.return_value = mock_response

        # Execute search
        results = self.agent.search_firm("Test Investment Advisers")

        # Verify results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['firm_name'], "Test Investment Advisers")
        self.assertEqual(results[0]['crd_number'], "123456")
        self.assertEqual(results[0]['sec_number'], "801-12345")
        self.assertEqual(results[0]['firm_type'], "Investment Adviser")
        self.assertEqual(results[0]['registration_status'], "Approved")
        self.assertTrue('firm_url' in results[0])

        # Verify API call
        mock_session.return_value.get.assert_called_once()
        call_args = mock_session.return_value.get.call_args
        self.assertEqual(call_args[0][0], IAPD_CONFIG["base_search_url"])
        self.assertIn('query', call_args[1]['params'])
        self.assertEqual(call_args[1]['params']['query'], "Test Investment Advisers")

    @patch('requests.Session')
    def test_search_firm_by_crd_success(self, mock_session):
        """Test successful firm search by CRD number."""
        # Configure mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.sample_search_response
        mock_session.return_value.get.return_value = mock_response

        # Execute search
        results = self.agent.search_firm_by_crd("123456")

        # Verify results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['firm_name'], "Test Investment Advisers")
        self.assertEqual(results[0]['crd_number'], "123456")
        self.assertEqual(results[0]['sec_number'], "801-12345")
        self.assertEqual(results[0]['firm_type'], "Investment Adviser")
        self.assertEqual(results[0]['registration_status'], "Approved")
        self.assertTrue('firm_url' in results[0])

        # Verify API call
        mock_session.return_value.get.assert_called_once()
        call_args = mock_session.return_value.get.call_args
        self.assertEqual(call_args[0][0], IAPD_CONFIG["base_search_url"])
        self.assertIn('query', call_args[1]['params'])
        self.assertEqual(call_args[1]['params']['query'], "123456")

    @patch('requests.Session')
    def test_get_firm_details_success(self, mock_session):
        """Test successful retrieval of firm details."""
        # Configure mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.sample_details_response
        mock_session.return_value.get.return_value = mock_response

        # Execute details retrieval
        details = self.agent.get_firm_details("123456")

        # Verify results
        self.assertEqual(details['org_name'], "Test Investment Advisers")
        self.assertEqual(details['org_pk'], "123456")
        self.assertEqual(details['sec_number'], "801-12345")
        self.assertEqual(details['firm_type'], "Investment Adviser")
        self.assertEqual(details['registration_status'], "Approved")
        self.assertEqual(details['firm_website'], "www.testfirm.com")
        self.assertEqual(details['firm_crd_reg_start_date'], "2000-01-01")

        # Verify API call
        mock_session.return_value.get.assert_called_once()
        call_args = mock_session.return_value.get.call_args
        self.assertTrue(call_args[0][0].endswith("/123456"))

    @patch('requests.Session')
    def test_search_firm_http_error(self, mock_session):
        """Test handling of HTTP errors during firm search."""
        # Configure mock to raise HTTPError
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Client Error")
        mock_session.return_value.get.return_value = mock_response

        # Verify error handling
        with self.assertRaises(SECRequestError):
            self.agent.search_firm("Test Investment Advisers")

    @patch('requests.Session')
    def test_search_firm_invalid_response(self, mock_session):
        """Test handling of invalid response data."""
        # Configure mock with invalid response structure
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"invalid": "response"}
        mock_session.return_value.get.return_value = mock_response

        # Verify error handling
        with self.assertRaises(SECResponseError):
            self.agent.search_firm("Test Investment Advisers")

    @patch('requests.Session')
    def test_rate_limiting(self, mock_session):
        """Test rate limiting behavior."""
        # Configure mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.sample_search_response
        mock_session.return_value.get.return_value = mock_response

        # Make multiple requests
        start_time = datetime.now()
        self.agent.search_firm("Test Investment Advisers")
        self.agent.search_firm("Test Investment Advisers")
        end_time = datetime.now()

        # Verify that the second request was delayed
        elapsed = (end_time - start_time).total_seconds()
        self.assertGreaterEqual(elapsed, 5.0)  # RATE_LIMIT_DELAY is 5 seconds

    def test_save_results(self):
        """Test saving results to a file."""
        # Sample results to save
        results = {
            "search_query": "Test Investment Advisers",
            "total_results": 1,
            "results": [{
                "firm_name": "Test Investment Advisers",
                "crd_number": "123456",
                "sec_number": "801-12345"
            }]
        }

        # Create temporary directory for test
        test_output_dir = Path("test_output")
        test_output_dir.mkdir(exist_ok=True)

        try:
            # Save results
            self.agent.save_results(results, str(test_output_dir))

            # Verify file was created and contains correct data
            saved_files = list(test_output_dir.glob("sec_iapd_results_*.json"))
            self.assertEqual(len(saved_files), 1)

            with open(saved_files[0], 'r') as f:
                saved_data = json.load(f)
                self.assertEqual(saved_data, results)

        finally:
            # Cleanup
            for file in test_output_dir.glob("*"):
                file.unlink()
            test_output_dir.rmdir()

if __name__ == '__main__':
    unittest.main() 