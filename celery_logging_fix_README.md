# Celery Logging Fix

## Problem

We encountered the following error in our Celery worker logs:

```
[2025-08-11 21:22:17,557: INFO/MainProcess] Task process_firm_compliance_claim[b5f0ff83-c8d2-4ee4-b012-a22cd8fab79b] received
[2025-08-11 21:22:17,559: WARNING/ForkPoolWorker-1] --- Logging error ---
[2025-08-11 21:22:17,559: WARNING/ForkPoolWorker-1] Traceback (most recent call last):
[2025-08-11 21:22:17,559: WARNING/ForkPoolWorker-1]   File "/usr/lib64/python3.9/logging/__init__.py", line 1086, in emit
    stream.write(msg + self.terminator)
[2025-08-11 21:22:17,559: WARNING/ForkPoolWorker-1] OSError: [Errno 5] Input/output error
```

This error occurs when the Celery worker process encounters an I/O error while trying to write to its log file. This can happen due to:

1. Disk space issues (full disk)
2. File permission problems
3. Disk I/O errors or filesystem corruption
4. Network-mounted filesystem issues (if logs are stored on a network drive)

The problem is that when this error occurs, it can cause the Celery worker to crash or behave unpredictably, potentially affecting task processing.

## Solution

We've implemented a robust logging solution that can handle I/O errors gracefully without crashing the Celery worker. The solution consists of:

1. A diagnostic script (`check_celery_logging.py`) to identify common issues
2. A robust logging configuration (`utils/robust_logging_config.py`) that handles I/O errors
3. A modified Celery worker script (`robust_celery_worker.py`) that uses the robust logging
4. A test script (`test_robust_logging.py`) to verify the solution works

### Key Features

- **Error-Handling File Handler**: Catches I/O errors during logging and prevents them from crashing the worker
- **Fallback Logging**: Automatically switches to console logging if file logging fails
- **Automatic Recovery**: Attempts to recover file logging when possible
- **Diagnostic Tools**: Helps identify and fix underlying issues

## Usage

### Running the Diagnostic Script

To check for common issues that might cause logging errors:

```bash
python check_celery_logging.py
```

This will check disk space, log directory permissions, and test log file writing.

### Starting Celery Workers with Robust Logging

Instead of using the standard Celery command, use our robust worker script:

```bash
python robust_celery_worker.py -A api.celery_app worker -Q firm_compliance_queue,webhook_queue,dead_letter_queue --concurrency=4 --prefetch-multiplier=1 --loglevel=info
```

This script accepts all the same arguments as the standard `celery worker` command.

### Testing the Robust Logging

To verify that the robust logging solution works correctly:

```bash
python test_robust_logging.py
```

This will run tests to ensure that logging continues to work even when I/O errors occur.

## Implementation Details

### ErrorHandlingRotatingFileHandler

This is a custom file handler that extends `RotatingFileHandler` to catch I/O errors during logging. When an error occurs:

1. It logs the error to stderr
2. It attempts to use a fallback handler (usually console)
3. After a configurable number of errors, it disables itself to prevent further errors

### Robust Celery Worker

The robust Celery worker script:

1. Sets up robust logging before starting the worker
2. Configures each worker process with its own error-handling log handlers
3. Patches Celery's logging system to use our robust handlers
4. Ensures that logging errors don't affect task processing

## Troubleshooting

If you continue to experience logging issues:

1. Check disk space: `df -h`
2. Verify log directory permissions: `ls -la logs/`
3. Check for disk I/O errors: `dmesg | grep -i error`
4. Consider moving logs to a different filesystem if network storage is causing issues

## Long-Term Recommendations

1. **Monitoring**: Set up monitoring for disk space and I/O errors
2. **Log Rotation**: Ensure log rotation is properly configured to prevent disk space issues
3. **Centralized Logging**: Consider using a centralized logging system (e.g., ELK stack, Graylog) to reduce dependency on local disk I/O
4. **Regular Maintenance**: Schedule regular cleanup of old log files

## Files

- `check_celery_logging.py`: Diagnostic script to identify common issues
- `utils/robust_logging_config.py`: Robust logging configuration with error handling
- `robust_celery_worker.py`: Modified Celery worker script with robust logging
- `test_robust_logging.py`: Test script to verify the solution works
- `celery_logging_fix_README.md`: This documentation file