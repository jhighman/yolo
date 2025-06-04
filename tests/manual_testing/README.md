# Manual Testing Instructions

This folder contains examples and instructions for manually testing the Firm Compliance Claim Processing API.

## Prerequisites

- The API server must be running on `localhost:8000`
- `curl` command-line tool must be installed
- Basic understanding of REST APIs and JSON

## Test Files

This folder contains the following files:

- `README.md` - This file with testing instructions
- `curl_examples.sh` - Shell script with example curl commands
- `test_data.json` - JSON file with example test data that can be used for testing
- `run_all_tests.sh` - Script to automatically run all tests

## Starting the API Server

To start the API server, run the following command from the project root directory:

```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --log-level info
```

## Running the Tests

### Method 1: Using the curl_examples.sh Script

1. Make the script executable:
   ```bash
   chmod +x tests/manual_testing/curl_examples.sh
   ```

2. Run individual commands from the script by copying and pasting them into your terminal.

### Method 2: Manual Testing

The `curl_examples.sh` file contains example curl commands that you can copy and paste into your terminal to test different API endpoints.

### Method 3: Using test_data.json

The `test_data.json` file contains example JSON payloads that you can use for testing. You can:

1. Use the data directly in your curl commands:
   ```bash
   curl -X POST "http://localhost:8000/process-claim-basic" \
     -H "Content-Type: application/json" \
     -d "$(cat tests/manual_testing/test_data.json | jq '.[0]')"
   ```

2. Modify the data for your own test cases:
   ```bash
   # Extract the first test case to a temporary file
   jq '.[0]' tests/manual_testing/test_data.json > /tmp/test_case.json
   
   # Edit the file with your preferred editor
   nano /tmp/test_case.json
   
   # Use the modified data in your curl command
   curl -X POST "http://localhost:8000/process-claim-basic" \
     -H "Content-Type: application/json" \
     -d @/tmp/test_case.json
   ```

Note: These examples require the `jq` command-line JSON processor to be installed.

### Method 4: Using the Automated Test Script

The `run_all_tests.sh` script will automatically run all the tests and display the results:

1. Make the script executable (if not already):
   ```bash
   chmod +x tests/manual_testing/run_all_tests.sh
   ```

2. Run the script:
   ```bash
   ./tests/manual_testing/run_all_tests.sh
   ```

The script will:
- Check if the API server is running
- Run all the test cases
- Display the results with color-coded output
- Format the JSON responses using `jq` for better readability

Note: This script requires the `jq` command-line JSON processor to be installed.

## Test Cases

### 1. Process Claims with Basic Mode

These tests verify that the API can process claims with all the required fields and additional fields from the inbound data.

#### Example 1: Able Wealth Management, LLC

```bash
curl -X POST "http://localhost:8000/process-claim-basic" \
  -H "Content-Type: application/json" \
  -d '{
    "_id": {"$oid":"67bcdac22e749a352e23befe"},
    "type": "Thing/Other",
    "workProduct": "WP24-0037036",
    "entity": "EN-114236",
    "entityName": "Able Wealth Management, LLC",
    "name": "Able Wealth Management, LLC",
    "normalizedName": "ablewealthmanagementllc",
    "principal": "Able Wealth Management, LLC,",
    "street1": "695 Cross Street",
    "city": "Lakewood",
    "state": "New Jersey",
    "zip": "8701",
    "taxID": "",
    "organizationCRD": "298085",
    "status": "",
    "notes": "",
    "reference_id": "test-ref-001",
    "business_ref": "BIZ_001",
    "business_name": "Able Wealth Management, LLC",
    "tax_id": "123456789"
  }'
```

**Expected Result**: A JSON response containing the processed claim with all the original fields echoed back in the `claim` field.

### 2. Cache Management

These tests verify that the cache management endpoints are working correctly.

#### List Cache for a Business

```bash
curl -X GET "http://localhost:8000/cache/list?business_ref=BIZ_001"
```

**Expected Result**: A JSON response listing all cached files for the specified business.

#### Clear Cache for a Business

```bash
curl -X POST "http://localhost:8000/cache/clear/BIZ_001"
```

**Expected Result**: A JSON response confirming that the cache for the specified business has been cleared.

### 3. Compliance Report Retrieval

These tests verify that the compliance report retrieval endpoints are working correctly.

#### Get Latest Compliance Report

```bash
curl -X GET "http://localhost:8000/compliance/latest/BIZ_001"
```

**Expected Result**: A JSON response containing the latest compliance report for the specified business.

#### Get Compliance Report by Reference ID

```bash
curl -X GET "http://localhost:8000/compliance/by-ref/BIZ_001/test-ref-001"
```

**Expected Result**: A JSON response containing the compliance report with the specified reference ID for the specified business.

## Validation Checklist

For each test, verify the following:

1. The API returns a 200 OK status code for successful requests
2. The response contains the expected data structure
3. For claim processing, all fields from the request are echoed back in the response
4. Error cases return appropriate error messages and status codes

## Troubleshooting

- If you get a "Connection refused" error, make sure the API server is running
- If you get a 404 Not Found error, check that you're using the correct endpoint URL
- If you get a 500 Internal Server Error, check the API server logs for more details