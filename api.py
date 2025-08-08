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
Ensure Redis is running for Celery (e.g., `redis://localhost:6379/1`).

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

# Generate a unique worker ID for Prometheus metrics
import socket
import uuid

# Create a unique worker ID using hostname and a random suffix
WORKER_ID = f"{socket.gethostname()}-{uuid.uuid4().hex[:6]}"
logger.info(f"Worker ID for metrics: {WORKER_ID}")

# Initialize Prometheus metrics with worker_id label for proper aggregation
task_counter = Counter('celery_tasks_total', 'Total number of Celery tasks',
                      ['task_name', 'status', 'worker_id'])
task_duration = Histogram('celery_task_duration_seconds', 'Task duration in seconds',
                         ['task_name', 'worker_id'])
webhook_counter = Counter('webhook_delivery_total', 'Total number of webhook deliveries',
                         ['status', 'worker_id'])
webhook_duration = Histogram('webhook_delivery_duration_seconds', 'Webhook delivery duration in seconds',
                            ['worker_id'])

# Start Prometheus metrics server on port 8000 if enabled
# Use environment variable to control whether to start the server
# This prevents port conflicts when running multiple workers on one host
prometheus_enabled = os.getenv("ENABLE_PROMETHEUS", "true").lower() in ("true", "1", "yes")
prometheus_port = int(os.getenv("PROMETHEUS_PORT", "8000"))

if prometheus_enabled:
    try:
        # Allow configuring the port via environment variable
        start_http_server(prometheus_port)
        logger.info(f"Prometheus metrics server started on port {prometheus_port}")
    except Exception as e:
        logger.error(f"Failed to start Prometheus metrics server: {str(e)}")
        logger.info("If running multiple workers, set ENABLE_PROMETHEUS=true only for one worker")
        logger.info("or use different PROMETHEUS_PORT values for each worker")
else:
    logger.info("Prometheus metrics server disabled by environment variable")

# Initialize Celery with Redis
# Use a distinct Redis DB (1) for entity as per requirements
celery_app = Celery(
    "firm_compliance_tasks",
    broker="redis://localhost:6379/1",
    backend="redis://localhost:6379/1",
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    task_time_limit=3600,
    worker_concurrency=4,  # Increased from 1 for better throughput
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_default_queue="firm_compliance_queue",
    # Added reliability settings
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
    broker_transport_options={'visibility_timeout': 3600},
)

# Configure Celery to use a dead letter queue and proper queues
celery_app.conf.update(
    task_routes={
        'process_firm_compliance_claim': {'queue': 'firm_compliance_queue'},
        'firm.send_webhook_notification': {'queue': 'webhook_queue'},
        'dead_letter_task': {'queue': 'dead_letter_queue'}
        # webhook_failure_handler is no longer a Celery task
    },
    task_acks_late=True,  # Only acknowledge task after it's processed
    task_reject_on_worker_lost=True  # Requeue task if worker dies
)

