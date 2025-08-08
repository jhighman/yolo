# Celery Worker Configuration Guide

This document provides guidance on how to properly configure and run Celery workers for the webhook reliability system.

## Running Celery Workers

While some Celery configuration is set in the code (`task_acks_late`, `task_default_queue`, etc.), worker-specific settings like concurrency and prefetch multiplier should be specified on the command line or via environment variables.

### Recommended Command

```bash
celery -A api.celery_app worker \
  -Q firm_compliance_queue,webhook_queue,dead_letter_queue \
  --concurrency=4 \
  --prefetch-multiplier=1 \
  --loglevel=info
```

### Configuration Options

- **-Q, --queues**: Comma-separated list of queues to consume from
  - `firm_compliance_queue`: For processing firm compliance claims
  - `webhook_queue`: For webhook delivery tasks
  - `dead_letter_queue`: For handling permanently failed tasks

- **--concurrency**: Number of worker processes/threads
  - Recommended: 4 (adjust based on available CPU cores)
  - Note: This setting is ignored when specified in app.conf.update()

- **--prefetch-multiplier**: How many messages to prefetch at a time
  - Recommended: 1 (ensures fair work distribution and prevents task starvation)
  - Lower values are better for long-running tasks

- **--loglevel**: Logging level (debug, info, warning, error, critical)
  - Recommended: info for production, debug for development

## Environment Variables

You can also use environment variables to configure the workers:

```bash
export CELERYD_CONCURRENCY=4
export CELERYD_PREFETCH_MULTIPLIER=1
celery -A api.celery_app worker -Q firm_compliance_queue,webhook_queue,dead_letter_queue --loglevel=info
```

## Prometheus Metrics

When running multiple workers, use the `ENABLE_PROMETHEUS` and `PROMETHEUS_PORT` environment variables to control which worker starts the Prometheus metrics server:

```bash
# First worker - enable Prometheus
ENABLE_PROMETHEUS=true PROMETHEUS_PORT=8000 celery -A api.celery_app worker -Q firm_compliance_queue,webhook_queue,dead_letter_queue --concurrency=4 --prefetch-multiplier=1 --loglevel=info

# Additional workers - disable Prometheus to avoid port conflicts
ENABLE_PROMETHEUS=false celery -A api.celery_app worker -Q firm_compliance_queue,webhook_queue,dead_letter_queue --concurrency=4 --prefetch-multiplier=1 --loglevel=info
```

## Monitoring Queues

To monitor the queues and see pending tasks:

```bash
celery -A api.celery_app inspect active
celery -A api.celery_app inspect scheduled
celery -A api.celery_app inspect reserved
```

To purge all queues (use with caution):

```bash
celery -A api.celery_app purge
```

## Dead Letter Queue (DLQ)

Failed webhooks are automatically moved to the DLQ after max retries. You can view them using the API endpoint:

```
GET /webhook-statuses?status=failed
```

Or directly in Redis:

```bash
redis-cli -n 2 SMEMBERS "dead_letter:webhook:index"