"""Unit tests for the FINRA Firm Broker Check Agent."""

import unittest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime
from pathlib import Path
import sys

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from agents.finra_firm_broker_check_agent import (
    FinraFirmBrokerCheckAgent,
    RATE_LIMIT_DELAY,
    BROKERCHECK_CONFIG
)

class TestFinraFirmBrokerCheckAgent(unittest.TestCase):
    """Test cases for the FINRA Broker Check Agent."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.agent = FinraFirmBrokerCheckAgent()
        self.mock_response = MagicMock()
        self.mock_response.status_code = 200

    def test_search_firm_success(self):
        """Test successful firm search by name."""
        self.mock_response.json.return_value = {
            "hits": {
                "total": 1,
                "hits": [
                    {
                        "_source": {
                            "org_name": "Test Firm",
                            "org_source_id": "123456"
                        }
                    }
                ]
            }
        }

        with patch.object(self.agent.session, 'get', return_value=self.mock_response) as mock_get:
            print("\n=== FINRA test_search_firm_success ===")
            results = self.agent.search_firm("Test Firm")
            print(f"Mock response: {self.mock_response.json.return_value}")
            print(f"Actual results: {results}")
            print(f"Mock get call count: {mock_get.call_count}")

            self.assertGreater(len(results), 0, "Expected at least one result from search")
            self.assertIn('firm_name', results[0], "Result should contain 'firm_name' key")
            self.assertEqual(results[0]['firm_name'], "Test Firm", "firm_name should match mocked org_name")
            self.assertEqual(results[0]['crd_number'], "123456", "crd_number should match mocked org_source_id")

            mock_get.assert_called_once_with(
                BROKERCHECK_CONFIG["base_search_url"],
                params={**BROKERCHECK_CONFIG["default_params"], "query": "Test Firm"},
                timeout=(10, 30)
            )

    def test_search_firm_by_crd_success(self):
        """Test successful firm search by CRD number."""
        self.mock_response.json.return_value = {
            "hits": {
                "total": 1,
                "hits": [
                    {
                        "_source": {
                            "org_name": "Test Firm",
                            "org_source_id": "123456",
                            "firm_other_names": ["Test Alias"],
                            "firm_ia_scope": "ACTIVE",
                            "firm_ia_disclosure_fl": "N",
                            "firm_branches_count": 5,
                            "firm_ia_address_details": json.dumps({"city": "Test City"})
                        }
                    }
                ]
            }
        }

        with patch.object(self.agent.session, 'get', return_value=self.mock_response) as mock_get:
            print("\n=== FINRA test_search_firm_by_crd_success ===")
            results = self.agent.search_firm_by_crd("123456")
            print(f"Mock response: {self.mock_response.json.return_value}")
            for i, hit in enumerate(results):
                print(f"Result {i} raw source: {hit}")
            print(f"Actual results: {results}")
            print(f"Mock get call count: {mock_get.call_count}")
            print(f"Mock get call args: {mock_get.call_args}")

            self.assertGreater(len(results), 0, "Expected at least one result from CRD search")
            self.assertIn('firm_name', results[0], "Result should contain 'firm_name' key")
            self.assertEqual(results[0]['firm_name'], "Test Firm", "firm_name should match mocked org_name")
            self.assertEqual(results[0]['crd_number'], "123456", "crd_number should match mocked org_source_id")

            mock_get.assert_called_once_with(
                BROKERCHECK_CONFIG["base_search_url"],
                params={**BROKERCHECK_CONFIG["default_params"], "query": "123456"},
                timeout=(10, 30)
            )

    def test_get_firm_details_success(self):
        """Test successful retrieval of firm details."""
        self.mock_response.json.return_value = {
            "hits": {
                "total": 1,
                "hits": [
                    {
                        "_source": {
                            "content": json.dumps({
                                "org_name": "Test Firm",
                                "org_source_id": "123456",
                                "status": "Active"
                            })
                        }
                    }
                ]
            }
        }

        with patch.object(self.agent.session, 'get', return_value=self.mock_response) as mock_get:
            print("\n=== FINRA test_get_firm_details_success ===")
            details = self.agent.get_firm_details("123456")
            print(f"Mock response: {self.mock_response.json.return_value}")
            print(f"Actual details: {details}")
            print(f"Mock get call count: {mock_get.call_count}")

            self.assertIsInstance(details, dict, "Details should be a dictionary")
            self.assertIn('org_name', details, "Details should contain 'org_name' key")
            self.assertEqual(details['org_name'], "Test Firm", "org_name should match mocked response")
            self.assertEqual(details['org_source_id'], "123456", "org_source_id should match mocked response")

            mock_get.assert_called_once_with(
                "https://api.brokercheck.finra.org/search/firm/123456",
                params=BROKERCHECK_CONFIG["default_params"]
            )

    def test_rate_limiting(self):
        """Test rate limiting behavior."""
        self.mock_response.json.return_value = {
            "hits": {
                "total": 0,
                "hits": []
            }
        }

        with patch.object(self.agent.session, 'get', return_value=self.mock_response) as mock_get:
            print("\n=== FINRA test_rate_limiting ===")
            start_time = datetime.now()
            self.agent.search_firm("Test Firm 1")
            self.agent.search_firm("Test Firm 2")
            end_time = datetime.now()

            elapsed = (end_time - start_time).total_seconds()
            print(f"Elapsed time: {elapsed:.2f} seconds")
            print(f"Mock get call count: {mock_get.call_count}")
            print(f"Mock get call args: {mock_get.call_args_list}")

            self.assertEqual(mock_get.call_count, 2, "Expected two API calls")
            self.assertGreaterEqual(elapsed, RATE_LIMIT_DELAY,
                                   f"Elapsed time ({elapsed:.2f}s) should be at least {RATE_LIMIT_DELAY}s")

if __name__ == '__main__':
    unittest.main()