# Define webhook_failure_handler as a regular function with the correct signature
def webhook_failure_handler(exc, task_id, args, kwargs, einfo):
    """Handle webhook task failures by updating status and writing to DLQ.
    
    This follows the Celery on_failure handler signature:
    - exc: The exception raised
    - task_id: The ID of the task that failed
    - args: The arguments the task was called with
    - kwargs: The keyword arguments the task was called with
    - einfo: Exception information object with traceback, etc.
    """
    # Debug logging
    logger.info(f"WEBHOOK FAILURE HANDLER CALLED with task_id={task_id}")
    logger.info(f"args: {args}")
    logger.info(f"kwargs: {kwargs}")
    logger.info(f"exc: {exc}")
    logger.info(f"einfo: {einfo}")
    
    try:
        # Extract information from task arguments
        webhook_url = (kwargs or {}).get('webhook_url', 'unknown')
        reference_id = (kwargs or {}).get('reference_id', 'unknown')
        payload = (kwargs or {}).get('payload', {})
        
        # Create webhook_id
        webhook_id = f"{reference_id}_{task_id}"
        
        # Log the failure
        logger.error(f"Webhook task {task_id} permanently failed: {exc}")
        logger.error(f"Webhook URL: {webhook_url}, Reference ID: {reference_id}")
        
        # Update status to failed
        logger.info(f"Checking webhook status for {webhook_id}")
        current_status = get_webhook_status(webhook_id)
        logger.info(f"Current status: {current_status}")
        
        if current_status:
            logger.info(f"Updating webhook status to 'failed' for {webhook_id}")
            update_result = update_webhook_status(webhook_id, {
                "status": "failed",
                "error": f"Max retries exceeded: {exc}",
                "error_type": "max_retries_exceeded",
                "updated_at": get_iso_timestamp()
            })
            logger.info(f"Update result: {update_result}")
            
            # Write to DLQ
            logger.info(f"Writing to DLQ for {webhook_id}")
            dlq_result = write_to_dlq(webhook_id, payload, f"Max retries exceeded: {exc}", "max_retries_exceeded")
            logger.info(f"DLQ result: {dlq_result}")
            
            # Update Prometheus metrics
            webhook_counter.labels(status='failed').inc()
            
            logger.info(f"Updated webhook status to 'failed' and wrote to DLQ for {webhook_id}")
        else:
            logger.warning(f"Could not find webhook status for {webhook_id}")
            
            # Create a new status entry
            logger.info(f"Creating new webhook status for {webhook_id}")
            status_data = {
                "webhook_id": webhook_id,
                "reference_id": reference_id,
                "task_id": task_id,
                "webhook_url": webhook_url,
                "status": "failed",
                "attempts": 1,
                "max_attempts": 3,  # Default max_retries
                "response_code": None,
                "error": f"Max retries exceeded: {exc}",
                "error_type": "max_retries_exceeded",
                "created_at": get_iso_timestamp(),
                "updated_at": get_iso_timestamp(),
                "correlation_id": generate_correlation_id()
            }
            store_result = store_webhook_status(reference_id, task_id, status_data)
            logger.info(f"Store result: {store_result}")
            
            # Write to DLQ
            logger.info(f"Writing to DLQ for {webhook_id}")
            dlq_result = write_to_dlq(webhook_id, payload, f"Max retries exceeded: {exc}", "max_retries_exceeded")
            logger.info(f"DLQ result: {dlq_result}")
    except Exception as e:
        logger.error(f"Error in webhook_failure_handler: {str(e)}")
        logger.error(traceback.format_exc())

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

# Dedicated Redis client for webhook status storage
import redis
import uuid
from datetime import datetime, timezone

# Redis client for webhook status storage
def get_redis_client():
    """Get dedicated Redis client for webhook status storage."""
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    # Use Redis DB 2 for webhook status storage to avoid collisions with Celery (DB 1)
    redis_db = int(os.getenv("REDIS_DB", 2))
    
    return redis.Redis(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        decode_responses=True
    )

# TTL constants for Redis keys (in seconds)
WEBHOOK_TTL_SUCCESS = 30 * 60            # 30 minutes for successful webhooks
WEBHOOK_TTL_FAILED = 7 * 24 * 60 * 60    # 7 days for failed webhooks
WEBHOOK_TTL_PENDING = 7 * 24 * 60 * 60   # 7 days for pending/retrying webhooks

def generate_correlation_id():
    """Generate a unique correlation ID for webhook tracking."""
    return str(uuid.uuid4())

def get_iso_timestamp():
    """Get current timestamp in ISO 8601 format with UTC timezone."""
    return datetime.now(timezone.utc).isoformat()

def store_webhook_status(reference_id, task_id, status_data):
    """Store webhook status in Redis with appropriate TTL using per-delivery keying."""
    try:
        logger.info(f"Storing webhook status for reference_id={reference_id}, task_id={task_id}")
        redis_client = get_redis_client()
        
        # Create a unique webhook_id combining reference_id and task_id
        webhook_id = f"{reference_id}_{task_id}"
        key = f"webhook_status:{webhook_id}"
        
        # Ensure webhook_id is in the status data
        status_data["webhook_id"] = webhook_id
        
        # Determine TTL based on status
        status = status_data.get("status", "pending")
        if status == "delivered":  # Changed from "success" to "delivered" per spec
            ttl = WEBHOOK_TTL_SUCCESS
        elif status == "failed":
            ttl = WEBHOOK_TTL_FAILED
        else:  # pending, in_progress, or retrying
            ttl = WEBHOOK_TTL_PENDING
        
        # Store with TTL
        logger.info(f"Setting Redis key {key} with TTL {ttl}")
        set_result = redis_client.set(key, json.dumps(status_data), ex=ttl)
        logger.info(f"Redis SET result: {set_result}")
        
        # Add to reference_id index set for listing
        index_key = f"webhook_status:index:{reference_id}"
        logger.info(f"Adding to index {index_key}")
        sadd_result = redis_client.sadd(index_key, webhook_id)
        logger.info(f"Redis SADD result: {sadd_result}")
        
        expire_result = redis_client.expire(index_key, WEBHOOK_TTL_FAILED)  # Use longest TTL
        logger.info(f"Redis EXPIRE result: {expire_result}")
        
        return status_data
    except Exception as e:
        logger.error(f"Error storing webhook status: {str(e)}")
        logger.error(traceback.format_exc())
        return status_data

