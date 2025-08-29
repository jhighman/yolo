# Idle Crash Test: Disable Retries in FINRA/SEC Agents

## Purpose
This change disables retry logic in the FINRA and SEC API agents to test if retries on connection errors are causing silent crashes (no logs) during idle periods in our Celery/Redis queuing system.

## Changes
- **Files Modified**:
  - `agents/finra_firm_broker_check_agent.py`: Nullified `retry_with_backoff` to try API calls once, log errors, and raise immediately.
  - `agents/sec_firm_iapd_agent.py`: Applied same nullification to the retry decorator.
- **Details**: The `retry_with_backoff` decorator was modified to disable retries, failing fast on connection errors to prevent resource exhaustion during idle.

## Why
Retries (up to 3 attempts with backoff) on connection errors (e.g., FINRA/SEC API drops) during idle periods may cause memory/socket leaks or deadlocks in Celery workers, leading to silent crashes. Disabling retries tests this hypothesis.

## Monitoring Instructions
1. **Deploy**: Push the updated code to prod.
2. **Run**:
   - Start app and Celery workers: `celery -A api.celery_app worker --loglevel=debug --concurrency=1`.
   - Queue jobs (e.g., FINRA/SEC API calls via `webhook_queue` or `firm_compliance_queue`).
   - Let system idle for 1-4 hours (or overnight when queues are empty).
3. **Monitor**:
   - **CPU/Memory**: Use `htop` or Prometheus to check for spikes or leaks.
   - **Redis Queues**: Run `redis-cli LLEN webhook_queue` (should stay low during idle).
   - **Logs**: Check `logs/agents/agents.log` for `Retries disabled for ...` errors.
4. **Duration**: Monitor for 3-5 days to confirm stability during idle periods.
5. **Outcomes**:
   - **No Crashes**: Retries caused the issue. Plan a permanent fix.
   - **Crashes Persist**: Revert with `git revert <commit-hash>` and investigate commits `1d2a476` or `918e98a`.
6. **Rollback**: Run `git revert <commit-hash>` if needed.

## Contact
For issues or results, contact the DevOps team.

## Notes
- Watch for new log errors (e.g., connection failures now surfacing).
- Ensure debug logging is enabled to catch issues.
- This is a temporary change to diagnose the idle crash issue.