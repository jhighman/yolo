import unittest
import asyncio
import threading
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from celery import Celery
import time
import json
from datetime import datetime
from api import app, process_firm_compliance_claim, PROCESSING_MODES, facade, AsyncResult
from services.firm_business import process_claim

# Setup test Celery app with in-memory Redis
celery_app = Celery(
    "test_firm_compliance_tasks",
    broker="redis://localhost:6379/0",  # Will be mocked
    backend="redis://localhost:6379/0",
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    task_time_limit=3600,
    task_concurrency=1,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_default_queue="firm_compliance_queue",
)

# MockRedis class (unchanged from original)
class MockRedis:
    def __init__(self, *args, **kwargs):
        self.data = {}
        self.sets = {}
        self.lists = {}
        self.connection_pool = kwargs.get('connection_pool', None)
    
    def ping(self):
        return True
    
    def get(self, key):
        return self.data.get(key)
    
    def set(self, key, value, **kwargs):
        self.data[key] = value
        return True
    
    def delete(self, *keys):
        count = 0
        for key in keys:
            if key in self.data:
                del self.data[key]
                count += 1
            if key in self.sets:
                del self.sets[key]
                count += 1
            if key in self.lists:
                del self.lists[key]
                count += 1
        return count
    
    def exists(self, key):
        return key in self.data or key in self.sets or key in self.lists
    
    def keys(self, pattern='*'):
        all_keys = list(self.data.keys()) + list(self.sets.keys()) + list(self.lists.keys())
        return list(set(all_keys))
    
    def flushdb(self):
        self.data = {}
        self.sets = {}
        self.lists = {}
        return True
    
    def pipeline(self):
        return MockRedisPipeline(self)
    
    def lpush(self, key, *values):
        if key not in self.lists:
            self.lists[key] = []
        self.lists[key] = list(values) + self.lists.get(key, [])
        return len(self.lists[key])
    
    def rpush(self, key, *values):
        if key not in self.lists:
            self.lists[key] = []
        self.lists[key].extend(values)
        return len(self.lists[key])
    
    def rpop(self, key):
        if key not in self.lists or not self.lists[key]:
            return None
        return self.lists[key].pop()
    
    def lpop(self, key):
        if key not in self.lists or not self.lists[key]:
            return None
        return self.lists[key].pop(0)
    
    def llen(self, key):
        if key not in self.lists:
            return 0
        return len(self.lists[key])
    
    def lrange(self, key, start, end):
        if key not in self.lists:
            return []
        return self.lists[key][start:end if end != -1 else None]
    
    def sadd(self, key, *values):
        if key not in self.sets:
            self.sets[key] = set()
        old_size = len(self.sets[key])
        self.sets[key].update(values)
        return len(self.sets[key]) - old_size
    
    def srem(self, key, *values):
        if key not in self.sets:
            return 0
        count = 0
        for value in values:
            if value in self.sets[key]:
                self.sets[key].remove(value)
                count += 1
        return count
    
    def smembers(self, key):
        if key not in self.sets:
            return set()
        return self.sets[key]
    
    def sismember(self, key, value):
        if key not in self.sets:
            return False
        return value in self.sets[key]
    
    def scard(self, key):
        if key not in self.sets:
            return 0
        return len(self.sets[key])
    
    def hset(self, key, field, value):
        if key not in self.data:
            self.data[key] = {}
        is_new = field not in self.data[key]
        self.data[key][field] = value
        return 1 if is_new else 0
    
    def hget(self, key, field):
        if key not in self.data or field not in self.data[key]:
            return None
        return self.data[key][field]
    
    def hdel(self, key, *fields):
        if key not in self.data:
            return 0
        count = 0
        for field in fields:
            if field in self.data[key]:
                del self.data[key][field]
                count += 1
        return count
    
    def hgetall(self, key):
        if key not in self.data:
            return {}
        return self.data[key]
    
    def hincrby(self, key, field, increment=1):
        if key not in self.data:
            self.data[key] = {}
        if field not in self.data[key]:
            self.data[key][field] = 0
        self.data[key][field] += increment
        return self.data[key][field]
    
    def expire(self, key, seconds):
        return 1 if key in self.data or key in self.sets or key in self.lists else 0
    
    def ttl(self, key):
        return 1000 if key in self.data or key in self.sets or key in self.lists else -2

