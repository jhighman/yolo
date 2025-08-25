"""
SEC IAPD Agent

This module provides an agent for interacting with the SEC IAPD API, which offers
public access to professional information about investment adviser firms
registered with the SEC (Securities and Exchange Commission). The agent fetches data without
handling caching, leaving that to the calling client.

Key Features:
- Firm search by name or CRD number
- Detailed firm profile retrieval
- Structured logging with optional employee number for traceability
- No caching; clients manage persistence
- Support for mock mode for testing and development
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import requests
from requests.adapters import HTTPAdapter
from typing import Dict, Optional, Any, List
import json
import logging
from logging import Logger
import time
from functools import wraps
import requests.exceptions
import os

# Handle imports differently when run as a script vs imported as a module
if __name__ == "__main__":
    # When run as a script
    import os
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from agents.exceptions import RateLimitExceeded
    from agents.mock_data import (
        get_mock_sec_search_results,
        get_mock_sec_firm_details,
        get_mock_sec_firm_by_crd
    )
else:
    # When imported as a module
    from .exceptions import RateLimitExceeded
    from .mock_data import (
        get_mock_sec_search_results,
        get_mock_sec_firm_details,
        get_mock_sec_firm_by_crd
    )

# Configure logging
def setup_logging():
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'agents')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'agents.log')
    
    logger = logging.getLogger('sec_iapd_agent')
    logger.setLevel(logging.DEBUG)
    
    # Create file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

# Configuration for SEC IAPD API
IAPD_CONFIG: Dict[str, Any] = {
    "base_search_url": "https://api.adviserinfo.sec.gov/search/individual",
    "firm_search_url": "https://api.adviserinfo.sec.gov/search/firm",
    "default_params": {
        "includePrevious": "true",  # Include past registrations
        "hl": "true",  # Highlight search terms in results
        "nrows": "12",  # Number of rows per response
        "start": "0",  # Starting index for pagination
        "r": "25",  # Radius (not typically used for CRD searches, kept for API compatibility)
        "sort": "score+desc",  # Sort by relevance score descending
        "wt": "json"  # Response format (JSON)
    }
}

# Rate limiting configuration
RATE_LIMIT_DELAY = 5  # seconds between API calls

def rate_limit(func):
    """Decorator to enforce rate limiting between API calls"""
    last_call = {}
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        current_time = time.time()
        if func.__name__ in last_call:
            elapsed = current_time - last_call[func.__name__]
            if elapsed < RATE_LIMIT_DELAY:
                time.sleep(RATE_LIMIT_DELAY - elapsed)
        last_call[func.__name__] = time.time()
        return func(*args, **kwargs)
    
    return wrapper

def retry_with_backoff(max_retries=3, backoff_factor=1.5, max_wait=30, jitter=0.1):
    """Retry decorator with exponential backoff and jitter.
    
    Args:
        max_retries: Maximum number of retries before giving up
        backoff_factor: Multiplier for the delay between retries
        max_wait: Maximum wait time in seconds
        jitter: Random factor to add to delay to prevent thundering herd
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except (requests.exceptions.ConnectionError, ConnectionResetError, requests.exceptions.ChunkedEncodingError) as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}: {e}")
                        raise
                    
                    # Calculate backoff with jitter
                    wait_time = min(backoff_factor * (2 ** (retries - 1)), max_wait)
                    jitter_amount = wait_time * jitter * (2 * random.random() - 1)
                    wait_time = max(0.1, wait_time + jitter_amount)  # Ensure positive wait time
                    
                    logger.warning(f"Connection error in {func.__name__}, retrying in {wait_time:.2f}s (attempt {retries}/{max_retries}): {e}")
                    time.sleep(wait_time)
            return func(*args, **kwargs)  # This line should never be reached
        return wrapper
    return decorator

# Import random for jitter in retry logic
import random

class SECAPIError(Exception):
    """Base exception for SEC API errors."""
    pass

class SECResponseError(SECAPIError):
    """Exception raised when SEC API returns an error response."""
    pass

