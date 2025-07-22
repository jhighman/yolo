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

# Simple in-memory storage for webhook statuses
# In a production environment, this would be replaced with a database
webhook_statuses = {}

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
    """
    Celery task to process a firm compliance claim asynchronously.
    
    Args:
        request_dict (Dict[str, Any]): Claim request data.
        mode (str): Processing mode ("basic", "extended", "complete").
    
    Returns:
        Dict[str, Any]: Processed compliance report or error details.
    """
    logger.info(f"Starting Celery task for reference_id={request_dict['reference_id']} with mode={mode}")
    
    self.update_state(state="PENDING", meta={"reference_id": request_dict['reference_id']})
    
    try:
        request = ClaimRequest(**request_dict)
        mode_settings = PROCESSING_MODES[mode]
        claim = request.dict(exclude_unset=True)
        business_ref = claim.get("business_ref")
        webhook_url = claim.pop("webhook_url", None)

        if "_id" in claim and isinstance(claim["_id"], dict) and "$oid" in claim["_id"]:
            claim["mongo_id"] = claim["_id"]["$oid"]

        report = process_claim(
            claim=claim,
            facade=celery_facade,  # Use the Celery worker's facade instance
            business_ref=business_ref,
            skip_financials=mode_settings["skip_financials"],
            skip_legal=mode_settings["skip_legal"]
        )
        
        if report is None:
            logger.error(f"Failed to process claim for reference_id={request.reference_id}: process_claim returned None")
            raise ValueError("Claim processing failed unexpectedly")

        complete_claim = claim.copy()
        complete_claim["business_ref"] = business_ref
        report["claim"] = complete_claim
        
        logger.info(f"Successfully processed claim for reference_id={request.reference_id}")

        if webhook_url:
            # Queue webhook delivery as a separate task with retries
            logger.info(f"Queuing webhook delivery for reference_id={request.reference_id}")
            send_webhook_notification.delay(webhook_url, report, request.reference_id)
        
        return report
    
    except Exception as e:
        logger.error(f"Error processing claim for reference_id={request_dict['reference_id']}: {str(e)}", exc_info=True)
        error_report = {
            "status": "error",
            "reference_id": request_dict["reference_id"],
            "message": f"Claim processing failed: {str(e)}"
        }
        if webhook_url:
            # Queue webhook delivery for error report
            logger.info(f"Queuing webhook delivery for error report, reference_id={request_dict['reference_id']}")
            send_webhook_notification.delay(webhook_url, error_report, request_dict["reference_id"])
        self.retry(exc=e, countdown=60)
        return error_report