def get_webhook_status(webhook_id):
    """Get webhook status from Redis using webhook_id."""
    try:
        redis_client = get_redis_client()
        key = f"webhook_status:{webhook_id}"
        data = redis_client.get(key)
        if data:
            # Handle both string and bytes responses
            if isinstance(data, bytes):
                return json.loads(data.decode('utf-8'))
            elif isinstance(data, str):
                return json.loads(data)
        return None
    except Exception as e:
        logger.error(f"Error getting webhook status for {webhook_id}: {str(e)}")
        return None

def get_webhook_status_by_reference(reference_id):
    """Get all webhook statuses for a reference_id."""
    try:
        redis_client = get_redis_client()
        index_key = f"webhook_status:index:{reference_id}"
        
        # Get all webhook IDs for this reference_id
        webhook_ids = []
        try:
            # Get members as a set
            members = redis_client.smembers(index_key)
            # Convert to list of strings
            if members:
                webhook_ids = []  # Initialize once
                # Process each member directly
                for m in members:  # type: ignore
                    if isinstance(m, bytes):
                        webhook_ids.append(m.decode('utf-8'))
                    else:
                        webhook_ids.append(m)
        except Exception as e:
            logger.error(f"Error getting webhook IDs for reference {reference_id}: {str(e)}")
        
        # Get status for each webhook ID
        results = []
        for webhook_id in webhook_ids:
            status = get_webhook_status(webhook_id)
            if status:
                results.append(status)
        
        # Sort by updated_at (most recent first)
        results.sort(key=lambda x: x.get("updated_at", "0"), reverse=True)
        return results
    except Exception as e:
        logger.error(f"Error getting webhook statuses for reference {reference_id}: {str(e)}")
        return []

def update_webhook_status(webhook_id, updates):
    """Update webhook status in Redis with appropriate TTL."""
    current = get_webhook_status(webhook_id)
    if not current:
        return None
    
    # Update the status data
    current.update(updates)
    
    # Ensure updated_at is set to current time
    current["updated_at"] = get_iso_timestamp()
    
    # Get reference_id and task_id from webhook_id
    reference_id, task_id = webhook_id.rsplit("_", 1)
    
    # Store with updated TTL based on new status
    return store_webhook_status(reference_id, task_id, current)

def delete_webhook_status(webhook_id):
    """Delete webhook status from Redis."""
    redis_client = get_redis_client()
    key = f"webhook_status:{webhook_id}"
    
    # Get the status to extract reference_id
    status = get_webhook_status(webhook_id)
    if status:
        reference_id = status.get("reference_id")
        if reference_id:
            # Remove from reference index
            index_key = f"webhook_status:index:{reference_id}"
            redis_client.srem(index_key, webhook_id)
    
    # Delete the status
    redis_client.delete(key)
    return True

def _scan_keys(redis_client, pattern):
    """Helper function to scan Redis keys using SCAN instead of KEYS.
    
    This is more production-friendly for large datasets as it doesn't block Redis.
    
    Args:
        redis_client: Redis client instance
        pattern: Key pattern to match
        
    Returns:
        List of matching keys as strings
    """
    result_keys = []
    cursor = 0
    while True:
        cursor, keys = redis_client.scan(cursor=cursor, match=pattern, count=100)
        # Process each key
        for k in keys:
            if isinstance(k, bytes):
                result_keys.append(k.decode('utf-8'))
            else:
                result_keys.append(k)
        
        # Exit when cursor returns to 0
        if cursor == 0:
            break
    
    return result_keys

def list_webhook_statuses(reference_id=None, status_filter=None, offset=0, limit=10):
    """List webhook statuses from Redis with pagination and filtering."""
    results = []
    try:
        redis_client = get_redis_client()
        
        if reference_id:
            # Get statuses for specific reference_id
            statuses = get_webhook_status_by_reference(reference_id)
            
            # Filter by status if needed
            if status_filter:
                statuses = [item for item in statuses if item.get("status") == status_filter]
                
            results = statuses
        else:
            # Get all reference_id index keys
            all_index_keys = []
            try:
                # Use SCAN instead of KEYS for better production performance
                all_index_keys = _scan_keys(redis_client, "webhook_status:index:*")
            except Exception as e:
                logger.error(f"Error getting webhook index keys: {str(e)}")
            
            # Process each index key
            for index_key in all_index_keys:
                # Extract reference_id from the index key
                ref_id = index_key.replace("webhook_status:index:", "")
                
                # Get statuses for this reference_id
                ref_statuses = get_webhook_status_by_reference(ref_id)
                
                # Filter by status if needed
                if status_filter:
                    ref_statuses = [item for item in ref_statuses if item.get("status") == status_filter]
                
                # Add to results
                results.extend(ref_statuses)
        
        # Sort by updated_at (most recent first)
        results.sort(key=lambda x: x.get("updated_at", "0"), reverse=True)
    except Exception as e:
        logger.error(f"Error listing webhook statuses: {str(e)}")
    
    # Apply pagination
    paginated = results[offset:offset+limit]
    
    return {
        "total": len(results),
        "items": paginated
    }