class SECRequestError(SECAPIError):
    """Exception raised when there is an error making a request to SEC API."""
    pass

class SECFirmIAPDAgent:
    """SEC IAPD API agent.

    This agent provides public access to professional information about investment adviser firms
    through the SEC IAPD API. It can operate in mock mode for testing and development.
    """

    def __init__(self, config: Optional[Dict] = None, use_mock: bool = False):
        """Initialize the SEC IAPD API agent.

        Args:
            config: Optional configuration dictionary.
            use_mock: Whether to use mock data instead of making real API calls.
        """
        self.config = config or {}
        self.use_mock = use_mock
        
        # Create a more robust session with connection pooling and retry configuration
        self.session = requests.Session()
        
        # Configure connection pooling
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=0,  # We handle retries ourselves with the retry_with_backoff decorator
            pool_block=False
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # Set reasonable timeouts
        self.timeout = (10, 30)  # (connect timeout, read timeout)
        
        logger.info("Initialized SEC IAPD API agent with config: %s, use_mock: %s",
                    self.config, self.use_mock)

    @rate_limit
    @retry_with_backoff()
    def search_firm(self, firm_name: str) -> List[Dict]:
        """Search for firms by name.

        Args:
            firm_name: Name of the firm to search for.

        Returns:
            List of dictionaries containing firm information.

        Raises:
            SECAPIError: If there is an error with the SEC API.
        """
        try:
            logger.info("Searching for firm: %s", firm_name)
            
            if self.use_mock:
                results = get_mock_sec_search_results(firm_name)
                logger.info("Found %d mock results for firm: %s", len(results), firm_name)
                return results
            
            url = IAPD_CONFIG["firm_search_url"]
            params = {**IAPD_CONFIG["default_params"], "query": firm_name}
            
            logger.debug("Fetching firm info from SEC IAPD API", 
                        extra={"url": url, "params": params})
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                results = []
                
                # Log the raw response for debugging
                logger.debug("API response: %s", json.dumps(data))
                
                # Check for API error messages
                if "errorCode" in data and data["errorCode"] != 0:
                    error_msg = data.get("errorMessage", "Unknown API error")
                    logger.warning("API returned error: %s", error_msg)
                    return []
                
                # Handle different response formats
                if "hits" in data and data["hits"] is not None and "hits" in data["hits"]:
                    for hit in data["hits"]["hits"]:
                        if "_source" in hit:
                            source = hit["_source"]
                            results.append({
                                "org_name": source.get("org_name", ""),
                                "org_crd": source.get("org_crd", ""),
                                "firm_ia_sec_number": source.get("firm_ia_sec_number", ""),
                                "firm_ia_full_sec_number": source.get("firm_ia_full_sec_number", ""),
                                "firm_other_names": source.get("firm_other_names", []),
                                "firm_type": source.get("firm_type", ""),
                                "registration_status": source.get("registration_status", ""),
                                "firm_ia_scope": source.get("firm_ia_scope", ""),
                                "firm_ia_disclosure_fl": source.get("firm_ia_disclosure_fl", ""),
                                "firm_branches_count": source.get("firm_branches_count", 0)
                            })
                elif "results" in data:
                    for result in data["results"]:
                        results.append({
                            "org_name": result.get("name", ""),
                            "org_crd": result.get("crd", ""),
                            "firm_ia_sec_number": result.get("sec_number", ""),
                            "firm_ia_full_sec_number": result.get("full_sec_number", ""),
                            "firm_other_names": result.get("other_names", []),
                            "firm_type": result.get("type", ""),
                            "registration_status": result.get("status", ""),
                            "firm_ia_scope": result.get("scope", ""),
                            "firm_ia_disclosure_fl": result.get("disclosure_flag", ""),
                            "firm_branches_count": result.get("branches_count", 0)
                        })
                
                logger.info("Found %d results for firm: %s", len(results), firm_name)
                return results
            elif response.status_code == 403:
                logger.error("Rate limit exceeded for firm search: %s", firm_name)
                raise RateLimitExceeded(f"Rate limit exceeded for firm search: {firm_name}")
            else:
                logger.error("Error searching for firm: %s, status code: %d", 
                            firm_name, response.status_code)
                raise SECResponseError(f"Error searching for firm: {firm_name}, status code: {response.status_code}")
        
        except requests.exceptions.HTTPError as e:
            logger.error("HTTP error during firm search: %s", e)
            raise SECRequestError(f"HTTP error during firm search: {e}")
        except requests.exceptions.RequestException as e:
            logger.error("Request error during firm search: %s", e)
            raise SECRequestError(f"Request error during firm search: {e}")
        except Exception as e:
            logger.error("Unexpected error during firm search: %s", e)
            raise SECAPIError(f"Unexpected error during firm search: {e}")

    @rate_limit
    @retry_with_backoff()
    def search_firm_by_crd(self, crd_number: str, employee_number: Optional[str] = None) -> Dict:
        """Search for a firm by CRD number.

        Args:
            crd_number: CRD number of the firm.
            employee_number: Optional identifier for logging.

        Returns:
            Dictionary containing firm information.

        Raises:
            SECAPIError: If there is an error with the SEC API.
        """
        log_context = {
            "firm_crd": crd_number,
            "employee_number": employee_number
        }
        
        try:
            logger.info("Searching for firm by CRD: %s", crd_number, extra=log_context)
            
            if self.use_mock:
                result = get_mock_sec_firm_by_crd(crd_number)
                logger.info("Found mock result for firm CRD: %s", crd_number, extra=log_context)
                return result
            
            url = IAPD_CONFIG["firm_search_url"]
            params = {**IAPD_CONFIG["default_params"], "query": crd_number}
            
            logger.debug("Fetching firm info from SEC IAPD API",
                        extra={**log_context, "url": url, "params": params})
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                
                # Log the raw response for debugging
                logger.debug("API response: %s", json.dumps(data))
                
                # Check for API error messages
                if "errorCode" in data and data["errorCode"] != 0:
                    error_msg = data.get("errorMessage", "Unknown API error")
                    logger.warning("API returned error: %s", error_msg, extra=log_context)
                    return {}
                
                # Handle different response formats
                if "hits" in data and data["hits"] is not None and "hits" in data["hits"] and data["hits"]["hits"]:
                    # Process the first hit
                    hit = data["hits"]["hits"][0]
                    if "_source" in hit:
                        source = hit["_source"]
                        
                        # Handle standard format with org_name and org_crd
                        if "org_name" in source and "org_crd" in source:
                            return {
                                "org_name": source.get("org_name", ""),
                                "org_crd": source.get("org_crd", ""),
                                "firm_ia_sec_number": source.get("firm_ia_sec_number", ""),
                                "firm_ia_full_sec_number": source.get("firm_ia_full_sec_number", ""),
                                "firm_other_names": source.get("firm_other_names", []),
                                "firm_type": source.get("firm_type", ""),
                                "registration_status": source.get("registration_status", ""),
                                "firm_ia_scope": source.get("firm_ia_scope", ""),
                                "firm_ia_disclosure_fl": source.get("firm_ia_disclosure_fl", ""),
                                "firm_branches_count": source.get("firm_branches_count", 0)
                            }
                        # Handle alternative format with firm_source_id and firm_name
                        elif "firm_source_id" in source and "firm_name" in source:
                            return {
                                "org_name": source.get("firm_name", ""),
                                "org_crd": source.get("firm_source_id", ""),
                                "firm_ia_sec_number": source.get("firm_ia_sec_number", ""),
                                "firm_ia_full_sec_number": source.get("firm_ia_full_sec_number", ""),
                                "firm_other_names": source.get("firm_other_names", []),
                                "firm_type": source.get("firm_type", ""),
                                "registration_status": source.get("registration_status", ""),
                                "firm_ia_scope": source.get("firm_scope", ""),  # Note: different field name
                                "firm_ia_disclosure_fl": source.get("firm_ia_disclosure_fl", ""),
                                "firm_branches_count": source.get("firm_branches_count", 0)
                            }
                        # If neither format is found, try to extract from content if available
                        elif "content" in source:
                            try:
                                content = source["content"]
                                if isinstance(content, str):
                                    content = json.loads(content)
                                
                                basic_info = content.get("basicInformation", {})
                                return {
                                    "org_name": basic_info.get("firmName", ""),
                                    "org_crd": str(basic_info.get("firmId", "")),
                                    "firm_ia_sec_number": basic_info.get("iaSECNumber", ""),
                                    "firm_ia_full_sec_number": f"{basic_info.get('iaSECNumberType', '')}-{basic_info.get('iaSECNumber', '')}" if basic_info.get('iaSECNumber') else "",
                                    "firm_other_names": basic_info.get("otherNames", []),
                                    "firm_type": basic_info.get("firmType", ""),
                                    "registration_status": basic_info.get("firmStatus", ""),
                                    "firm_ia_scope": basic_info.get("iaScope", ""),
                                    "firm_ia_disclosure_fl": content.get("iaDisclosureFlag", ""),
                                    "firm_branches_count": source.get("firm_branches_count", 0)
                                }
                            except Exception as e:
                                logger.error(f"Error parsing content: {e}", extra=log_context)
                                # Continue with other formats
                        
                        # If we still don't have a match, return whatever we can find
                        return {
                            "org_name": source.get("org_name", source.get("firm_name", "")),
                            "org_crd": source.get("org_crd", source.get("firm_source_id", "")),
                            "firm_ia_sec_number": source.get("firm_ia_sec_number", ""),
                            "firm_ia_full_sec_number": source.get("firm_ia_full_sec_number", ""),
                            "firm_other_names": source.get("firm_other_names", []),
                            "firm_type": source.get("firm_type", ""),
                            "registration_status": source.get("registration_status", ""),
                            "firm_ia_scope": source.get("firm_ia_scope", source.get("firm_scope", "")),
                            "firm_ia_disclosure_fl": source.get("firm_ia_disclosure_fl", ""),
                            "firm_branches_count": source.get("firm_branches_count", 0)
                        }
                elif "results" in data and data["results"]:
                    result = data["results"][0]
                    return {
                        "org_name": result.get("name", ""),
                        "org_crd": result.get("crd", ""),
                        "firm_ia_sec_number": result.get("sec_number", ""),
                        "firm_ia_full_sec_number": result.get("full_sec_number", ""),
                        "firm_other_names": result.get("other_names", []),
                        "firm_type": result.get("type", ""),
                        "registration_status": result.get("status", ""),
                        "firm_ia_scope": result.get("scope", ""),
                        "firm_ia_disclosure_fl": result.get("disclosure_flag", ""),
                        "firm_branches_count": result.get("branches_count", 0)
                    }
                
                logger.warning("No firm found for CRD: %s", crd_number, extra=log_context)
                return {}
            elif response.status_code == 403:
                logger.error("Rate limit exceeded for firm CRD: %s", crd_number, extra=log_context)
                raise RateLimitExceeded(f"Rate limit exceeded for firm CRD {crd_number}.")
            else:
                logger.error("Error searching for firm by CRD: %s, status code: %d", 
                            crd_number, response.status_code, extra=log_context)
                raise SECResponseError(f"Error searching for firm by CRD: {crd_number}, status code: {response.status_code}")
        
        except requests.exceptions.HTTPError as e:
            logger.error("HTTP error during firm CRD search: %s", e, extra=log_context)
            raise SECRequestError(f"HTTP error during firm CRD search: {e}")
        except requests.exceptions.RequestException as e:
            logger.error("Request error during firm CRD search: %s", e, extra=log_context)
            raise SECRequestError(f"Request error during firm CRD search: {e}")
        except Exception as e:
            logger.error("Unexpected error during firm CRD search: %s", e, extra=log_context)
            raise SECAPIError(f"Unexpected error during firm CRD search: {e}")

    @rate_limit
    @retry_with_backoff()
    def get_firm_details(self, crd_number: str, employee_number: Optional[str] = None) -> Dict:
        """Get detailed information about a firm by CRD number.

        Args:
            crd_number: CRD number of the firm.
            employee_number: Optional identifier for logging.

        Returns:
            Dictionary containing firm details.

        Raises:
            SECAPIError: If there is an error with the SEC API.
        """
        log_context = {
            "firm_crd": crd_number,
            "employee_number": employee_number
        }
        
        try:
            logger.info("Getting firm details for CRD: %s", crd_number, extra=log_context)
            
            if self.use_mock:
                details = get_mock_sec_firm_details(crd_number)
                logger.info("Found mock details for firm CRD: %s", crd_number, extra=log_context)
                return details
            
            url = f"{IAPD_CONFIG['firm_search_url']}/{crd_number}"
            params = IAPD_CONFIG["default_params"]
            
            logger.debug("Fetching firm details from SEC IAPD API", 
                        extra={**log_context, "url": url, "params": params})
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                
                # Log the raw response for debugging
                logger.debug("API response: %s", json.dumps(data))
                
                # Check for API error messages
                if "errorCode" in data and data["errorCode"] != 0:
                    error_msg = data.get("errorMessage", "Unknown API error")
                    logger.warning("API returned error: %s", error_msg, extra=log_context)
                    return {}
                
                if "hits" in data and data["hits"] is not None and "hits" in data["hits"] and data["hits"]["hits"]:
                    hit = data["hits"]["hits"][0]
                    if "_source" in hit and "iacontent" in hit["_source"]:
                        try:
                            # Parse the JSON string into a dictionary
                            iacontent = hit["_source"]["iacontent"]
                            if isinstance(iacontent, str):
                                details = json.loads(iacontent)
                            else:
                                details = iacontent
                                
                            logger.info("Successfully retrieved firm details for CRD: %s",
                                       crd_number, extra=log_context)
                            return details
                        except Exception as e:
                            logger.error("Failed to parse content for CRD: %s, error: %s",
                                        crd_number, e, extra=log_context)
                            raise SECResponseError(f"Failed to parse content for CRD: {crd_number}, error: {e}")
                
                logger.warning("No details found for CRD: %s", crd_number, extra=log_context)
                return {}
            elif response.status_code == 403:
                logger.error("Rate limit exceeded for firm details CRD: %s", crd_number, extra=log_context)
                raise RateLimitExceeded(f"Rate limit exceeded for firm details CRD {crd_number}.")
            else:
                logger.error("Error getting firm details for CRD: %s, status code: %d", 
                            crd_number, response.status_code, extra=log_context)
                raise SECResponseError(f"Error getting firm details for CRD: {crd_number}, status code: {response.status_code}")
        
        except requests.exceptions.HTTPError as e:
            logger.error("HTTP error during firm details fetch: %s", e, extra=log_context)
            raise SECRequestError(f"HTTP error during firm details fetch: {e}")
        except requests.exceptions.RequestException as e:
            logger.error("Request error during firm details fetch: %s", e, extra=log_context)
            raise SECRequestError(f"Request error during firm details fetch: {e}")
        except Exception as e:
            logger.error("Unexpected error during firm details fetch: %s", e, extra=log_context)
            raise SECAPIError(f"Unexpected error during firm details fetch: {e}")