# Dedicated Celery task for webhook delivery
@celery_app.task(name="send_webhook_notification", bind=True, max_retries=5, default_retry_delay=30)
def send_webhook_notification(self, webhook_url: str, report: Dict[str, Any], reference_id: str):
    """
    Dedicated Celery task for webhook delivery with robust retry logic.
    
    Args:
        webhook_url (str): The URL to send the webhook to
        report (Dict[str, Any]): The report data to send
        reference_id (str): Reference ID for tracking
        
    Returns:
        bool: True if successful, raises exception on failure (which triggers retry)
    """
    webhook_logger = loggers.get("webhook", logger)
    
    # Create a webhook error log file if it doesn't exist
    webhook_log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(webhook_log_dir, exist_ok=True)
    webhook_log_file = os.path.join(webhook_log_dir, "webhook_errors.log")
    
    # Initialize or update webhook status
    current_time = self.request.id or str(time.time())
    if reference_id not in webhook_statuses:
        webhook_statuses[reference_id] = {
            "reference_id": reference_id,
            "webhook_url": webhook_url,
            "task_id": self.request.id,
            "attempts": 0,
            "last_attempt": None,
            "status": "pending",
            "response_code": None,
            "error": None,
            "created_at": current_time,
            "updated_at": current_time
        }
    
    # Update attempt count and status
    webhook_statuses[reference_id]["attempts"] += 1
    webhook_statuses[reference_id]["last_attempt"] = current_time
    webhook_statuses[reference_id]["status"] = "retrying" if self.request.retries > 0 else "pending"
    webhook_statuses[reference_id]["updated_at"] = current_time
    
    try:
        webhook_logger.info(f"Attempt {self.request.retries + 1} sending webhook for reference_id={reference_id}")
        
        # Add timestamp and attempt number to the report for tracking
        if isinstance(report, dict):
            report["webhook_sent_at"] = self.request.id
            report["webhook_attempt"] = self.request.retries + 1
        
        # Use synchronous requests for Celery worker
        response = requests.post(webhook_url, json=report, timeout=30)
        
        if response.status_code == 200:
            webhook_logger.info(f"Successfully sent webhook for reference_id={reference_id}")
            
            # Update webhook status to success
            webhook_statuses[reference_id]["status"] = "success"
            webhook_statuses[reference_id]["response_code"] = response.status_code
            webhook_statuses[reference_id]["updated_at"] = str(time.time())
            
            return True
        else:
            error_msg = f"Webhook delivery failed for reference_id={reference_id}: Status {response.status_code}, Response: {response.text}"
            webhook_logger.error(error_msg)
            
            # Update webhook status with error
            webhook_statuses[reference_id]["status"] = "failed"
            webhook_statuses[reference_id]["response_code"] = response.status_code
            webhook_statuses[reference_id]["error"] = error_msg
            webhook_statuses[reference_id]["updated_at"] = str(time.time())
            
            # Write to dedicated webhook error log file
            with open(webhook_log_file, "a") as f:
                f.write(f"[{self.request.id}] {error_msg}\n")
            
            raise Exception(f"Webhook failed with status {response.status_code}: {response.text}")
    
    except (requests.Timeout, requests.ConnectionError) as e:
        error_msg = f"Webhook connection error for reference_id={reference_id}: {str(e)}"
        webhook_logger.error(error_msg)
        
        # Update webhook status with error
        webhook_statuses[reference_id]["status"] = "retrying"
        webhook_statuses[reference_id]["error"] = error_msg
        webhook_statuses[reference_id]["updated_at"] = str(time.time())
        
        with open(webhook_log_file, "a") as f:
            f.write(f"[{self.request.id}] {error_msg}\n")
        
        # Exponential backoff with jitter for network-related errors
        retry_countdown = min(2 ** self.request.retries * 30 + random.uniform(0, 30), 300)
        self.retry(exc=e, countdown=retry_countdown)
        
    except Exception as e:
        error_msg = f"Error sending webhook for reference_id={reference_id}: {str(e)}"
        webhook_logger.error(error_msg, exc_info=True)
        
        # Update webhook status with error
        webhook_statuses[reference_id]["status"] = "retrying"
        webhook_statuses[reference_id]["error"] = error_msg
        webhook_statuses[reference_id]["updated_at"] = str(time.time())
        
        # Write to dedicated webhook error log file
        with open(webhook_log_file, "a") as f:
            f.write(f"[{self.request.id}] {error_msg}\n")
        
        # Exponential backoff with jitter for general errors
        retry_countdown = min(2 ** self.request.retries * 30 + random.uniform(0, 30), 300)
        self.retry(exc=e, countdown=retry_countdown)

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
async def get_webhook_status(reference_id: str):
    """
    Get the status of webhook deliveries for a specific reference_id.
    
    Args:
        reference_id (str): The reference ID to check webhook status for
        
    Returns:
        Dict[str, Any]: Webhook status details
    """
    if reference_id not in webhook_statuses:
        raise HTTPException(status_code=404, detail=f"No webhook status found for reference_id={reference_id}")
    
    return webhook_statuses[reference_id]

@app.get("/webhook-statuses")
async def list_webhook_statuses(
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
    filtered_statuses: List[Dict[str, Any]] = []
    
    for webhook_status in webhook_statuses.values():
        if status is None or webhook_status["status"] == status:
            filtered_statuses.append(webhook_status)
    
    # Sort by updated_at (most recent first)
    filtered_statuses.sort(key=lambda x: x["updated_at"], reverse=True)
    
    # Paginate
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_statuses = filtered_statuses[start_idx:end_idx]
    
    return {
        "total": len(filtered_statuses),
        "page": page,
        "page_size": page_size,
        "pages": (len(filtered_statuses) + page_size - 1) // page_size,
        "statuses": paginated_statuses
    }

@app.delete("/webhook-status/{reference_id}")
async def delete_webhook_status(reference_id: str):
    """
    Delete webhook status for a specific reference_id.
    
    Args:
        reference_id (str): The reference ID to delete webhook status for
        
    Returns:
        Dict[str, Any]: Confirmation message
    """
    if reference_id not in webhook_statuses:
        raise HTTPException(status_code=404, detail=f"No webhook status found for reference_id={reference_id}")
    
    del webhook_statuses[reference_id]
    
    return {
        "status": "success",
        "message": f"Webhook status for reference_id={reference_id} deleted"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000, log_level="info")