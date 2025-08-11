# Release Notes – Celery Logging Fix

**Release Date:** 2025-08-11
**Affected Component:** Celery Worker Logging
**Change Type:** Bug fix, reliability enhancement

## Background

Celery workers were experiencing crashes due to I/O errors when writing to log files:

```
[2025-08-11 21:22:17,559: WARNING/ForkPoolWorker-1] --- Logging error ---
[2025-08-11 21:22:17,559: WARNING/ForkPoolWorker-1] Traceback (most recent call last):
[2025-08-11 21:22:17,559: WARNING/ForkPoolWorker-1]   File "/usr/lib64/python3.9/logging/__init__.py", line 1086, in emit
    stream.write(msg + self.terminator)
[2025-08-11 21:22:17,559: WARNING/ForkPoolWorker-1] OSError: [Errno 5] Input/output error
```

This issue can be caused by disk space problems, permission issues, filesystem corruption, or network-mounted filesystem issues. When this error occurs, it can cause Celery workers to crash or behave unpredictably.

## Changes Implemented

### 1. Diagnostic Tools

- Added `check_celery_logging.py` script to diagnose common issues:
  - Disk space checks
  - Log directory permission verification
  - Log file writing tests
  - Process and file descriptor inspection

### 2. Robust Logging Configuration

- Created `utils/robust_logging_config.py` with:
  - Custom `ErrorHandlingRotatingFileHandler` that catches I/O errors
  - Fallback to console logging when file logging fails
  - Automatic disabling of problematic handlers after repeated errors
  - Configurable error thresholds and recovery mechanisms

### 3. Robust Celery Worker

- Implemented `robust_celery_worker.py` as a drop-in replacement for standard Celery worker:
  - Configures robust logging before starting worker processes
  - Patches Celery's logging system to use error-handling handlers
  - Ensures logging errors don't affect task processing
  - Maintains compatibility with all standard Celery worker options

### 4. Testing & Documentation

- Added `test_robust_logging.py` to verify the solution works
- Created comprehensive documentation in `celery_logging_fix_README.md`

## Operational Impact

- **Reliability:** Celery workers continue processing tasks even when logging fails
- **Observability:** Logging errors are captured and reported without crashing workers
- **Maintainability:** Diagnostic tools help identify and fix underlying issues
- **Performance:** No impact on task processing performance

## Deployment Instructions

1. Check for underlying issues that might be causing logging errors:

```bash
python check_celery_logging.py
```

2. Stop all Celery workers:

```bash
pkill -f "celery worker"
```

3. Deploy the new files:
   - `check_celery_logging.py`
   - `utils/robust_logging_config.py`
   - `robust_celery_worker.py`
   - `test_robust_logging.py`
   - `celery_logging_fix_README.md`

4. Verify the solution works:

```bash
python test_robust_logging.py
```

5. Start Celery workers using the robust worker script:

```bash
python robust_celery_worker.py -A api.celery_app worker \
  -Q firm_compliance_queue,webhook_queue,dead_letter_queue \
  --concurrency=4 \
  --prefetch-multiplier=1 \
  --loglevel=info
```

6. Monitor for any logging-related errors in the worker output

7. If disk space issues were identified, implement a log rotation and cleanup policy

---

# Release Notes – Entity Queue Reliability & Webhook Improvements

**Release Date:** 2025-08-08
**Affected Component:** Entity Celery Worker & Webhook Delivery
**Change Type:** Bug fix, operational improvement, reliability enhancement

## Background

The entity processing queue was intermittently hanging, leaving webhooks in a "pending" state and preventing completion. Investigation showed:

- Stale/invalid tasks persisted in Redis.
- Blocking KEYS calls slowing Redis and workers.
- Inconsistent status recording between code paths.
- Unsafe variable access in error branches.
- Missing operational safeguards in webhook delivery.

## Changes Implemented

### 1. Queue & Redis State Management

- Added safe flush procedure for entity queue state without impacting other services.
- Replaced all redis.keys() calls with non-blocking SCAN iteration in:
  - list_webhook_statuses
  - /webhook-cleanup
- Documented targeted Redis key cleanup for entity-only state.

### 2. Safe Task Execution

- webhook_url initialized early in process_firm_compliance_claim to prevent UnboundLocalError on validation failures.
- All duration metrics (task_duration, webhook_duration) now wrap the entire function for accurate timing, regardless of exit path.

### 3. Celery Configuration

- Removed unused/invalid task_concurrency setting.
- Standardized concurrency control to worker CLI flag:

```bash
celery -A ... worker --concurrency=4
```

### 4. Webhook Delivery Hardening

- Added X-Idempotency-Key header for duplicate suppression on retries.
- Changed request timeout from a single 30s to a (5s connect / 30s read) tuple for faster network failure detection.
- Unified retry and status recording for all delivery attempts (success, failure, non-retryable errors).

### 5. Observability & Metrics

- Added PROMETHEUS_PORT environment variable to avoid port collisions between workers.
- Reduced label cardinality for performance and cost control.
- Metrics now accurately capture total webhook sends, failures, and per-task durations.

### 6. Code Cleanups

- Removed duplicate imports (FirmServicesFacade, CacheManager).
- Marked unused aiohttp and asyncio imports for removal unless actively used.
- Adjusted webhook_failure_handler logging to reduce noise in production.

### 7. Security & Operational Guidance

- Provided optional webhook domain allowlist (regex via env var).
- Documented safe Redis flush steps for entity state.
- Added recommendations for HMAC signing of webhook payloads.

## Operational Impact

- **Reliability:** No more Redis blocking from KEYS; queue state can be safely cleared if stuck.
- **Performance:** Lower Redis latency; faster failure handling for bad webhooks.
- **Metrics:** Accurate end-to-end timing and task outcome counts.
- **Security:** Optional idempotency and outbound URL controls reduce risk of duplicate processing and abuse.

## Deployment Notes

1. Stop all entity workers before deploying to avoid mixed Redis key formats.

2. If queues are stuck before deployment:

```bash
celery -A ... purge -Q entity_queue
redis-cli -n <db> scan 0 match "entity:*" | xargs redis-cli -n <db> del
```

3. Restart workers with:

```bash
celery -A ... worker -Q entity_queue,webhook_queue \
  --concurrency=4 --prefetch-multiplier=1 --loglevel=info
```

4. Confirm Prometheus scraping the correct PROMETHEUS_PORT.

5. Optionally enable outbound URL allowlist via:

```bash
export WEBHOOK_ALLOWLIST="^https://hooks\.slack\.com/.*$"