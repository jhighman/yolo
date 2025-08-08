#!/usr/bin/env python3
"""
Test script for webhook reliability implementation.

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

def test_webhook_delivery():
    """Test the webhook functionality with the new reliability implementation."""
    # API endpoint
    url = "http://localhost:9000/process-claim-basic"
    
    # Payload from the error logs
    payload = {
        "reference_id": "SP826561222312211_EBI-B8231735EED347D",
        "organization_crd": "157379",
        "business_name": None,
        "business_ref": "EN-202508011958-12",
        "webhook_url": "http://localhost:9001/webhook-receiver",  # Local webhook receiver for testing
        "test_id": f"test-{int(time.time())}"  # Add a unique test ID
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
        
        # Extract task_id from response for status checking
        try:
            response_data = response.json()
            task_id = response_data.get("task_id")
            if task_id:
                logger.info(f"Task ID: {task_id}")
                # Check webhook status
                time.sleep(2)  # Wait a bit for the task to start
                check_webhook_status(payload["reference_id"], task_id)
        except Exception as e:
            logger.error(f"Error parsing response: {str(e)}")
        
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

def check_webhook_status(reference_id, task_id=None):
    """Check the status of a webhook delivery."""
    webhook_id = f"{reference_id}_{task_id}" if task_id else reference_id
    
    try:
        # First try with webhook_id (new format)
        url = f"http://localhost:9000/webhook-status/{webhook_id}"
        response = requests.get(url)
        
        if response.status_code == 404 and task_id:
            # Try with just reference_id (old format)
            url = f"http://localhost:9000/webhook-status/{reference_id}"
            response = requests.get(url)
        
        if response.status_code == 200:
            status_data = response.json()
            logger.info(f"Webhook status: {json.dumps(status_data, indent=2)}")
            return status_data
        else:
            logger.warning(f"Failed to get webhook status: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error checking webhook status: {str(e)}")
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
        # First test: without webhook
        logger.info("=== TESTING WITHOUT WEBHOOK ===")
        response_no_webhook = test_without_webhook()
        
        if response_no_webhook and response_no_webhook.status_code == 200:
            logger.info("Request without webhook was successful. This confirms the API can process the claim correctly.")
        else:
            logger.error("Request without webhook failed. This suggests the issue is with claim processing, not webhook delivery.")
        
        # Wait a bit before the next test
        time.sleep(5)
        
        # Second test: with webhook to test the new reliability implementation
        logger.info("\n=== TESTING WITH WEBHOOK ===")
        response = test_webhook_delivery()
        
        if response and response.status_code == 200:
            logger.info("Request to API was successful. Check the API logs for webhook delivery status.")
            
            # Extract reference_id and task_id from response
            try:
                response_data = response.json()
                reference_id = response_data.get("reference_id")
                task_id = response_data.get("task_id")
                
                if reference_id and task_id:
                    # Wait for webhook to be processed (up to 60 seconds)
                    logger.info("Waiting for webhook to be processed (timeout: 60 seconds)...")
                    
                    # Wait in smaller increments and check status
                    for i in range(12):  # 12 x 5 seconds = 60 seconds
                        time.sleep(5)
                        status_data = check_webhook_status(reference_id, task_id)
                        
                        if status_data:
                            status = status_data.get("status")
                            if status in ["delivered", "failed"]:
                                logger.info(f"Webhook delivery completed with status: {status}")
                                break
                            else:
                                logger.info(f"Webhook status: {status} (waiting for completion)")
                        else:
                            logger.info(f"Still waiting for webhook... ({(i+1)*5}/60 seconds)")
                    
                    # Final status check
                    final_status = check_webhook_status(reference_id, task_id)
                    if final_status:
                        logger.info(f"Final webhook status: {final_status.get('status')}")
                        if final_status.get("status") == "delivered":
                            logger.info("Webhook delivery was successful!")
                        else:
                            logger.warning(f"Webhook delivery ended with status: {final_status.get('status')}")
                            logger.warning(f"Error: {final_status.get('error')}")
                    else:
                        logger.warning("Could not determine final webhook status")
                else:
                    logger.warning("Could not extract reference_id or task_id from response")
            except Exception as e:
                logger.error(f"Error checking webhook status: {str(e)}")
            
            logger.info("Check webhook_receiver.log and webhook_data_*.json files for received webhooks.")
        else:
            logger.error("Request to API failed.")
    
    except KeyboardInterrupt:
        logger.info("Test interrupted by user.")

if __name__ == "__main__":
    main()