#!/usr/bin/env python3
"""
Test script to reproduce webhook failure issue.

This script tests the webhook functionality by sending requests to the API
with and without a webhook URL. It requires the webhook_receiver_server.py
to be running in a separate terminal.

Usage:
    1. Start the webhook receiver server in a separate terminal:
       python webhook_receiver_server.py
    
    2. Run this test script:
       python test_webhook_failure.py
"""

import requests
import json
import logging
import sys
import time
import subprocess
import os
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent))

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_webhook_failure():
    """Test the webhook functionality to reproduce the failure."""
    # API endpoint
    url = "http://localhost:9000/process-claim-basic"
    
    # Payload from the error logs
    payload = {
        "reference_id": "SP826561222312211_EBI-B8231735EED347D",
        "organization_crd": "157379",
        "business_name": None,
        "business_ref": "EN-202508011958-12",
        "webhook_url": "http://localhost:9001/webhook-receiver"  # Local webhook receiver for testing
    }
    
    # Headers
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        # Send the request
        logger.info(f"Sending request to {url} with payload: {payload}")
        response = requests.post(url, json=payload, headers=headers)
        
        # Log the response
        logger.info(f"Response status code: {response.status_code}")
        logger.info(f"Response body: {response.text}")
        
        return response
    except Exception as e:
        logger.error(f"Error sending request: {str(e)}")
        return None

def test_without_webhook():
    """Test the API without webhook callback to isolate the issue."""
    # API endpoint
    url = "http://localhost:9000/process-claim-basic"
    
    # Same payload but without webhook_url
    payload = {
        "reference_id": "SP826561222312211_EBI-B8231735EED347D_NOWH",
        "organization_crd": "157379",
        "business_name": None,
        "business_ref": "EN-202508011958-12"
        # No webhook_url means synchronous processing
    }
    
    # Headers
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        # Send the request
        logger.info(f"Testing without webhook - Sending request to {url} with payload: {payload}")
        response = requests.post(url, json=payload, headers=headers)
        
        # Log the response
        logger.info(f"Response status code: {response.status_code}")
        logger.info(f"Response body: {response.text[:500]}...")  # Log first 500 chars to avoid huge output
        
        # Check if the response contains a valid compliance report
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Received valid compliance report with reference_id: {data.get('reference_id')}")
            logger.info(f"Report contains {len(json.dumps(data))} bytes")
            
            # Check for key sections that might cause issues
            for section in ['entity', 'search_evaluation', 'status_evaluation', 'final_evaluation']:
                if section in data:
                    logger.info(f"Section '{section}' is present in the report")
                else:
                    logger.warning(f"Section '{section}' is missing from the report")
        
        return response
    except Exception as e:
        logger.error(f"Error sending request: {str(e)}")
        return None

def check_webhook_receiver_running():
    """Check if the webhook receiver server is running."""
    try:
        response = requests.get("http://localhost:9001/status", timeout=1)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def ensure_webhook_receiver_running():
    """Ensure the webhook receiver server is running."""
    if check_webhook_receiver_running():
        logger.info("Webhook receiver server is already running")
        return True
    
    logger.warning("Webhook receiver server is not running")
    logger.info("Please start the webhook receiver server in a separate terminal:")
    logger.info("python webhook_receiver_server.py")
    
    # Ask the user if they want to continue
    response = input("Do you want to continue anyway? (y/n): ")
    if response.lower() != 'y':
        logger.info("Exiting test script")
        return False
    
    return True

def main():
    """Main function to run the test."""
    # Ensure the webhook receiver server is running
    if not ensure_webhook_receiver_running():
        return
    
    try:
        # First test: without webhook to isolate the issue
        logger.info("=== TESTING WITHOUT WEBHOOK ===")
        response_no_webhook = test_without_webhook()
        
        if response_no_webhook and response_no_webhook.status_code == 200:
            logger.info("Request without webhook was successful. This confirms the API can process the claim correctly.")
            logger.info("The issue is likely with the webhook delivery mechanism, not with the payload generation.")
        else:
            logger.error("Request without webhook failed. This suggests the issue is with claim processing, not webhook delivery.")
        
        # Wait a bit before the next test
        time.sleep(5)
        
        # Second test: with webhook to reproduce the failure
        logger.info("\n=== TESTING WITH WEBHOOK ===")
        response = test_webhook_failure()
        
        if response and response.status_code == 200:
            logger.info("Request to API was successful. Check the API logs for webhook delivery status.")
            
            # Wait for webhook to be received (up to 60 seconds)
            logger.info("Waiting for webhook to be received (timeout: 60 seconds)...")
            
            # Wait in smaller increments and log progress
            for i in range(12):  # 12 x 5 seconds = 60 seconds
                time.sleep(5)
                logger.info(f"Still waiting for webhook... ({(i+1)*5}/60 seconds)")
            
            logger.info("Webhook wait time expired.")
            logger.info("Check webhook_receiver.log and webhook_data_*.json files for received webhooks.")
            logger.info("Check the API logs for webhook retry status.")
        else:
            logger.error("Request to API failed.")
    
    except KeyboardInterrupt:
        logger.info("Test interrupted by user.")

if __name__ == "__main__":
    main()