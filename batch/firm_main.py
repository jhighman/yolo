"""
Main script for batch processing of business entity compliance claims from CSV files.
Provides a CLI menu or headless mode to run processing, manage settings, and handle signals.
"""

import argparse
import csv
import json
import os
import signal
import sys
import logging
from typing import Dict, Set
from batch.firm_main_config import DEFAULT_WAIT_TIME, OUTPUT_FOLDER, load_config, save_config, INPUT_FOLDER, CHECKPOINT_FILE
from batch.firm_main_file_utils import setup_folders, load_checkpoint, save_checkpoint, get_csv_files, archive_file
from batch.firm_main_csv_processing import CSVProcessor
from batch.firm_main_menu_helper import display_menu, handle_menu_choice
from services.firm_services import FirmServicesFacade
from utils.logging_config import setup_logging, reconfigure_logging, flush_logs, LOGGER_GROUPS

logger = logging.getLogger('main')  # Changed to match the core group logger name
csv_processor = CSVProcessor()  # Global instance for signal handling

# Define log levels for menu options
LOG_LEVELS = {
    "1": ("DEBUG", logging.DEBUG),
    "2": ("INFO", logging.INFO),
    "3": ("WARNING", logging.WARNING),
    "4": ("ERROR", logging.ERROR),
    "5": ("CRITICAL", logging.CRITICAL)
}

def signal_handler(sig, frame):
    """Handle interrupt signals by saving checkpoint and exiting."""
    if csv_processor.current_csv and csv_processor.current_line > 0:
        logger.info(f"Signal received ({signal.Signals(sig).name}), saving checkpoint: {csv_processor.current_csv}, line {csv_processor.current_line}")
        save_checkpoint(csv_processor.current_csv, csv_processor.current_line)
    logger.info("Exiting due to signal")
    sys.exit(0)

def run_batch_processing(facade: FirmServicesFacade, config: Dict[str, bool], wait_time: float, loggers: dict):
    """Run batch processing on CSV files in INPUT_FOLDER."""
    csv_processor.skipped_records.clear()
    
    print("\nRunning batch processing...")
    checkpoint = load_checkpoint()
    csv_files = get_csv_files()
    if not csv_files:
        logger.warning(f"No CSV files found in {INPUT_FOLDER}")
        print(f"No CSV files found in {INPUT_FOLDER}")
        return

    start_file = checkpoint["csv_file"] if checkpoint else None
    start_line = checkpoint["line"] if checkpoint else 0

    processed_files = 0
    processed_records = 0
    skipped_count = 0

    for csv_file in csv_files:
        csv_path = os.path.join(INPUT_FOLDER, csv_file)
        if start_file and csv_file < start_file:
            logger.debug(f"Skipping {csv_file} - before start_file {start_file}")
            continue
        logger.info(f"Processing {csv_path} from line {start_line}")
        csv_processor.process_csv(csv_path, start_line, facade, config, wait_time)
        try:
            with open(csv_path, 'r') as f:
                csv_reader = csv.reader(f)
                next(csv_reader)  # Skip header
                for row in csv_reader:
                    if any(field.strip() for field in row):
                        processed_records += 1
                        ref_id = row[0] if row else csv_processor.generate_reference_id()
                        report_path = os.path.join(OUTPUT_FOLDER, f"{ref_id}.json")
                        if os.path.exists(report_path):
                            with open(report_path, 'r') as rf:
                                report = json.load(rf)
                                if report.get("final_evaluation", {}).get("overall_compliance", True) is False and "Insufficient data" in report.get("final_evaluation", {}).get("compliance_explanation", ""):
                                    skipped_count += 1
        except Exception as e:
            logger.error(f"Error counting records in {csv_path}: {str(e)}", exc_info=True)
        archive_file(csv_path)
        processed_files += 1
        start_line = 0

    if csv_processor.skipped_records:
        csv_processor.write_skipped_records()
        skipped_count = sum(len(records) for records in csv_processor.skipped_records.values())
    
    logger.info(f"Processed {processed_files} files, {processed_records} records, {skipped_count} skipped")
    if os.path.exists(CHECKPOINT_FILE):
        try:
            os.remove(CHECKPOINT_FILE)
            logger.debug(f"Removed checkpoint file: {CHECKPOINT_FILE}")
        except Exception as e:
            logger.error(f"Error removing checkpoint file {CHECKPOINT_FILE}: {str(e)}")

