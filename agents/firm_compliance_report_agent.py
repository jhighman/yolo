"""
Agent for handling firm compliance report operations.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from cache_manager.config import DEFAULT_CACHE_FOLDER as CACHE_FOLDER, DATE_FORMAT

# Configure logging
logger = logging.getLogger(__name__)

def has_significant_changes(new_report: Dict[str, Any], old_report: Dict[str, Any]) -> bool:
    """
    Compare two compliance reports to determine if significant changes warrant a new version.
    
    Args:
        new_report: The new compliance report to evaluate
        old_report: The latest cached report for comparison
        
    Returns:
        bool: True if compliance flags, alert count, or raw search results differ, False otherwise
    """
    try:
        # Check overall compliance
        new_compliance = new_report.get("final_evaluation", {}).get("overall_compliance")
        old_compliance = old_report.get("final_evaluation", {}).get("overall_compliance")
        
        if new_compliance != old_compliance:
            logger.debug(f"Overall compliance changed: {old_compliance} -> {new_compliance}")
            return True
        
        # Check section compliances
        sections = [
            "search_evaluation",
            "registration_status",
            "regulatory_oversight",
            "disclosures",
            "financials",
            "legal",
            "qualifications",
            "data_integrity"
        ]
        
        for section in sections:
            new_section = new_report.get(section, {}).get("compliance")
            old_section = old_report.get(section, {}).get("compliance")
            
            if new_section != old_section:
                logger.debug(f"{section} compliance changed: {old_section} -> {new_section}")
                return True
        
        # Compare alert counts
        new_alerts = new_report.get("final_evaluation", {}).get("alerts", [])
        old_alerts = old_report.get("final_evaluation", {}).get("alerts", [])
        
        if len(new_alerts) != len(old_alerts):
            logger.debug(f"Alert count changed: {len(old_alerts)} -> {len(new_alerts)}")
            return True
        
        # Check for changes in raw search results
        new_sec_result = new_report.get("search_evaluation", {}).get("sec_search_result")
        old_sec_result = old_report.get("search_evaluation", {}).get("sec_search_result")
        
        if new_sec_result != old_sec_result:
            logger.debug("SEC search result changed")
            return True
        
        new_finra_result = new_report.get("search_evaluation", {}).get("finra_search_result")
        old_finra_result = old_report.get("search_evaluation", {}).get("finra_search_result")
        
        if new_finra_result != old_finra_result:
            logger.debug("FINRA search result changed")
            return True
        
        # No significant changes detected
        return False
        
    except Exception as e:
        logger.error(f"Error comparing reports: {str(e)}")
        # Return True to be safe (will create new version)
        return True

def _get_latest_version(files: List[Path], reference_id: str, date_str: str) -> int:
    """
    Get the latest version number from existing files.
    
    Args:
        files: List of existing file paths
        reference_id: Report reference ID
        date_str: Date string in the filename
        
    Returns:
        int: Latest version number, or 0 if no files exist
    """
    version = 0
    prefix = f"FirmComplianceReport_{reference_id}_v"
    suffix = f"_{date_str}.json"
    
    for file in files:
        name = file.name
        if name.startswith(prefix) and name.endswith(suffix):
            try:
                current = int(name[len(prefix):-len(suffix)].split('_')[0])
                version = max(version, current)
            except (ValueError, IndexError):
                continue
    
    return version

def save_compliance_report(
    report: Dict[str, Any],
    business_ref: Optional[str] = None,
    logger: logging.Logger = logger
) -> bool:
    """
    Save a compliance report to the cache with versioning based on changes.
    
    Args:
        report: Compliance report dictionary (must contain reference_id)
        business_ref: Optional business identifier (e.g., "BIZ_001")
        logger: Logger instance for custom logging
        
    Returns:
        bool: True if saved successfully, False otherwise
    """
    try:
        # Validate report
        if not isinstance(report, dict) or not report:
            logger.error("Invalid report: must be a non-empty dictionary")
            return False
        
        reference_id = report.get("reference_id")
        if not reference_id:
            logger.error("Missing reference_id in report")
            return False
        
        # Get business_ref from input, report, or default
        if not business_ref:
            business_ref = report.get("claim", {}).get("business_ref", "Unknown")
        
        if not isinstance(business_ref, str):
            logger.error(f"Invalid business_ref type: {type(business_ref)}")
            return False
        
        logger.info(f"Processing compliance report for reference_id={reference_id}, business_ref={business_ref}")
        
        # Create cache directory
        cache_path = CACHE_FOLDER / business_ref
        cache_path.mkdir(parents=True, exist_ok=True)
        
        # Generate date string for filename
        date_str = datetime.now().strftime(DATE_FORMAT)
        
        # Find existing files for this reference_id and date
        existing_files = sorted(
            cache_path.glob(f"FirmComplianceReport_{reference_id}_v*_{date_str}.json")
        )
        
        # Get latest version and file
        latest_version = _get_latest_version(existing_files, reference_id, date_str)
        latest_file = None if not existing_files else existing_files[-1]
        
        # Check for significant changes if we have a previous version
        should_save = True
        if latest_file and latest_file.exists():
            try:
                with latest_file.open('r') as f:
                    old_report = json.load(f)
                should_save = has_significant_changes(report, old_report)
            except Exception as e:
                logger.error(f"Error reading latest file: {str(e)}")
                should_save = True  # Save new version if we can't compare
        
        if not should_save:
            logger.info(f"No significant changes detected for {reference_id}, skipping save")
            return True
        
        # Create new version
        new_version = latest_version + 1
        new_filename = f"FirmComplianceReport_{reference_id}_v{new_version}_{date_str}.json"
        new_path = cache_path / new_filename
        
        # Save new version
        try:
            with new_path.open('w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"Saved compliance report: {new_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save report: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"Unexpected error in save_compliance_report: {str(e)}")
        return False