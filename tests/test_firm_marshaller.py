"""Unit tests for the firm data marshaller service."""

import unittest
from unittest.mock import patch, MagicMock
import json
from pathlib import Path
import shutil
import tempfile
from datetime import datetime, timedelta

from services.firm_marshaller import (
    get_current_date,
    get_manifest_timestamp,
    is_cache_valid,
    build_cache_path,
    build_file_name,
    read_manifest,
    write_manifest,
    load_cached_data,
    save_cached_data,
    save_multiple_results,
    log_request,
    fetch_agent_data,
    check_cache_or_fetch,
    fetch_finra_firm_search,
    fetch_finra_firm_by_crd,
    fetch_finra_firm_details,
    fetch_sec_firm_search,
    fetch_sec_firm_by_crd,
    fetch_sec_firm_details,
    CACHE_FOLDER,
    DATE_FORMAT,
    MANIFEST_DATE_FORMAT
)

class TestFirmMarshaller(unittest.TestCase):
    """Test cases for the firm data marshaller service."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.original_cache_folder = CACHE_FOLDER
        self.patcher = patch('services.firm_marshaller.CACHE_FOLDER', Path(self.temp_dir))
        self.mock_cache_folder = self.patcher.start()

        # Sample test data
        self.sample_firm_data = {
            "firm_name": "Test Firm",
            "crd_number": "123456",
            "firm_url": "https://example.com/firm/123456"
        }
        
        self.sample_firm_details = {
            "firm_name": "Test Firm",
            "crd_number": "123456",
            "registration_status": "APPROVED",
            "disclosure_count": 0
        }

    def tearDown(self):
        """Clean up test fixtures."""
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)
        self.patcher.stop()

    def test_get_current_date(self):
        """Test getting current date in correct format."""
        date = get_current_date()
        # Verify format matches YYYYMMDD
        self.assertTrue(len(date) == 8)
        self.assertTrue(date.isdigit())

    def test_get_manifest_timestamp(self):
        """Test getting manifest timestamp in correct format."""
        timestamp = get_manifest_timestamp()
        # Try parsing the timestamp to verify format
        try:
            datetime.strptime(timestamp, MANIFEST_DATE_FORMAT)
            is_valid = True
        except ValueError:
            is_valid = False
        self.assertTrue(is_valid)

    def test_is_cache_valid(self):
        """Test cache validity checking."""
        # Test valid cache (today)
        today = datetime.now().strftime(DATE_FORMAT)
        self.assertTrue(is_cache_valid(today))

        # Test invalid cache (91 days old)
        old_date = (datetime.now() - timedelta(days=91)).strftime(DATE_FORMAT)
        self.assertFalse(is_cache_valid(old_date))

        # Test invalid date format
        self.assertFalse(is_cache_valid("invalid-date"))

    def test_build_cache_path(self):
        """Test building cache path."""
        firm_id = "FIRM123"
        agent_name = "TEST_Agent"
        service = "search_firm"
        
        expected_path = Path(self.temp_dir) / firm_id / agent_name / service
        actual_path = build_cache_path(firm_id, agent_name, service)
        
        self.assertEqual(expected_path, actual_path)

    def test_build_file_name(self):
        """Test building file names for cache files."""
        agent_name = "TEST_Agent"
        firm_id = "FIRM123"
        service = "search_firm"
        date = "20240101"
        
        # Test without ordinal
        expected = "TEST_Agent_FIRM123_search_firm_20240101.json"
        actual = build_file_name(agent_name, firm_id, service, date)
        self.assertEqual(expected, actual)
        
        # Test with ordinal
        expected = "TEST_Agent_FIRM123_search_firm_20240101_1.json"
        actual = build_file_name(agent_name, firm_id, service, date, 1)
        self.assertEqual(expected, actual)

    def test_manifest_operations(self):
        """Test writing and reading manifest files."""
        test_path = Path(self.temp_dir) / "test_manifest"
        timestamp = datetime.now().strftime(MANIFEST_DATE_FORMAT)
        
        # Test writing manifest
        write_manifest(test_path, timestamp)
        self.assertTrue((test_path / "manifest.txt").exists())
        
        # Test reading manifest
        cached_date = read_manifest(test_path)
        self.assertEqual(cached_date, datetime.now().strftime(DATE_FORMAT))

    def test_cache_data_operations(self):
        """Test saving and loading cached data."""
        test_path = Path(self.temp_dir) / "test_cache"
        file_name = "test_data.json"
        
        # Test saving single result
        save_cached_data(test_path, file_name, self.sample_firm_data)
        self.assertTrue((test_path / file_name).exists())
        
        # Test loading single result
        loaded_data = load_cached_data(test_path, is_multiple=False)
        self.assertEqual(loaded_data, self.sample_firm_data)
        
        # Test saving multiple results
        results = [self.sample_firm_data, self.sample_firm_details]
        save_multiple_results(
            test_path, "TEST_Agent", "FIRM123", "search_firm",
            datetime.now().strftime(DATE_FORMAT), results
        )
        
        # Test loading multiple results
        loaded_results = load_cached_data(test_path, is_multiple=True)
        self.assertIsInstance(loaded_results, list)
        if loaded_results:  # Check if list is not empty
            self.assertTrue(isinstance(loaded_results[0], dict))
            self.assertGreater(len(loaded_results), 1)

    @patch('services.firm_marshaller.AGENT_SERVICES')
    def test_fetch_agent_data(self, mock_agent_services):
        """Test fetching data from agents."""
        # Mock agent function
        mock_agent_fn = MagicMock(return_value=[self.sample_firm_data])
        mock_agent_services.__getitem__.return_value = {
            "search_firm": mock_agent_fn
        }
        
        # Test successful fetch
        results, duration = fetch_agent_data(
            "TEST_Agent", "search_firm", {"firm_name": "Test Firm"}
        )
        self.assertEqual(results, [self.sample_firm_data])
        self.assertIsNotNone(duration)
        
        # Test error handling
        mock_agent_fn.side_effect = Exception("Test error")
        results, duration = fetch_agent_data(
            "TEST_Agent", "search_firm", {"firm_name": "Test Firm"}
        )
        self.assertEqual(results, [])
        self.assertIsNone(duration)

    @patch('services.firm_marshaller.fetch_agent_data')
    def test_check_cache_or_fetch(self, mock_fetch):
        """Test cache checking and fetching logic."""
        mock_fetch.return_value = ([self.sample_firm_data], 0.1)
        
        # Test with invalid firm_id
        with self.assertRaises(ValueError):
            check_cache_or_fetch("TEST_Agent", "search_firm", "", {})
        
        # Test cache miss
        result = check_cache_or_fetch(
            "TEST_Agent", "search_firm", "FIRM123",
            {"firm_name": "Test Firm"}
        )
        self.assertEqual(result, [self.sample_firm_data])
        
        # Test cache hit (run same query again)
        result = check_cache_or_fetch(
            "TEST_Agent", "search_firm", "FIRM123",
            {"firm_name": "Test Firm"}
        )
        self.assertEqual(result, [self.sample_firm_data])
        # Verify fetch was only called once
        self.assertEqual(mock_fetch.call_count, 1)

    def test_log_request(self):
        """Test request logging."""
        firm_id = "FIRM123"
        agent_name = "TEST_Agent"
        service = "search_firm"
        status = "Cached"
        duration = 0.1
        
        log_request(firm_id, agent_name, service, status, duration)
        
        log_path = Path(self.temp_dir) / firm_id / "request_log.txt"
        self.assertTrue(log_path.exists())
        
        with log_path.open("r") as f:
            log_content = f.read()
            self.assertIn(agent_name, log_content)
            self.assertIn(service, log_content)
            self.assertIn(status, log_content)
            self.assertIn("0.10s", log_content)

    @patch('services.firm_marshaller.check_cache_or_fetch')
    def test_fetcher_functions(self, mock_check_cache):
        """Test the high-level fetcher functions."""
        mock_check_cache.return_value = [self.sample_firm_data]
        
        # Test FINRA fetchers
        result = fetch_finra_firm_search("FIRM123", {"firm_name": "Test Firm"})
        self.assertEqual(result, [self.sample_firm_data])
        
        result = fetch_finra_firm_by_crd("FIRM123", {"crd_number": "123456"})
        self.assertEqual(result, [self.sample_firm_data])
        
        result = fetch_finra_firm_details("FIRM123", {"crd_number": "123456"})
        self.assertEqual(result, [self.sample_firm_data])
        
        # Test SEC fetchers
        result = fetch_sec_firm_search("FIRM123", {"firm_name": "Test Firm"})
        self.assertEqual(result, [self.sample_firm_data])
        
        result = fetch_sec_firm_by_crd("FIRM123", {"crd_number": "123456"})
        self.assertEqual(result, [self.sample_firm_data])
        
        result = fetch_sec_firm_details("FIRM123", {"crd_number": "123456"})
        self.assertEqual(result, [self.sample_firm_data])

if __name__ == '__main__':
    unittest.main() 