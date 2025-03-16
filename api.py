"""
==============================================
📌 FIRM COMPLIANCE CLAIM PROCESSING API OVERVIEW
==============================================
🗂 PURPOSE
This FastAPI application provides endpoints for processing business compliance claims
and managing cached compliance data. It currently supports only a basic processing mode,
along with cache management and compliance report retrieval features.

🔧 USAGE
Run the API with `uvicorn api:app --host 0.0.0.0 --port 8000 --log-level info`.
Use endpoints like `/process-claim-basic`, `/cache/clear`, `/compliance/latest`, etc.

📝 NOTES
- Integrates `cache_manager` for cache operations and `firm-business` for claim processing.
- Uses `FirmServicesFacade` for claim processing and `CacheManager` for cache management.
- Supports asynchronous webhook notifications for processed claims.
"""

import json
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import aiohttp
import asyncio
import logging

from services.firm_services import FirmServicesFacade  # Updated import
from services.firm_business import process_claim  # Updated import
from cache_manager.cache_operations import CacheManager
from cache_manager.firm_compliance_handler import FirmComplianceHandler
from cache_manager.file_handler import FileHandler
# Note: FirmSummaryGenerator is a placeholder; uncomment when implemented
# from cache_manager.firm_summary_generator import FirmSummaryGenerator

# Setup basic logging (assuming no logger_config module yet)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("api")

# Initialize FastAPI app
app = FastAPI(
    title="Firm Compliance Claim Processing API",
    description="API for processing business compliance claims and managing cached compliance data with basic mode support",
    version="1.0.0"
)

# Initialize services and cache management (singleton instances)
facade = FirmServicesFacade()  # Updated to use FirmServicesFacade
cache_manager = CacheManager()
file_handler = FileHandler(cache_manager.cache_folder)
compliance_handler = FirmComplianceHandler(file_handler.base_path)
# Placeholder for future summary generator
# summary_generator = FirmSummaryGenerator(file_handler=file_handler, compliance_handler=compliance_handler)

# Define processing mode (only basic mode implemented)
PROCESSING_MODES = {
    "basic": {
        "skip_disciplinary": True,  # Maps to skip_financials in process_claim
        "skip_regulatory": True,    # Maps to skip_legal in process_claim
        "description": "Minimal processing: skips disciplinary and regulatory reviews"
    }
}

# Define the request model using Pydantic with mandatory fields
class ClaimRequest(BaseModel):
    reference_id: str
    business_ref: str
    business_name: str
    tax_id: str
    organization_crd: Optional[str] = None
    webhook_url: Optional[str] = None

    class Config:
        extra = "allow"

async def send_to_webhook(webhook_url: str, report: Dict[str, Any], reference_id: str):
    """Asynchronously send the report to the specified webhook URL."""
    async with aiohttp.ClientSession() as session:
        try:
            logger.info(f"Sending report to webhook URL: {webhook_url} for reference_id={reference_id}")
            async with session.post(webhook_url, json=report) as response:
                if response.status == 200:
                    logger.info(f"Successfully sent report to webhook for reference_id={reference_id}")
                else:
                    logger.error(f"Webhook delivery failed for reference_id={reference_id}: Status {response.status}, Response: {await response.text()}")
        except Exception as e:
            logger.error(f"Error sending to webhook for reference_id={reference_id}: {str(e)}", exc_info=True)

