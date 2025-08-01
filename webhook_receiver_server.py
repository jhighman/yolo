#!/usr/bin/env python3
"""
Standalone webhook receiver server for testing webhook deliveries.

This server listens for webhook requests and simulates different responses
based on configuration. It can be run independently of test scripts to ensure
it remains available for webhook deliveries from Celery workers.

Usage:
    python webhook_receiver_server.py [--port PORT] [--response-code CODE]

Options:
    --port PORT           Port to listen on (default: 9001)
    --response-code CODE  HTTP response code to return (default: 500)
    --log-file FILE       Log file to write to (default: webhook_receiver.log)
"""

import argparse
import json
import logging
import signal
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("webhook_receiver.log")
    ]
)
logger = logging.getLogger("webhook_receiver")

# Global variables
received_webhooks = []
server = None
response_code = 500  # Default response code
server_start_time = 0  # Will be set when server starts


class WebhookHandler(BaseHTTPRequestHandler):
    """HTTP request handler for webhook receiver."""

    def log_request(self, code='-', size='-'):
        """Override to use our logger."""
        logger.info(f"Request: {self.command} {self.path} {code} {size}")

    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.info(format % args)
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/status":
            logger.info("Received status check request")
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            status_response = {
                "status": "running",
                "received_webhooks": len(received_webhooks),
                "uptime": time.time() - server_start_time
            }
            self.wfile.write(json.dumps(status_response).encode('utf-8'))
            logger.info(f"Sent status response: {json.dumps(status_response)}")
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode('utf-8'))

    def do_POST(self):
        """Handle POST requests."""
        global received_webhooks

        logger.info(f"Received POST request to {self.path}")
        logger.info(f"Headers: {self.headers}")

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        # Parse and log the received data
        try:
            data = json.loads(post_data.decode('utf-8'))
            logger.info(f"Received webhook data: {json.dumps(data, indent=2)}")
            
            # Store the received webhook
            received_webhooks.append({
                'timestamp': time.time(),
                'path': self.path,
                'headers': dict(self.headers),
                'data': data
            })
            
            # Write to a file for later analysis
            with open(f"webhook_data_{len(received_webhooks)}.json", "w") as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved webhook data to webhook_data_{len(received_webhooks)}.json")
        except json.JSONDecodeError:
            logger.warning(f"Received non-JSON data: {post_data.decode('utf-8')}")
            received_webhooks.append({
                'timestamp': time.time(),
                'path': self.path,
                'headers': dict(self.headers),
                'data': post_data.decode('utf-8')
            })

        # Send the configured response
        logger.info(f"Sending {response_code} response")
        self.send_response(response_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        # Send the error message
        error_response = {"message": "Internal error!!"}
        self.wfile.write(json.dumps(error_response).encode('utf-8'))
        logger.info(f"Sent error response: {json.dumps(error_response)}")


def signal_handler(sig, frame):
    """Handle Ctrl+C to gracefully shut down the server."""
    logger.info("Shutting down webhook receiver server...")
    if server:
        server.shutdown()
    logger.info(f"Received {len(received_webhooks)} webhooks during this session")
    sys.exit(0)


def main():
    """Main function to run the webhook receiver server."""
    global server, response_code, server_start_time
    
    # Set server start time
    server_start_time = time.time()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Webhook receiver server for testing")
    parser.add_argument("--port", type=int, default=9001, help="Port to listen on")
    parser.add_argument("--response-code", type=int, default=500, help="HTTP response code to return")
    parser.add_argument("--log-file", type=str, default="webhook_receiver.log", help="Log file to write to")
    args = parser.parse_args()
    
    # Update global variables
    response_code = args.response_code
    
    # Add file handler with the specified log file
    file_handler = logging.FileHandler(args.log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start the server
    server_address = ('localhost', args.port)
    server = HTTPServer(server_address, WebhookHandler)
    logger.info(f"Starting webhook receiver server on http://localhost:{args.port}")
    logger.info(f"Configured to return {response_code} response code")
    logger.info("Press Ctrl+C to stop the server")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        logger.info("Server stopped")


if __name__ == "__main__":
    main()