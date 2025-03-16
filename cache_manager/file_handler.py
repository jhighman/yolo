"""
file_handler.py

This module provides the FileHandler class for managing filesystem operations
related to cache management. It handles file and directory operations with proper
error handling and logging.
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Union

# Configure logging
logger = logging.getLogger("FileHandler")

class FileHandler:
    """Handles filesystem operations for cache management."""
    
    def __init__(self, base_path: Path):
        """Initialize the file handler.
        
        Args:
            base_path: Base directory for file operations
        """
        self.base_path = base_path
        if not self.base_path.exists():
            logger.warning(f"Base path does not exist: {self.base_path}")
            self.base_path.mkdir(parents=True, exist_ok=True)

    def list_files(self, path: Union[str, Path], pattern: str = "*.json") -> List[Path]:
        """List files in a directory matching a pattern.
        
        Args:
            path: Directory to list files from
            pattern: Glob pattern for file matching (default: "*.json")
            
        Returns:
            List of matching file paths, sorted for consistency
        """
        path = Path(path)
        if not path.exists():
            logger.warning(f"Directory does not exist: {path}")
            return []
        
        try:
            files = sorted(path.glob(pattern))
            return files
        except Exception as e:
            logger.error(f"Failed to list files in {path}: {str(e)}")
            return []

    def read_json(self, file_path: Union[str, Path]) -> Optional[Dict]:
        """Read and parse a JSON file.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            Dictionary of parsed JSON data or None if reading fails
        """
        file_path = Path(file_path)
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return None
        
        try:
            with file_path.open('r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in {file_path}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {str(e)}")
            return None

    def delete_path(self, path: Union[str, Path]) -> bool:
        """Delete a file or directory.
        
        Args:
            path: Path to delete (file or directory)
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            path = Path(path)
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
            return True
        except Exception as e:
            logger.error(f"Failed to delete {path}: {str(e)}")
            return False

    def get_last_modified(self, file_path: Union[str, Path]) -> datetime:
        """Get the last modification time of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            datetime: Last modification time
            
        Raises:
            FileNotFoundError: If the file does not exist
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        return datetime.fromtimestamp(file_path.stat().st_mtime)

    def ensure_directory(self, directory: Union[str, Path]) -> bool:
        """Ensure a directory exists, creating it if necessary.
        
        Args:
            directory: Directory path to ensure
            
        Returns:
            bool: True if directory exists or was created, False on error
        """
        try:
            directory = Path(directory)
            directory.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {directory}: {str(e)}")
            return False 