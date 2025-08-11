import logging
import logging.handlers
import os
import sys
import traceback
from pathlib import Path
from typing import Dict, Set, Any, Optional

# Import the original logging configuration
from utils.logging_config import LOGGER_GROUPS, _LOGGING_INITIALIZED

class ErrorHandlingRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """A RotatingFileHandler that catches I/O errors and logs them to stderr.
    
    This prevents I/O errors from crashing the application, which is especially
    important for long-running processes like Celery workers.
    """
    
    def __init__(self, *args, **kwargs):
        self.fallback_handler = None
        self.error_count = 0
        self.max_errors = kwargs.pop('max_errors', 5)
        self.disabled_due_to_errors = False
        super().__init__(*args, **kwargs)
    
    def set_fallback_handler(self, handler):
        """Set a fallback handler to use if this handler fails."""
        self.fallback_handler = handler
    
    def handleError(self, record):
        """Handle errors that occur during emission of the log record."""
        self.error_count += 1
        
        # Get the exception info
        exc_type, exc_value, exc_traceback = sys.exc_info()
        
        # Log the error to stderr
        error_type_name = exc_type.__name__ if exc_type else "Unknown"
        sys.stderr.write(f"Error in log handler ({self.baseFilename}): {error_type_name}: {exc_value}\n")
        
        # If we've had too many errors, disable this handler
        if self.error_count >= self.max_errors and not self.disabled_due_to_errors:
            sys.stderr.write(f"Too many errors ({self.error_count}) in log handler. Disabling {self.baseFilename}\n")
            self.disabled_due_to_errors = True
        
        # Try to use the fallback handler if available
        if self.fallback_handler and hasattr(self.fallback_handler, 'emit'):
            try:
                # Add a note about the original error
                if not hasattr(record, 'original_error'):
                    error_type_name = exc_type.__name__ if exc_type else "Unknown"
                    record.original_error = f"{error_type_name}: {exc_value}"
                self.fallback_handler.emit(record)
            except Exception:
                # If the fallback also fails, use the default handleError
                super().handleError(record)
    
    def emit(self, record):
        """Emit a record, catching any errors."""
        if self.disabled_due_to_errors:
            # If this handler is disabled due to errors, try the fallback
            if self.fallback_handler:
                try:
                    self.fallback_handler.emit(record)
                except Exception:
                    pass
            return
        
        try:
            super().emit(record)
        except Exception:
            self.handleError(record)

def setup_robust_logging(debug: bool = False, max_errors: int = 5) -> Dict[str, logging.Logger]:
    """Configure logging with error handling for all modules.
    
    This is a more robust version of setup_logging that handles I/O errors gracefully.
    
    Args:
        debug: Whether to enable debug logging
        max_errors: Maximum number of errors before disabling a handler
        
    Returns:
        Dictionary of configured loggers
    """
    global _LOGGING_INITIALIZED
    if _LOGGING_INITIALIZED:
        return {key: logging.getLogger(name) for key, name in LOGGER_GROUPS['core'].items()}

    # Create logs directory structure
    log_dir = "logs"
    for group in LOGGER_GROUPS.keys():
        os.makedirs(os.path.join(log_dir, group), exist_ok=True)

    # Set level based on debug flag
    base_level = logging.DEBUG if debug else logging.INFO

    # Get root logger and clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Create console handler for all logs
    console_handler = logging.StreamHandler()
    console_handler.setLevel(base_level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(base_level)

    # Initialize all loggers from groups
    loggers = {}
    for group_name, group_loggers in LOGGER_GROUPS.items():
        # Create a file handler for this group
        group_log_file = os.path.join(log_dir, group_name, f"{group_name}.log")
        
        try:
            # Create the error-handling file handler
            file_handler = ErrorHandlingRotatingFileHandler(
                group_log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                max_errors=max_errors
            )
            file_handler.setLevel(base_level)
            file_handler.setFormatter(formatter)
            
            # Set the console handler as the fallback
            file_handler.set_fallback_handler(console_handler)
            
            # Create and configure loggers for this group
            for logger_key, logger_name in group_loggers.items():
                logger = logging.getLogger(logger_name)
                logger.setLevel(base_level)
                logger.propagate = False  # Don't propagate to root logger
                logger.addHandler(console_handler)  # Add console handler
                logger.addHandler(file_handler)  # Add group-specific file handler
                loggers[logger_key] = logger
                
        except Exception as e:
            sys.stderr.write(f"Error setting up log handler for {group_name}: {str(e)}\n")
            # Still create the loggers, but only with console handler
            for logger_key, logger_name in group_loggers.items():
                logger = logging.getLogger(logger_name)
                logger.setLevel(base_level)
                logger.propagate = False
                logger.addHandler(console_handler)
                loggers[logger_key] = logger

    # Add group information to the loggers dict
    loggers['_groups'] = LOGGER_GROUPS

    _LOGGING_INITIALIZED = True
    return loggers

def create_celery_logger(name: str, log_dir: Optional[str] = None) -> logging.Logger:
    """Create a logger specifically for Celery workers with robust error handling.
    
    Args:
        name: Name of the logger
        log_dir: Directory to store log files (defaults to 'logs/celery')
        
    Returns:
        Configured logger instance
    """
    if log_dir is None:
        log_dir = os.path.join("logs", "celery")
    
    # Ensure the directory exists
    os.makedirs(log_dir, exist_ok=True)
    
    # Create the logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False  # Don't propagate to root logger
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatters
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Create file handler with error handling
    try:
        log_file = os.path.join(log_dir, f"{name}.log")
        file_handler = ErrorHandlingRotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            max_errors=5
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        file_handler.set_fallback_handler(console_handler)
        logger.addHandler(file_handler)
    except Exception as e:
        sys.stderr.write(f"Error setting up log file for {name}: {str(e)}\n")
        # Continue with just the console handler
    
    return logger

def flush_logs():
    """Flush all log handlers to ensure logs are written to disk."""
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        try:
            handler.flush()
        except Exception as e:
            sys.stderr.write(f"Error flushing log handler: {str(e)}\n")