def main():
    """Main entry point for the batch processing script."""
    parser = argparse.ArgumentParser(description='Batch process business entity compliance claims from CSV files.')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode without interactive menu')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--wait-time', type=float, default=DEFAULT_WAIT_TIME, help=f"Seconds to wait between records (default: {DEFAULT_WAIT_TIME})")
    parser.add_argument('--skip-financials', action='store_true', help="Skip financial review for all claims")
    parser.add_argument('--skip-legal', action='store_true', help="Skip legal review for all claims")
    args = parser.parse_args()

    # Initialize logging with debug mode if specified
    loggers = setup_logging(debug=args.debug)
    global logger
    logger = loggers['main']  # Use the 'main' logger from the core group

    logger.info("=== Starting application ===")
    logger.debug("Debug logging is enabled" if args.debug else "Debug logging is disabled")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    setup_folders()

    try:
        facade = FirmServicesFacade()
    except Exception as e:
        logger.error(f"Failed to initialize FirmServicesFacade: {str(e)}", exc_info=True)
        return

    # Configure logging groups
    enabled_groups = {"core", "agents"}  # Enable both core and agents groups
    group_levels = {
        "core": "INFO",
        "agents": "INFO"
    }
    
    # Reconfigure logging with the specified groups and levels
    reconfigure_logging(loggers, enabled_groups, group_levels)
    
    # Load configuration
    config = load_config()
    wait_time = config.get("wait_time", args.wait_time)

    if args.headless:
        # Headless mode configuration
        config = {
            "evaluate_financials": False,
            "evaluate_legal": False,
            "skip_financials": args.skip_financials,
            "skip_legal": args.skip_legal,
            "enabled_logging_groups": ["core", "agents"],  # Include both core and agents groups
            "logging_levels": {"core": "INFO", "agents": "INFO"},
            "config_file": "config.json",
            "default_wait_time": DEFAULT_WAIT_TIME
        }
        if not (args.skip_financials or args.skip_legal):
            loaded_config = load_config()
            config.update({
                "evaluate_financials": not loaded_config.get("skip_financials", True),
                "evaluate_legal": not loaded_config.get("skip_legal", True)
            })
        
        # Reconfigure logging based on loaded settings
        reconfigure_logging(loggers, set(config["enabled_logging_groups"]), config["logging_levels"])
        run_batch_processing(facade, config, args.wait_time, loggers)
        return

    # Interactive mode settings
    skip_financials = True
    skip_legal = True
    enabled_groups = {"core", "agents"}  # Start with both core and agents groups enabled
    group_levels = {"core": "INFO", "agents": "INFO", "services": "WARNING"}  # Default levels for all groups
    wait_time = DEFAULT_WAIT_TIME

    config = {
        "evaluate_search": True,
        "evaluate_registration": True,
        "evaluate_disclosures": True,
        "evaluate_financials": False,
        "evaluate_legal": False,
        "skip_financials": skip_financials,
        "skip_legal": skip_legal,
        "enabled_logging_groups": list(enabled_groups),
        "logging_levels": dict(group_levels),
        "config_file": "config.json",
        "default_wait_time": DEFAULT_WAIT_TIME
    }

    while True:
        choice = display_menu(skip_financials, skip_legal, wait_time)
        if choice == "1":
            logger.info(f"Running batch with config: {config}, wait_time: {wait_time}")
            # Use string levels from group_levels directly
            reconfigure_logging(loggers, enabled_groups, group_levels)
            run_batch_processing(facade, config, wait_time, loggers)
        else:
            skip_financials, skip_legal, enabled_groups, group_levels, wait_time = handle_menu_choice(
                choice, skip_financials, skip_legal, enabled_groups, group_levels, wait_time,
                config, loggers, LOG_LEVELS, save_config, flush_logs
            )
            if choice == "10":
                break
        if choice in ["7", "8"]:  # Trace mode or production mode
            # Use string levels from group_levels directly
            reconfigure_logging(loggers, enabled_groups, group_levels)

if __name__ == "__main__":
    main()