import unittest
import asyncio
import time
from fastapi.testclient import TestClient
import json
import logging
from services.firm_business_api import app  # Import from firm_business_api instead of api

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class TestAPIIntegration(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.start_time = time.time()
        logger.info("=== Starting Integration Test ===")
        
    def tearDown(self):
        end_time = time.time()
        total_time = end_time - self.start_time
        logger.info(f"=== Integration Test Completed ===")
        logger.info(f"Total execution time: {total_time:.2f} seconds")
        
    # The check_task_status_until_complete method is no longer needed since the new API
    # processes requests synchronously and doesn't use task IDs
    
    async def async_test_sequential_processing(self):
        """
        Test sending three requests to the API in succession and measure the end-to-end time.
        Verify that each request returns a valid compliance report.
        """
        # Define the three test requests
        requests = [
            {
                "crdNumber": "8361",
                "referenceId": "IT01",
                "entityName": "ALLIANCE GLOBAL PARTNERS",
                "webhook_url": "https://webhook.site/integration-test-1"
            },
            {
                "crdNumber": "131940",
                "referenceId": "IT02",
                "entityName": "MORGAN STANLEY SMITH BARNEY",
                "webhook_url": "https://webhook.site/integration-test-2"
            },
            {
                "crdNumber": "315604",
                "referenceId": "IT03",
                "entityName": "ROBINHOOD FINANCIAL LLC",
                "webhook_url": "https://webhook.site/integration-test-3"
            }
        ]
        
        # Send the three requests in succession
        task_ids = []
        for i, req in enumerate(requests, 1):
            logger.info(f"Sending request {i}: {json.dumps(req, indent=2)}")
            response = self.client.post("/process-claim-basic", json=req)
            self.assertEqual(response.status_code, 200)
            
            response_data = response.json()
            logger.info(f"Response for request {i}: {json.dumps(response_data, indent=2)}")
            
            # Check that the response contains the expected fields for a report
            self.assertIn("claim", response_data)
            self.assertEqual(response_data["claim"]["referenceId"], req["referenceId"])
            self.assertIn("final_evaluation", response_data)
            
            # Store the reference ID for later checks
            task_ids.append(req["referenceId"])
            
            # Small delay to ensure FIFO order
            await asyncio.sleep(0.1)
        
        # Since the new API processes requests synchronously and returns the report directly,
        # we don't need to check for the report separately
        logger.info(f"All three requests processed successfully")
        
        # The firm_business_api.py doesn't have endpoints for retrieving compliance reports,
        # so we just verify that the initial requests were successful and returned the expected data
        
        # Calculate and log the total processing time
        end_time = time.time()
        total_time = end_time - self.start_time
        logger.info(f"End-to-end processing time for all three requests: {total_time:.2f} seconds")
        
        return total_time
    
    def test_sequential_processing(self):
        """Run the async test using asyncio.run"""
        try:
            total_time = asyncio.run(self.async_test_sequential_processing())
            logger.info(f"Test completed successfully. Total time: {total_time:.2f} seconds")
        except KeyboardInterrupt:
            logger.info("Test was interrupted by user")
        except Exception as e:
            logger.error(f"Test failed with error: {str(e)}")
            raise

if __name__ == "__main__":
    unittest.main()