#!/usr/bin/env python3
"""
propagate.py

This script reads organization CRD and entity data from a CSV file and sends requests
to the firm_business module for processing. It tracks processed records and prints
the count to the console with each iteration.

Usage:
    python propagate.py [--csv-path CSV_PATH] [--skip-financials] [--skip-legal]

Arguments:
    --csv-path: Path to the CSV file (default: _test_data/_example_entities/arch.csv)
    --skip-financials: Skip financial evaluations
    --skip-legal: Skip legal evaluations
"""

import csv
import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent))

from utils.logging_config import setup_logging
from services.firm_business import process_claim
from services.firm_services import FirmServicesFacade

# Initialize logging
loggers = setup_logging(debug=True)
logger = loggers.get('propagate', logging.getLogger(__name__))

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Process organization CRD and entity data from a CSV file"
    )
    
    parser.add_argument(
        "--csv-path",
        default="_test_data/_example_entities/arch.csv",
        help="Path to the CSV file (default: _test_data/_example_entities/arch.csv)"
    )
    
    parser.add_argument(
        "--skip-financials",
        action="store_true",
        help="Skip financial evaluations"
    )
    
    parser.add_argument(
        "--skip-legal",
        action="store_true",
        help="Skip legal evaluations"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level (default: INFO)"
    )
    
    return parser.parse_args()

def read_csv_data(csv_path: str) -> List[Dict[str, str]]:
    """
    Read data from a CSV file.
    
    Args:
        csv_path: Path to the CSV file
        
    Returns:
        List of dictionaries containing the CSV data
    """
    logger.info(f"Reading CSV data from {csv_path}")
    data = []
    
    try:
        with open(csv_path, 'r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                data.append(row)
        
        logger.info(f"Successfully read {len(data)} records from CSV")
        return data
    except Exception as e:
        logger.error(f"Error reading CSV file: {str(e)}")
        raise

def process_records(
    records: List[Dict[str, str]], 
    facade: FirmServicesFacade,
    skip_financials: bool = False,
    skip_legal: bool = False
) -> None:
    """
    Process records by sending requests to firm_business.py.
    
    Args:
        records: List of records to process
        facade: FirmServicesFacade instance
        skip_financials: Flag to skip financial evaluations
        skip_legal: Flag to skip legal evaluations
    """
    total_records = len(records)
    processed_count = 0
    
    logger.info(f"Starting to process {total_records} records")
    
    for record in records:
        try:
            # Extract organizationCRD and entity from the record
            organization_crd = record.get('organizationCRD', '').strip('"')
            entity = record.get('entity', '').strip('"')
            
            # Skip if either field is missing
            if not organization_crd or not entity:
                logger.warning(f"Skipping record with missing data: {record}")
                continue
            
            # Create claim using entity for both reference and employee ID
            claim = {
                "reference_id": entity,
                "business_ref": entity,
                "organization_crd": organization_crd,
                "entityName": entity
            }
            
            # Process the claim
            logger.info(f"Processing claim for entity: {entity}, CRD: {organization_crd}")
            process_claim(
                claim=claim,
                facade=facade,
                business_ref=entity,
                skip_financials=skip_financials,
                skip_legal=skip_legal
            )
            
            # Increment processed count and print progress
            processed_count += 1
            print(f"Processed {processed_count}/{total_records} records")
            
        except Exception as e:
            logger.error(f"Error processing record {record}: {str(e)}")
            # Continue with next record even if current one fails
            continue
    
    logger.info(f"Completed processing {processed_count}/{total_records} records")

def main():
    """Main entry point for the script."""
    args = parse_args()
    
    # Configure logging with user-specified level
    log_level = getattr(logging, args.log_level)
    for logger_name in loggers:
        if isinstance(logger_name, str) and not logger_name.startswith('_'):
            loggers[logger_name].setLevel(log_level)
    
    try:
        # Read CSV data
        records = read_csv_data(args.csv_path)
        
        # Initialize facade
        facade = FirmServicesFacade()
        
        # Process records
        process_records(
            records=records,
            facade=facade,
            skip_financials=args.skip_financials,
            skip_legal=args.skip_legal
        )
        
        print(f"Successfully processed all records from {args.csv_path}")
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}", exc_info=True)
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()