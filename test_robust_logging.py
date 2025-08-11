#!/usr/bin/env python3
"""
Test script for robust logging configuration

This script tests the robust logging configuration by:
1. Setting up logging with the robust configuration
2. Simulating I/O errors during logging
3. Verifying that logging continues to work despite errors

Usage:
    python test_robust_logging.py
"""

import os
import sys
import time
import logging
import tempfile
import shutil
from pathlib import Path

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our robust logging configuration
from utils.robust_logging_config import (
    ErrorHandlingRotatingFileHandler,
    setup_robust_logging,
    create_celery_logger
)

def test_error_handling_handler():
    """Test that the ErrorHandlingRotatingFileHandler handles I/O errors gracefully."""
    print("\n=== Testing ErrorHandlingRotatingFileHandler ===")
    
    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp()
    log_file = os.path.join(temp_dir, "test.log")
    
    try:
        # Create a logger with our error handling handler
        logger = logging.getLogger("test_handler")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()
        
        # Create console handler as fallback
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        
        # Create file handler with error handling
        file_handler = ErrorHandlingRotatingFileHandler(
            log_file,
            maxBytes=1024,  # Small size for testing
            backupCount=3,
            max_errors=3
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        file_handler.set_fallback_handler(console_handler)
        
        # Add handlers to logger
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        # Test normal logging
        print("Testing normal logging...")
        logger.info("This is a test log message")
        logger.warning("This is a warning message")
        logger.error("This is an error message")
        
        # Verify log file was created
        if os.path.exists(log_file):
            print(f"✅ Log file created successfully: {log_file}")
            with open(log_file, 'r') as f:
                content = f.read()
                print(f"Log file content:\n{content}")
        else:
            print(f"❌ Log file was not created: {log_file}")
        
        # Simulate I/O error by making the log file read-only
        print("\nSimulating I/O error by making log file read-only...")
        os.chmod(log_file, 0o444)  # Read-only
        
        # Try to log after making file read-only
        logger.info("This message should go to the fallback handler")
        logger.warning("This warning should go to the fallback handler")
        logger.error("This error should go to the fallback handler")
        
        # Verify handler switched to fallback after errors
        print(f"Error count: {file_handler.error_count}")
        print(f"Handler disabled: {file_handler.disabled_due_to_errors}")
        
        if file_handler.error_count > 0:
            print("✅ Error handling worked - errors were caught")
        else:
            print("❌ No errors were caught - something is wrong")
            
        if file_handler.disabled_due_to_errors:
            print("✅ Handler was disabled after max errors")
        
        # Make the file writable again
        print("\nMaking log file writable again...")
        os.chmod(log_file, 0o644)  # Read-write
        
        # Create a new handler to test recovery
        logger.handlers.clear()
        new_file_handler = ErrorHandlingRotatingFileHandler(
            log_file,
            maxBytes=1024,
            backupCount=3,
            max_errors=3
        )
        new_file_handler.setLevel(logging.INFO)
        new_file_handler.setFormatter(formatter)
        new_file_handler.set_fallback_handler(console_handler)
        
        logger.addHandler(console_handler)
        logger.addHandler(new_file_handler)
        
        # Test logging after recovery
        print("Testing logging after recovery...")
        logger.info("This message should go to the log file again")
        
        # Verify log file was updated
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                content = f.read()
                if "after recovery" in content:
                    print("✅ Logging recovered successfully")
                else:
                    print("❌ Logging did not recover")
        
    finally:
        # Clean up
        shutil.rmtree(temp_dir)

def test_setup_robust_logging():
    """Test the setup_robust_logging function."""
    print("\n=== Testing setup_robust_logging ===")
    
    # Set up robust logging
    loggers = setup_robust_logging(debug=True)
    
    # Test logging with each logger
    for logger_name, logger in loggers.items():
        if logger_name != '_groups' and hasattr(logger, 'info'):
            print(f"Testing logger: {logger_name}")
            logger.info(f"Test info message from {logger_name}")
            logger.warning(f"Test warning message from {logger_name}")
            logger.error(f"Test error message from {logger_name}")
    
    print("✅ setup_robust_logging test complete")

def test_create_celery_logger():
    """Test the create_celery_logger function."""
    print("\n=== Testing create_celery_logger ===")
    
    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Create a Celery logger
        logger = create_celery_logger("test_celery", log_dir=temp_dir)
        
        # Test logging
        logger.info("Test info message from Celery logger")
        logger.warning("Test warning message from Celery logger")
        logger.error("Test error message from Celery logger")
        
        # Verify log file was created
        log_file = os.path.join(temp_dir, "test_celery.log")
        if os.path.exists(log_file):
            print(f"✅ Celery log file created successfully: {log_file}")
            with open(log_file, 'r') as f:
                content = f.read()
                print(f"Log file content:\n{content}")
        else:
            print(f"❌ Celery log file was not created: {log_file}")
        
        # Simulate I/O error
        print("\nSimulating I/O error by making log file read-only...")
        os.chmod(log_file, 0o444)  # Read-only
        
        # Try to log after making file read-only
        logger.info("This message should go to the fallback handler")
        logger.warning("This warning should go to the fallback handler")
        logger.error("This error should go to the fallback handler")
        
        print("✅ create_celery_logger test complete")
        
    finally:
        # Clean up
        shutil.rmtree(temp_dir)

def main():
    """Run all tests."""
    print("=== ROBUST LOGGING TESTS ===")
    
    # Run tests
    test_error_handling_handler()
    test_setup_robust_logging()
    test_create_celery_logger()
    
    print("\n=== ALL TESTS COMPLETE ===")

if __name__ == "__main__":
    main()