def write_to_dlq(webhook_id, payload, error, error_type=None):
    """Write a failed webhook to the Dead Letter Queue."""
    try:
        logger.info(f"Writing to DLQ for webhook_id={webhook_id}, error_type={error_type}")
        redis_client = get_redis_client()
        
        dlq_key = f"dead_letter:webhook:{webhook_id}"
        
        dlq_data = {
            "webhook_id": webhook_id,
            "payload": payload,
            "error": error,
            "error_type": error_type,
            "created_at": get_iso_timestamp()
        }
        
        # Debug logging
        logger.info(f"Writing to DLQ: {dlq_key}")
        logger.info(f"DLQ data: {json.dumps(dlq_data)}")
        
        # Store with 30-day TTL (in seconds)
        set_result = redis_client.set(dlq_key, json.dumps(dlq_data), ex=30*24*60*60)
        logger.info(f"Redis SET result for DLQ: {set_result}")
        
        # Add to DLQ index
        sadd_result = redis_client.sadd("dead_letter:webhook:index", webhook_id)
        logger.info(f"Redis SADD result for DLQ index: {sadd_result}")
        
        expire_result = redis_client.expire("dead_letter:webhook:index", 30*24*60*60)
        logger.info(f"Redis EXPIRE result for DLQ index: {expire_result}")
        
        # Check if the entry was actually stored
        get_result = redis_client.get(dlq_key)
        logger.info(f"Verification - Redis GET result for DLQ: {get_result is not None}")
        
        return dlq_data
    except Exception as e:
        logger.error(f"Error writing to DLQ: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": str(e)}

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

@celery_app.task(name="process_firm_compliance_claim", bind=True, max_retries=3, default_retry_delay=60)
def process_firm_compliance_claim(self, request_dict: Dict[str, Any], mode: str):
    """Celery task to process a firm compliance claim asynchronously."""
    reference_id = request_dict.get('reference_id', 'unknown')
    webhook_url = request_dict.get('webhook_url')  # Initialize webhook_url up-front to avoid UnboundLocalError
    start_time = time.time()
    task_counter.labels(task_name='process_firm_compliance_claim', status='started', worker_id=WORKER_ID).inc()
    logger.info(f"Starting Celery task for reference_id={reference_id} with mode={mode}")
    
    try:
        # Add task context to all logs
        task_context = {
            "task_id": self.request.id,
            "reference_id": reference_id,
            "mode": mode,
            "attempt": self.request.retries + 1
        }
        
        # PENDING is the default state, no need to explicitly set it
        
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
            webhook_url = claim.pop("webhook_url", webhook_url)  # Use the pre-initialized webhook_url as fallback

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
                # Use the renamed task
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
                # Use the renamed task
                send_webhook_notification.delay(webhook_url, error_report, reference_id)
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
                # Use the renamed task
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
                # Use the renamed task
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
    finally:
        # Observe task duration on all paths
        task_duration.labels(task_name='process_firm_compliance_claim', worker_id=WORKER_ID).observe(time.time() - start_time)

