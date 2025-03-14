"""Unit tests for the FirmServicesFacade class."""

import unittest
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List
import argparse

from services.firm_services import FirmServicesFacade

class TestFirmServicesFacade(unittest.TestCase):
    """Test cases for FirmServicesFacade."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.facade = FirmServicesFacade()
        self.subject_id = "TEST_SUBJECT_001"
        
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
        results = self.facade.search_firm(self.subject_id, "Test Firm")
        
        # Verify results
        self.assertEqual(len(results), 2)
        self.assertIn(self.normalized_finra_search_result, results)
        self.assertIn(self.normalized_sec_search_result, results)
        
        # Verify mocks called correctly
        mock_finra_search.assert_called_once_with(self.subject_id, "search_Test Firm", {"firm_name": "Test Firm"})
        mock_sec_search.assert_called_once_with(self.subject_id, "search_Test Firm", {"firm_name": "Test Firm"})

    @patch('services.firm_services.fetch_finra_firm_search')
    @patch('services.firm_services.fetch_sec_firm_search')
    def test_search_firm_finra_error(self, mock_sec_search, mock_finra_search):
        """Test firm search when FINRA fails but SEC succeeds."""
        # Setup mocks
        mock_finra_search.side_effect = Exception("FINRA API Error")
        mock_sec_search.return_value = [self.sample_sec_result]
        
        # Execute search
        results = self.facade.search_firm(self.subject_id, "Test Firm")
        
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
        result = self.facade.get_firm_details(self.subject_id, "12345")
        
        # Verify result
        self.assertEqual(result, self.normalized_finra_details)
        
        # Verify only FINRA was called (SEC shouldn't be called if FINRA succeeds)
        mock_finra_details.assert_called_once_with(self.subject_id, "details_12345", {"crd_number": "12345"})
        mock_sec_details.assert_not_called()

    @patch('services.firm_services.fetch_finra_firm_details')
    @patch('services.firm_services.fetch_sec_firm_details')
    def test_get_firm_details_finra_fails_sec_success(self, mock_sec_details, mock_finra_details):
        """Test getting firm details when FINRA fails but SEC succeeds."""
        # Setup mocks
        mock_finra_details.side_effect = Exception("FINRA API Error")
        mock_sec_details.return_value = self.sample_sec_result
        
        # Execute search
        result = self.facade.get_firm_details(self.subject_id, "12345")
        
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
        result = self.facade.search_firm_by_crd(self.subject_id, "12345")
        
        # Verify result
        self.assertEqual(result, self.normalized_finra_search_result)
        
        # Verify only FINRA was called
        mock_finra_search.assert_called_once_with(self.subject_id, "search_crd_12345", {"crd_number": "12345"})
        mock_sec_search.assert_not_called()

    @patch('services.firm_services.fetch_finra_firm_by_crd')
    @patch('services.firm_services.fetch_sec_firm_by_crd')
    def test_search_firm_by_crd_both_fail(self, mock_sec_search, mock_finra_search):
        """Test searching firm by CRD when both services fail."""
        # Setup mocks
        mock_finra_search.side_effect = Exception("FINRA API Error")
        mock_sec_search.side_effect = Exception("SEC API Error")
        
        # Execute search
        result = self.facade.search_firm_by_crd(self.subject_id, "12345")
        
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
                results = self.facade.search_firm(self.subject_id, "Test Firm")
                self.assertEqual(len(results), 0)
                
                # Test with string response instead of list
                mock_finra.return_value = "Invalid Response"
                mock_sec.return_value = "Invalid Response"
                results = self.facade.search_firm(self.subject_id, "Test Firm")
                self.assertEqual(len(results), 0)
                
                # Test with list containing non-dict items
                mock_finra.return_value = ["not a dict", 123]
                mock_sec.return_value = ["not a dict", 123]
                results = self.facade.search_firm(self.subject_id, "Test Firm")
                self.assertEqual(len(results), 0)

class TestFirmServicesCLI(unittest.TestCase):
    """Test cases for the FirmServices CLI."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.facade = FirmServicesFacade()
        self.subject_id = "TEST_SUBJECT_001"
        
        # Sample test data
        self.sample_search_results = [
            {
                "firm_name": "Test Firm FINRA",
                "crd_number": "12345",
                "source": "FINRA",
                "raw_data": {
                    "org_name": "Test Firm FINRA",
                    "org_source_id": "12345"
                }
            }
        ]
        
        self.sample_details = {
            "firm_name": "Test Firm FINRA",
            "crd_number": "12345",
            "source": "FINRA",
            "registration_status": "APPROVED",
            "addresses": [],
            "disclosures": [],
            "raw_data": {
                "org_name": "Test Firm FINRA",
                "org_source_id": "12345",
                "registration_status": "APPROVED"
            }
        }

    @patch('argparse.ArgumentParser.parse_args')
    @patch('services.firm_services.FirmServicesFacade.search_firm')
    def test_cli_search_command(self, mock_search, mock_args):
        """Test the CLI search command."""
        # Setup mock arguments
        mock_args.return_value = argparse.Namespace(
            command='search',
            firm_name='Test Firm',
            subject_id=self.subject_id,
            interactive=False
        )
        
        # Setup mock search results
        mock_search.return_value = self.sample_search_results
        
        # Capture stdout to verify output
        from io import StringIO
        import sys
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            from services.firm_services import main
            main()
            
            # Verify the output contains expected data
            output = captured_output.getvalue()
            self.assertIn("Test Firm FINRA", output)
            self.assertIn("12345", output)
            self.assertIn("FINRA", output)
            
            # Verify search was called with correct parameters
            mock_search.assert_called_once_with(self.subject_id, "Test Firm")
        finally:
            sys.stdout = sys.__stdout__

    @patch('argparse.ArgumentParser.parse_args')
    @patch('services.firm_services.FirmServicesFacade.get_firm_details')
    def test_cli_details_command(self, mock_details, mock_args):
        """Test the CLI details command."""
        # Setup mock arguments
        mock_args.return_value = argparse.Namespace(
            command='details',
            crd_number='12345',
            subject_id=self.subject_id,
            interactive=False
        )
        
        # Setup mock details results
        mock_details.return_value = self.sample_details
        
        # Capture stdout to verify output
        from io import StringIO
        import sys
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            from services.firm_services import main
            main()
            
            # Verify the output contains expected data
            output = captured_output.getvalue()
            self.assertIn("Test Firm FINRA", output)
            self.assertIn("12345", output)
            self.assertIn("APPROVED", output)
            
            # Verify details was called with correct parameters
            mock_details.assert_called_once_with(self.subject_id, "12345")
        finally:
            sys.stdout = sys.__stdout__

    @patch('argparse.ArgumentParser.parse_args')
    @patch('services.firm_services.FirmServicesFacade.search_firm_by_crd')
    def test_cli_search_crd_command(self, mock_search_crd, mock_args):
        """Test the CLI search-crd command."""
        # Setup mock arguments
        mock_args.return_value = argparse.Namespace(
            command='search-crd',
            crd_number='12345',
            subject_id=self.subject_id,
            interactive=False
        )
        
        # Setup mock search results
        mock_search_crd.return_value = self.sample_search_results[0]
        
        # Capture stdout to verify output
        from io import StringIO
        import sys
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            from services.firm_services import main
            main()
            
            # Verify the output contains expected data
            output = captured_output.getvalue()
            self.assertIn("Test Firm FINRA", output)
            self.assertIn("12345", output)
            self.assertIn("FINRA", output)
            
            # Verify search_crd was called with correct parameters
            mock_search_crd.assert_called_once_with(self.subject_id, "12345")
        finally:
            sys.stdout = sys.__stdout__

    @patch('builtins.input')
    @patch('services.firm_services.FirmServicesFacade.search_firm')
    def test_interactive_search(self, mock_search, mock_input):
        """Test the interactive search functionality."""
        # Setup mock inputs (search firm, then exit)
        mock_input.side_effect = ["1", "Test Firm", "", "4"]
        
        # Setup mock search results
        mock_search.return_value = self.sample_search_results
        
        # Capture stdout to verify output
        from io import StringIO
        import sys
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            from services.firm_services import interactive_menu
            interactive_menu(self.subject_id)
            
            # Verify the output contains expected data
            output = captured_output.getvalue()
            self.assertIn("Test Firm FINRA", output)
            self.assertIn("12345", output)
            self.assertIn("FINRA", output)
            
            # Verify search was called with correct parameters
            mock_search.assert_called_once_with(self.subject_id, "Test Firm")
        finally:
            sys.stdout = sys.__stdout__

    @patch('builtins.input')
    @patch('services.firm_services.FirmServicesFacade.get_firm_details')
    def test_interactive_details(self, mock_details, mock_input):
        """Test the interactive get firm details functionality."""
        # Setup mock inputs (get details, then exit)
        mock_input.side_effect = ["2", "12345", "", "4"]
        
        # Setup mock details results
        mock_details.return_value = self.sample_details
        
        # Capture stdout to verify output
        from io import StringIO
        import sys
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            from services.firm_services import interactive_menu
            interactive_menu(self.subject_id)
            
            # Verify the output contains expected data
            output = captured_output.getvalue()
            self.assertIn("Test Firm FINRA", output)
            self.assertIn("12345", output)
            self.assertIn("APPROVED", output)
            
            # Verify details was called with correct parameters
            mock_details.assert_called_once_with(self.subject_id, "12345")
        finally:
            sys.stdout = sys.__stdout__

    @patch('builtins.input')
    @patch('services.firm_services.FirmServicesFacade.search_firm_by_crd')
    def test_interactive_search_crd(self, mock_search_crd, mock_input):
        """Test the interactive search by CRD functionality."""
        # Setup mock inputs (search by CRD, then exit)
        mock_input.side_effect = ["3", "12345", "", "4"]
        
        # Setup mock search results
        mock_search_crd.return_value = self.sample_search_results[0]
        
        # Capture stdout to verify output
        from io import StringIO
        import sys
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            from services.firm_services import interactive_menu
            interactive_menu(self.subject_id)
            
            # Verify the output contains expected data
            output = captured_output.getvalue()
            self.assertIn("Test Firm FINRA", output)
            self.assertIn("12345", output)
            self.assertIn("FINRA", output)
            
            # Verify search_crd was called with correct parameters
            mock_search_crd.assert_called_once_with(self.subject_id, "12345")
        finally:
            sys.stdout = sys.__stdout__

    @patch('builtins.input')
    def test_interactive_invalid_choice(self, mock_input):
        """Test handling of invalid menu choices."""
        # Setup mock inputs (invalid choice, then exit)
        mock_input.side_effect = ["invalid", "", "4"]
        
        # Capture stdout to verify output
        from io import StringIO
        import sys
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            from services.firm_services import interactive_menu
            interactive_menu(self.subject_id)
            
            # Verify the output contains error message
            output = captured_output.getvalue()
            self.assertIn("Invalid choice", output)
        finally:
            sys.stdout = sys.__stdout__

    @patch('builtins.input')
    def test_interactive_empty_input(self, mock_input):
        """Test handling of empty input values."""
        # Setup mock inputs (search firm with empty name, then exit)
        mock_input.side_effect = ["1", "", "", "4"]
        
        # Capture stdout to verify output
        from io import StringIO
        import sys
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            from services.firm_services import interactive_menu
            interactive_menu(self.subject_id)
            
            # Verify no results were displayed
            output = captured_output.getvalue()
            self.assertNotIn("Results:", output)
        finally:
            sys.stdout = sys.__stdout__

    @patch('argparse.ArgumentParser.parse_args')
    @patch('services.firm_services.FirmServicesFacade.search_firm')
    def test_cli_search_no_results(self, mock_search, mock_args):
        """Test CLI search command when no results are found."""
        # Setup mock arguments
        mock_args.return_value = argparse.Namespace(
            command='search',
            firm_name='Nonexistent Firm',
            subject_id=self.subject_id,
            interactive=False
        )
        
        # Setup mock search results - empty list
        mock_search.return_value = []
        
        # Capture stdout
        from io import StringIO
        import sys
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            from services.firm_services import main
            main()
            
            # Verify output indicates no results
            output = captured_output.getvalue()
            self.assertIn("No results found", output)
        finally:
            sys.stdout = sys.__stdout__

    @patch('argparse.ArgumentParser.parse_args')
    @patch('services.firm_services.FirmServicesFacade.get_firm_details')
    def test_cli_details_not_found(self, mock_details, mock_args):
        """Test CLI details command when firm is not found."""
        # Setup mock arguments
        mock_args.return_value = argparse.Namespace(
            command='details',
            crd_number='99999',
            subject_id=self.subject_id,
            interactive=False
        )
        
        # Setup mock details result - None indicates not found
        mock_details.return_value = None
        
        # Capture stdout
        from io import StringIO
        import sys
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            from services.firm_services import main
            main()
            
            # Verify output indicates no results
            output = captured_output.getvalue()
            self.assertIn("No results found", output)
        finally:
            sys.stdout = sys.__stdout__

    @patch('argparse.ArgumentParser.parse_args')
    @patch('services.firm_services.FirmServicesFacade.search_firm')
    @patch('sys.exit')
    def test_cli_search_service_error(self, mock_exit, mock_search, mock_args):
        """Test CLI search command when service throws an error."""
        # Setup mock arguments
        mock_args.return_value = argparse.Namespace(
            command='search',
            firm_name='Test Firm',
            subject_id=self.subject_id,
            interactive=False
        )
        
        # Setup mock to raise an exception
        mock_search.side_effect = Exception("Service unavailable")
        
        # Capture stdout
        from io import StringIO
        import sys
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            from services.firm_services import main
            main()
            
            # Verify error output
            output = captured_output.getvalue()
            self.assertIn("error", output.lower())
            self.assertIn("service unavailable", output.lower())
            
            # Verify sys.exit was called with code 1
            mock_exit.assert_called_once_with(1)
        finally:
            sys.stdout = sys.__stdout__

    @patch('builtins.input')
    @patch('services.firm_services.FirmServicesFacade.search_firm')
    def test_interactive_search_service_error(self, mock_search, mock_input):
        """Test interactive search when service throws an error."""
        # Setup mock inputs (search firm, then exit)
        mock_input.side_effect = ["1", "Test Firm", "", "4"]
        
        # Setup mock to raise an exception
        mock_search.side_effect = Exception("Service unavailable")
        
        # Capture stdout
        from io import StringIO
        import sys
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            from services.firm_services import interactive_menu
            interactive_menu(self.subject_id)
            
            # Verify error output
            output = captured_output.getvalue()
            self.assertIn("Error", output.lower())
        finally:
            sys.stdout = sys.__stdout__

    @patch('builtins.input')
    def test_interactive_keyboard_interrupt(self, mock_input):
        """Test handling of KeyboardInterrupt in interactive mode."""
        # Setup mock to raise KeyboardInterrupt
        mock_input.side_effect = KeyboardInterrupt()
        
        # Capture stdout
        from io import StringIO
        import sys
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            from services.firm_services import interactive_menu
            interactive_menu(self.subject_id)
            
            # Verify graceful exit message
            output = captured_output.getvalue()
            self.assertIn("Exiting", output)
        finally:
            sys.stdout = sys.__stdout__

    @patch('builtins.input')
    def test_interactive_multiple_invalid_inputs(self, mock_input):
        """Test handling of multiple invalid inputs in interactive mode."""
        # Setup mock inputs (multiple invalid choices, then exit)
        mock_input.side_effect = ["invalid1", "invalid2", "0", "5", "", "4"]
        
        # Capture stdout
        from io import StringIO
        import sys
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            from services.firm_services import interactive_menu
            interactive_menu(self.subject_id)
            
            # Verify multiple error messages
            output = captured_output.getvalue()
            error_count = output.lower().count("invalid choice")
            self.assertGreater(error_count, 1)
        finally:
            sys.stdout = sys.__stdout__

if __name__ == '__main__':
    unittest.main() 