# For backward compatibility with the functional API
def search_firm_by_crd(crd_number: str, employee_number: Optional[str] = None) -> Dict:
    """
    Search for a firm by CRD number.
    
    Args:
        crd_number (str): The Central Registration Depository (CRD) number of the firm.
        employee_number (Optional[str]): Optional identifier for logging.
    
    Returns:
        Dict: A dictionary with firm info if successful, empty dict if the fetch fails.
    """
    agent = SECFirmIAPDAgent(use_mock=True)  # Default to mock mode for backward compatibility
    return agent.search_firm_by_crd(crd_number, employee_number)

def get_firm_details(crd_number: str, employee_number: Optional[str] = None) -> Dict:
    """
    Get detailed information about a firm by CRD number.
    
    Args:
        crd_number (str): The Central Registration Depository (CRD) number of the firm.
        employee_number (Optional[str]): Optional identifier for logging.
    
    Returns:
        Dict: A dictionary with firm details if successful, empty dict if the fetch fails.
    """
    agent = SECFirmIAPDAgent(use_mock=True)  # Default to mock mode for backward compatibility
    return agent.get_firm_details(crd_number, employee_number)

def search_entity_detailed_info(crd_number: str, employee_number: Optional[str] = None) -> Dict:
    """
    Get detailed information about a firm by CRD number.
    
    Args:
        crd_number (str): The Central Registration Depository (CRD) number of the firm.
        employee_number (Optional[str]): Optional identifier for logging.
    
    Returns:
        Dict: A dictionary with firm details if successful, empty dict if the fetch fails.
    """
    return get_firm_details(crd_number, employee_number)