# Dedicated Celery task for webhook delivery
@celery_app.task(
    name="firm.send_webhook_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
    reject_on_worker_lost=True,
    on_failure=webhook_failure_handler
)
def send_webhook_notification(self, webhook_url: str, payload: Dict[str, Any], reference_id: str):
    """Dedicated Celery task for webhook delivery with robust retry logic."""
    webhook_counter.labels(status='started', worker_id=WORKER_ID).inc()
    webhook_logger = loggers.get("webhook", logger)
    
    # Use a context manager to ensure webhook_duration is always recorded for the entire function
    with webhook_duration.labels(worker_id=WORKER_ID).time():
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
            webhook_counter.labels(status='validation_error', worker_id=WORKER_ID).inc()
            return {
                "status": "error",
                "reference_id": reference_id,
                "message": f"Invalid webhook URL: {webhook_url}",
                "error_type": "validation_error"
            }
        
        # Validate webhook URL format (must start with http:// or https://)
        if not webhook_url.startswith(('http://', 'https://')):
            webhook_logger.error(f"Invalid webhook URL format: {webhook_url}", extra=task_context)
            error_msg = f"Invalid webhook URL format: {webhook_url} - must start with http:// or https://"
            
            # Create a failed status entry
            webhook_id = f"{reference_id}_{self.request.id}"
            status_data = {
                "webhook_id": webhook_id,
                "reference_id": reference_id,
                "task_id": self.request.id,
                "webhook_url": webhook_url,
                "status": "failed",
                "attempts": 1,
                "max_attempts": self.max_retries,
                "response_code": None,
                "error": error_msg,
                "error_type": "validation_error",
                "created_at": get_iso_timestamp(),
                "updated_at": get_iso_timestamp(),
                "correlation_id": generate_correlation_id()
            }
            store_webhook_status(reference_id, self.request.id, status_data)
            
            # Write to DLQ
            write_to_dlq(webhook_id, payload, error_msg, "validation_error")
            
            webhook_counter.labels(status='validation_error', worker_id=WORKER_ID).inc()
            return {
                "status": "error",
                "reference_id": reference_id,
                "message": error_msg,
                "error_type": "validation_error"
            }
        
        if not reference_id or not isinstance(reference_id, str):
            webhook_logger.error(f"Invalid reference_id: {reference_id}", extra=task_context)
            webhook_counter.labels(status='validation_error', worker_id=WORKER_ID).inc()
            return {
                "status": "error",
                "reference_id": reference_id,
                "message": "Invalid reference ID",
                "error_type": "validation_error"
            }
        
        if not isinstance(payload, dict):
            webhook_logger.error(f"Invalid payload type: {type(payload)}", extra=task_context)
            webhook_counter.labels(status='validation_error', worker_id=WORKER_ID).inc()
            return {
                "status": "error",
                "reference_id": reference_id,
                "message": f"Invalid payload type: {type(payload)}",
                "error_type": "validation_error"
            }
    
    # Initialize or update webhook status in Redis
    correlation_id = generate_correlation_id()
    current_time = get_iso_timestamp()
    webhook_id = f"{reference_id}_{self.request.id}"
    current_status = get_webhook_status(webhook_id)
    
    if not current_status:
        # Create new status
        status_data = {
            "webhook_id": webhook_id,
            "reference_id": reference_id,
            "task_id": self.request.id,
            "webhook_url": webhook_url,
            "status": "in_progress",  # Start with in_progress per spec
            "attempts": 1,
            "max_attempts": self.max_retries,
            "response_code": None,
            "error": None,
            "error_type": None,
            "created_at": current_time,
            "updated_at": current_time,
            "correlation_id": correlation_id
        }
        store_webhook_status(reference_id, self.request.id, status_data)
    else:
        # Update existing status
        updates = {
            "attempts": current_status.get("attempts", 0) + 1,
            "status": "in_progress",  # Always set to in_progress before attempting delivery
            "updated_at": current_time
        }
        update_webhook_status(webhook_id, updates)
    
    try:
        webhook_logger.info(f"Attempt {self.request.retries + 1} sending webhook for reference_id={reference_id}", extra=task_context)
        
        # Add correlation ID to task context for consistent logging
        task_context["correlation_id"] = correlation_id
        
        # Use synchronous requests for Celery worker with timeout
        try:
            # Add required headers
            headers = {
                "Content-Type": "application/json",
                "X-Reference-ID": reference_id,
                "X-Correlation-ID": correlation_id
            }
            
            # Send the request
            response = requests.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            # Handle 4xx responses differently - only retry once for client errors
            if 400 <= response.status_code < 500:
                if self.request.retries >= 1:
                    error_msg = f"Permanent client error: HTTP {response.status_code}"
                    webhook_logger.error(f"{error_msg} for reference_id={reference_id}", extra=task_context)
                    
                    # Update status to failed
                    update_webhook_status(webhook_id, {
                        "status": "failed",
                        "response_code": response.status_code,
                        "error": error_msg,
                        "error_type": "permanent_client_error",
                        "updated_at": get_iso_timestamp()
                    })
                    
                    # Write to DLQ
                    write_to_dlq(webhook_id, payload, error_msg, "permanent_client_error")
                    
                    return {
                        "status": "error",
                        "reference_id": reference_id,
                        "message": error_msg,
                        "error_type": "permanent_client_error",
                        "retrying": False
                    }
                else:
                    # First attempt with 4xx - retry once
                    raise requests.exceptions.HTTPError(f"Client error: {response.status_code}")
            
            # For other status codes, use raise_for_status
            response.raise_for_status()  # Raise exception for 5XX status codes
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
        webhook_counter.labels(status='delivered', worker_id=WORKER_ID).inc()
        
        # Update webhook status to delivered in Redis
        update_webhook_status(webhook_id, {
            "status": "delivered",
            "response_code": response.status_code,
            "updated_at": get_iso_timestamp()
        })
        
        # No need for explicit duration tracking - the context manager handles it
        return {
            "status": "success",
            "reference_id": reference_id,
            "response_code": response.status_code
        }
    
    except (requests.Timeout, requests.ConnectionError) as e:
        webhook_counter.labels(status='network_error', worker_id=WORKER_ID).inc()
        error_msg = f"Webhook connection error for reference_id={reference_id}: {str(e)}"
        webhook_logger.error(error_msg, extra=task_context, exc_info=True)
        
        # Check if this is the final retry
        is_final_retry = self.request.retries >= self.max_retries
        
        # Update webhook status with error in Redis
        update_webhook_status(webhook_id, {
            "status": "failed" if is_final_retry else "retrying",
            "error": error_msg,
            "error_type": "network_error",
            "updated_at": get_iso_timestamp()
        })
        
        with open(webhook_log_file, "a") as f:
            f.write(f"[{self.request.id}] {error_msg}\n")
        
        # If this is the final retry, write to DLQ
        if is_final_retry:
            logger.info(f"Final retry failed for webhook {webhook_id}, writing to DLQ")
            dlq_result = write_to_dlq(webhook_id, payload, error_msg, "network_error")
            logger.info(f"DLQ write result: {dlq_result}")
            webhook_counter.labels(status='failed', worker_id=WORKER_ID).inc()
            logger.error(f"Final retry failed for webhook {webhook_id}: {error_msg}")
            return {
                "status": "failed",
                "reference_id": reference_id,
                "message": f"Webhook delivery failed after {self.request.retries + 1} attempts: {str(e)}",
                "error_type": "network_error",
                "retrying": False
            }
        
        # Exponential backoff with jitter for network-related errors
        retry_countdown = min(2 ** self.request.retries * 30 + random.uniform(0, 30), 300)
        try:
            self.retry(exc=e, countdown=retry_countdown)
        except self.MaxRetriesExceededError:
            webhook_logger.error(f"Max retries exceeded for reference_id={reference_id}", extra=task_context)
            # Update status to failed
            update_webhook_status(webhook_id, {
                "status": "failed",
                "error_type": "network_error",
                "updated_at": get_iso_timestamp()
            })
            
            # Write to DLQ
            write_to_dlq(webhook_id, payload, error_msg, "network_error")
            return {
                "status": "error",
                "reference_id": reference_id,
                "message": f"Webhook delivery failed after {self.request.retries + 1} attempts: {str(e)}",
                "error_type": "network_error",
                "retrying": False
            }
        
        # No need for explicit duration tracking - the context manager handles it
        return {
            "status": "error",
            "reference_id": reference_id,
            "message": f"Webhook delivery failed: {str(e)}",
            "error_type": "network_error",
            "retrying": True
        }
        
    except Exception as e:
        webhook_counter.labels(status='unexpected_error', worker_id=WORKER_ID).inc()
        error_msg = f"Error sending webhook for reference_id={reference_id}: {str(e)}"
        webhook_logger.error(error_msg, extra=task_context, exc_info=True)
        
        # Capture stack trace for better debugging
        stack_trace = traceback.format_exc()
        webhook_logger.error(f"Stack trace: {stack_trace}", extra=task_context)
        
        # Check if this is the final retry
        is_final_retry = self.request.retries >= self.max_retries
        
        # Update webhook status with error in Redis
        update_webhook_status(webhook_id, {
            "status": "failed" if is_final_retry else "retrying",
            "error": error_msg,
            "error_type": "unexpected_error",
            "updated_at": get_iso_timestamp()
        })
        
        # Write to dedicated webhook error log file
        with open(webhook_log_file, "a") as f:
            f.write(f"[{self.request.id}] {error_msg}\n")
            f.write(f"[{self.request.id}] Stack trace: {stack_trace}\n")
        
        # If this is the final retry, write to DLQ
        if is_final_retry:
            logger.info(f"Final retry failed for webhook {webhook_id}, writing to DLQ")
            dlq_result = write_to_dlq(webhook_id, payload, error_msg, "unexpected_error")
            logger.info(f"DLQ write result: {dlq_result}")
            webhook_counter.labels(status='failed', worker_id=WORKER_ID).inc()
            logger.error(f"Final retry failed for webhook {webhook_id}: {error_msg}")
            return {
                "status": "failed",
                "reference_id": reference_id,
                "message": f"Webhook delivery failed after {self.request.retries + 1} attempts: {str(e)}",
                "error_type": "unexpected_error",
                "retrying": False
            }
        
        # Exponential backoff with jitter for general errors
        retry_countdown = min(2 ** self.request.retries * 30 + random.uniform(0, 30), 300)
        try:
            self.retry(exc=e, countdown=retry_countdown)
        except self.MaxRetriesExceededError:
            webhook_logger.error(f"Max retries exceeded for reference_id={reference_id}", extra=task_context)
            # Update status to failed
            update_webhook_status(webhook_id, {
                "status": "failed",
                "error_type": "unexpected_error",
                "updated_at": get_iso_timestamp()
            })
            
            # Write to DLQ
            write_to_dlq(webhook_id, payload, error_msg, "unexpected_error")
            return {
                "status": "error",
                "reference_id": reference_id,
                "message": f"Webhook delivery failed after {self.request.retries + 1} attempts: {str(e)}",
                "error_type": "unexpected_error",
                "retrying": False
            }
        
        # No need for explicit duration tracking - the context manager handles it
        return {
            "status": "error",
            "reference_id": reference_id,
            "message": f"Webhook delivery failed: {str(e)}",
            "error_type": "unexpected_error",
            "retrying": True
        }

