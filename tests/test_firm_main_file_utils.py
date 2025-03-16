import unittest
import os
import json
import shutil
import tempfile
from datetime import datetime
from unittest.mock import patch
from batch.firm_main_file_utils import (
    setup_folders,
    load_checkpoint,
    save_checkpoint,
    get_csv_files,
    archive_file,
)

class TestFirmMainFileUtils(unittest.TestCase):
    def setUp(self):
        """Set up test environment with temporary directories"""
        # Create a temporary root directory
        self.temp_root = tempfile.mkdtemp()
        
        # Create paths for input, output, and archive folders
        self.input_folder = os.path.join(self.temp_root, "drop")
        self.output_folder = os.path.join(self.temp_root, "output")
        self.archive_folder = os.path.join(self.temp_root, "archive")
        self.checkpoint_file = os.path.join(self.output_folder, "checkpoint.json")
        
        # Patch the paths in firm_main_file_utils
        self.patcher = patch.multiple(
            'batch.firm_main_file_utils',
            INPUT_FOLDER=self.input_folder,
            OUTPUT_FOLDER=self.output_folder,
            ARCHIVE_FOLDER=self.archive_folder,
            CHECKPOINT_FILE=self.checkpoint_file
        )
        self.patcher.start()

    def tearDown(self):
        """Clean up temporary files and directories"""
        self.patcher.stop()
        shutil.rmtree(self.temp_root)

    def test_setup_folders(self):
        """Test creation of necessary folders"""
        setup_folders()
        
        # Verify all folders were created
        self.assertTrue(os.path.exists(self.input_folder))
        self.assertTrue(os.path.exists(self.output_folder))
        self.assertTrue(os.path.exists(self.archive_folder))
        
        # Test idempotency - should not raise errors when folders exist
        setup_folders()

    def test_checkpoint_operations(self):
        """Test saving and loading checkpoint data"""
        # Ensure output directory exists
        os.makedirs(self.output_folder, exist_ok=True)
        
        # Test with no existing checkpoint
        self.assertIsNone(load_checkpoint())
        
        # Test saving and loading checkpoint
        test_csv = "test.csv"
        test_line = 42
        save_checkpoint(test_csv, test_line)
        
        checkpoint = load_checkpoint()
        if checkpoint is not None:  # Type guard for checkpoint
            self.assertEqual(checkpoint["csv_file"], test_csv)
            self.assertEqual(checkpoint["line"], test_line)
        else:
            self.fail("Checkpoint should not be None after saving")
        
        # Test invalid checkpoint data
        save_checkpoint("", -1)  # Use empty string and invalid line number instead of None
        self.assertTrue(os.path.exists(self.checkpoint_file))
        
        # Test corrupted checkpoint file
        with open(self.checkpoint_file, 'w') as f:
            f.write("invalid json")
        self.assertIsNone(load_checkpoint())

    def test_get_csv_files(self):
        """Test retrieving CSV files from input folder"""
        # Create input folder and test files
        os.makedirs(self.input_folder)
        test_files = ["test1.csv", "test2.CSV", "test3.txt", "test4.csv"]
        
        for file in test_files:
            with open(os.path.join(self.input_folder, file), 'w') as f:
                f.write("test")
        
        csv_files = get_csv_files()
        
        # Should only get .csv files, case-insensitive
        self.assertEqual(len(csv_files), 3)
        self.assertIn("test1.csv", csv_files)
        self.assertIn("test2.CSV", csv_files)
        self.assertIn("test4.csv", csv_files)
        self.assertNotIn("test3.txt", csv_files)
        
        # Test with non-existent directory
        shutil.rmtree(self.input_folder)
        self.assertEqual(get_csv_files(), [])

    def test_archive_file(self):
        """Test archiving CSV files"""
        # Create test file and directories
        os.makedirs(self.input_folder)
        test_file = os.path.join(self.input_folder, "test.csv")
        with open(test_file, 'w') as f:
            f.write("test data")
        
        # Archive the file
        archive_file(test_file)
        
        # Verify file was moved to date-based archive folder
        date_str = datetime.now().strftime("%m-%d-%Y")
        archive_path = os.path.join(self.archive_folder, date_str, "test.csv")
        
        self.assertTrue(os.path.exists(archive_path))
        self.assertFalse(os.path.exists(test_file))
        
        # Test archiving non-existent file
        with self.assertLogs(level='ERROR') as cm:
            archive_file("nonexistent.csv")
            self.assertTrue(any("Error archiving" in msg for msg in cm.output))

if __name__ == '__main__':
    unittest.main() 