# Example usage
if __name__ == "__main__":
    import argparse
    
    # Sample data for testing
    SAMPLE_ENTITIES = [
        {
            "_id": {"$oid":"67bcdac22e749a352e23befe"},
            "type": "Thing/Other",
            "workProduct": "WP24-0037036",
            "entity": "EN-114236",
            "entityName": "Able Wealth Management, LLC",
            "name": "Able Wealth Management, LLC",
            "normalizedName": "ablewealthmanagementllc",
            "principal": "Able Wealth Management, LLC,",
            "street1": "695 Cross Street",
            "city": "Lakewood",
            "state": "New Jersey",
            "zip": "8701",
            "taxID": "",
            "organizationCRD": "298085",
            "status": "",
            "notes": "",
            "reference_id": "test-ref-001",
            "business_ref": "BIZ_001",
            "business_name": "Able Wealth Management, LLC",
            "tax_id": "123456789"
        },
        {
            "_id": {"$oid":"67bcdac22e749a352e23beff"},
            "type": "Thing/Other",
            "workProduct": "WP24-0037424",
            "entity": "EN-017252",
            "entityName": "Adell, Harriman & Carpenter, Inc.",
            "name": "Adell, Harriman & Carpenter, Inc.",
            "normalizedName": "adellharrimancarpenterinc",
            "principal": "Adell, Harriman & Carpenter, Inc.,",
            "street1": "2700 Post Oak Blvd. Suite 1200",
            "city": "Houston",
            "state": "Texas",
            "zip": "77056",
            "taxID": "",
            "organizationCRD": "107488",
            "status": "",
            "notes": "",
            "reference_id": "test-ref-002",
            "business_ref": "BIZ_002",
            "business_name": "Adell, Harriman & Carpenter, Inc.",
            "tax_id": "987654321"
        },
        {
            "_id": {"$oid":"67bcdac22e749a352e23bf00"},
            "type": "Thing/Other",
            "workProduct": "WP24-0036284",
            "entity": "EN-109946",
            "entityName": "ALLIANCE GLOBAL PARTNERS, LLC",
            "name": "ALLIANCE GLOBAL PARTNERS, LLC",
            "normalizedName": "allianceglobalpartnersllc",
            "principal": "ALLIANCE GLOBAL PARTNERS, LLC,",
            "street1": "88 Post Road West",
            "city": "Westport",
            "state": "Connecticut",
            "zip": "6880",
            "taxID": "",
            "organizationCRD": "8361",
            "status": "",
            "notes": "",
            "reference_id": "test-ref-003",
            "business_ref": "BIZ_003",
            "business_name": "ALLIANCE GLOBAL PARTNERS, LLC",
            "tax_id": "456789123"
        }
    ]
    
    def print_menu():
        print("\nSEC IAPD Agent Test Menu")
        print("================================")
        print("1. Select from sample entities")
        print("2. Search firm by name")
        print("3. Search firm by CRD number")
        print("4. Get firm details by CRD number")
        print("0. Exit")
        print("================================")
        return input("Enter your choice (0-4): ")
    
    def print_entities():
        print("\nSample Entities:")
        print("================")
        for i, entity in enumerate(SAMPLE_ENTITIES, 1):
            print(f"{i}. {entity['name']} (CRD: {entity['organizationCRD']})")
        print("================")
        return input("Select entity (1-3): ")
    
    def get_input(prompt, default=None):
        value = input(prompt)
        if not value and default:
            return default
        return value
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='SEC IAPD Agent CLI')
    parser.add_argument('--mock', action='store_true', help='Use mock data instead of real API')
    args = parser.parse_args()
    
    # Create an agent
    agent = SECFirmIAPDAgent(use_mock=args.mock)
    print(f"Using {'mock' if args.mock else 'real'} data")
    
    while True:
        choice = print_menu()
        
        if choice == '0':
            print("Exiting...")
            break
            
        employee = get_input("Enter employee number (optional, press Enter to skip): ", "EMP001")
            
        try:
            if choice == '1':
                entity_choice = print_entities()
                try:
                    entity_idx = int(entity_choice) - 1
                    if 0 <= entity_idx < len(SAMPLE_ENTITIES):
                        selected_entity = SAMPLE_ENTITIES[entity_idx]
                        print("\nSelected Entity:")
                        print(json.dumps(selected_entity, indent=2))
                        
                        sub_choice = input("\nWhat would you like to do with this entity?\n"
                                          "1. Search by name\n"
                                          "2. Search by CRD\n"
                                          "3. Get firm details\n"
                                          "Choice (1-3): ")
                        
                        if sub_choice == '1':
                            results = agent.search_firm(selected_entity['name'])
                            if results:
                                print(f"Found {len(results)} results:")
                                print(json.dumps(results, indent=2))
                            else:
                                print(f"No firms found with name: {selected_entity['name']}")
                                
                        elif sub_choice == '2':
                            result = agent.search_firm_by_crd(selected_entity['organizationCRD'], employee)
                            if result:
                                print(f"Firm Data retrieved: {json.dumps(result, indent=2)}")
                            else:
                                print(f"No firm data retrieved for CRD {selected_entity['organizationCRD']}")
                                
                        elif sub_choice == '3':
                            details = agent.get_firm_details(selected_entity['organizationCRD'], employee)
                            if details:
                                print(f"Firm Details retrieved: {json.dumps(details, indent=2)}")
                            else:
                                print(f"No firm details retrieved for CRD {selected_entity['organizationCRD']}")
                        else:
                            print("Invalid choice.")
                    else:
                        print("Invalid entity selection.")
                except ValueError:
                    print("Please enter a valid number.")
                    
            elif choice == '2':
                firm_name = get_input("Enter firm name: ", "Baker Avenue Asset Management")
                results = agent.search_firm(firm_name)
                if results:
                    print(f"Found {len(results)} results:")
                    print(json.dumps(results, indent=2))
                else:
                    print(f"No firms found with name: {firm_name}")
                    
            elif choice == '3':
                firm_crd = get_input("Enter firm CRD number: ", "131940")
                result = agent.search_firm_by_crd(firm_crd, employee)
                if result:
                    print(f"Firm Data retrieved: {json.dumps(result, indent=2)}")
                else:
                    print(f"No firm data retrieved for CRD {firm_crd}")
                    
            elif choice == '4':
                firm_crd = get_input("Enter firm CRD number: ", "131940")
                details = agent.get_firm_details(firm_crd, employee)
                if details:
                    print(f"Firm Details retrieved: {json.dumps(details, indent=2)}")
                else:
                    print(f"No firm details retrieved for CRD {firm_crd}")
                    
            else:
                print("Invalid choice. Please try again.")
                
        except RateLimitExceeded as e:
            print(f"Rate limit error: {e}")
        except SECAPIError as e:
            print(f"SEC API error: {e}")
        
        input("\nPress Enter to continue...")

__all__ = [
    'SECFirmIAPDAgent',
    'search_firm_by_crd',
    'get_firm_details',
    'RATE_LIMIT_DELAY',
    'IAPD_CONFIG'
]