# The async send_to_webhook function has been removed
# All webhook deliveries now use the Celery task send_webhook_notification

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
            # Use the Celery task instead of the async function
            send_webhook_notification.delay(webhook_url, report, request.reference_id)
        
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
# Define a Pydantic model for the test webhook request
class WebhookTestRequest(BaseModel):
    webhook_url: str
    test_payload: Optional[Dict[str, Any]] = None

@app.post("/test-webhook")
async def test_webhook(request: WebhookTestRequest):
    """
    Test a webhook URL by sending a test payload.
    
    Args:
        request (WebhookTestRequest): The webhook test request containing:
            - webhook_url: The webhook URL to test
            - test_payload: Optional custom payload to send
        
    Returns:
        Dict[str, Any]: Result of the webhook test
    """
    if not request.webhook_url:
        raise HTTPException(status_code=400, detail="webhook_url is required")
    
    test_payload = request.test_payload
    if test_payload is None:
        test_payload = {
            "test": True,
            "timestamp": get_iso_timestamp(),
            "message": "This is a test webhook payload"
        }
    
    reference_id = f"test-{get_iso_timestamp()}"
    # Use the Celery task instead of the async function
    task = send_webhook_notification.delay(request.webhook_url, test_payload, reference_id)
    
    return {
        "status": "queued",
        "message": "Webhook test queued for delivery",
        "webhook_url": request.webhook_url,
        "task_id": task.id,
        "reference_id": reference_id
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
@app.get("/webhook-status/{webhook_id}")
async def get_webhook_status_endpoint(webhook_id: str):
    """
    Get the status of a specific webhook delivery by webhook_id.
    
    Args:
        webhook_id (str): The webhook ID to check status for
        
    Returns:
        Dict[str, Any]: Webhook status details
    """
    status = get_webhook_status(webhook_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"No webhook status found for webhook_id={webhook_id}")
    
    return status

@app.get("/webhook-statuses")
async def list_webhook_statuses_endpoint(
    reference_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Optional[str] = None
):
    """
    List webhook statuses with optional filtering and pagination.
    
    Args:
        reference_id (str, optional): Filter by reference_id
        page (int): Page number (1-based)
        page_size (int): Number of items per page
        status (str, optional): Filter by status (pending, in_progress, retrying, delivered, failed)
        
    Returns:
        Dict[str, Any]: Paginated list of webhook statuses
    """
    offset = (page - 1) * page_size
    result = list_webhook_statuses(reference_id, status, offset, page_size)
    
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
async def cleanup_old_webhook_statuses(
    status: Optional[str] = None,
    older_than_days: Optional[int] = None,
    reference_id: Optional[str] = None
):
    """
    Manually trigger cleanup of old webhook statuses.
    This is typically not needed as Redis TTL handles automatic cleanup,
    but can be useful for immediate cleanup or testing.
    
    Args:
        status (str, optional): Filter by status (pending, in_progress, retrying, delivered, failed)
        older_than_days (int, optional): Only clean up statuses older than this many days
        reference_id (str, optional): Only clean up statuses for this reference_id
        
    Returns:
        Dict[str, Any]: Cleanup results
    """
    redis_client = get_redis_client()
    cleaned = 0
    errors = 0
    
    # Get all index keys or just the one for the specified reference_id
    if reference_id:
        index_keys = [f"webhook_status:index:{reference_id}"]
    else:
        # Use SCAN instead of KEYS for better production performance
        try:
            index_keys = _scan_keys(redis_client, "webhook_status:index:*")
        except Exception as e:
            logger.error(f"Error getting webhook index keys: {str(e)}")
            index_keys = []
    
    try:
        # Process each index key
        for index_key_str in index_keys:
            try:
                # Get webhook IDs for this index - use synchronous Redis client
                try:
                    webhook_ids_raw = redis_client.smembers(index_key_str)
                    webhook_ids = []
                    # Process each item directly
                    for item in webhook_ids_raw:  # type: ignore
                        if isinstance(item, bytes):
                            webhook_ids.append(item.decode('utf-8'))
                        else:
                            webhook_ids.append(item)
                except Exception as e:
                    logger.error(f"Error getting webhook IDs for index {index_key_str}: {str(e)}")
                    webhook_ids = []
                
                # Process each webhook ID
                for webhook_id_str in webhook_ids:
                    status_data = get_webhook_status(webhook_id_str)
                    
                    # If status doesn't exist but is in the index, remove from index
                    if not status_data:
                        redis_client.srem(index_key_str, webhook_id_str)
                        cleaned += 1
                        continue
                    
                    # Apply status filter if provided
                    if status and status_data.get("status") != status:
                        continue
                    
                    # Check if status is old enough to be cleaned up
                    updated_at = status_data.get("updated_at", "0")
                    try:
                        # Convert to timestamp if it's not already
                        if not isinstance(updated_at, (int, float)):
                            # Try to parse as ISO format or timestamp string
                            try:
                                dt = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                                updated_timestamp = dt.timestamp()
                            except Exception:
                                updated_timestamp = float(updated_at)
                        else:
                            updated_timestamp = float(updated_at)
                            
                        current_time = time.time()
                        
                        # Apply age filter if provided
                        if older_than_days and (current_time - updated_timestamp) < (older_than_days * 86400):
                            continue
                        
                        # Apply cleanup rules based on status
                        status_type = status_data.get("status", "pending")
                        if status_type == "delivered" and current_time - updated_timestamp > WEBHOOK_TTL_SUCCESS:
                            # Delivered webhooks expire after 30 minutes
                            delete_webhook_status(webhook_id_str)
                            cleaned += 1
                            logger.info(f"Cleaned up delivered webhook status for {webhook_id_str} (age: {current_time - updated_timestamp:.1f}s)")
                        elif status_type == "failed" and current_time - updated_timestamp > WEBHOOK_TTL_FAILED:
                            # Failed webhooks expire after 7 days
                            delete_webhook_status(webhook_id_str)
                            cleaned += 1
                            logger.info(f"Cleaned up failed webhook status for {webhook_id_str} (age: {(current_time - updated_timestamp)/86400:.1f} days)")
                        elif status_type in ["pending", "in_progress", "retrying"] and current_time - updated_timestamp > WEBHOOK_TTL_PENDING:
                            # Pending/in_progress/retrying webhooks expire after 7 days
                            delete_webhook_status(webhook_id_str)
                            cleaned += 1
                            logger.info(f"Cleaned up {status_type} webhook status for {webhook_id_str} (age: {(current_time - updated_timestamp)/86400:.1f} days)")
                    except Exception as e:
                        logger.error(f"Error cleaning up webhook status {webhook_id_str}: {str(e)}")
                        errors += 1
            except Exception as e:
                logger.error(f"Error processing index key {index_key_str}: {str(e)}")
                continue
    except Exception as e:
        logger.error(f"Error in webhook cleanup: {str(e)}")
        errors += 1
    
    return {
        "status": "success",
        "cleaned": cleaned,
        "errors": errors,
        "message": f"Cleaned up {cleaned} old webhook statuses with {errors} errors"
    }

@app.delete("/webhook-status/{webhook_id}")
async def delete_webhook_status_endpoint(webhook_id: str):
    """
    Delete webhook status for a specific webhook_id.
    
    Args:
        webhook_id (str): The webhook ID to delete status for
        
    Returns:
        Dict[str, Any]: Confirmation message
    """
    status = get_webhook_status(webhook_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"No webhook status found for webhook_id={webhook_id}")
    
    delete_webhook_status(webhook_id)
    
    return {
        "status": "success",
        "message": f"Webhook status for webhook_id={webhook_id} deleted"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000, log_level="info")