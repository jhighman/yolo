"""
==============================================
📌 FIRM COMPLIANCE CLAIM PROCESSING API OVERVIEW
==============================================
🗂 PURPOSE
This FastAPI application provides endpoints for processing business compliance claims
and managing cached compliance data. It supports multiple processing modes (basic, extended, complete),
asynchronous task queuing with Celery, and webhook notifications for processed claims.

🔧 USAGE
Run the API with `uvicorn api:app --host 0.0.0.0 --port 9000 --log-level info`.
Use endpoints like `/process-claim-{mode}`, `/cache/clear`, `/compliance/latest`, etc.
Ensure Redis is running for Celery (e.g., `redis://localhost:6379/0`).

📝 NOTES
- Integrates `cache_manager` for cache operations and `firm_business` for claim processing.
- Uses `FirmServicesFacade` for claim processing and `CacheManager` for cache management.
- Supports asynchronous webhook notifications with Celery task queuing.
- Accepts and echoes back additional fields from inbound data (e.g., workProduct, entity information).
- Includes centralized logging and storage management.
"""

import json
import logging
import random
import time
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel, validator
from celery import Celery
from celery.result import AsyncResult
import aiohttp
import asyncio
import os
import requests
import traceback
from prometheus_client import Counter, Histogram, start_http_server

from utils.logging_config import setup_logging
from services.firm_services import FirmServicesFacade
from services.firm_business import process_claim
from cache_manager.cache_operations import CacheManager
from cache_manager.firm_compliance_handler import FirmComplianceHandler
from cache_manager.file_handler import FileHandler

# Setup logging
loggers = setup_logging(debug=True)
logger = loggers["api"]
webhook_logger = logging.getLogger("webhook")  # Get the webhook logger

# Initialize services for Celery workers
from services.firm_services import FirmServicesFacade
from cache_manager.cache_operations import CacheManager
from cache_manager.file_handler import FileHandler
from cache_manager.firm_compliance_handler import FirmComplianceHandler

# Initialize global instances for Celery workers
celery_facade = FirmServicesFacade()
celery_cache_manager = CacheManager()
celery_file_handler = FileHandler(celery_cache_manager.cache_folder)
celery_compliance_handler = FirmComplianceHandler(celery_file_handler.base_path)
logger.info("Celery worker services initialized")

# Initialize Prometheus metrics
task_counter = Counter('celery_tasks_total', 'Total number of Celery tasks', ['task_name', 'status'])
task_duration = Histogram('celery_task_duration_seconds', 'Task duration in seconds', ['task_name'])
webhook_counter = Counter('webhook_delivery_total', 'Total number of webhook deliveries', ['status'])
webhook_duration = Histogram('webhook_delivery_duration_seconds', 'Webhook delivery duration in seconds')

# Start Prometheus metrics server on port 8000
try:
    start_http_server(8000)
    logger.info("Prometheus metrics server started on port 8000")
except Exception as e:
    logger.error(f"Failed to start Prometheus metrics server: {str(e)}")

# Initialize Celery with Redis
celery_app = Celery(
    "firm_compliance_tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    task_time_limit=3600,
    task_concurrency=4,  # Increased from 1 for better throughput
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_default_queue="firm_compliance_queue",
    # Added reliability settings
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
    broker_transport_options={'visibility_timeout': 3600},
)

# Configure Celery to use a dead letter queue
celery_app.conf.update(
    task_routes={
        'process_firm_compliance_claim': {'queue': 'firm_compliance_queue'},
        'send_webhook_notification': {'queue': 'webhook_queue'},
        'dead_letter_task': {'queue': 'dead_letter_queue'}
    }
)

# Dead letter task to handle permanently failed tasks
@celery_app.task(name="dead_letter_task")
def dead_letter_task(task_name, args, kwargs, exc_info):
    logger.error(f"Task {task_name} permanently failed: {exc_info}")
    # Store in database or send alert

# Settings, ClaimRequest, TaskStatusResponse, and WebhookStatus models
class Settings(BaseModel):
    headless: bool = True
    debug: bool = False

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    reference_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class WebhookStatus(BaseModel):
    reference_id: str
    webhook_url: str
    task_id: Optional[str] = None
    attempts: int = 0
    last_attempt: Optional[str] = None
    status: str = "pending"  # pending, success, failed, retrying
    response_code: Optional[int] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str

class ClaimRequest(BaseModel):
    reference_id: str
    business_ref: str
    business_name: Optional[str] = None
    tax_id: Optional[str] = None
    organization_crd: Optional[str] = None
    webhook_url: Optional[str] = None
    _id: Optional[Dict[str, str]] = None
    type: Optional[str] = None
    workProduct: Optional[str] = None
    entity: Optional[str] = None
    entityName: Optional[str] = None
    name: Optional[str] = None
    normalizedName: Optional[str] = None
    principal: Optional[str] = None
    street1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        extra = "allow"

    @validator('tax_id', 'organization_crd', pre=True, always=True)
    def validate_empty_strings(cls, v):
        if v == "":
            return None
        return v

    @validator('business_ref', 'reference_id')
    def validate_required_fields(cls, v):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("Field must be a non-empty string")
        return v

# Initialize FastAPI app
app = FastAPI(
    title="Firm Compliance Claim Processing API",
    description="API for processing business compliance claims with multiple modes and managing cached compliance data",
    version="1.0.0"
)

# Global instances
settings = Settings()
facade = None
cache_manager = None
file_handler = None
compliance_handler = None

# Redis-based storage for webhook statuses
# Uses the same Redis instance as Celery for persistence
def get_redis_client():
    """Get Redis client from Celery's backend."""
    return celery_app.backend.client

