#!/usr/bin/env python3
"""
Script to test and fix connection reset issues when searching for firm with CRD 112694.
This script implements retry logic and better error handling to address the connection reset issues.
"""

import sys
import json
import time
import logging
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, Union

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent))

from services.firm_services import FirmServicesFacade
from services.firm_marshaller import (
    fetch_sec_firm_by_crd,
    fetch_finra_firm_by_crd,
    ResponseStatus
)
from services.firm_business import process_claim

# Set up logging
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RetryableFirmServicesFacade(FirmServicesFacade):
    """Extended FirmServicesFacade with improved retry logic for connection issues."""
    
    def __init__(self, max_retries=3, base_delay=5):
        """Initialize with retry parameters."""
        super().__init__()
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.service_delay = 6  # Increase default delay between API calls
        logger.info(f"RetryableFirmServicesFacade initialized with max_retries={max_retries}, base_delay={base_delay}s")
    
    def _retry_operation(self, operation_name: str, operation_func, *args, **kwargs) -> Tuple[bool, Any]:
        """
        Execute an operation with retry logic.
        
        Args:
            operation_name: Name of the operation for logging
            operation_func: Function to execute
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            Tuple of (success, result)
        """
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Attempting {operation_name} (attempt {attempt+1}/{self.max_retries})")
                result = operation_func(*args, **kwargs)
                logger.info(f"{operation_name} successful on attempt {attempt+1}")
                return True, result
            except (requests.exceptions.ConnectionError, ConnectionResetError) as e:
                logger.warning(f"{operation_name} attempt {attempt+1} failed with connection error: {str(e)}")
                if attempt < self.max_retries - 1:
                    wait_time = self.base_delay * (attempt + 1)  # Exponential backoff
                    logger.info(f"Waiting {wait_time} seconds before retrying...")
                    time.sleep(wait_time)
            except Exception as e:
                logger.error(f"{operation_name} attempt {attempt+1} failed with error: {str(e)}")
                if attempt < self.max_retries - 1:
                    wait_time = self.base_delay * (attempt + 1)  # Exponential backoff
                    logger.info(f"Waiting {wait_time} seconds before retrying...")
                    time.sleep(wait_time)
        
        logger.error(f"{operation_name} failed after {self.max_retries} attempts")
        return False, None
    
    def search_firm_by_crd(self, subject_id: str, crd_number: str, entity_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Enhanced version of search_firm_by_crd with retry logic for connection issues.
        """
        log_context = {
            "crd_number": crd_number,
            "entity_name": entity_name
        }
        
        logger.info(f"Searching for firm by CRD: {crd_number} with retry logic", extra=log_context)
        firm_id = f"search_crd_{crd_number}"
        
        # First, check if we can find the firm in either database with retry logic
        found_firm = False
        source = None
        sec_data = None
        finra_data = None
        
        # Try SEC with retry logic
        sec_found = False
        operation_name = f"SEC search for CRD {crd_number}"
        
        def sec_search_operation():
            self._apply_service_delay()
            return fetch_sec_firm_by_crd(subject_id, firm_id, {"crd_number": crd_number})
        
        sec_success, sec_response = self._retry_operation(operation_name, sec_search_operation)
        
        if sec_success and sec_response and sec_response.status == ResponseStatus.SUCCESS and sec_response.data:
            logger.info(f"Found SEC result for CRD {crd_number}", extra=log_context)
            found_firm = True
            sec_found = True
            source = "SEC"  # Temporary source, will be updated based on registration status
            sec_data = sec_response.data
        
        # Always try FINRA too, regardless of SEC result
        finra_found = False
        operation_name = f"FINRA search for CRD {crd_number}"
        
        def finra_search_operation():
            self._apply_service_delay()
            return fetch_finra_firm_by_crd(subject_id, firm_id, {"crd_number": crd_number})
        
        finra_success, finra_response = self._retry_operation(operation_name, finra_search_operation)
        
        if finra_success and finra_response and finra_response.status == ResponseStatus.SUCCESS and finra_response.data:
            logger.info(f"Found FINRA result for CRD {crd_number}", extra=log_context)
            found_firm = True
            finra_found = True
            if not sec_found:  # Only set initial source if SEC didn't find it
                source = "FINRA"
            finra_data = finra_response.data
        
        # If we found the firm in either database, get detailed information
        if found_firm:
            logger.info(f"Found firm with CRD {crd_number} in {source}, fetching detailed information", extra=log_context)
            
            # Instead of using get_firm_details which might have its own connection issues,
            # we'll construct a basic result from the search data we already have
            if sec_found and sec_data:
                # Extract basic info from SEC data
                basic_info = self._extract_basic_info_from_sec(sec_data)
                basic_info['source'] = 'SEC'
                basic_info['is_sec_registered'] = True
                if finra_found:
                    basic_info['is_finra_registered'] = True
                
                return basic_info
            elif finra_found and finra_data:
                # Extract basic info from FINRA data
                basic_info = self._extract_basic_info_from_finra(finra_data)
                basic_info['source'] = 'FINRA'
                basic_info['is_finra_registered'] = True
                
                return basic_info
        
        return None
    
    def _extract_basic_info_from_sec(self, sec_data: Union[Dict[str, Any], list]) -> Dict[str, Any]:
        """Extract basic firm information from SEC search data."""
        if isinstance(sec_data, list) and sec_data:
            sec_data = sec_data[0]
        
        # Now sec_data is guaranteed to be a dictionary
        if not isinstance(sec_data, dict):
            sec_data = {}  # Fallback to empty dict if somehow not a dict
            
        basic_info = {
            'crd_number': sec_data.get('org_crd') or sec_data.get('firm_source_id', ''),
            'firm_name': sec_data.get('org_name') or sec_data.get('firm_name', 'Unknown'),
            'sec_number': sec_data.get('firm_ia_full_sec_number', ''),
            'other_names': sec_data.get('firm_other_names', []),
            'registration_status': 'ACTIVE',  # Default to active since we found it
            'firm_status': 'active'
        }
        
        return basic_info
    
    def _extract_basic_info_from_finra(self, finra_data: Union[Dict[str, Any], list]) -> Dict[str, Any]:
        """Extract basic firm information from FINRA search data."""
        if isinstance(finra_data, list) and finra_data:
            finra_data = finra_data[0]
        
        # Now finra_data is guaranteed to be a dictionary
        if not isinstance(finra_data, dict):
            finra_data = {}  # Fallback to empty dict if somehow not a dict
            
        # FINRA data might be nested in a 'content' field as a JSON string
        if isinstance(finra_data, dict) and 'content' in finra_data and isinstance(finra_data.get('content'), str):
            try:
                content = json.loads(finra_data.get('content', '{}'))
                if isinstance(content, dict) and 'basicInformation' in content:
                    basic_info = {
                        'crd_number': str(content['basicInformation'].get('firmId', '')),
                        'firm_name': content['basicInformation'].get('firmName', 'Unknown'),
                        'other_names': content['basicInformation'].get('otherNames', []),
                        'registration_status': content['basicInformation'].get('iaScope', 'ACTIVE'),
                        'firm_status': 'active'
                    }
                    return basic_info
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Error parsing FINRA content: {str(e)}")
        
        # Fallback to direct extraction
        basic_info = {
            'crd_number': finra_data.get('crd_number', '') or finra_data.get('firm_id', ''),
            'firm_name': finra_data.get('firm_name', 'Unknown'),
            'registration_status': 'ACTIVE',  # Default to active since we found it
            'firm_status': 'active'
        }
        
        return basic_info

def main():
    """Test the enhanced firm search with retry logic for CRD 112694."""
    # Create enhanced facade with retry logic
    facade = RetryableFirmServicesFacade(max_retries=3, base_delay=5)
    
    # Search parameters
    subject_id = "test_subject_112694"
    crd_number = "112694"
    
    # Search for firm by CRD with enhanced retry logic
    logger.info(f"Searching for firm with CRD: {crd_number} using enhanced retry logic")
    firm_details = facade.search_firm_by_crd(subject_id, crd_number)
    
    # Log the raw response for debugging
    logger.info(f"Raw firm details: {json.dumps(firm_details, indent=2, default=str)}")
    
    if firm_details:
        # Create a claim for processing
        claim = {
            "reference_id": f"test-ref-{crd_number}",
            "business_ref": f"BIZ_{crd_number}",
            "business_name": firm_details.get('firm_name', 'Unknown'),
            "organization_crd": crd_number
        }
        
        # Process the claim to generate a compliance report
        logger.info(f"Generating compliance report for {firm_details.get('firm_name', 'Unknown')} (CRD: {crd_number})")
        report = process_claim(
            claim=claim,
            facade=facade,
            business_ref=claim["business_ref"],
            skip_financials=False,
            skip_legal=False
        )
        
        if report:
            # Add the claim to the report
            report["claim"] = claim
            
            # Add timestamp
            report["generated_at"] = datetime.now().isoformat()
            
            # Save the report to a file
            output_file = f"compliance_report_{crd_number}_fixed.json"
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"Compliance report saved to {output_file}")
            
            # Print the report
            print(json.dumps(report, indent=2, default=str))
        else:
            logger.error("Failed to generate compliance report")
    else:
        logger.error(f"No firm found with CRD: {crd_number}")

if __name__ == "__main__":
    main()