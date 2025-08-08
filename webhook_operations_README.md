# Entity Webhook Operations Guide

This document provides operational commands and instructions for verifying and managing the webhook delivery system.

## Overview

The webhook delivery system has been redesigned to provide:

1. Single, reliable webhook delivery path via Celery with retries/backoff
2. Deterministic, per-delivery status tracking in Redis with TTLs
3. Clear logs/metrics and a dead-letter queue for final failures
4. Improved observability with correlation IDs, ISO timestamps, headers, and Prometheus labels

## Celery Configuration

The system uses a dedicated Redis DB for entity webhooks:

```
broker="redis://localhost:6379/1"
backend="redis://localhost:6379/1"
```

### Queues

- Default: `firm_compliance_queue` - For claim processing tasks
- Webhooks: `webhook_queue` - For webhook delivery tasks
- Dead Letter: `dead_letter_queue` - For permanently failed tasks

## Operational Commands

### Starting Workers

Workers must consume both queues:

```bash
celery -A api worker -Q firm_compliance_queue,webhook_queue -l info
```

### Inspecting Workers and Queues

Check registered tasks:

```bash
celery -A api inspect registered
```

Check active tasks:

```bash
celery -A api inspect active
```

Check scheduled tasks (retries):

```bash
celery -A api inspect scheduled
```

Check reserved tasks:

```bash
celery -A api inspect reserved
```

### Monitoring Queue Lengths

```bash
redis-cli -n 1 llen firm_compliance_queue
redis-cli -n 1 llen webhook_queue
redis-cli -n 1 llen dead_letter_queue
```

### Monitoring Webhook Status

List all webhook statuses:

```bash
curl -X GET "http://localhost:9000/webhook-statuses"
```

List webhook statuses for a specific reference_id:

```bash
curl -X GET "http://localhost:9000/webhook-statuses?reference_id=YOUR_REFERENCE_ID"
```

Filter by status:

```bash
curl -X GET "http://localhost:9000/webhook-statuses?status=delivered"
curl -X GET "http://localhost:9000/webhook-statuses?status=failed"
curl -X GET "http://localhost:9000/webhook-statuses?status=pending"
curl -X GET "http://localhost:9000/webhook-statuses?status=in_progress"
curl -X GET "http://localhost:9000/webhook-statuses?status=retrying"
```

Get details for a specific webhook delivery:

```bash
curl -X GET "http://localhost:9000/webhook-status/REFERENCE_ID_TASK_ID"
```

### Cleanup Operations

Manually trigger cleanup of old webhook statuses:

```bash
curl -X POST "http://localhost:9000/webhook-cleanup"
```

With filters:

```bash
curl -X POST "http://localhost:9000/webhook-cleanup?status=failed&older_than_days=3"
curl -X POST "http://localhost:9000/webhook-cleanup?reference_id=YOUR_REFERENCE_ID"
```

### Testing Webhooks

Test a webhook URL:

```bash
curl -X POST "http://localhost:9000/test-webhook?webhook_url=http://example.com/webhook"
```

With custom payload:

```bash
curl -X POST "http://localhost:9000/test-webhook" \
  -H "Content-Type: application/json" \
  -d '{"webhook_url": "http://example.com/webhook", "test_payload": {"key": "value"}}'
```

## Troubleshooting

### Common Issues

1. **Webhook tasks appear stuck in PENDING state**
   - Check if workers are running and consuming from the webhook_queue
   - Verify Redis connectivity
   - Check webhook logs for errors

2. **High failure rate for webhooks**
   - Check webhook receiver logs
   - Verify webhook URLs are valid and accessible
   - Check network connectivity

3. **Missing webhook statuses**
   - Verify Redis DB is correct (DB 1)
   - Check TTL settings

### Viewing Webhook Logs

```bash
curl -X GET "http://localhost:9000/webhook-logs?lines=50"
```

Or view the log file directly:

```bash
tail -f logs/webhooks/webhooks.log
```

### Checking Dead Letter Queue

The DLQ entries are stored in Redis with keys like `dead_letter:webhook:{webhook_id}`.

To list all DLQ entries:

```bash
redis-cli -n 1 keys "dead_letter:webhook:*"
```

To view a specific DLQ entry:

```bash
redis-cli -n 1 get "dead_letter:webhook:{webhook_id}"
```

## Metrics

The system exports Prometheus metrics on port 8000:

- `webhook_delivery_total{status, reference_id}` - Counter for webhook deliveries
- `webhook_delivery_seconds{reference_id}` - Histogram for webhook delivery duration

You can view these metrics at `http://localhost:8000/metrics`.

## Acceptance Criteria Verification

To verify the system meets the acceptance criteria:

1. **Queue/Worker**
   - Run `celery -A api inspect registered` to verify `firm.send_webhook_notification` is registered
   - Start a worker with `-Q firm_compliance_queue,webhook_queue` and verify it pulls webhook tasks

2. **Single Delivery Path**
   - Verify that claim processing only calls `send_webhook_notification.delay(...)` and not the async function

3. **Redis Status Model**
   - Verify status documents are written at `webhook_status:{reference_id}_{task_id}`
   - Verify timestamps are ISO 8601 UTC strings
   - Verify TTLs match: delivered=30m, others=7d
   - Verify `webhook_status:index:{reference_id}` contains the webhook_id

4. **Retries & DLQ**
   - Test with a simulated 5xx receiver to verify retries with backoff
   - Verify DLQ entry is created after final failure
   - Test with a 4xx response to verify at most one retry occurs

5. **Success Path**
   - Verify status becomes "delivered" with response_code and updated_at
   - Verify Prometheus metrics are incremented

6. **Headers & Correlation**
   - Verify outbound requests include X-Reference-ID and X-Correlation-ID
   - Verify logs contain the same correlation_id across attempts

7. **Admin & Cleanup**
   - Verify `/webhook-status/{webhook_id}` returns the persisted document
   - Verify `/webhook-statuses?reference_id={ref}` returns all deliveries for that reference
   - Verify `/webhook-cleanup` removes items according to filters