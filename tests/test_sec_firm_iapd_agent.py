"""Unit tests for the SEC IAPD Agent."""

import unittest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime
from pathlib import Path
import sys

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from agents.sec_firm_iapd_agent import (
    SECFirmIAPDAgent,
    RATE_LIMIT_DELAY,
    IAPD_CONFIG
)

class TestSECFirmIAPDAgent(unittest.TestCase):
    """Test cases for the SEC IAPD Agent."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.agent = SECFirmIAPDAgent()
        self.mock_response = MagicMock()
        self.mock_response.status_code = 200

    def test_search_firm_success(self):
        """Test successful firm search by name."""
        # Configure mock response
        self.mock_response.json.return_value = {
            "hits": {
                "total": 1,
                "hits": [
                    {
                        "_source": {
                            "org_name": "Test Investment Advisers",
                            "org_pk": "123456",
                            "sec_number": "801-12345",
                            "firm_type": "Investment Adviser",
                            "registration_status": "ACTIVE"
                        }
                    }
                ]
            }
        }

        # Patch the agent's session.get method
        with patch.object(self.agent.session, 'get', return_value=self.mock_response) as mock_get:
            # Execute search
            print("\n=== SEC test_search_firm_success ===")
            results = self.agent.search_firm("Test Investment Advisers")
            print(f"Mock response: {self.mock_response.json.return_value}")
            print(f"Actual results: {results}")
            print(f"Mock get call count: {mock_get.call_count}")
            print(f"Mock get call args: {mock_get.call_args}")

            # Verify results
            self.assertGreater(len(results), 0, "Expected at least one result from search")
            self.assertIn('firm_name', results[0], "Result should contain 'firm_name' key")
            self.assertEqual(results[0]['firm_name'], "Test Investment Advisers",
                            "firm_name should match mocked org_name")
            self.assertEqual(results[0]['crd_number'], "123456", "crd_number should match mocked org_pk")

            # Verify mock call
            mock_get.assert_called_once_with(
                IAPD_CONFIG["base_search_url"],
                params={**IAPD_CONFIG["default_params"], "query": "Test Investment Advisers"},
                timeout=(10, 30)
            )

    def test_search_firm_by_crd_success(self):
        """Test successful firm search by CRD number."""
        # Configure mock response
        self.mock_response.json.return_value = {
            "hits": {
                "total": 1,
                "hits": [
                    {
                        "_source": {
                            "org_name": "Test Investment Advisers",
                            "org_pk": "123456",
                            "sec_number": "801-12345",
                            "firm_type": "Investment Adviser",
                            "registration_status": "ACTIVE"
                        }
                    }
                ]
            }
        }

        # Patch the agent's session.get method
        with patch.object(self.agent.session, 'get', return_value=self.mock_response) as mock_get:
            # Execute search
            print("\n=== SEC test_search_firm_by_crd_success ===")
            results = self.agent.search_firm_by_crd("123456")
            print(f"Mock response: {self.mock_response.json.return_value}")
            print(f"Actual results: {results}")
            print(f"Mock get call count: {mock_get.call_count}")
            print(f"Mock get call args: {mock_get.call_args}")

            # Verify results
            self.assertGreater(len(results), 0, "Expected at least one result from CRD search")
            self.assertIn('firm_name', results[0], "Result should contain 'firm_name' key")
            self.assertEqual(results[0]['firm_name'], "Test Investment Advisers",
                            "firm_name should match mocked org_name")
            self.assertEqual(results[0]['crd_number'], "123456", "crd_number should match mocked org_pk")

            # Verify mock call
            mock_get.assert_called_once_with(
                IAPD_CONFIG["base_search_url"],
                params={**IAPD_CONFIG["default_params"], "query": "123456"},
                timeout=(10, 30)
            )

    def test_get_firm_details_success(self):
        """Test successful retrieval of firm details."""
        # Configure mock response
        self.mock_response.json.return_value = {
            "hits": {
                "total": 1,
                "hits": [
                    {
                        "_source": {
                            "org_name": "Test Investment Advisers",
                            "org_pk": "123456",
                            "sec_number": "801-12345",
                            "firm_type": "Investment Adviser",
                            "registration_status": "ACTIVE"
                        }
                    }
                ]
            }
        }

        # Patch the agent's session.get method
        with patch.object(self.agent.session, 'get', return_value=self.mock_response) as mock_get:
            # Execute details retrieval
            print("\n=== SEC test_get_firm_details_success ===")
            details = self.agent.get_firm_details("123456")
            print(f"Mock response: {self.mock_response.json.return_value}")
            print(f"Actual details: {details}")
            print(f"Mock get call count: {mock_get.call_count}")
            print(f"Mock get call args: {mock_get.call_args}")

            # Verify results
            self.assertIsInstance(details, dict, "Details should be a dictionary")
            self.assertIn('org_name', details, "Details should contain 'org_name' key")
            self.assertEqual(details['org_name'], "Test Investment Advisers",
                            "org_name should match mocked response")
            self.assertEqual(details['org_pk'], "123456", "org_pk should match mocked response")

            # Verify mock call
            mock_get.assert_called_once_with(
                "https://api.adviserinfo.sec.gov/search/firm/123456",
                params=IAPD_CONFIG["default_params"],
                timeout=(10, 30)
            )

    def test_rate_limiting(self):
        """Test rate limiting behavior."""
        # Configure mock response
        self.mock_response.json.return_value = {
            "hits": {
                "total": 0,
                "hits": []
            }
        }

        # Patch the agent's session.get method
        with patch.object(self.agent.session, 'get', return_value=self.mock_response) as mock_get:
            # Execute multiple requests
            print("\n=== SEC test_rate_limiting ===")
            start_time = datetime.now()
            self.agent.search_firm("Test Investment Advisers 1")
            self.agent.search_firm("Test Investment Advisers 2")
            end_time = datetime.now()

            # Verify rate limiting
            elapsed = (end_time - start_time).total_seconds()
            print(f"Elapsed time: {elapsed:.2f} seconds")
            print(f"Mock get call count: {mock_get.call_count}")
            print(f"Mock get call args: {mock_get.call_args_list}")

            self.assertEqual(mock_get.call_count, 2, "Expected two API calls")
            self.assertGreaterEqual(elapsed, RATE_LIMIT_DELAY,
                                   f"Elapsed time ({elapsed:.2f}s) should be at least {RATE_LIMIT_DELAY}s")

if __name__ == '__main__':
    unittest.main()