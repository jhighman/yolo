#!/usr/bin/env python3
"""
Webhook Testing Script for Firm Compliance API

This script tests the webhook functionality of the Firm Compliance API by:
1. Starting a local HTTP server to act as a webhook receiver
2. Making a request to the API with the webhook URL pointing to our local server
3. Verifying that the webhook is received correctly

Usage:
    python test_webhook.py

Requirements:
    - requests
    - The API server must be running on localhost:9000
"""

import http.server
import json
import threading
import time
import socketserver
import requests
import uuid
import argparse
from typing import Dict, Any, List, Optional

# Configuration
DEFAULT_API_URL = "http://localhost:9000"
DEFAULT_WEBHOOK_PORT = 8000
DEFAULT_TEST_MODE = "test"  # Options: test, basic, extended, complete

# Global variables to store received webhooks
received_webhooks: List[Dict[str, Any]] = []
webhook_received_event = threading.Event()

class WebhookHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for receiving webhooks."""
    
    def do_POST(self):
        """Handle POST requests (webhooks)."""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            webhook_data = json.loads(post_data.decode('utf-8'))
            print("\n✅ Webhook received!")
            print(f"Path: {self.path}")
            print(f"Headers: {self.headers}")
            print(f"Data: {json.dumps(webhook_data, indent=2)}")
            
            # Store the webhook data
            received_webhooks.append(webhook_data)
            
            # Signal that we received a webhook
            webhook_received_event.set()
            
            # Send a 200 OK response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
        
        except Exception as e:
            print(f"❌ Error processing webhook: {str(e)}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Override to suppress HTTP server logs."""
        return

def start_webhook_server(port: int) -> socketserver.TCPServer:
    """Start a webhook receiver server on the specified port."""
    server = socketserver.TCPServer(("", port), WebhookHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    return server

def test_webhook_endpoint(api_url: str, webhook_url: str) -> Dict[str, Any]:
    """Test the /test-webhook endpoint."""
    print(f"\n🔍 Testing webhook endpoint with URL: {webhook_url}")
    response = requests.post(
        f"{api_url}/test-webhook",
        params={"webhook_url": webhook_url}
    )
    print(f"Response status: {response.status_code}")
    print(f"Response body: {json.dumps(response.json(), indent=2)}")
    return response.json()

def test_process_claim(api_url: str, webhook_url: str, mode: str) -> Dict[str, Any]:
    """Test the process-claim endpoint with the specified mode."""
    # Generate a unique reference ID
    reference_id = f"TEST-{uuid.uuid4()}"
    business_ref = f"EN-{uuid.uuid4().hex[:6].upper()}"
    
    print(f"\n🔍 Testing process-claim-{mode} endpoint")
    print(f"Reference ID: {reference_id}")
    print(f"Business Ref: {business_ref}")
    print(f"Webhook URL: {webhook_url}")
    
    # Prepare the request payload
    payload = {
        "reference_id": reference_id,
        "business_ref": business_ref,
        "business_name": "Test Company LLC",
        "organization_crd": "123456",
        "webhook_url": webhook_url
    }
    
    # Make the request
    response = requests.post(
        f"{api_url}/process-claim-{mode}",
        json=payload
    )
    
    print(f"Response status: {response.status_code}")
    print(f"Response body: {json.dumps(response.json(), indent=2)}")
    
    return response.json()

def check_webhook_logs(api_url: str) -> Dict[str, Any]:
    """Check the webhook logs endpoint."""
    print("\n🔍 Checking webhook logs")
    response = requests.get(f"{api_url}/webhook-logs")
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 200:
        logs = response.json()
        if "logs" in logs and logs["logs"]:
            print(f"Found {len(logs['logs'])} log entries")
            for log in logs["logs"][-5:]:  # Show last 5 logs
                print(f"  {log.strip()}")
        else:
            print("No webhook logs found")
    else:
        print(f"Error retrieving logs: {response.text}")
    
    return response.json()

def wait_for_webhook(timeout: int = 30) -> bool:
    """Wait for a webhook to be received."""
    print(f"\n⏳ Waiting for webhook (timeout: {timeout}s)...")
    return webhook_received_event.wait(timeout)

def main():
    """Main function to run the webhook test."""
    parser = argparse.ArgumentParser(description="Test webhook functionality of the Firm Compliance API")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help=f"API URL (default: {DEFAULT_API_URL})")
    parser.add_argument("--webhook-port", type=int, default=DEFAULT_WEBHOOK_PORT, help=f"Port for webhook server (default: {DEFAULT_WEBHOOK_PORT})")
    parser.add_argument("--mode", default=DEFAULT_TEST_MODE, choices=["test", "basic", "extended", "complete"], 
                        help=f"Test mode (default: {DEFAULT_TEST_MODE})")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds for webhook receipt (default: 30)")
    
    args = parser.parse_args()
    
    # Start the webhook server
    webhook_port = args.webhook_port
    webhook_url = f"http://localhost:{webhook_port}/webhook"
    
    print(f"🚀 Starting webhook test with API URL: {args.api_url}")
    print(f"🔌 Starting webhook receiver on port {webhook_port}")
    
    server = start_webhook_server(webhook_port)
    
    try:
        # Test the appropriate endpoint based on mode
        if args.mode == "test":
            test_webhook_endpoint(args.api_url, webhook_url)
        else:
            test_process_claim(args.api_url, webhook_url, args.mode)
        
        # Wait for the webhook
        webhook_received = wait_for_webhook(args.timeout)
        
        if webhook_received:
            print("\n✅ Webhook test successful!")
            print(f"Received {len(received_webhooks)} webhooks")
            
            # Display the last received webhook
            if received_webhooks:
                print("\nLast webhook data:")
                print(json.dumps(received_webhooks[-1], indent=2))
        else:
            print("\n❌ Webhook test failed: No webhook received within timeout period")
            
            # Check webhook logs to see if there were any errors
            check_webhook_logs(args.api_url)
            
            print("\nPossible issues:")
            print("1. The API server might not be running")
            print("2. The webhook URL might not be reachable from the API server")
            print("3. There might be an error in the webhook sending logic")
            print("4. The webhook might be taking longer than the timeout period")
            
    finally:
        # Shutdown the server
        print("\n🛑 Shutting down webhook server")
        server.shutdown()
        server.server_close()

if __name__ == "__main__":
    main()