import unittest
import os
import json
import tempfile
from batch.firm_main_config import (
    load_config,
    save_config,
    DEFAULT_CONFIG,
    canonical_fields,
)

class TestFirmMainConfig(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.test_dir, "test_config.json")

    def tearDown(self):
        # Clean up temporary files
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        os.rmdir(self.test_dir)

    def test_load_config_with_nonexistent_file(self):
        """Test loading config when file doesn't exist returns defaults"""
        config = load_config("nonexistent_config.json")
        self.assertEqual(config, DEFAULT_CONFIG)

    def test_load_config_with_valid_file(self):
        """Test loading config from a valid file"""
        test_config = {
            "evaluate_search": False,
            "evaluate_registration": False,
            "custom_setting": "test"
        }
        
        # Create a test config file
        with open(self.config_path, 'w') as f:
            json.dump(test_config, f)

        # Load the config
        loaded_config = load_config(self.config_path)

        # Verify that defaults are preserved and new values are loaded
        expected_config = DEFAULT_CONFIG.copy()
        expected_config.update(test_config)
        self.assertEqual(loaded_config, expected_config)

    def test_save_config(self):
        """Test saving config to file"""
        test_config = {
            "evaluate_search": False,
            "evaluate_registration": False,
            "custom_setting": "test"
        }

        # Save the config
        save_config(test_config, self.config_path)

        # Verify file exists and content is correct
        self.assertTrue(os.path.exists(self.config_path))
        with open(self.config_path, 'r') as f:
            saved_config = json.load(f)
        self.assertEqual(saved_config, test_config)

    def test_canonical_fields_structure(self):
        """Test the structure and content of canonical fields"""
        # Test that all canonical fields are lists
        for field, aliases in canonical_fields.items():
            self.assertIsInstance(aliases, list)
            self.assertTrue(len(aliases) > 0)
            
        # Test specific known mappings
        self.assertIn('reference_id', canonical_fields['reference_id'])
        self.assertIn('businessName', canonical_fields['business_name'])
        self.assertIn('tax_id', canonical_fields['tax_id'])

    def test_default_config_structure(self):
        """Test the structure and content of DEFAULT_CONFIG"""
        required_keys = [
            "evaluate_search",
            "evaluate_registration",
            "evaluate_disclosures",
            "evaluate_financials",
            "evaluate_legal",
            "skip_financials",
            "skip_legal",
            "enabled_logging_groups",
            "logging_levels"
        ]
        
        for key in required_keys:
            self.assertIn(key, DEFAULT_CONFIG)

        # Test specific boolean flags
        self.assertTrue(DEFAULT_CONFIG["evaluate_search"])
        self.assertTrue(DEFAULT_CONFIG["skip_financials"])
        self.assertTrue(DEFAULT_CONFIG["skip_legal"])

        # Test logging configuration
        self.assertEqual(DEFAULT_CONFIG["enabled_logging_groups"], ["core"])
        self.assertEqual(DEFAULT_CONFIG["logging_levels"]["core"], "INFO")

if __name__ == '__main__':
    unittest.main() 