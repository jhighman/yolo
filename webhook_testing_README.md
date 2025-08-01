# Webhook Testing Tools

This directory contains tools for testing and debugging webhook functionality in the compliance reporting system.

## Background

We've been experiencing issues with webhook deliveries failing with 500 errors. Our investigation revealed two key issues:

1. **Webhook Retry Mechanism Issue**: The webhook retry mechanism wasn't properly handling non-200 responses. This has been fixed by modifying the `send_webhook_notification` function in `api.py`.

2. **Connection Refused Errors**: When testing webhook functionality, we discovered that the webhook receiver server needs to be running continuously to receive webhook deliveries from Celery workers.

## Tools

### 1. Webhook Receiver Server (`webhook_receiver_server.py`)

A standalone server that simulates a webhook endpoint. It can be configured to return different response codes to test how the system handles various scenarios.

#### Features:
- Listens for webhook requests on a specified port (default: 9001)
- Returns configurable response codes (default: 500)
- Logs all received webhooks with timestamps
- Saves webhook payloads to JSON files for analysis
- Provides a status endpoint for health checks

#### Usage:
```bash
python webhook_receiver_server.py [--port PORT] [--response-code CODE] [--log-file FILE]
```

#### Options:
- `--port PORT`: Port to listen on (default: 9001)
- `--response-code CODE`: HTTP response code to return (default: 500)
- `--log-file FILE`: Log file to write to (default: webhook_receiver.log)

### 2. Webhook Test Script (`test_webhook_failure.py`)

A test script that sends requests to the API with and without webhook URLs to isolate and reproduce webhook issues.

#### Features:
- Tests API functionality without webhooks to verify basic claim processing
- Tests webhook functionality by sending requests with webhook URLs
- Checks if the webhook receiver server is running before testing
- Provides detailed logging of test results

#### Usage:
```bash
python test_webhook_failure.py
```

## Testing Procedure

1. **Start the Webhook Receiver Server**:
   ```bash
   python webhook_receiver_server.py
   ```
   This will start the server on port 9001 and configure it to return 500 responses.

2. **Run the Test Script**:
   ```bash
   python test_webhook_failure.py
   ```
   This will:
   - Check if the webhook receiver server is running
   - Test the API without a webhook URL to verify basic functionality
   - Test the API with a webhook URL to reproduce the webhook failure

3. **Analyze the Results**:
   - Check the webhook receiver logs (`webhook_receiver.log`)
   - Examine the webhook payload files (`webhook_data_*.json`)
   - Review the API and Celery worker logs for webhook delivery attempts

## Root Cause Analysis

Our investigation revealed that the primary issue with webhook failures is a **timing problem**:

1. When testing with a short-lived webhook receiver (embedded in the test script), the server shuts down before the Celery worker can deliver the webhook, resulting in "Connection refused" errors.

2. In production, webhook endpoints may be temporarily unavailable or overloaded when the system attempts delivery, resulting in non-200 responses.

## Recommendations

1. **Use a Standalone Webhook Receiver**: Always use the standalone webhook receiver server for testing webhook functionality to ensure it remains available for webhook deliveries.

2. **Implement Webhook Payload Customization**: Add options to customize webhook payloads to meet specific endpoint requirements.

3. **Improve Error Handling**: Enhance error handling in webhook endpoints to better handle large or complex payloads.

4. **Add Webhook Monitoring**: Implement monitoring for webhook deliveries to track success rates and identify problematic endpoints.

5. **Consider Webhook Queuing**: Implement a dedicated queue for webhook deliveries to better manage retries and backpressure.