# TTL constants for Redis keys (in seconds)
WEBHOOK_TTL_SUCCESS = 30 * 60            # 30 minutes for successful webhooks
WEBHOOK_TTL_FAILED = 7 * 24 * 60 * 60    # 7 days for failed webhooks
WEBHOOK_TTL_PENDING = 7 * 24 * 60 * 60   # 7 days for pending/retrying webhooks

def store_webhook_status(reference_id, status_data):
    """Store webhook status in Redis with appropriate TTL."""
    redis_client = get_redis_client()
    key = f"webhook_status:{reference_id}"
    
    # Determine TTL based on status
    status = status_data.get("status", "pending")
    if status == "success":
        ttl = WEBHOOK_TTL_SUCCESS
    elif status == "failed":
        ttl = WEBHOOK_TTL_FAILED
    else:  # pending or retrying
        ttl = WEBHOOK_TTL_PENDING
    
    # Store with TTL
    redis_client.set(key, json.dumps(status_data), ex=ttl)
    
    # Add to index set for listing (with its own TTL)
    redis_client.sadd("webhook_status:all", reference_id)
    # Refresh TTL on the index set (use the longest TTL to ensure it outlives all entries)
    # Both WEBHOOK_TTL_FAILED and WEBHOOK_TTL_PENDING are 7 days
    redis_client.expire("webhook_status:all", WEBHOOK_TTL_FAILED)
    
    return status_data

def get_webhook_status(reference_id):
    """Get webhook status from Redis."""
    redis_client = get_redis_client()
    key = f"webhook_status:{reference_id}"
    data = redis_client.get(key)
    if data:
        return json.loads(data)
    return None

def update_webhook_status(reference_id, updates):
    """Update webhook status in Redis with appropriate TTL."""
    current = get_webhook_status(reference_id)
    if not current:
        return None
    
    # Update the status data
    current.update(updates)
    
    # Store with updated TTL based on new status
    return store_webhook_status(reference_id, current)

def delete_webhook_status(reference_id):
    """Delete webhook status from Redis."""
    redis_client = get_redis_client()
    key = f"webhook_status:{reference_id}"
    redis_client.delete(key)
    redis_client.srem("webhook_status:all", reference_id)
    return True

