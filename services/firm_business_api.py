"""
firm_business_api.py

This module provides a FastAPI application with endpoints for processing business compliance claims.
It supports basic and complete processing modes, integrates with firm-business.py for data processing,
and provides webhook support for asynchronous report delivery.
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
    """Validates incoming claim data."""
    # Required fields
    reference_id: str
    business_ref: str
    
    # Optional fields (at least one identifier required)
    business_name: Optional[str] = None
    tax_id: Optional[str] = None
    organization_crd: Optional[str] = None
    business_location: Optional[str] = None
    webhook_url: Optional[HttpUrl] = None

    class Config:
        extra = "allow"  # Allow additional fields

    @validator("reference_id")
    def validate_reference_id(cls, v):
        """Validate that reference_id is not empty."""
        if not v or not v.strip():
            logger.error("Validation failed: reference_id is empty")
            raise ValueError("reference_id cannot be empty")
        return v.strip()

    @validator("business_ref")
    def validate_business_ref(cls, v):
        """Validate that business_ref is not empty."""
        if not v or not v.strip():
            logger.error("Validation failed: business_ref is empty")
            raise ValueError("business_ref cannot be empty")
        return v.strip()

    @root_validator(pre=True)
    def validate_identifiers(cls, values):
        """Validate that at least one identifier is provided."""
        identifiers = [
            values.get("business_name"),
            values.get("tax_id"),
            values.get("organization_crd")
        ]
        
        # Log the identifiers being checked
        logger.info("Checking identifiers:", extra={
            "business_name": values.get("business_name"),
            "tax_id": values.get("tax_id"),
            "organization_crd": values.get("organization_crd")
        })
        
        # Check if at least one identifier has a non-empty value
        if not any(id for id in identifiers if id and isinstance(id, str) and id.strip()):
            logger.error("Validation failed: No valid identifier provided")
            raise ValueError(
                "At least one identifier (business_name, tax_id, or organization_crd) must be provided"
            )
        return values

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
        "reference_id": request.reference_id,
        "business_name": request.business_name,
        "mode": mode
    })
    
    try:
        # Get mode settings
        mode_settings = PROCESSING_MODES[mode]
        
        # Convert request to dict and remove webhook_url
        claim_dict = request.dict()
        webhook_url = claim_dict.pop("webhook_url", None)
        
        # Process claim
        report = process_claim(
            claim=claim_dict,
            facade=facade,
            business_ref=claim_dict.get("business_ref"),
            skip_financials=mode_settings["skip_financials"],
            skip_legal=mode_settings["skip_legal"]
        )
        
        # Send to webhook if URL provided
        if webhook_url:
            asyncio.create_task(send_to_webhook(webhook_url, report, request.reference_id))
        
        return report
        
    except Exception as e:
        logger.error(f"Error processing claim", extra={
            "reference_id": request.reference_id,
            "business_name": request.business_name,
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
        facade.cleanup()  # Assuming facade has a cleanup method
        logger.info("Successfully cleaned up resources")
    except Exception as e:
        logger.error(f"Error during cleanup", extra={
            "error": str(e),
            "error_type": type(e).__name__
        }) 