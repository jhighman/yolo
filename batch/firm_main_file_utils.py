"""
Utilities for file operations in batch processing of business entity compliance claims.
Handles folder setup, checkpoint management, CSV file retrieval, and archiving.
"""

import os
import shutil
import json
import logging
from datetime import datetime
from typing import Dict, Optional, Any, List
from batch.firm_main_config import INPUT_FOLDER, OUTPUT_FOLDER, ARCHIVE_FOLDER, CHECKPOINT_FILE

logger = logging.getLogger('firm_main_file_utils')

def setup_folders():
    """
    Create necessary folders (INPUT_FOLDER, OUTPUT_FOLDER, ARCHIVE_FOLDER) if they don't exist.
    """
    for folder in [INPUT_FOLDER, OUTPUT_FOLDER, ARCHIVE_FOLDER]:
        try:
            os.makedirs(folder, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create folder {folder}: {str(e)}")
            raise

def load_checkpoint() -> Optional[Dict[str, Any]]:
    """
    Load the checkpoint file to resume batch processing.

    Returns:
        Optional[Dict[str, Any]]: Checkpoint data or None if not found or invalid.
    """
    try:
        with open(CHECKPOINT_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception as e:
        logger.error(f"Error loading checkpoint: {str(e)}")
        return None

def save_checkpoint(csv_file: str, line_number: int):
    """
    Save the current processing state to the checkpoint file.

    Args:
        csv_file (str): Name of the CSV file being processed.
        line_number (int): Last processed line number.
    """
    if not csv_file or line_number is None:
        logger.error(f"Cannot save checkpoint: csv_file={csv_file}, line_number={line_number}")
        return
    try:
        checkpoint_path = str(CHECKPOINT_FILE)
        with open(checkpoint_path, 'w') as f:
            json.dump({"csv_file": csv_file, "line": line_number}, f)
        logger.debug(f"Checkpoint saved: {csv_file}, line {line_number}")
    except Exception as e:
        logger.error(f"Error saving checkpoint: {str(e)}")

def get_csv_files() -> List[str]:
    """
    Retrieve a sorted list of CSV files from the INPUT_FOLDER.

    Returns:
        List[str]: List of CSV file names.
    """
    try:
        files = sorted([f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith('.csv')])
        logger.debug(f"Found CSV files: {files}")
        return files
    except Exception as e:
        logger.error(f"Error listing CSV files in {INPUT_FOLDER}: {str(e)}")
        return []

def archive_file(csv_file_path: str):
    """
    Move a processed CSV file to the ARCHIVE_FOLDER with a date-based subfolder.

    Args:
        csv_file_path (str): Path to the CSV file to archive.
    """
    date_str = datetime.now().strftime("%m-%d-%Y")
    archive_subfolder = os.path.join(ARCHIVE_FOLDER, date_str)
    try:
        os.makedirs(archive_subfolder, exist_ok=True)
        dest_path = os.path.join(archive_subfolder, os.path.basename(csv_file_path))
        shutil.move(csv_file_path, dest_path)
        logger.info(f"Archived {csv_file_path} to {dest_path}")
    except Exception as e:
        logger.error(f"Error archiving {csv_file_path}: {str(e)}")