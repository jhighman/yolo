import unittest
import os
import json
import csv
import tempfile
from datetime import datetime
from collections import defaultdict
from unittest.mock import patch, MagicMock, mock_open
from batch.firm_main_csv_processing import (
    CSVProcessor,
    SkipScenario,
)

class TestCSVProcessor(unittest.TestCase):
    def setUp(self):
        """Set up test environment with temporary directories"""
        self.temp_root = tempfile.mkdtemp()
        self.input_folder = os.path.join(self.temp_root, "drop")
        self.output_folder = os.path.join(self.temp_root, "output")
        self.archive_folder = os.path.join(self.temp_root, "archive")
        
        # Create necessary directories
        for folder in [self.input_folder, self.output_folder, self.archive_folder]:
            os.makedirs(folder, exist_ok=True)
        
        # Patch the module constants
        self.patcher = patch.multiple(
            'batch.firm_main_csv_processing',
            INPUT_FOLDER=self.input_folder,
            OUTPUT_FOLDER=self.output_folder,
            ARCHIVE_FOLDER=self.archive_folder
        )
        self.patcher.start()
        
        self.processor = CSVProcessor()

    def tearDown(self):
        """Clean up temporary files and directories"""
        self.patcher.stop()
        import shutil
        shutil.rmtree(self.temp_root)

    def test_generate_reference_id(self):
        """Test reference ID generation with various inputs"""
        # Test with valid tax ID
        tax_id = "123456789"
        ref_id = self.processor.generate_reference_id(tax_id)
        self.assertEqual(ref_id, f"TAX-{tax_id}")
        
        # Test with empty tax ID
        ref_id = self.processor.generate_reference_id("")
        self.assertTrue(ref_id.startswith("DEF-"))
        self.assertEqual(len(ref_id), 16)  # "DEF-" + 12 digits
        
        # Test with None tax ID
        ref_id = self.processor.generate_reference_id(None)
        self.assertTrue(ref_id.startswith("DEF-"))
        
        # Test with whitespace tax ID
        ref_id = self.processor.generate_reference_id("   ")
        self.assertTrue(ref_id.startswith("DEF-"))

    def test_resolve_headers(self):
        """Test header resolution with various inputs"""
        # Test with standard headers
        fieldnames = ["businessName", "tax_id", "reference_id", "unknown_field"]
        resolved = self.processor.resolve_headers(fieldnames)
        self.assertEqual(resolved["businessName"], "business_name")
        self.assertEqual(resolved["tax_id"], "tax_id")
        self.assertEqual(resolved["reference_id"], "reference_id")
        self.assertEqual(resolved["unknown_field"], "unknown_field")
        
        # Test with empty fieldnames
        resolved = self.processor.resolve_headers([])
        self.assertEqual(resolved, {})
        
        # Test with None fieldnames
        resolved = self.processor.resolve_headers(None)
        self.assertEqual(resolved, {})
        
        # Test case insensitivity
        fieldnames = ["BUSINESSNAME", "Tax_ID", "Reference_Id"]
        resolved = self.processor.resolve_headers(fieldnames)
        self.assertEqual(resolved["BUSINESSNAME"], "business_name")
        self.assertEqual(resolved["Tax_ID"], "tax_id")
        self.assertEqual(resolved["Reference_Id"], "reference_id")

    def test_write_records(self):
        """Test writing skipped and error records"""
        # Create test records
        test_records = defaultdict(list)
        test_records["test.csv"].append({
            "row_data": {"name": "Test Corp", "tax_id": "123"},
            "error": "Test error"
        })
        
        # Write records
        output_file = "test_errors.csv"
        self.processor._write_records(test_records, output_file, "error")
        
        # Verify file was created with correct content
        date_str = datetime.now().strftime("%m-%d-%Y")
        output_path = os.path.join(self.archive_folder, date_str, output_file)
        self.assertTrue(os.path.exists(output_path))
        
        with open(output_path, 'r', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["name"], "Test Corp")
            self.assertEqual(rows[0]["tax_id"], "123")
            self.assertEqual(rows[0]["error"], "Test error")

    def test_validate_row(self):
        """Test row validation with various inputs"""
        # Test valid row
        valid_row = {
            "business_ref": "123",
            "business_name": "Test Corp",
            "tax_id": "456",
            "organization_crd": "789"
        }
        is_valid, issues = self.processor.validate_row(valid_row)
        self.assertTrue(is_valid)
        self.assertEqual(len(issues), 0)
        
        # Test missing business reference
        invalid_row = {
            "business_name": "Test Corp",
            "tax_id": "456"
        }
        is_valid, issues = self.processor.validate_row(invalid_row)
        self.assertFalse(is_valid)
        self.assertIn(SkipScenario.NO_BUSINESS_REF.value, issues)
        
        # Test missing all identifiers
        invalid_row = {
            "business_ref": "123",
            "tax_id": "456"
        }
        is_valid, issues = self.processor.validate_row(invalid_row)
        self.assertFalse(is_valid)
        self.assertIn(SkipScenario.NO_BUSINESS_NAME.value, issues)
        self.assertIn(SkipScenario.NO_IDENTIFIERS.value, issues)

    @patch('batch.firm_main_csv_processing.process_claim')
    def test_process_row(self, mock_process_claim):
        """Test row processing with mocked dependencies"""
        # Setup test data
        row = {
            "Business Name": "Test Corp",
            "Tax ID": "123",
            "Business Ref": "456"
        }
        headers = {
            "Business Name": "business_name",
            "Tax ID": "tax_id",
            "Business Ref": "business_ref"
        }
        
        # Process row
        facade = MagicMock()
        config = {"skip_financials": True, "skip_legal": True}
        self.processor.process_row(row, headers, facade, config, 0.1)
        
        # Verify process_claim was called with correct arguments
        mock_process_claim.assert_called_once()
        args = mock_process_claim.call_args.args
        # First argument should be the claim dictionary
        self.assertEqual(args[0]["business_ref"], "456")
        # Second argument should be the facade
        self.assertIs(args[1], facade)
        # Third argument should be the business_ref
        self.assertEqual(args[2], "456")
        # Fourth and fifth arguments should be skip flags
        self.assertTrue(mock_process_claim.call_args.kwargs["skip_financials"])
        self.assertTrue(mock_process_claim.call_args.kwargs["skip_legal"])

        # Mock a return value for the next call
        mock_report = {
            "reference_id": "TEST-123",
            "business_ref": "456",
            "final_evaluation": {
                "overall_compliance": True
            }
        }
        mock_process_claim.return_value = mock_report

    def test_process_csv_with_sample_data(self):
        """Integration test with sample CSV data"""
        # Create sample CSV file
        csv_path = os.path.join(self.input_folder, "test.csv")
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Business Name", "Tax ID", "Business Ref"])
            writer.writerow(["Test Corp", "123", "456"])
            writer.writerow(["", "", ""])  # Invalid row
        
        # Mock dependencies
        facade = MagicMock()
        config = {"skip_financials": True, "skip_legal": True}
        
        # Process CSV
        with patch('batch.firm_main_csv_processing.process_claim') as mock_process_claim:
            mock_process_claim.return_value = {
                "reference_id": "TEST-123",
                "business_ref": "456",
                "final_evaluation": {"overall_compliance": True}
            }
            
            self.processor.process_csv(csv_path, 0, facade, config, 0.1)
        
        # Verify error and skipped records
        self.assertEqual(len(self.processor.error_records), 0)
        # The empty row should generate 4 skip scenarios
        date_str = datetime.now().strftime("%m-%d-%Y")
        skipped_file = os.path.join(self.archive_folder, date_str, "skipped.csv")
        with open(skipped_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            skipped_rows = list(reader)
            self.assertEqual(len(skipped_rows), 4)  # One row with 4 skip scenarios

if __name__ == '__main__':
    unittest.main() 