async def process_claim_helper(request: ClaimRequest, mode: str) -> Dict[str, Any]:
    """
    Helper function to process a claim with the specified mode.

    Args:
        request (ClaimRequest): The claim data to process.
        mode (str): Processing mode ("basic").

    Returns:
        Dict[str, Any]: Processed compliance report.
    """
    logger.info(f"Processing claim with mode='{mode}': {request.dict()}")

    # Extract mode settings
    mode_settings = PROCESSING_MODES[mode]

    # Convert Pydantic model to dict for process_claim
    claim = request.dict(exclude_unset=True)
    business_ref = claim.pop("business_ref")
    webhook_url = claim.pop("webhook_url", None)

    try:
        # Process the claim using firm-business.py with updated parameters
        report = process_claim(
            claim=claim,
            facade=facade,
            business_ref=business_ref,
            skip_financials=mode_settings["skip_disciplinary"],
            skip_legal=mode_settings["skip_regulatory"]
        )
        
        if report is None:
            logger.error(f"Failed to process claim for reference_id={request.reference_id}: process_claim returned None")
            raise HTTPException(status_code=500, detail="Claim processing failed unexpectedly")

        # Report is saved to cache/<business_ref>/ by process_claim
        logger.info(f"Successfully processed claim for reference_id={request.reference_id} with mode={mode}")

        # Handle webhook if provided
        if webhook_url:
            asyncio.create_task(send_to_webhook(webhook_url, report, request.reference_id))
        
        return report

    except Exception as e:
        logger.error(f"Error processing claim for reference_id={request.reference_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Claim Processing Endpoint
@app.post("/process-claim-basic", response_model=Dict[str, Any])
async def process_claim_basic(request: ClaimRequest):
    """Process a claim with basic mode (skips all reviews)."""
    return await process_claim_helper(request, "basic")

@app.get("/processing-modes")
async def get_processing_modes():
    """Return the available processing modes."""
    return PROCESSING_MODES

# Cache Management Endpoints
@app.post("/cache/clear/{business_ref}")
async def clear_cache(business_ref: str):
    """
    Clear all cache (except FirmComplianceReport) for a specific business.

    Args:
        business_ref (str): Business identifier (e.g., "BIZ_001").

    Returns:
        Dict[str, Any]: JSON response with clearance details.
    """
    result = cache_manager.clear_cache(business_ref)
    return json.loads(result)

@app.post("/cache/clear-all")
async def clear_all_cache():
    """
    Clear all cache (except FirmComplianceReport) across all businesses.

    Returns:
        Dict[str, Any]: JSON response with clearance details.
    """
    result = cache_manager.clear_all_cache()
    return json.loads(result)

@app.post("/cache/clear-agent/{business_ref}/{agent_name}")
async def clear_agent_cache(business_ref: str, agent_name: str):
    """
    Clear cache for a specific agent under a business.

    Args:
        business_ref (str): Business identifier (e.g., "BIZ_001").
        agent_name (str): Agent name (e.g., "SEC_Search_Agent").

    Returns:
        Dict[str, Any]: JSON response with clearance details.
    """
    result = cache_manager.clear_agent_cache(business_ref, agent_name)
    return json.loads(result)

@app.get("/cache/list")
async def list_cache(business_ref: Optional[str] = None, page: int = 1, page_size: int = 10):
    """
    List all cached files for a business or all businesses with pagination.

    Args:
        business_ref (Optional[str]): Business identifier or None/"ALL" for all businesses.
        page (int): Page number (default: 1).
        page_size (int): Items per page (default: 10).

    Returns:
        Dict[str, Any]: JSON response with cache contents.
    """
    result = cache_manager.list_cache(business_ref or "ALL", page, page_size)
    return json.loads(result)

@app.post("/cache/cleanup-stale")
async def cleanup_stale_cache():
    """
    Delete stale cache older than 90 days (except FirmComplianceReport).

    Returns:
        Dict[str, Any]: JSON response with cleanup details.
    """
    result = cache_manager.cleanup_stale_cache()
    return json.loads(result)

# Compliance Retrieval Endpoints
@app.get("/compliance/latest/{business_ref}")
async def get_latest_compliance(business_ref: str):
    """
    Retrieve the latest compliance report for a business.

    Args:
        business_ref (str): Business identifier (e.g., "BIZ_001").

    Returns:
        Dict[str, Any]: JSON response with the latest report.
    """
    result = compliance_handler.get_latest_compliance_report(business_ref)
    return json.loads(result)

@app.get("/compliance/by-ref/{business_ref}/{reference_id}")
async def get_compliance_by_ref(business_ref: str, reference_id: str):
    """
    Retrieve a compliance report by reference_id for a business.

    Args:
        business_ref (str): Business identifier (e.g., "BIZ_001").
        reference_id (str): Report identifier (e.g., "B123").

    Returns:
        Dict[str, Any]: JSON response with the report.
    """
    result = compliance_handler.get_compliance_report_by_ref(business_ref, reference_id)
    return json.loads(result)

@app.get("/compliance/list")
async def list_compliance_reports(business_ref: Optional[str] = None, page: int = 1, page_size: int = 10):
    """
    List all compliance reports for a business or all businesses with pagination.

    Args:
        business_ref (Optional[str]): Business identifier or None for all businesses.
        page (int): Page number (default: 1).
        page_size (int): Items per page (default: 10).

    Returns:
        Dict[str, Any]: JSON response with report list.
    """
    result = compliance_handler.list_compliance_reports(business_ref, page, page_size)
    return json.loads(result)

# Placeholder Analytics Endpoints (to be implemented with FirmSummaryGenerator)
@app.get("/compliance/summary/{business_ref}")
async def get_compliance_summary(business_ref: str, page: int = 1, page_size: int = 10):
    """
    Get a compliance summary for a specific business with pagination (placeholder).

    Args:
        business_ref (str): Business identifier (e.g., "BIZ_001").
        page (int): Page number (default: 1).
        page_size (int): Items per page (default: 10).

    Returns:
        Dict[str, Any]: JSON response (stubbed).
    """
    return {"status": "error", "message": "Summary generation not yet implemented"}

@app.get("/compliance/all-summaries")
async def get_all_compliance_summaries(page: int = 1, page_size: int = 10):
    """
    Get a compliance summary for all businesses with pagination (placeholder).

    Args:
        page (int): Page number (default: 1).
        page_size (int): Items per page (default: 10).

    Returns:
        Dict[str, Any]: JSON response (stubbed).
    """
    return {"status": "error", "message": "All summaries generation not yet implemented"}

@app.on_event("shutdown")
def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down API server")
    # No cleanup needed for FirmServicesFacade

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")