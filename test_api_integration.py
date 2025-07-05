import unittest
import asyncio
import time
from fastapi.testclient import TestClient
import json
import logging
from api import app

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
        
    async def check_task_status_until_complete(self, task_id, max_wait_time=300, check_interval=2):
        """
        Check the status of a task until it completes or fails, or until max_wait_time is reached.
        Logs state changes and keeps track of the number of checks.
        
        Args:
            task_id: The ID of the task to check
            max_wait_time: Maximum time to wait in seconds
            check_interval: Time between status checks in seconds
            
        Returns:
            The final task status response
        """
        logger.info(f"Starting status checks for task {task_id}")
        start_time = time.time()
        last_status = None
        check_count = 0
        
        while time.time() - start_time < max_wait_time:
            check_count += 1
            response = self.client.get(f"/task-status/{task_id}")
            self.assertEqual(response.status_code, 200)
            
            status_data = response.json()
            current_status = status_data["status"]
            
            # Log status changes
            if current_status != last_status:
                logger.info(f"Task {task_id} status changed to: {current_status} (check #{check_count})")
                logger.info(f"Status details: {json.dumps(status_data, indent=2)}")
                last_status = current_status
            else:
                logger.info(f"Task {task_id} status still: {current_status} (check #{check_count})")
            
            # If task is completed or failed, return the status
            if current_status in ["COMPLETED", "FAILED"]:
                elapsed = time.time() - start_time
                logger.info(f"Task {task_id} reached final state: {current_status} after {elapsed:.2f} seconds and {check_count} checks")
                return status_data
            
            # Wait before checking again
            await asyncio.sleep(check_interval)
        
        # If we get here, we've timed out
        logger.error(f"Timed out waiting for task {task_id} to complete after {max_wait_time} seconds and {check_count} checks")
        response = self.client.get(f"/task-status/{task_id}")
        return response.json()
    
    async def async_test_sequential_processing(self):
        """
        Test sending three requests to the API in succession and measure the end-to-end time.
        Also check the status of the third request to observe state changes.
        """
        # Define the three test requests
        requests = [
            {
                "organization_crd": "8361",
                "business_ref": "Integration Test One",
                "reference_id": "IT01",
                "webhook_url": "https://webhook.site/integration-test-1"
            },
            {
                "organization_crd": "131940",
                "business_ref": "Integration Test Two",
                "reference_id": "IT02",
                "webhook_url": "https://webhook.site/integration-test-2"
            },
            {
                "organization_crd": "315604",
                "business_ref": "Integration Test Three",
                "reference_id": "IT03",
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
            
            self.assertEqual(response_data["status"], "processing_queued")
            self.assertEqual(response_data["reference_id"], req["reference_id"])
            self.assertIn("task_id", response_data)
            
            task_ids.append(response_data["task_id"])
            
            # Small delay to ensure FIFO order
            await asyncio.sleep(0.1)
        
        # Check the status of all three tasks
        logger.info(f"All three requests sent. Monitoring status of all tasks...")
        
        # First, check the status of the first task a few times to see what's happening
        logger.info(f"Checking status of first task: {task_ids[0]}")
        for i in range(3):
            response = self.client.get(f"/task-status/{task_ids[0]}")
            status_data = response.json()
            logger.info(f"First task status check {i+1}: {json.dumps(status_data, indent=2)}")
            await asyncio.sleep(2)
        
        # Now monitor the third task until completion
        logger.info(f"Now monitoring the third task until completion: {task_ids[2]}")
        final_status = await self.check_task_status_until_complete(task_ids[2])
        
        # Verify the final status
        self.assertEqual(final_status["status"], "COMPLETED")
        self.assertEqual(final_status["reference_id"], "IT03")
        self.assertIsNotNone(final_status["result"])
        
        # Check the status of the first two tasks as well
        for i, task_id in enumerate(task_ids[:2], 1):
            response = self.client.get(f"/task-status/{task_id}")
            self.assertEqual(response.status_code, 200)
            status_data = response.json()
            logger.info(f"Final status of task {i}: {json.dumps(status_data, indent=2)}")
            self.assertEqual(status_data["status"], "COMPLETED")
        
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