import unittest
import os
import signal
import tempfile
from unittest.mock import patch, MagicMock

from batch.firm_main import main, signal_handler

class TestFirmMain(unittest.TestCase):
    def setUp(self):
        """Set up test environment with temporary directories"""
        self.temp_dir = tempfile.mkdtemp()
        self.input_dir = os.path.join(self.temp_dir, "drop")
        self.output_dir = os.path.join(self.temp_dir, "output")
        self.archive_dir = os.path.join(self.temp_dir, "archive")
        
        for folder in [self.input_dir, self.output_dir, self.archive_dir]:
            os.makedirs(folder, exist_ok=True)
        
        self.test_csv = os.path.join(self.input_dir, "test.csv")
        with open(self.test_csv, 'w') as f:
            f.write("Business Name,Tax ID,Business Ref\n")
            f.write("Test Corp,123,456\n")
        
        self.patches = {
            'input_folder': patch('batch.firm_main_config.INPUT_FOLDER', self.input_dir),
            'output_folder': patch('batch.firm_main_config.OUTPUT_FOLDER', self.output_dir),
            'archive_folder': patch('batch.firm_main_config.ARCHIVE_FOLDER', self.archive_dir),
        }
        for p in self.patches.values():
            p.start()
        
        self.mock_logger = MagicMock()
        self.mock_loggers = {
            'main': self.mock_logger,
            '_groups': {
                'core': {'main': 'main'},
                'services': {'services': 'services'},
                'agents': {'agents': 'agents'}
            }
        }

    def tearDown(self):
        """Clean up temporary files and patches"""
        for p in self.patches.values():
            p.stop()
        import shutil
        shutil.rmtree(self.temp_dir)

    @patch('sys.argv', ['firm_main.py'])
    @patch('batch.firm_main.setup_logging')
    @patch('batch.firm_main.FirmServicesFacade')
    def test_main_default_args(self, mock_facade_class, mock_setup_logging):
        """Test main function with default arguments"""
        mock_setup_logging.return_value = self.mock_loggers
        mock_facade = MagicMock()
        mock_facade_class.return_value = mock_facade

        with patch('builtins.input', side_effect=['10']):  # Exit interactive mode
            main()

        mock_setup_logging.assert_called_once_with(False)
        mock_facade_class.assert_called_once()

    @patch('sys.argv', ['firm_main.py', '--headless', '--diagnostic'])
    @patch('batch.firm_main.setup_logging')
    @patch('batch.firm_main.FirmServicesFacade')
    @patch('batch.firm_main.run_batch_processing')
    def test_main_headless_mode(self, mock_run_batch, mock_facade_class, mock_setup_logging):
        """Test main function in headless mode"""
        mock_setup_logging.return_value = self.mock_loggers
        mock_facade = MagicMock()
        mock_facade_class.return_value = mock_facade

        main()

        mock_setup_logging.assert_called_once_with(True)
        mock_run_batch.assert_called_once()

    @patch('sys.argv', ['firm_main.py'])
    @patch('batch.firm_main.setup_logging')
    @patch('batch.firm_main.FirmServicesFacade')
    @patch('batch.firm_main.display_menu')
    @patch('batch.firm_main.handle_menu_choice')
    def test_main_interactive_mode(self, mock_handle_menu, mock_display_menu, mock_facade_class, mock_setup_logging):
        """Test main function in interactive mode"""
        mock_setup_logging.return_value = self.mock_loggers
        mock_facade = MagicMock()
        mock_facade_class.return_value = mock_facade
        mock_display_menu.side_effect = ["1", "10"]
        mock_handle_menu.return_value = (True, True, {"core"}, {"core": "INFO"}, 0.1)

        main()

        mock_setup_logging.assert_called_once_with(False)
        mock_display_menu.assert_called()
        mock_handle_menu.assert_called()

    @patch('batch.firm_main.csv_processor')
    @patch('batch.firm_main.save_checkpoint')
    def test_signal_handler(self, mock_save_checkpoint, mock_csv_processor):
        """Test signal handler saves checkpoint and exits"""
        mock_csv_processor.current_csv = "test.csv"
        mock_csv_processor.current_line = 42

        with self.assertRaises(SystemExit):
            signal_handler(signal.SIGINT, None)

        mock_save_checkpoint.assert_called_once_with("test.csv", 42)

if __name__ == '__main__':
    unittest.main()