class MockRedisPipeline:
    def __init__(self, redis_instance):
        self.redis = redis_instance
        self.commands = []
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.commands = []
    
    def llen(self, key):
        self.commands.append(('llen', key))
        return self
    
    def sadd(self, key, *values):
        self.commands.append(('sadd', key, values))
        return self
    
    def execute(self):
        results = []
        for cmd, *args in self.commands:
            if cmd == 'llen':
                results.append(self.redis.llen(args[0]))
            elif cmd == 'sadd':
                results.append(self.redis.sadd(args[0], *args[1]))
        return results

class TestConcurrency(unittest.TestCase):
    def setUp(self):
        # Initialize FastAPI test client
        self.client = TestClient(app)
        
        # Mock Redis connections
        self.redis_patch = patch("redis.Redis", new=MockRedis)
        self.redis_patch.start()
        
        # Mock process_firm_compliance_claim and process_claim
        self.process_compliance_claim_patch = patch("api.process_firm_compliance_claim.delay")
        self.mock_process_compliance_claim = self.process_compliance_claim_patch.start()
        
        self.process_claim_patch = patch("services.firm_business.process_claim")
        self.mock_process_claim = self.process_claim_patch.start()
        
        self.api_process_claim_patch = patch("api.process_claim")
        self.api_mock_process_claim = self.api_process_claim_patch.start()
        
        # Mock global facade
        self.global_facade_patch = patch("api.facade")
        self.mock_global_facade = self.global_facade_patch.start()
        mock_facade = MagicMock()
        
        # Mock facade methods for firm compliance
        mock_sec_result = MagicMock()
        mock_sec_result.get.side_effect = lambda key, default=None: "Test Firm" if key == "strip" else default
        
        mock_financial_result = MagicMock()
        mock_financial_result.get.side_effect = lambda key, default=None: "Test Firm" if key == "strip" else default
        
        mock_facade.search_sec_iapd_firm.return_value = mock_sec_result
        mock_facade.search_financial_records.return_value = mock_financial_result
        mock_facade.save_compliance_report.return_value = True
        
        self.mock_global_facade.return_value = mock_facade
        
        self.task_timestamps = []
        self.processed_tasks = []
        self.task_exceptions = []
        self.webhook_calls = []
        self.retry_counts = {}
        
        # Mock aiohttp for webhook calls
        self.aiohttp_patch = patch("aiohttp.ClientSession.post", new_callable=AsyncMock)
        self.mock_aiohttp_post = self.aiohttp_patch.start()
        
        async def mock_post_side_effect(url, json=None):
            print(f"Mock webhook call to URL: {url}")
            self.webhook_calls.append((url, json))
            if "fail" in url:
                raise ConnectionError("Simulated webhook delivery failure")
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value="OK")
            return mock_response
            
        self.mock_aiohttp_post.side_effect = mock_post_side_effect
        
        self.task_queue = []
        self.task_lock = threading.Lock()
        
        def mock_celery_task(*args, **kwargs):
            print(f"Mock Celery task called with args: {args}")
            
            if len(args) > 0 and isinstance(args[0], dict) and "reference_id" in args[0]:
                reference_id = args[0]["reference_id"]
                request_data = args[0]
                
                with self.task_lock:
                    self.task_queue.append((reference_id, request_data))
                
                if reference_id == "REF_FAIL":
                    retry_count = self.retry_counts.get(reference_id, 0)
                    self.retry_counts[reference_id] = retry_count + 1
                    if retry_count == 0:
                        error = ValueError(f"Simulated failure in Celery task (attempt 1)")
                        self.task_exceptions.append(error)
            
            task_mock = MagicMock()
            task_mock.id = f"mock-task-id-{len(self.task_queue)}"
            
            if len(self.task_queue) == 1:
                thread = threading.Thread(target=self._process_task_queue)
                thread.daemon = True
                thread.start()
            
            return task_mock
            
        self.mock_process_compliance_claim.side_effect = mock_celery_task
        
        def mock_process_claim_side_effect(claim, *args, **kwargs):
            print(f"Mock process_claim called with claim: {claim}")
            
            timestamp = datetime.now().timestamp()
            self.task_timestamps.append(timestamp)
            
            reference_id = claim["reference_id"]
            self.processed_tasks.append(reference_id)
            
            print(f"Processing claim {reference_id}, sleeping for 2 seconds...")
            time.sleep(2)
            print(f"Finished processing claim {reference_id}")
            
            if reference_id == "REF_FAIL":
                error = ValueError("Simulated failure in process_claim")
                self.task_exceptions.append(error)
                print(f"Raising error for claim {reference_id}")
                raise error
            
            # Return a formatted response for firm compliance
            return {
                "reference_id": reference_id,
                "claim": claim,
                "search_evaluation": {
                    "source": None,
                    "basic_result": None,
                    "detailed_result": None,
                    "search_strategy": "search_with_tax_id_or_crd",
                    "tax_id": claim.get("tax_id"),
                    "organization_crd": claim.get("organization_crd"),
                    "compliance": False,
                    "compliance_explanation": "No valid data found in SEC IAPD or financial records."
                },
                "status_evaluation": {
                    "compliance": True,
                    "compliance_explanation": "No issues found in status checks.",
                    "alerts": [],
                    "source": None
                },
                "name_evaluation": {
                    "compliance": True,
                    "compliance_explanation": "Business name matches fetched record.",
                    "evaluation_details": {
                        "expected_name": claim.get("business_name"),
                        "claimed_name": claim.get("business_name"),
                        "all_matches": [],
                        "best_match": None,
                        "compliance": True,
                        "compliance_explanation": "Business name matches fetched record."
                    },
                    "alerts": [],
                    "source": None
                },
                "final_evaluation": {
                    "compliance": True,
                    "compliance_explanation": "All checks passed",
                    "overall_compliance": True,
                    "overall_risk_level": "Low",
                    "recommendations": "No action needed",
                    "alerts": []
                }
            }
        
        self.mock_process_claim.side_effect = mock_process_claim_side_effect
        self.api_mock_process_claim.side_effect = mock_process_claim_side_effect

    def _process_task_queue(self):
        try:
            while self.task_queue:
                with self.task_lock:
                    if not self.task_queue:
                        break
                    task_info = self.task_queue[0]
                    reference_id = task_info[0]
                    request_data = task_info[1]
                
                timestamp = datetime.now().timestamp()
                self.task_timestamps.append(timestamp)
                
                self.processed_tasks.append(reference_id)
                
                if reference_id == "REF_FAIL":
                    retry_count = self.retry_counts.get(reference_id, 0)
                    self.retry_counts[reference_id] = retry_count + 1
                    
                    error = ValueError(f"Simulated failure in Celery task (attempt {retry_count + 1})")
                    self.task_exceptions.append(error)
                    print(f"Simulated failure for task {reference_id} (attempt {retry_count + 1})")
                    
                    if retry_count < 2:
                        print(f"Requeueing task {reference_id} for retry {retry_count + 2}")
                        with self.task_lock:
                            self.task_queue.insert(0, (reference_id, request_data))
                
                print(f"Processing task {reference_id}, sleeping for 2 seconds...")
                time.sleep(2)
                print(f"Finished processing task {reference_id}")
                
                if request_data and "webhook_url" in request_data and request_data["webhook_url"]:
                    webhook_url = request_data["webhook_url"]
                    result_payload = {
                        "reference_id": reference_id,
                        "status": "success" if reference_id != "REF_FAIL" else "error",
                        "result": {
                            "compliance": True,
                            "compliance_explanation": "All checks passed",
                            "overall_risk_level": "Low"
                        }
                    }
                    
                    loop = asyncio.new_event_loop()
                    try:
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(self._send_webhook(webhook_url, result_payload))
                    except Exception as e:
                        print(f"Error sending webhook for {reference_id}: {e}")
                    finally:
                        loop.close()
                
                with self.task_lock:
                    if self.task_queue and self.task_queue[0][0] == reference_id:
                        self.task_queue.pop(0)
        except Exception as e:
            print(f"Error in _process_task_queue: {e}")
    
    async def _send_webhook(self, url, payload):
        try:
            print(f"Sending webhook to {url}")
            response = await self.mock_aiohttp_post(url, json=payload)
            print(f"Webhook response status: {response.status}")
            return True
        except Exception as e:
            print(f"Error sending webhook: {e}")
            return False

    def tearDown(self):
        if hasattr(self, 'redis_patch'):
            self.redis_patch.stop()
        if hasattr(self, 'process_compliance_claim_patch'):
            self.process_compliance_claim_patch.stop()
        if hasattr(self, 'process_claim_patch'):
            self.process_claim_patch.stop()
        if hasattr(self, 'api_process_claim_patch'):
            self.api_process_claim_patch.stop()
        if hasattr(self, 'aiohttp_patch'):
            self.aiohttp_patch.stop()
        if hasattr(self, 'global_facade_patch'):
            self.global_facade_patch.stop()
        
        print(f"Test completed with processed tasks: {self.processed_tasks}")
        print(f"Task timestamps: {self.task_timestamps}")
        print(f"Task exceptions: {self.task_exceptions}")
        print(f"Webhook calls: {self.webhook_calls}")
        print(f"Retry counts: {self.retry_counts}")

    async def async_test_concurrency_behavior(self):
        requests = [
            {
                "reference_id": f"REF{i}",
                "business_ref": f"BIZ{i}",
                "business_name": f"Test Firm {i}",
                "tax_id": f"TAX{i}",
                "webhook_url": f"https://webhook.site/test-{i}"
            } for i in range(1, 4)
        ]
        responses = []
        response_times = []
        for req in requests:
            start_time = time.time()
            response = self.client.post("/process-claim-basic", json=req)
            response_times.append(time.time() - start_time)
            responses.append(response)
            time.sleep(0.1)  # Ensure FIFO submission order

        for i, response in enumerate(responses, 1):
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "processing_queued")
            self.assertEqual(data["reference_id"], f"REF{i}")
            self.assertIn("task_id", data)
            self.assertLess(response_times[i-1], 0.5, f"Response {i} took {response_times[i-1]:.2f}s, too slow")

        await asyncio.sleep(8)  # 3 tasks * 2 seconds + buffer
        self.assertEqual(len(self.processed_tasks), 3, "Expected 3 tasks to be processed")
        self.assertEqual(self.processed_tasks, ["REF1", "REF2", "REF3"], "Tasks should be processed in FIFO order")
        for i in range(1, len(self.task_timestamps)):
            time_diff = self.task_timestamps[i] - self.task_timestamps[i-1]
            self.assertGreaterEqual(
                time_diff, 2.0,
                f"Task REF{i+1} started {time_diff:.2f}s after REF{i}, violating sequential processing"
            )
        self.assertEqual(len(self.webhook_calls), 3, "Expected 3 webhook calls")
        for i, (url, json_data) in enumerate(self.webhook_calls, 1):
            self.assertEqual(url, f"https://webhook.site/test-{i}")
            self.assertEqual(json_data["reference_id"], f"REF{i}")
            self.assertEqual(json_data["status"], "success")

    async def async_test_synchronous_processing(self):
        request = {
            "reference_id": "REF_SYNC",
            "business_ref": "BIZ_SYNC",
            "business_name": "Sync Firm",
            "tax_id": "TAX_SYNC"
        }
        start_time = time.time()
        response = self.client.post("/process-claim-basic", json=request)
        response_time = time.time() - start_time
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["reference_id"], "REF_SYNC")
        self.assertGreaterEqual(response_time, 2.0, "Synchronous response should take at least 2 seconds")
        self.assertEqual(len(self.webhook_calls), 0, "No webhook calls should be made")

    async def async_test_error_handling(self):
        request = {
            "reference_id": "REF_FAIL",
            "business_ref": "BIZ_FAIL",
            "business_name": "Fail Firm",
            "tax_id": "TAX_FAIL",
            "webhook_url": "https://webhook.site/error-test"
        }
        response = self.client.post("/process-claim-basic", json=request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "processing_queued")
        await asyncio.sleep(10)  # Wait for 3 retries (2 seconds each + buffer)
        self.assertIn("REF_FAIL", self.processed_tasks, "Task should have attempted processing")
        self.assertEqual(self.retry_counts.get("REF_FAIL", 0), 3, "Expected 3 retry attempts")
        self.assertEqual(len(self.task_exceptions), 3, "Expected 3 exceptions for retries")
        self.assertEqual(len(self.webhook_calls), 2, "Expected 2 webhook calls for failure (one per retry)")
        url, json_data = self.webhook_calls[0]
        self.assertEqual(url, "https://webhook.site/error-test")
        self.assertEqual(json_data["status"], "error")
        self.assertEqual(json_data["reference_id"], "REF_FAIL")

    async def async_test_webhook_failure(self):
        request = {
            "reference_id": "REF_WEBHOOK_FAIL",
            "business_ref": "BIZ_WEBHOOK_FAIL",
            "business_name": "Webhook Fail Firm",
            "tax_id": "TAX_WEBHOOK_FAIL",
            "webhook_url": "https://webhook.site/fail-test"
        }
        response = self.client.post("/process-claim-basic", json=request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "processing_queued")
        await asyncio.sleep(3)  # Wait for task completion
        self.assertIn("REF_WEBHOOK_FAIL", self.processed_tasks, "Task should complete despite webhook failure")
        self.assertEqual(len(self.webhook_calls), 1, "Expected 1 webhook call attempt")
        url, json_data = self.webhook_calls[0]
        self.assertEqual(url, "https://webhook.site/fail-test")
        self.assertEqual(json_data["reference_id"], "REF_WEBHOOK_FAIL")
        self.assertEqual(json_data["status"], "success")

    async def async_test_task_status(self):
        request = {
            "reference_id": "REF_STATUS",
            "business_ref": "BIZ_STATUS",
            "business_name": "Status Firm",
            "tax_id": "TAX_STATUS",
            "webhook_url": "https://webhook.site/test-status"
        }
        
        with patch('api.process_firm_compliance_claim.delay') as mock_delay:
            mock_task = MagicMock()
            mock_task.id = "test-task-id-123"
            mock_delay.return_value = mock_task
            
            response = self.client.post("/process-claim-basic", json=request)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "processing_queued")
            task_id = data["task_id"]
            self.assertEqual(task_id, "test-task-id-123")
            
            with patch('api.AsyncResult') as mock_async_result:
                mock_task = MagicMock()
                mock_task.state = "PENDING"
                mock_task.info = {"reference_id": "REF_STATUS"}
                mock_task.result = None
                mock_async_result.return_value = mock_task
                
                status_response = self.client.get(f"/task-status/{task_id}")
                self.assertEqual(status_response.status_code, 200)
                data = status_response.json()
                self.assertEqual(data["task_id"], task_id)
                self.assertEqual(data["status"], "QUEUED")
                self.assertEqual(data["reference_id"], "REF_STATUS")
                self.assertIsNone(data["result"])
                self.assertIsNone(data["error"])
                
                mock_task.state = "STARTED"
                status_response = self.client.get(f"/task-status/{task_id}")
                self.assertEqual(status_response.status_code, 200)
                data = status_response.json()
                self.assertEqual(data["status"], "PROCESSING")
                
                mock_task.state = "SUCCESS"
                mock_task.result = {
                    "reference_id": "REF_STATUS",
                    "status": "success",
                    "result": {
                        "compliance": True,
                        "compliance_explanation": "All checks passed",
                        "overall_risk_level": "Low"
                    }
                }
                status_response = self.client.get(f"/task-status/{task_id}")
                self.assertEqual(status_response.status_code, 200)
                data = status_response.json()
                self.assertEqual(data["status"], "COMPLETED")
                self.assertEqual(data["result"]["reference_id"], "REF_STATUS")
                self.assertEqual(data["result"]["status"], "success")
                
                mock_task.state = "FAILURE"
                mock_task.result = "Simulated failure in Celery task"
                status_response = self.client.get(f"/task-status/{task_id}")
                self.assertEqual(status_response.status_code, 200)
                data = status_response.json()
                self.assertEqual(data["status"], "FAILED")
                self.assertEqual(data["error"], "Simulated failure in Celery task")
                
                mock_task.state = "RETRY"
                status_response = self.client.get(f"/task-status/{task_id}")
                self.assertEqual(status_response.status_code, 200)
                data = status_response.json()
                self.assertEqual(data["status"], "RETRYING")
                
                mock_async_result.return_value = None
                status_response = self.client.get("/task-status/invalid-task-id")
                self.assertEqual(status_response.status_code, 404)
                self.assertEqual(status_response.json()["detail"], "Task not found")

    def test_concurrency_behavior(self):
        asyncio.run(self.async_test_concurrency_behavior())

    def test_synchronous_processing(self):
        asyncio.run(self.async_test_synchronous_processing())

    def test_error_handling(self):
        asyncio.run(self.async_test_error_handling())

    def test_webhook_failure(self):
        asyncio.run(self.async_test_webhook_failure())

    def test_task_status(self):
        asyncio.run(self.async_test_task_status())

if __name__ == "__main__":
    unittest.main()