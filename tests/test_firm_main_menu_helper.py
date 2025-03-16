import unittest
from unittest.mock import patch, MagicMock
from io import StringIO
from logging import Logger
from typing import Dict, cast
from batch.firm_main_menu_helper import (
    display_menu,
    handle_menu_choice,
    manage_logging_groups
)

class TestMenuHelper(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.skip_financials = False
        self.skip_legal = False
        self.enabled_groups = {"core"}
        self.group_levels = {"core": "INFO", "services": "WARNING", "agents": "WARNING"}
        self.wait_time = 0.1
        self.config = {
            "config_file": "test_config.json",
            "default_wait_time": 0.1,
            "skip_financials": False,
            "skip_legal": False,
            "enabled_logging_groups": ["core"],
            "logging_levels": {"core": "INFO"}
        }
        # Create mocks that are compatible with Logger type
        self.loggers: Dict[str, Logger] = {
            "core": cast(Logger, MagicMock(spec=Logger)),
            "services": cast(Logger, MagicMock(spec=Logger)),
            "agents": cast(Logger, MagicMock(spec=Logger))
        }
        self.LOG_LEVELS = {
            "1": ("DEBUG", 10),
            "2": ("INFO", 20),
            "3": ("WARNING", 30),
            "4": ("ERROR", 40),
            "5": ("CRITICAL", 50)
        }
        self.save_config_func = MagicMock()
        self.flush_logs_func = MagicMock()

    @patch('builtins.input')
    @patch('builtins.print')
    def test_display_menu(self, mock_print, mock_input):
        """Test menu display and input handling"""
        # Test normal input
        mock_input.return_value = "1"
        result = display_menu(False, False, 0.1)
        self.assertEqual(result, "1")
        
        # Verify menu items were printed
        mock_print.assert_any_call("\nFirm Compliance CSV Processor Menu:")
        mock_print.assert_any_call("1. Run batch processing")
        
        # Test with different settings
        mock_input.return_value = "2"
        result = display_menu(True, True, 0.5)
        self.assertEqual(result, "2")

    @patch('builtins.input')
    @patch('builtins.print')
    def test_handle_menu_choice_toggle_financials(self, mock_print, mock_input):
        """Test toggling financial review setting"""
        result = handle_menu_choice(
            "2", self.skip_financials, self.skip_legal,
            self.enabled_groups, self.group_levels, self.wait_time,
            self.config, self.loggers, self.LOG_LEVELS,
            self.save_config_func, self.flush_logs_func
        )
        
        self.assertTrue(result[0])  # skip_financials should be toggled
        mock_print.assert_called_with("Financial review is now skipped")

    @patch('builtins.input')
    @patch('builtins.print')
    def test_handle_menu_choice_toggle_legal(self, mock_print, mock_input):
        """Test toggling legal review setting"""
        result = handle_menu_choice(
            "3", self.skip_financials, self.skip_legal,
            self.enabled_groups, self.group_levels, self.wait_time,
            self.config, self.loggers, self.LOG_LEVELS,
            self.save_config_func, self.flush_logs_func
        )
        
        self.assertTrue(result[1])  # skip_legal should be toggled
        mock_print.assert_called_with("Legal review is now skipped")

    @patch('builtins.input')
    @patch('builtins.print')
    def test_handle_menu_choice_save_settings(self, mock_print, mock_input):
        """Test saving settings"""
        result = handle_menu_choice(
            "4", self.skip_financials, self.skip_legal,
            self.enabled_groups, self.group_levels, self.wait_time,
            self.config, self.loggers, self.LOG_LEVELS,
            self.save_config_func, self.flush_logs_func
        )
        
        self.save_config_func.assert_called_once()
        mock_print.assert_called_with(f"Settings saved to {self.config['config_file']}")

    @patch('builtins.input')
    @patch('builtins.print')
    def test_handle_menu_choice_trace_mode(self, mock_print, mock_input):
        """Test enabling trace mode"""
        result = handle_menu_choice(
            "7", self.skip_financials, self.skip_legal,
            self.enabled_groups, self.group_levels, self.wait_time,
            self.config, self.loggers, self.LOG_LEVELS,
            self.save_config_func, self.flush_logs_func
        )
        
        self.assertEqual(result[2], {"services", "agents", "core"})
        self.assertEqual(result[3]["core"], "DEBUG")
        self.assertEqual(result[3]["services"], "DEBUG")
        self.assertEqual(result[3]["agents"], "DEBUG")

    @patch('builtins.input')
    @patch('builtins.print')
    def test_handle_menu_choice_production_mode(self, mock_print, mock_input):
        """Test enabling production mode"""
        result = handle_menu_choice(
            "8", self.skip_financials, self.skip_legal,
            self.enabled_groups, self.group_levels, self.wait_time,
            self.config, self.loggers, self.LOG_LEVELS,
            self.save_config_func, self.flush_logs_func
        )
        
        self.assertEqual(result[2], {"core"})
        self.assertEqual(result[3]["core"], "INFO")
        self.assertEqual(result[3]["services"], "WARNING")
        self.assertEqual(result[3]["agents"], "WARNING")

    @patch('builtins.input')
    @patch('builtins.print')
    def test_handle_menu_choice_set_wait_time(self, mock_print, mock_input):
        """Test setting wait time"""
        mock_input.return_value = "0.5"
        result = handle_menu_choice(
            "9", self.skip_financials, self.skip_legal,
            self.enabled_groups, self.group_levels, self.wait_time,
            self.config, self.loggers, self.LOG_LEVELS,
            self.save_config_func, self.flush_logs_func
        )
        
        self.assertEqual(result[4], 0.5)

    @patch('builtins.input')
    @patch('builtins.print')
    def test_manage_logging_groups_toggle(self, mock_print, mock_input):
        """Test toggling logging groups"""
        mock_input.side_effect = ["1", "services"]
        manage_logging_groups(self.enabled_groups, self.group_levels, self.LOG_LEVELS)
        
        self.assertIn("services", self.enabled_groups)

    @patch('builtins.input')
    @patch('builtins.print')
    def test_manage_logging_groups_set_level(self, mock_print, mock_input):
        """Test setting logging group levels"""
        mock_input.side_effect = ["2", "core", "1"]
        manage_logging_groups(self.enabled_groups, self.group_levels, self.LOG_LEVELS)
        
        self.assertEqual(self.group_levels["core"], "DEBUG")

    @patch('builtins.input')
    @patch('builtins.print')
    def test_manage_logging_groups_invalid_input(self, mock_print, mock_input):
        """Test handling invalid input in logging groups management"""
        # Test invalid group name
        mock_input.side_effect = ["1", "invalid_group"]
        manage_logging_groups(self.enabled_groups, self.group_levels, self.LOG_LEVELS)
        mock_print.assert_any_call("Invalid group name")
        
        # Test invalid level choice
        mock_input.side_effect = ["2", "core", "6"]
        manage_logging_groups(self.enabled_groups, self.group_levels, self.LOG_LEVELS)
        mock_print.assert_any_call("Invalid level choice")

if __name__ == '__main__':
    unittest.main() 