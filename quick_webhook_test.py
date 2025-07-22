#!/usr/bin/env python3
"""
Quick Webhook Test for Firm Compliance API

This script provides a simple way to test the webhook functionality by:
1. Starting a local HTTP server to receive webhooks
2. Using the /test-webhook endpoint to send a test webhook
3. Verifying the webhook is received

Usage:
    python quick_webhook_test.py
"""

import http.server
import json
import threading
import socketserver
import requests
import sys
import time

# Configuration
API_URL = "http://localhost:9000"
WEBHOOK_PORT = 8000
WEBHOOK_URL = f"http://localhost:{WEBHOOK_PORT}/webhook"

# Flag to track if webhook was received
webhook_received = False

class WebhookHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        global webhook_received
        
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            webhook_data = json.loads(post_data.decode('utf-8'))
            print("\n✅ Webhook received!")
            print(f"Data: {json.dumps(webhook_data, indent=2)}")
            
            # Mark that we received the webhook
            webhook_received = True
            
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

def main():
    # Start webhook server
    print(f"🔌 Starting webhook receiver on port {WEBHOOK_PORT}")
    server = socketserver.TCPServer(("", WEBHOOK_PORT), WebhookHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    try:
        # Test the webhook endpoint
        print(f"🔍 Testing webhook endpoint with URL: {WEBHOOK_URL}")
        response = requests.post(
            f"{API_URL}/test-webhook",
            params={"webhook_url": WEBHOOK_URL}
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {json.dumps(response.json(), indent=2)}")
        
        # Wait for webhook (with timeout)
        print("\n⏳ Waiting for webhook (timeout: 10s)...")
        timeout = time.time() + 10
        while not webhook_received and time.time() < timeout:
            time.sleep(0.5)
        
        if webhook_received:
            print("\n✅ Webhook test successful! The webhook was received.")
        else:
            print("\n❌ Webhook test failed: No webhook received within timeout period")
            print("\nCheck the webhook logs for errors:")
            print(f"  curl {API_URL}/webhook-logs")
            
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        
    finally:
        # Shutdown the server
        print("\n🛑 Shutting down webhook server")
        server.shutdown()
        server.server_close()

if __name__ == "__main__":
    main()