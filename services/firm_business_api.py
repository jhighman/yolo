"""
firm_business_api.py

This module provides a FastAPI application with endpoints for processing business compliance claims.
It supports basic and complete processing modes, integrates with firm-business.py for data processing,
and provides webhook support for asynchronous report delivery.

CSV Input Format:
For CSV input, the expected format is:
referenceId,crdNumber,entityName

Example:
SPID_EntityBioId,288933,"CLEAR STREET LLC"
"""

import json
import logging
from typing import Dict, Any, Optional
import asyncio
import aiohttp
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl, root_validator, validator
import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from utils.logging_config import setup_logging
from services.firm_services import FirmServicesFacade
from services.firm_business import process_claim

# Initialize logging
loggers = setup_logging(debug=True)
logger = loggers.get('firm_business_api', logging.getLogger(__name__))

# Initialize FastAPI application
app = FastAPI(
    title="Firm Business Compliance API",
    description="API for processing business compliance claims and generating evaluation reports",
    version="1.0.0"
)

# Initialize facade
facade = FirmServicesFacade()

# Define processing modes and their settings
PROCESSING_MODES = {
    "basic": {
        "skip_financials": True,
        "skip_legal": True,
        "description": "Minimal processing: skips financial and legal reviews"
    },
    "complete": {
        "skip_financials": False,
        "skip_legal": False,
        "description": "Full processing: includes all reviews (financial, legal)"
    }
}

class ClaimRequest(BaseModel):
    """Validates incoming claim data for the simplified API."""
    # Required fields
    referenceId: str
    crdNumber: str
    entityName: str
    webhook_url: Optional[HttpUrl] = None

    class Config:
        extra = "allow"  # Allow additional fields

    @validator("referenceId")
    def validate_reference_id(cls, v):
        """Validate that referenceId is not empty."""
        if not v or not v.strip():
            logger.error("Validation failed: referenceId is empty")
            raise ValueError("referenceId cannot be empty")
        return v.strip()

    @validator("crdNumber")
    def validate_crd_number(cls, v):
        """Validate that crdNumber is not empty."""
        if not v or not v.strip():
            logger.error("Validation failed: crdNumber is empty")
            raise ValueError("crdNumber cannot be empty")
        return v.strip()
        
    @validator("entityName")
    def validate_entity_name(cls, v):
        """Validate that entityName is not empty."""
        if not v or not v.strip():
            logger.error("Validation failed: entityName is empty")
            raise ValueError("entityName cannot be empty")
        return v.strip()

async def send_to_webhook(webhook_url: str, report: Dict[str, Any], reference_id: str) -> None:
    """
    Asynchronously sends the report to a specified webhook URL.
    
    Args:
        webhook_url: URL to send the report to
        report: The compliance report to send
        reference_id: Claim identifier for logging
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=report) as response:
                if response.status == 200:
                    logger.info(f"Successfully sent report to webhook", extra={
                        "reference_id": reference_id,
                        "webhook_url": webhook_url,
                        "status": response.status
                    })
                else:
                    logger.error(f"Failed to send report to webhook", extra={
                        "reference_id": reference_id,
                        "webhook_url": webhook_url,
                        "status": response.status,
                        "response_text": await response.text()
                    })
    except Exception as e:
        logger.error(f"Error sending report to webhook", extra={
            "reference_id": reference_id,
            "webhook_url": webhook_url,
            "error": str(e),
            "error_type": type(e).__name__
        })

async def process_claim_helper(request: ClaimRequest, mode: str) -> Dict[str, Any]:
    """
    Helper function to process a claim with the specified mode.
    
    Args:
        request: The validated claim request
        mode: Processing mode ("basic" or "complete")
        
    Returns:
        Dictionary containing the compliance report
        
    Raises:
        HTTPException: If processing fails
    """
    logger.info(f"Processing claim in {mode} mode", extra={
        "reference_id": request.referenceId,
        "entity_name": request.entityName,
        "mode": mode
    })
    
    try:
        # Get mode settings
        mode_settings = PROCESSING_MODES[mode]
        
        # Convert request to dict and remove webhook_url
        claim_dict = request.dict()
        webhook_url = claim_dict.pop("webhook_url", None)
        
        # Map the new API fields to the internal claim format
        internal_claim = {
            "reference_id": claim_dict.get("referenceId"),
            "business_ref": claim_dict.get("referenceId"),  # Use referenceId as business_ref
            "organization_crd": claim_dict.get("crdNumber"),
            "business_name": claim_dict.get("entityName")
        }
        
        # Process claim
        report = process_claim(
            claim=internal_claim,
            facade=facade,
            business_ref=internal_claim.get("business_ref"),
            skip_financials=mode_settings["skip_financials"],
            skip_legal=mode_settings["skip_legal"]
        )
        
        # Send to webhook if URL provided
        if webhook_url:
            asyncio.create_task(send_to_webhook(webhook_url, report, request.referenceId))
        
        return report
        
    except Exception as e:
        logger.error(f"Error processing claim", extra={
            "reference_id": request.referenceId,
            "entity_name": request.entityName,
            "mode": mode,
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise HTTPException(
            status_code=500,
            detail=f"Error processing claim: {str(e)}"
        )

@app.post("/process-claim-basic")
async def process_claim_basic(request: ClaimRequest) -> Dict[str, Any]:
    """Process a claim in basic mode (skips financial and legal reviews)."""
    return await process_claim_helper(request, "basic")

@app.post("/process-claim-complete")
async def process_claim_complete(request: ClaimRequest) -> Dict[str, Any]:
    """Process a claim in complete mode (includes all reviews)."""
    return await process_claim_helper(request, "complete")

@app.get("/processing-modes")
async def get_processing_modes() -> Dict[str, Any]:
    """Get available processing modes and their configurations."""
    return PROCESSING_MODES

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on API shutdown."""
    logger.info("Shutting down API")
    try:
        # Use a more defensive approach to cleanup
        if facade is not None:
            cleanup_method = getattr(facade, 'cleanup', None)
            if callable(cleanup_method):
                cleanup_method()
                logger.info("Successfully cleaned up resources")
            else:
                logger.info("No cleanup method available on facade")
        else:
            logger.info("No facade instance to clean up")
    except Exception as e:
        logger.error(f"Error during cleanup", extra={
            "error": str(e),
            "error_type": type(e).__name__
        })