#!/usr/bin/env python3
"""
Robust Celery Worker with Error-Handling Logging

This script starts a Celery worker with robust logging that can handle I/O errors
without crashing the worker process. It's designed to be a drop-in replacement for
the standard Celery worker command.

Usage:
    python robust_celery_worker.py [celery worker options]

Example:
    python robust_celery_worker.py -A api.celery_app worker -Q firm_compliance_queue,webhook_queue,dead_letter_queue --concurrency=4 --prefetch-multiplier=1 --loglevel=info
"""

import os
import sys
import logging
import traceback
from celery.signals import setup_logging, worker_process_init
from celery.utils.log import get_task_logger

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our robust logging configuration
from utils.robust_logging_config import create_celery_logger, ErrorHandlingRotatingFileHandler

# Prevent Celery from setting up its own logging
@setup_logging.connect
def setup_celery_logging(**kwargs):
    return True

# Set up logging for each worker process
@worker_process_init.connect
def setup_worker_logging(**kwargs):
    """Set up robust logging for each worker process."""
    try:
        # Create logs directory if it doesn't exist
        os.makedirs("logs/celery", exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.handlers.clear()  # Remove any existing handlers
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.INFO)
        root_logger.addHandler(console_handler)
        root_logger.setLevel(logging.INFO)
        
        # Create file handler with error handling for the worker
        worker_id = os.environ.get('HOSTNAME', 'unknown')
        log_file = f"logs/celery/worker-{worker_id}.log"
        
        try:
            file_handler = ErrorHandlingRotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                max_errors=5
            )
            file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(processName)s - %(message)s')
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(logging.INFO)
            file_handler.set_fallback_handler(console_handler)
            root_logger.addHandler(file_handler)
            
            # Log successful setup
            root_logger.info(f"Robust logging configured for worker {worker_id}")
        except Exception as e:
            # If we can't set up the file handler, log to console and continue
            console_handler.setLevel(logging.WARNING)
            root_logger.warning(f"Could not set up log file {log_file}: {str(e)}")
            root_logger.warning("Continuing with console logging only")
    
    except Exception as e:
        # Last resort: print to stderr
        sys.stderr.write(f"Error setting up worker logging: {str(e)}\n")
        traceback.print_exc()

def patch_celery_logging():
    """Patch Celery's logging to use our robust logger."""
    # Replace Celery's get_task_logger with our version
    original_get_task_logger = get_task_logger
    
    def robust_get_task_logger(name):
        """Get a task logger that can handle I/O errors."""
        try:
            return create_celery_logger(name, log_dir="logs/celery")
        except Exception:
            # Fall back to the original if our version fails
            return original_get_task_logger(name)
    
    # Apply the patch
    get_task_logger.__code__ = robust_get_task_logger.__code__

def main():
    """Run the Celery worker with robust logging."""
    # Patch Celery's logging
    patch_celery_logging()
    
    # Set up environment variables for Celery
    os.environ['PYTHONUNBUFFERED'] = '1'  # Ensure logs are not buffered
    
    # Get Celery command-line arguments
    celery_args = sys.argv[1:] if len(sys.argv) > 1 else [
        "-A", "api.celery_app", "worker",
        "-Q", "firm_compliance_queue,webhook_queue,dead_letter_queue",
        "--concurrency=4",
        "--prefetch-multiplier=1",
        "--loglevel=info"
    ]
    
    # Ensure we're using the worker command
    if not celery_args or celery_args[0] != "worker" and "-A" in celery_args:
        celery_args.insert(1, "worker")
    
    # Print startup message
    print(f"Starting Celery worker with robust logging: celery {' '.join(celery_args)}")
    
    # Import and run Celery
    from celery.__main__ import main as celery_main
    sys.argv = ["celery"] + celery_args
    celery_main()

if __name__ == "__main__":
    main()