def list_webhook_statuses(status_filter=None, offset=0, limit=10):
    """List webhook statuses from Redis with pagination."""
    redis_client = get_redis_client()
    all_refs = redis_client.smembers("webhook_status:all")
    
    results = []
    for ref in all_refs:
        ref_str = ref.decode('utf-8') if isinstance(ref, bytes) else ref
        status_data = get_webhook_status(ref_str)
        if status_data and (status_filter is None or status_data.get("status") == status_filter):
            results.append(status_data)
    
    # Sort by updated_at (most recent first)
    results.sort(key=lambda x: x.get("updated_at", "0"), reverse=True)
    
    # Apply pagination
    paginated = results[offset:offset+limit]
    
    return {
        "total": len(results),
        "items": paginated
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize API services on startup."""
    global facade, cache_manager, file_handler, compliance_handler
    
    try:
        # Initialize services
        facade = FirmServicesFacade()
        cache_manager = CacheManager()
        file_handler = FileHandler(cache_manager.cache_folder)
        compliance_handler = FirmComplianceHandler(file_handler.base_path)
        logger.info("API services successfully initialized")
        
    except Exception as e:
        logger.error(f"Critical error during startup: {str(e)}", exc_info=True)
        raise

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down API server")
    try:
        if facade:
            # FirmServicesFacade doesn't have cleanup method, so we just log
            logger.debug("FirmServicesFacade cleanup not required")
    except Exception as e:
        logger.error(f"Error cleaning up: {str(e)}")

# Helper function for Celery dependency injection
def get_celery_app():
    return celery_app

# Celery task for processing claims
# Circuit breaker for external service calls
class CircuitBreaker:
    def __init__(self, name, fail_max=5, reset_timeout=60):
        self.name = name
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.state = "closed"  # closed, open, half-open
        self.last_failure_time = 0
        
    def __call__(self, func):
        def wrapper(*args, **kwargs):
            current_time = time.time()
            
            # Check if circuit is open
            if self.state == "open":
                if current_time - self.last_failure_time > self.reset_timeout:
                    logger.info(f"Circuit {self.name} transitioning from open to half-open")
                    self.state = "half-open"
                else:
                    logger.warning(f"Circuit {self.name} is open, rejecting call")
                    raise RuntimeError(f"Circuit {self.name} is open")
            
            try:
                result = func(*args, **kwargs)
                
                # Success - reset circuit if in half-open state
                if self.state == "half-open":
                    logger.info(f"Circuit {self.name} transitioning from half-open to closed")
                    self.state = "closed"
                    self.failures = 0
                
                return result
                
            except Exception as e:
                self.failures += 1
                self.last_failure_time = current_time
                
                if self.failures >= self.fail_max:
                    logger.warning(f"Circuit {self.name} transitioning to open after {self.failures} failures")
                    self.state = "open"
                
                raise e
                
        return wrapper

# Create circuit breakers for external services
finra_breaker = CircuitBreaker("finra_api", fail_max=5, reset_timeout=60)
sec_breaker = CircuitBreaker("sec_api", fail_max=5, reset_timeout=60)

@celery_app.task(name="process_firm_compliance_claim", bind=True, max_retries=3, default_retry_delay=60)
def process_firm_compliance_claim(self, request_dict: Dict[str, Any], mode: str):
    """Celery task to process a firm compliance claim asynchronously."""
    reference_id = request_dict.get('reference_id', 'unknown')
    start_time = time.time()
    task_counter.labels(task_name='process_firm_compliance_claim', status='started').inc()
    logger.info(f"Starting Celery task for reference_id={reference_id} with mode={mode}")
    
    # Add task context to all logs
    task_context = {
        "task_id": self.request.id,
        "reference_id": reference_id,
        "mode": mode,
        "attempt": self.request.retries + 1
    }
    
    self.update_state(state="PENDING", meta={"reference_id": reference_id})
    
    # Pre-execution validation and health checks
    try:
        # Validate input parameters
        if not reference_id or not isinstance(reference_id, str):
            raise ValueError(f"Invalid reference_id: {reference_id}")
            
        # Check if required services are available
        if not celery_facade or not celery_cache_manager:
            raise RuntimeError("Required services not initialized")
            
        # Verify Redis connection (broker/backend)
        try:
            self.app.backend.client.ping()
        except Exception as e:
            logger.error(f"Redis backend unavailable: {str(e)}", extra=task_context)
            raise RuntimeError(f"Redis backend unavailable: {str(e)}")
    except (ValueError, RuntimeError) as e:
        # Don't retry on validation errors - these are permanent failures
        logger.error(f"Task validation failed: {str(e)}", extra=task_context, exc_info=True)
        return {
            "status": "error",
            "reference_id": reference_id,
            "message": f"Task validation failed: {str(e)}",
            "error_type": "validation_error"
        }
    
    try:
        request = ClaimRequest(**request_dict)
        mode_settings = PROCESSING_MODES.get(mode)
        if not mode_settings:
            raise ValueError(f"Invalid processing mode: {mode}")
            
        claim = request.dict(exclude_unset=True)
        business_ref = claim.get("business_ref")
        webhook_url = claim.pop("webhook_url", None)

        if "_id" in claim and isinstance(claim["_id"], dict) and "$oid" in claim["_id"]:
            claim["mongo_id"] = claim["_id"]["$oid"]

        # Wrap the process_claim call in a specific try/except to catch failures
        try:
            report = process_claim(
                claim=claim,
                facade=celery_facade,
                business_ref=business_ref,
                skip_financials=mode_settings["skip_financials"],
                skip_legal=mode_settings["skip_legal"]
            )
        except Exception as process_error:
            logger.error(
                f"Error in process_claim for reference_id={reference_id}: {str(process_error)}",
                extra=task_context,
                exc_info=True
            )
            raise RuntimeError(f"Process claim execution failed: {str(process_error)}")
        
        if report is None:
            error_msg = f"Failed to process claim for reference_id={reference_id}: process_claim returned None"
            logger.error(error_msg, extra=task_context)
            raise ValueError(error_msg)

        complete_claim = claim.copy()
        complete_claim["business_ref"] = business_ref
        report["claim"] = complete_claim
        
        logger.info(f"Successfully processed claim for reference_id={reference_id}", extra=task_context)

        if webhook_url:
            # Queue webhook delivery as a separate task with retries
            logger.info(f"Queuing webhook delivery for reference_id={reference_id}", extra=task_context)
            send_webhook_notification.delay(webhook_url, report, reference_id)
        
        return report
    
    except (ValueError, TypeError) as e:
        # Data validation errors - don't retry these
        logger.error(f"Validation error for reference_id={reference_id}: {str(e)}", extra=task_context, exc_info=True)
        error_report = {
            "status": "error",
            "reference_id": reference_id,
            "message": f"Validation error: {str(e)}",
            "error_type": "validation_error"
        }
        if webhook_url:
            send_webhook_notification.delay(webhook_url, error_report, reference_id)
        task_duration.labels(task_name='process_firm_compliance_claim').observe(time.time() - start_time)
        return error_report
        
    except (requests.Timeout, requests.ConnectionError, aiohttp.ClientError) as e:
        # Network errors - these are retryable
        logger.error(f"Network error for reference_id={reference_id}: {str(e)}", extra=task_context, exc_info=True)
        error_report = {
            "status": "error",
            "reference_id": reference_id,
            "message": f"Network error: {str(e)}",
            "error_type": "network_error",
            "retrying": self.request.retries < self.max_retries
        }
        if webhook_url:
            send_webhook_notification.delay(webhook_url, error_report, reference_id)
            
        # Use exponential backoff with jitter
        retry_countdown = min(2 ** self.request.retries * 60 + random.uniform(0, 30), 300)
        try:
            self.retry(exc=e, countdown=retry_countdown)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for reference_id={reference_id}", extra=task_context)
            error_report["retrying"] = False
            error_report["message"] = f"Network error (max retries exceeded): {str(e)}"
        return error_report
    
    except Exception as e:
        # Unexpected errors - log extensively and retry
        logger.error(
            f"Unexpected error processing claim for reference_id={reference_id}: {str(e)}",
            extra=task_context,
            exc_info=True
        )
        
        # Capture stack trace for better debugging
        stack_trace = traceback.format_exc()
        logger.error(f"Stack trace: {stack_trace}", extra=task_context)
        
        error_report = {
            "status": "error",
            "reference_id": reference_id,
            "message": f"Unexpected error: {str(e)}",
            "error_type": "unexpected_error",
            "retrying": self.request.retries < self.max_retries
        }
        
        if webhook_url:
            send_webhook_notification.delay(webhook_url, error_report, reference_id)
        
        # Use exponential backoff with jitter
        retry_countdown = min(2 ** self.request.retries * 60 + random.uniform(0, 30), 300)
        try:
            self.retry(exc=e, countdown=retry_countdown)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for reference_id={reference_id}", extra=task_context)
            error_report["retrying"] = False
            error_report["message"] = f"Unexpected error (max retries exceeded): {str(e)}"
        
        return error_report

# Dedicated Celery task for webhook delivery
@celery_app.task(name="send_webhook_notification", bind=True, max_retries=3, default_retry_delay=30)
def send_webhook_notification(self, webhook_url: str, report: Dict[str, Any], reference_id: str):
    """Dedicated Celery task for webhook delivery with robust retry logic."""
    start_time = time.time()
    webhook_counter.labels(status='started').inc()
    webhook_logger = loggers.get("webhook", logger)
    
    # Add task context to all logs
    task_context = {
        "task_id": self.request.id,
        "reference_id": reference_id,
        "webhook_url": webhook_url,
        "attempt": self.request.retries + 1
    }
    
    # Create a webhook error log file if it doesn't exist
    webhook_log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(webhook_log_dir, exist_ok=True)
    webhook_log_file = os.path.join(webhook_log_dir, "webhook_errors.log")
    
    # Pre-execution validation
    if not webhook_url or not isinstance(webhook_url, str):
        webhook_logger.error(f"Invalid webhook_url: {webhook_url}", extra=task_context)
        return {
            "status": "error",
            "reference_id": reference_id,
            "message": f"Invalid webhook URL: {webhook_url}",
            "error_type": "validation_error"
        }
    
    if not reference_id or not isinstance(reference_id, str):
        webhook_logger.error(f"Invalid reference_id: {reference_id}", extra=task_context)
        return {
            "status": "error",
            "reference_id": reference_id,
            "message": "Invalid reference ID",
            "error_type": "validation_error"
        }
    
    if not isinstance(report, dict):
        webhook_logger.error(f"Invalid report type: {type(report)}", extra=task_context)
        webhook_counter.labels(status='validation_error').inc()
        webhook_duration.observe(time.time() - start_time)
        return {
            "status": "error",
            "reference_id": reference_id,
            "message": f"Invalid report type: {type(report)}",
            "error_type": "validation_error"
        }
    
    # Initialize or update webhook status in Redis
    current_time = self.request.id or str(time.time())
    current_status = get_webhook_status(reference_id)
    
    if not current_status:
        # Create new status
        status_data = {
            "reference_id": reference_id,
            "webhook_url": webhook_url,
            "task_id": self.request.id,
            "attempts": 1,
            "last_attempt": current_time,
            "status": "retrying" if self.request.retries > 0 else "pending",
            "response_code": None,
            "error": None,
            "created_at": current_time,
            "updated_at": current_time
        }
        store_webhook_status(reference_id, status_data)
    else:
        # Update existing status
        updates = {
            "attempts": current_status.get("attempts", 0) + 1,
            "last_attempt": current_time,
            "status": "retrying" if self.request.retries > 0 else "pending",
            "updated_at": current_time
        }
        update_webhook_status(reference_id, updates)
    
    try:
        webhook_logger.info(f"Attempt {self.request.retries + 1} sending webhook for reference_id={reference_id}", extra=task_context)
        
        # Add timestamp and attempt number to the report for tracking
        if isinstance(report, dict):
            report["webhook_sent_at"] = self.request.id
            report["webhook_attempt"] = self.request.retries + 1
        
        # Use synchronous requests for Celery worker with timeout
        try:
            response = requests.post(webhook_url, json=report, timeout=30)
            response.raise_for_status()  # Raise exception for 4XX/5XX status codes
        except requests.exceptions.Timeout as e:
            webhook_logger.error(f"Webhook request timed out for reference_id={reference_id}", extra=task_context)
            raise e
        except requests.exceptions.ConnectionError as e:
            webhook_logger.error(f"Webhook connection error for reference_id={reference_id}: {str(e)}", extra=task_context)
            raise e
        except requests.exceptions.HTTPError as e:
            webhook_logger.error(f"Webhook HTTP error for reference_id={reference_id}: {str(e)}", extra=task_context)
            raise e
        except requests.exceptions.RequestException as e:
            webhook_logger.error(f"Webhook request error for reference_id={reference_id}: {str(e)}", extra=task_context)
            raise e
        
        webhook_logger.info(f"Successfully sent webhook for reference_id={reference_id}", extra=task_context)
        webhook_counter.labels(status='success').inc()
        
        # Update webhook status to success in Redis
        update_webhook_status(reference_id, {
            "status": "success",
            "response_code": response.status_code,
            "updated_at": str(time.time())
        })
        
        webhook_duration.observe(time.time() - start_time)
        return {
            "status": "success",
            "reference_id": reference_id,
            "response_code": response.status_code
        }
    
    except (requests.Timeout, requests.ConnectionError) as e:
        webhook_counter.labels(status='network_error').inc()
        error_msg = f"Webhook connection error for reference_id={reference_id}: {str(e)}"
        webhook_logger.error(error_msg, extra=task_context, exc_info=True)
        
        # Update webhook status with error in Redis
        update_webhook_status(reference_id, {
            "status": "retrying",
            "error": error_msg,
            "updated_at": str(time.time())
        })
        
        with open(webhook_log_file, "a") as f:
            f.write(f"[{self.request.id}] {error_msg}\n")
        
        # Exponential backoff with jitter for network-related errors
        retry_countdown = min(2 ** self.request.retries * 30 + random.uniform(0, 30), 300)
        try:
            self.retry(exc=e, countdown=retry_countdown)
        except self.MaxRetriesExceededError:
            webhook_logger.error(f"Max retries exceeded for reference_id={reference_id}", extra=task_context)
            update_webhook_status(reference_id, {"status": "failed"})
            return {
                "status": "error",
                "reference_id": reference_id,
                "message": f"Webhook delivery failed after {self.request.retries + 1} attempts: {str(e)}",
                "error_type": "network_error",
                "retrying": False
            }
        
        webhook_duration.observe(time.time() - start_time)
        return {
            "status": "error",
            "reference_id": reference_id,
            "message": f"Webhook delivery failed: {str(e)}",
            "error_type": "network_error",
            "retrying": True
        }
        
    except Exception as e:
        webhook_counter.labels(status='unexpected_error').inc()
        error_msg = f"Error sending webhook for reference_id={reference_id}: {str(e)}"
        webhook_logger.error(error_msg, extra=task_context, exc_info=True)
        
        # Capture stack trace for better debugging
        stack_trace = traceback.format_exc()
        webhook_logger.error(f"Stack trace: {stack_trace}", extra=task_context)
        
        # Update webhook status with error in Redis
        update_webhook_status(reference_id, {
            "status": "retrying",
            "error": error_msg,
            "updated_at": str(time.time())
        })
        
        # Write to dedicated webhook error log file
        with open(webhook_log_file, "a") as f:
            f.write(f"[{self.request.id}] {error_msg}\n")
            f.write(f"[{self.request.id}] Stack trace: {stack_trace}\n")
        
        # Exponential backoff with jitter for general errors
        retry_countdown = min(2 ** self.request.retries * 30 + random.uniform(0, 30), 300)
        try:
            self.retry(exc=e, countdown=retry_countdown)
        except self.MaxRetriesExceededError:
            webhook_logger.error(f"Max retries exceeded for reference_id={reference_id}", extra=task_context)
            update_webhook_status(reference_id, {"status": "failed"})
            return {
                "status": "error",
                "reference_id": reference_id,
                "message": f"Webhook delivery failed after {self.request.retries + 1} attempts: {str(e)}",
                "error_type": "unexpected_error",
                "retrying": False
            }
        
        webhook_duration.observe(time.time() - start_time)
        return {
            "status": "error",
            "reference_id": reference_id,
            "message": f"Webhook delivery failed: {str(e)}",
            "error_type": "unexpected_error",
            "retrying": True
        }

# Original async webhook function (kept for FastAPI endpoints)
async def send_to_webhook(webhook_url: str, report: Dict[str, Any], reference_id: str):
    """Asynchronously send the report to the specified webhook URL."""
    webhook_logger = loggers.get("webhook", logger)
    
    # Create a webhook error log file if it doesn't exist
    webhook_log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(webhook_log_dir, exist_ok=True)
    webhook_log_file = os.path.join(webhook_log_dir, "webhook_errors.log")
    
    async with aiohttp.ClientSession() as session:
        try:
            webhook_logger.info(f"Sending report to webhook URL: {webhook_url} for reference_id={reference_id}")
            
            # Add timestamp to the report for tracking
            if isinstance(report, dict):
                report["webhook_sent_at"] = asyncio.get_event_loop().time()
            
            async with session.post(webhook_url, json=report, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    webhook_logger.info(f"Successfully sent report to webhook for reference_id={reference_id}")
                    return True
                else:
                    error_msg = f"Webhook delivery failed for reference_id={reference_id}: Status {response.status}, Response: {await response.text()}"
                    webhook_logger.error(error_msg)
                    
                    # Write to dedicated webhook error log file
                    with open(webhook_log_file, "a") as f:
                        f.write(f"[{asyncio.get_event_loop().time()}] {error_msg}\n")
                    
                    return False
        except asyncio.TimeoutError:
            error_msg = f"Webhook timeout for reference_id={reference_id} to URL: {webhook_url}"
            webhook_logger.error(error_msg)
            with open(webhook_log_file, "a") as f:
                f.write(f"[{asyncio.get_event_loop().time()}] {error_msg}\n")
            return False
        except Exception as e:
            error_msg = f"Error sending to webhook for reference_id={reference_id}: {str(e)}"
            webhook_logger.error(error_msg, exc_info=True)
            
            # Write to dedicated webhook error log file
            with open(webhook_log_file, "a") as f:
                f.write(f"[{asyncio.get_event_loop().time()}] {error_msg}\n")
            
            return False

# Helper function for synchronous claim processing
async def process_claim_helper(request: ClaimRequest, mode: str, send_webhook: bool = True) -> Dict[str, Any]:
    """
    Helper function to process a claim with the specified mode.

    Args:
        request (ClaimRequest): The claim data to process.
        mode (str): Processing mode ("basic", "extended", "complete").
        send_webhook (bool): Whether to send the result to webhook if webhook_url is provided.

    Returns:
        Dict[str, Any]: Processed compliance report.
    """
    logger.info(f"Processing claim with mode='{mode}': {request.dict()}")

    mode_settings = PROCESSING_MODES[mode]
    claim = request.dict(exclude_unset=True)
    business_ref = claim.get("business_ref")
    webhook_url = claim.pop("webhook_url", None)

    if "_id" in claim and isinstance(claim["_id"], dict) and "$oid" in claim["_id"]:
        claim["mongo_id"] = claim["_id"]["$oid"]

    try:
        report = process_claim(
            claim=claim,
            facade=facade,  # Use the FastAPI app's facade instance
            business_ref=business_ref,
            skip_financials=mode_settings["skip_financials"],
            skip_legal=mode_settings["skip_legal"]
        )
        
        if report is None:
            logger.error(f"Failed to process claim for reference_id={request.reference_id}: process_claim returned None")
            raise HTTPException(status_code=500, detail="Claim processing failed unexpectedly")

        complete_claim = claim.copy()
        complete_claim["business_ref"] = business_ref
        report["claim"] = complete_claim
        
        logger.info(f"Successfully processed claim for reference_id={request.reference_id} with mode={mode}")

        if webhook_url and send_webhook:
            asyncio.create_task(send_to_webhook(webhook_url, report, request.reference_id))
        
        return report

    except Exception as e:
        logger.error(f"Error processing claim for reference_id={request.reference_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Settings endpoints
@app.put("/settings")
async def update_settings(new_settings: Settings):
    """Update API settings and reinitialize services if needed."""
    global settings, facade
    old_headless = settings.headless
    settings = new_settings
    
    if old_headless != settings.headless:
        if facade:
            # FirmServicesFacade doesn't have cleanup method
            logger.debug("FirmServicesFacade cleanup not required")
        facade = FirmServicesFacade()
        logger.info(f"Reinitialized FirmServicesFacade with headless={settings.headless}")
    
    return {"message": "Settings updated", "settings": settings.dict()}

@app.get("/settings")
async def get_settings():
    """Get current API settings."""
    return settings.dict()

# Processing modes
PROCESSING_MODES = {
    "basic": {
        "skip_financials": True,
        "skip_legal": True,
        "description": "Minimal processing: skips financial and legal reviews"
    },
    "extended": {
        "skip_financials": False,
        "skip_legal": True,
        "description": "Extended processing: includes financial reviews, skips legal"
    },
    "complete": {
        "skip_financials": False,
        "skip_legal": False,
        "description": "Full processing: includes financial and legal reviews"
    }
}

# Claim processing endpoints
@app.post("/process-claim-basic", response_model=Dict[str, Any])
async def process_claim_basic(request: ClaimRequest):
    """
    Process a claim with basic mode (skips financial and legal reviews).
    If webhook_url is provided, queues the task with Celery for asynchronous processing.
    If no webhook_url, processes synchronously.
    """
    identifiers = [request.business_name, request.tax_id, request.organization_crd]
    if not any(id for id in identifiers if id and isinstance(id, str) and id.strip()):
        logger.error("Validation failed: No valid identifier provided")
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Validation Error",
                "message": "At least one identifier (business_name, tax_id, or organization_crd) must be provided",
                "provided_data": request.dict(exclude_unset=True)
            }
        )
    
    if request.webhook_url:
        logger.info(f"Queuing claim processing for reference_id={request.reference_id} with mode=basic")
        task = process_firm_compliance_claim.delay(request.dict(), "basic")
        return {
            "status": "processing_queued",
            "reference_id": request.reference_id,
            "task_id": task.id,
            "message": "Claim processing queued; result will be sent to webhook"
        }
    else:
        logger.info(f"Synchronous processing started for reference_id={request.reference_id} with mode=basic")
        return await process_claim_helper(request, "basic")

@app.post("/process-claim-extended", response_model=Dict[str, Any])
async def process_claim_extended(request: ClaimRequest):
    """
    Process a claim with extended mode (includes financial reviews, skips legal).
    If webhook_url is provided, queues the task with Celery for asynchronous processing.
    If no webhook_url, processes synchronously.
    """
    identifiers = [request.business_name, request.tax_id, request.organization_crd]
    if not any(id for id in identifiers if id and isinstance(id, str) and id.strip()):
        logger.error("Validation failed: No valid identifier provided")
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Validation Error",
                "message": "At least one identifier (business_name, tax_id, or organization_crd) must be provided",
                "provided_data": request.dict(exclude_unset=True)
            }
        )
    
    store_ref = request.reference_id
    if request.webhook_url:
        logger.info(f"Queuing claim processing for reference_id={store_ref} with mode=extended")
        task = process_firm_compliance_claim.delay(request.dict(), "extended")
        return {
            "status": "processing_queued",
            "reference_id": store_ref,
            "task_id": task.id,
            "message": "Claim processing queued; result will be sent to webhook"
        }
    else:
        logger.info(f"Synchronous processing started for reference_id={store_ref} with mode=extended")
        return await process_claim_helper(request, "extended")

@app.post("/process-claim-complete", response_model=Dict[str, Any])
async def process_claim_complete(request: ClaimRequest):
    """
    Process a claim with complete mode (includes all reviews).
    If webhook_url is provided, queues the task with Celery for asynchronous processing.
    If no webhook_url, processes synchronously.
    """
    identifiers = [request.business_name, request.tax_id, request.organization_crd]
    if not any(id for id in identifiers if id and isinstance(id, str) and id.strip()):
        logger.error("Validation failed: No valid identifier provided")
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Validation Error",
                "message": "At least one identifier (business_name, tax_id, or organization_crd) must be provided",
                "provided_data": request.dict(exclude_unset=True)
            }
        )
    
    if request.webhook_url:
        logger.info(f"Queuing claim processing for reference_id={request.reference_id} with mode=complete")
        task = process_firm_compliance_claim.delay(request.dict(), "complete")
        return {
            "status": "processing_queued",
            "reference_id": request.reference_id,
            "task_id": task.id,
            "message": "Claim processing queued; result will be sent to webhook"
        }
    else:
        logger.info(f"Synchronous processing started for reference_id={request.reference_id} with mode=complete")
        return await process_claim_helper(request, "complete")

@app.get("/processing-modes")
async def get_processing_modes():
    """Return the available processing modes and their configurations."""
    return PROCESSING_MODES

@app.get("/task-status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str, celery_app=Depends(get_celery_app)):
    """
    Check the status of a queued or in-progress task.
    
    Args:
        task_id (str): The unique task ID returned in the response of an asynchronous claim processing request.
        
    Returns:
        TaskStatusResponse: The current status of the task, including reference_id, result or error if available.
    """
    task = AsyncResult(task_id, app=celery_app)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_info = task.info or {}
    reference_id = task_info.get("reference_id") if isinstance(task_info, dict) else None
    
    status_map = {
        "PENDING": "QUEUED",
        "STARTED": "PROCESSING",
        "SUCCESS": "COMPLETED",
        "FAILURE": "FAILED",
        "RETRY": "RETRYING"
    }
    status = status_map.get(task.state, task.state)
    
    result = task.result if task.state == "SUCCESS" and isinstance(task.result, dict) else None
    error = str(task.result) if task.state == "FAILURE" else None
    
    return {
        "task_id": task_id,
        "status": status,
        "reference_id": reference_id,
        "result": result,
        "error": error
    }

# Cache management endpoints
@app.post("/cache/clear/{business_ref}")
async def clear_cache(business_ref: str):
    """
    Clear all cache (except FirmComplianceReport) for a specific business.
    """
    if cache_manager is None:
        raise HTTPException(status_code=500, detail="Cache manager not initialized")
    result = cache_manager.clear_cache(business_ref)
    return json.loads(result)

@app.post("/cache/clear-all")
async def clear_all_cache():
    """
    Clear all cache (except FirmComplianceReport) across all businesses.
    """
    if cache_manager is None:
        raise HTTPException(status_code=500, detail="Cache manager not initialized")
    result = cache_manager.clear_all_cache()
    return json.loads(result)

@app.post("/cache/clear-agent/{business_ref}/{agent_name}")
async def clear_agent_cache(business_ref: str, agent_name: str):
    """
    Clear cache for a specific agent under a business.
    """
    if cache_manager is None:
        raise HTTPException(status_code=500, detail="Cache manager not initialized")
    result = cache_manager.clear_agent_cache(business_ref, agent_name)
    return json.loads(result)

@app.get("/cache/list")
async def list_cache(business_ref: Optional[str] = None, page: int = 1, page_size: int = 10):
    """
    List all cached files for a business or all businesses with pagination.
    """
    if cache_manager is None:
        raise HTTPException(status_code=500, detail="Cache manager not initialized")
    result = cache_manager.list_cache(business_ref or "ALL", page, page_size)
    return json.loads(result)

@app.post("/cache/cleanup-stale")
async def cleanup_stale_cache():
    """
    Delete stale cache older than 90 days (except FirmComplianceReport).
    """
    if cache_manager is None:
        raise HTTPException(status_code=500, detail="Cache manager not initialized")
    result = cache_manager.cleanup_stale_cache()
    return json.loads(result)

# Compliance retrieval endpoints
@app.get("/compliance/latest/{business_ref}")
async def get_latest_compliance(business_ref: str):
    """
    Retrieve the latest compliance report for a business.
    """
    if compliance_handler is None:
        raise HTTPException(status_code=500, detail="Compliance handler not initialized")
    result = compliance_handler.get_latest_compliance_report(business_ref)
    return json.loads(result)

@app.get("/compliance/by-ref/{business_ref}/{reference_id}")
async def get_compliance_by_ref(business_ref: str, reference_id: str):
    """
    Retrieve a compliance report by reference_id for a business.
    """
    if compliance_handler is None:
        raise HTTPException(status_code=500, detail="Compliance handler not initialized")
    result = compliance_handler.get_compliance_report_by_ref(business_ref, reference_id)
    return json.loads(result)

@app.get("/compliance/list")
async def list_compliance_reports(business_ref: Optional[str] = None, page: int = 1, page_size: int = 10):
    """
    List all compliance reports for a business or all businesses with pagination.
    """
    if compliance_handler is None:
        raise HTTPException(status_code=500, detail="Compliance handler not initialized")
    result = compliance_handler.list_compliance_reports(business_ref, page, page_size)
    return json.loads(result)

# Compliance analytics endpoints - simplified without summary generator
@app.get("/compliance/summary/{business_ref}")
async def get_compliance_summary(business_ref: str, page: int = 1, page_size: int = 10):
    """
    Get a compliance summary for a specific business with pagination.
    """
    if cache_manager is None:
        raise HTTPException(status_code=500, detail="Cache manager not initialized")
    # Simplified implementation - just return basic info
    return {
        "business_ref": business_ref,
        "page": page,
        "page_size": page_size,
        "message": "Summary generation not implemented"
    }

@app.get("/compliance/all-summaries")
async def get_all_compliance_summaries(page: int = 1, page_size: int = 10):
    """
    Get a compliance summary for all businesses with pagination.
    """
    if cache_manager is None:
        raise HTTPException(status_code=500, detail="Cache manager not initialized")
    # Simplified implementation - just return basic info
    return {
        "page": page,
        "page_size": page_size,
        "message": "All summaries generation not implemented"
    }

# Webhook testing endpoints
@app.post("/test-webhook")
async def test_webhook(webhook_url: str, test_payload: Optional[Dict[str, Any]] = None):
    """
    Test a webhook URL by sending a test payload.
    
    Args:
        webhook_url (str): The webhook URL to test
        test_payload (Dict[str, Any], optional): Custom payload to send. If not provided, a default test payload is used.
        
    Returns:
        Dict[str, Any]: Result of the webhook test
    """
    if not webhook_url:
        raise HTTPException(status_code=400, detail="webhook_url is required")
    
    if test_payload is None:
        test_payload = {
            "test": True,
            "timestamp": asyncio.get_event_loop().time(),
            "message": "This is a test webhook payload"
        }
    
    reference_id = f"test-{asyncio.get_event_loop().time()}"
    success = await send_to_webhook(webhook_url, test_payload, reference_id)
    
    if success:
        return {
            "status": "success",
            "message": "Webhook test successful",
            "webhook_url": webhook_url
        }
    else:
        return {
            "status": "error",
            "message": "Webhook test failed. Check webhook_errors.log for details.",
            "webhook_url": webhook_url
        }

@app.get("/webhook-logs")
async def get_webhook_logs(lines: int = 50):
    """
    Get the most recent webhook error logs.
    
    Args:
        lines (int): Number of recent log lines to return
        
    Returns:
        Dict[str, Any]: Recent webhook error logs
    """
    webhook_log_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "logs",
        "webhook_errors.log"
    )
    
    if not os.path.exists(webhook_log_file):
        return {"logs": [], "message": "No webhook error logs found"}
    
    try:
        with open(webhook_log_file, "r") as f:
            all_logs = f.readlines()
        
        recent_logs = all_logs[-lines:] if len(all_logs) > lines else all_logs
        return {
            "logs": recent_logs,
            "total_errors": len(all_logs),
            "showing": len(recent_logs)
        }
    except Exception as e:
        logger.error(f"Error reading webhook logs: {str(e)}", exc_info=True)
        return {"error": f"Failed to read webhook logs: {str(e)}"}

# Webhook status endpoints
@app.get("/webhook-status/{reference_id}")
async def get_webhook_status_endpoint(reference_id: str):
    """
    Get the status of webhook deliveries for a specific reference_id.
    
    Args:
        reference_id (str): The reference ID to check webhook status for
        
    Returns:
        Dict[str, Any]: Webhook status details
    """
    status = get_webhook_status(reference_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"No webhook status found for reference_id={reference_id}")
    
    return status

@app.get("/webhook-statuses")
async def list_webhook_statuses_endpoint(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Optional[str] = None
):
    """
    List all webhook statuses with optional filtering and pagination.
    
    Args:
        page (int): Page number (1-based)
        page_size (int): Number of items per page
        status (str, optional): Filter by status (pending, success, failed, retrying)
        
    Returns:
        Dict[str, Any]: Paginated list of webhook statuses
    """
    offset = (page - 1) * page_size
    result = list_webhook_statuses(status, offset, page_size)
    
    return {
        "total": result["total"],
        "page": page,
        "page_size": page_size,
        "pages": (result["total"] + page_size - 1) // page_size,
        "statuses": result["items"]
    }
    
@app.get("/health")
async def health_check():
    """Check the health of the API and its dependencies."""
    health = {"status": "healthy", "components": {}}
    
    # Check Redis connection
    try:
        redis_client = celery_app.backend.client
        redis_client.ping()
        health["components"]["redis"] = "healthy"
    except Exception as e:
        health["components"]["redis"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"
    
    # Check facade service
    try:
        if facade:
            health["components"]["facade"] = "healthy"
        else:
            health["components"]["facade"] = "not_initialized"
            health["status"] = "degraded"
    except Exception as e:
        health["components"]["facade"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"
    
    # Add more component checks as needed
    
    return health

@app.post("/webhook-cleanup")
async def cleanup_old_webhook_statuses():
    """
    Manually trigger cleanup of old webhook statuses.
    This is typically not needed as Redis TTL handles automatic cleanup,
    but can be useful for immediate cleanup or testing.
    
    Returns:
        Dict[str, Any]: Cleanup results
    """
    redis_client = get_redis_client()
    all_refs = redis_client.smembers("webhook_status:all")
    
    cleaned = 0
    errors = 0
    
    for ref in all_refs:
        ref_str = ref.decode('utf-8') if isinstance(ref, bytes) else ref
        status = get_webhook_status(ref_str)
        
        # If status doesn't exist but is in the index, remove from index
        if not status:
            redis_client.srem("webhook_status:all", ref_str)
            cleaned += 1
            continue
        
        # Check if status is old enough to be cleaned up
        updated_at = status.get("updated_at", "0")
        try:
            # Convert to timestamp if it's not already
            if not isinstance(updated_at, (int, float)):
                # Try to parse as ISO format or timestamp string
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                    updated_timestamp = dt.timestamp()
                except:
                    updated_timestamp = float(updated_at)
            else:
                updated_timestamp = float(updated_at)
                
            current_time = time.time()
            
            # Apply cleanup rules based on status
            status_type = status.get("status", "pending")
            if status_type == "success" and current_time - updated_timestamp > WEBHOOK_TTL_SUCCESS:
                # Success webhooks expire after 30 minutes
                delete_webhook_status(ref_str)
                cleaned += 1
                logger.info(f"Cleaned up successful webhook status for {ref_str} (age: {current_time - updated_timestamp:.1f}s)")
            elif status_type == "failed" and current_time - updated_timestamp > WEBHOOK_TTL_FAILED:
                # Failed webhooks expire after 7 days
                delete_webhook_status(ref_str)
                cleaned += 1
                logger.info(f"Cleaned up failed webhook status for {ref_str} (age: {(current_time - updated_timestamp)/86400:.1f} days)")
            elif status_type in ["pending", "retrying"] and current_time - updated_timestamp > WEBHOOK_TTL_PENDING:
                # Pending/retrying webhooks expire after 7 days
                delete_webhook_status(ref_str)
                cleaned += 1
                logger.info(f"Cleaned up {status_type} webhook status for {ref_str} (age: {(current_time - updated_timestamp)/86400:.1f} days)")
        except Exception as e:
            logger.error(f"Error cleaning up webhook status {ref_str}: {str(e)}")
            errors += 1
    
    return {
        "status": "success",
        "cleaned": cleaned,
        "errors": errors,
        "message": f"Cleaned up {cleaned} old webhook statuses with {errors} errors"
    }

@app.delete("/webhook-status/{reference_id}")
async def delete_webhook_status_endpoint(reference_id: str):
    """
    Delete webhook status for a specific reference_id.
    
    Args:
        reference_id (str): The reference ID to delete webhook status for
        
    Returns:
        Dict[str, Any]: Confirmation message
    """
    status = get_webhook_status(reference_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"No webhook status found for reference_id={reference_id}")
    
    delete_webhook_status(reference_id)
    
    return {
        "status": "success",
        "message": f"Webhook status for reference_id={reference_id} deleted"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000, log_level="info")