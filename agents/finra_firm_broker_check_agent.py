"""
FINRA BrokerCheck Agent

This module provides an agent for interacting with the FINRA BrokerCheck API, which offers
public access to professional information about entities (brokers, investment advisors, or firms)
registered with FINRA (Financial Industry Regulatory Authority). The agent fetches data without
handling caching, leaving that to the calling client.

Key Features:
- Three services: Firm search by CRD, entity basic search, and entity detailed profile retrieval.
- Uses CRD (Central Registration Depository) numbers to identify entities (individuals or firms).
- Structured logging with optional employee number for traceability.
- No caching; clients manage persistence.
- Support for mock mode for testing and development.

Terminology (from FINRA BrokerCheck):
- CRD Number: A unique identifier assigned to brokers, investment advisers, or firms by FINRA.
- Broker: An individual registered to sell securities (e.g., Series 6, 7).
- Investment Adviser (IA): A registered adviser under the Investment Advisers Act.
- Firm: A registered broker-dealer or investment advisory firm.
- BrokerCheck: FINRA's public tool for researching entity backgrounds.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import requests
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
        get_mock_finra_search_results,
        get_mock_finra_firm_details,
        get_mock_finra_firm_by_crd
    )
else:
    # When imported as a module
    from .exceptions import RateLimitExceeded
    from .mock_data import (
        get_mock_finra_search_results,
        get_mock_finra_firm_details,
        get_mock_finra_firm_by_crd
    )

# Configure logging
def setup_logging():
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'agents')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'agents.log')
    
    logger = logging.getLogger('finra_brokercheck_agent')
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

# Configuration for FINRA BrokerCheck API
BROKERCHECK_CONFIG: Dict[str, Any] = {
    "firm_search_url": "https://api.brokercheck.finra.org/search/firm",
    "entity_search_url": "https://api.brokercheck.finra.org/search/individual",  # Used for individuals; firms use firm_search_url
    "base_search_url": "https://api.brokercheck.finra.org/search/firm",  # For backward compatibility with tests
    "default_params": {
        "filter": "active=true,prev=true,bar=true,broker=true,ia=true,brokeria=true",
        "includePrevious": "true",
        "hl": "true",
        "nrows": "12",
        "start": "0",
        "r": "25",
        "wt": "json"
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


def retry_with_backoff(max_retries=3, backoff_factor=1.5):
    """Retry decorator with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            max_wait = 30  # Maximum wait time in seconds
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except (requests.exceptions.ConnectionError, ConnectionResetError) as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}: {e}")
                        raise
                    
                    wait_time = min(backoff_factor * (2 ** (retries - 1)), max_wait)
                    logger.warning(f"Connection error in {func.__name__}, retrying in {wait_time:.2f}s (attempt {retries}/{max_retries}): {e}")
                    time.sleep(wait_time)
            return func(*args, **kwargs)  # This line should never be reached
        return wrapper
    return decorator
class FinraAPIError(Exception):
    """Base exception for FINRA API errors."""
    pass

class FinraResponseError(FinraAPIError):
    """Exception raised when FINRA API returns an error response."""
    pass

class FinraRequestError(FinraAPIError):
    """Exception raised when there is an error making a request to FINRA API."""
    pass

class FinraFirmBrokerCheckAgent:
    """FINRA BrokerCheck API agent.

    This agent provides public access to professional information about registered firms
    through the FINRA BrokerCheck API. It can operate in mock mode for testing and development.
    """

    def __init__(self, config: Optional[Dict] = None, use_mock: bool = False):
        """Initialize the FINRA BrokerCheck API agent.

        Args:
            config: Optional configuration dictionary.
            use_mock: Whether to use mock data instead of making real API calls.
        """
        self.config = config or {}
        self.use_mock = use_mock
        self.session = requests.Session()
        # Add User-Agent header to avoid potential blocking
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        logger.info("Initialized FINRA BrokerCheck API agent with config: %s, use_mock: %s", 
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
            FinraAPIError: If there is an error with the FINRA API.
        """
        try:
            logger.info("Searching for firm: %s", firm_name)
            
            if self.use_mock:
                results = get_mock_finra_search_results(firm_name)
                logger.info("Found %d mock results for firm: %s", len(results), firm_name)
                # Transform to match the expected format in tests
                return [{"firm_name": r["org_name"], "crd_number": r["org_source_id"]} for r in results]
            
            url = BROKERCHECK_CONFIG["firm_search_url"]
            params = {**BROKERCHECK_CONFIG["default_params"], "query": firm_name}
            
            logger.debug("Fetching firm info from BrokerCheck API", 
                        extra={"url": url, "params": params})
            
            response = self.session.get(url, params=params, timeout=(10, 30))
            if response.status_code == 200:
                data = response.json()
                results = []
                
                # Log the raw response for debugging
                logger.debug("API response: %s", json.dumps(data))
                
                # Check for API error messages
                if "errorCode" in data and data["errorCode"] != 0:
                    error_msg = data.get("errorMessage", "Unknown API error")
                    # Special handling for "Search unavailable" error
                    if "Search unavailable" in error_msg:
                        logger.info("FINRA search unavailable for firm: %s - treating as no results", firm_name)
                    else:
                        logger.warning("API returned error: %s", error_msg)
                    return []
                
                # Handle different response formats
                if "hits" in data and data["hits"] is not None and "hits" in data["hits"]:
                    for hit in data["hits"]["hits"]:
                        if "_source" in hit:
                            source = hit["_source"]
                            results.append({
                                "firm_name": source.get("org_name", ""),
                                "crd_number": source.get("org_source_id", "")
                            })
                elif "results" in data:
                    for result in data["results"]:
                        results.append({
                            "firm_name": result.get("name", ""),
                            "crd_number": result.get("crd", "")
                        })
                
                logger.info("Found %d results for firm: %s", len(results), firm_name)
                return results
            elif response.status_code == 403:
                logger.error("Rate limit exceeded for firm search: %s", firm_name)
                raise RateLimitExceeded(f"Rate limit exceeded for firm search: {firm_name}")
            else:
                logger.error("Error searching for firm: %s, status code: %d", 
                            firm_name, response.status_code)
                raise FinraResponseError(f"Error searching for firm: {firm_name}, status code: {response.status_code}")
        
        except requests.exceptions.HTTPError as e:
            logger.error("HTTP error during firm search: %s", e)
            raise FinraRequestError(f"HTTP error during firm search: {e}")
        except requests.exceptions.RequestException as e:
            logger.error("Request error during firm search: %s", e)
            raise FinraRequestError(f"Request error during firm search: {e}")
        except Exception as e:
            logger.error("Unexpected error during firm search: %s", e)
            raise FinraAPIError(f"Unexpected error during firm search: {e}")

    @rate_limit
    @retry_with_backoff()
    def search_firm_by_crd(self, crd_number: str, employee_number: Optional[str] = None) -> List[Dict]:
        """Search for a firm by CRD number.

        Args:
            crd_number: CRD number of the firm.
            employee_number: Optional identifier for logging.

        Returns:
            List of dictionaries containing firm information.

        Raises:
            FinraAPIError: If there is an error with the FINRA API.
        """
        log_context = {
            "firm_crd": crd_number,
            "employee_number": employee_number
        }
        
        try:
            logger.info("Searching for firm by CRD: %s", crd_number, extra=log_context)
            
            if self.use_mock:
                result = get_mock_finra_firm_by_crd(crd_number)
                logger.info("Found mock result for firm CRD: %s", crd_number, extra=log_context)
                if result:
                    # Transform to match the expected format in tests
                    return [{"firm_name": result["org_name"], "crd_number": result["org_source_id"]}]
                return []
            
            url = f"{BROKERCHECK_CONFIG['firm_search_url']}/{crd_number}"
            params = BROKERCHECK_CONFIG["default_params"]
            
            logger.debug("Fetching firm info from BrokerCheck API", 
                        extra={**log_context, "url": url, "params": params})
            
            response = self.session.get(url, params=params, timeout=(10, 30))
            if response.status_code == 200:
                data = response.json()
                results = []
                
                # Log the raw response for debugging
                logger.debug("API response: %s", json.dumps(data))
                
                # Check for API error messages
                if "errorCode" in data and data["errorCode"] != 0:
                    error_msg = data.get("errorMessage", "Unknown API error")
                    # Special handling for "Search unavailable" error
                    if "Search unavailable" in error_msg:
                        logger.info("FINRA search unavailable for CRD: %s - treating as no results", crd_number, extra=log_context)
                    else:
                        logger.warning("API returned error: %s", error_msg, extra=log_context)
                    return []
                
                # Handle different response formats
                if "hits" in data and data["hits"] is not None and "hits" in data["hits"]:
                    for hit in data["hits"]["hits"]:
                        if "_source" in hit:
                            source = hit["_source"]
                            results.append({
                                "firm_name": source.get("org_name", ""),
                                "crd_number": source.get("org_source_id", "")
                            })
                elif "results" in data:
                    for result in data["results"]:
                        results.append({
                            "firm_name": result.get("name", ""),
                            "crd_number": result.get("crd", "")
                        })
                
                logger.info("Found %d results for firm CRD: %s", len(results), crd_number, extra=log_context)
                return results
            elif response.status_code == 403:
                logger.error("Rate limit exceeded for firm CRD: %s", crd_number, extra=log_context)
                raise RateLimitExceeded(f"Rate limit exceeded for firm CRD {crd_number}.")
            else:
                logger.error("Error searching for firm by CRD: %s, status code: %d", 
                            crd_number, response.status_code, extra=log_context)
                raise FinraResponseError(f"Error searching for firm by CRD: {crd_number}, status code: {response.status_code}")
        
        except requests.exceptions.HTTPError as e:
            logger.error("HTTP error during firm CRD search: %s", e, extra=log_context)
            raise FinraRequestError(f"HTTP error during firm CRD search: {e}")
        except requests.exceptions.RequestException as e:
            logger.error("Request error during firm CRD search: %s", e, extra=log_context)
            raise FinraRequestError(f"Request error during firm CRD search: {e}")
        except Exception as e:
            logger.error("Unexpected error during firm CRD search: %s", e, extra=log_context)
            raise FinraAPIError(f"Unexpected error during firm CRD search: {e}")

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
            FinraAPIError: If there is an error with the FINRA API.
        """
        log_context = {
            "firm_crd": crd_number,
            "employee_number": employee_number
        }
        
        try:
            logger.info("Getting firm details for CRD: %s", crd_number, extra=log_context)
            
            if self.use_mock:
                details = get_mock_finra_firm_details(crd_number)
                logger.info("Found mock details for firm CRD: %s", crd_number, extra=log_context)
                return details
            
            url = f"{BROKERCHECK_CONFIG['firm_search_url']}/{crd_number}"
            params = BROKERCHECK_CONFIG["default_params"]
            
            logger.debug("Fetching firm details from BrokerCheck API", 
                        extra={**log_context, "url": url, "params": params})
            
            response = self.session.get(url, params=params)
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
                    if "_source" in hit and "content" in hit["_source"]:
                        try:
                            content_str = hit["_source"]["content"]
                            details = json.loads(content_str)
                            logger.info("Successfully retrieved firm details for CRD: %s",
                                       crd_number, extra=log_context)
                            return details
                        except json.JSONDecodeError as e:
                            logger.error("Failed to parse content JSON for CRD: %s, error: %s",
                                        crd_number, e, extra=log_context)
                            raise FinraResponseError(f"Failed to parse content JSON for CRD: {crd_number}, error: {e}")
                
                logger.warning("No details found for CRD: %s", crd_number, extra=log_context)
                return {}
            elif response.status_code == 403:
                logger.error("Rate limit exceeded for firm details CRD: %s", crd_number, extra=log_context)
                raise RateLimitExceeded(f"Rate limit exceeded for firm details CRD {crd_number}.")
            else:
                logger.error("Error getting firm details for CRD: %s, status code: %d", 
                            crd_number, response.status_code, extra=log_context)
                raise FinraResponseError(f"Error getting firm details for CRD: {crd_number}, status code: {response.status_code}")
        
        except requests.exceptions.HTTPError as e:
            logger.error("HTTP error during firm details fetch: %s", e, extra=log_context)
            raise FinraRequestError(f"HTTP error during firm details fetch: {e}")
        except requests.exceptions.RequestException as e:
            logger.error("Request error during firm details fetch: %s", e, extra=log_context)
            raise FinraRequestError(f"Request error during firm details fetch: {e}")
        except Exception as e:
            logger.error("Unexpected error during firm details fetch: %s", e, extra=log_context)
            raise FinraAPIError(f"Unexpected error during firm details fetch: {e}")

    @rate_limit
    @retry_with_backoff()
    def search_entity(self, crd_number: str, entity_type: str = "individual",
                     employee_number: Optional[str] = None) -> Optional[Dict]:
        """
        Fetches basic information from FINRA BrokerCheck for an entity (individual or firm) using their CRD number.
        
        Args:
            crd_number (str): The Central Registration Depository (CRD) number of the entity.
            entity_type (str): Type of entity ('individual' or 'firm'). Defaults to 'individual'.
            employee_number (Optional[str]): An optional identifier for logging context.
        
        Returns:
            Optional[Dict]: A dictionary with basic entity info if successful, None if the fetch fails.
        """
        log_context = {
            "crd_number": crd_number,
            "entity_type": entity_type,
            "employee_number": employee_number
        }
        
        if not crd_number or not isinstance(crd_number, str):
            logger.error("Invalid CRD number", extra=log_context)
            return None

        # Select appropriate endpoint based on entity type
        base_url = BROKERCHECK_CONFIG["firm_search_url"] if entity_type.lower() == "firm" else BROKERCHECK_CONFIG["entity_search_url"]
        # Use the CRD in the path instead of as a query parameter
        url = f"{base_url}/{crd_number}"
        
        logger.info(f"Starting FINRA BrokerCheck basic entity search ({entity_type})", extra=log_context)

        if self.use_mock:
            if entity_type.lower() == "firm":
                result = get_mock_finra_firm_by_crd(crd_number)
                logger.info(f"Found mock result for entity CRD: {crd_number} ({entity_type})", extra=log_context)
                return result
            # For individuals, we don't have mock data yet, so return None
            logger.warning(f"No mock data available for individual CRD: {crd_number}", extra=log_context)
            return None

        try:
            params = dict(BROKERCHECK_CONFIG["default_params"])
            # No need to add crd_number as a query parameter since it's in the URL path
            logger.debug(f"Fetching basic entity info from BrokerCheck API ({entity_type})",
                        extra={**log_context, "url": url, "params": params})

            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Log the raw response for debugging
                logger.debug("API response: %s", json.dumps(data))
                
                # Check for API error messages
                if "errorCode" in data and data["errorCode"] != 0:
                    error_msg = data.get("errorMessage", "Unknown API error")
                    # Special handling for "Search unavailable" error
                    if "Search unavailable" in error_msg:
                        logger.info("FINRA search unavailable for entity CRD: %s - treating as no results", crd_number, extra=log_context)
                    else:
                        logger.warning("API returned error: %s", error_msg, extra=log_context)
                    return None
                
                logger.info(f"Basic entity data fetched successfully ({entity_type})", extra=log_context)
                return data
            elif response.status_code == 403:
                logger.error(f"Rate limit exceeded ({entity_type})", extra=log_context)
                raise RateLimitExceeded(f"Rate limit exceeded for CRD {crd_number} ({entity_type}).")
            else:
                logger.error(f"Unexpected status code ({entity_type})", 
                            extra={**log_context, "status_code": response.status_code})
                return None

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error during fetch ({entity_type})", 
                        extra={**log_context, "error": str(e)})
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error during fetch ({entity_type})", 
                        extra={**log_context, "error": str(e)})
            return None
        except Exception as e:
            logger.error(f"Unexpected error during entity search: {e}", extra=log_context)
            return None

    @rate_limit
    @retry_with_backoff()
    def search_entity_detailed_info(self, crd_number: str, entity_type: str = "individual",
                                   employee_number: Optional[str] = None) -> Optional[Dict]:
        """
        Fetches detailed information from FINRA BrokerCheck for an entity (individual or firm) using their CRD number.
        
        Args:
            crd_number (str): The Central Registration Depository (CRD) number of the entity.
            entity_type (str): Type of entity ('individual' or 'firm'). Defaults to 'individual'.
            employee_number (Optional[str]): An optional identifier for logging context.
        
        Returns:
            Optional[Dict]: A dictionary with detailed entity info if successful, None if the fetch or parsing fails.
        """
        log_context = {
            "crd_number": crd_number,
            "entity_type": entity_type,
            "employee_number": employee_number
        }
        
        if not crd_number or not isinstance(crd_number, str):
            logger.error("Invalid CRD number", extra=log_context)
            return None

        # Select appropriate endpoint based on entity type
        base_url = f'{BROKERCHECK_CONFIG["firm_search_url"]}/{crd_number}' if entity_type.lower() == "firm" else \
                f'{BROKERCHECK_CONFIG["entity_search_url"]}/{crd_number}'
        
        logger.info(f"Starting FINRA BrokerCheck detailed entity search ({entity_type})", extra=log_context)

        if self.use_mock:
            if entity_type.lower() == "firm":
                details = get_mock_finra_firm_details(crd_number)
                logger.info(f"Found mock details for entity CRD: {crd_number} ({entity_type})", extra=log_context)
                return details
            # For individuals, we don't have mock data yet, so return None
            logger.warning(f"No mock data available for individual CRD: {crd_number}", extra=log_context)
            return None

        try:
            params = dict(BROKERCHECK_CONFIG["default_params"])
            logger.debug(f"Fetching detailed entity info from BrokerCheck API ({entity_type})", 
                        extra={**log_context, "url": base_url, "params": params})

            response = self.session.get(base_url, params=params)
            
            if response.status_code == 200:
                raw_data = response.json()
                
                # Log the raw response for debugging
                logger.debug("API response: %s", json.dumps(raw_data))
                
                # Check for API error messages
                if "errorCode" in raw_data and raw_data["errorCode"] != 0:
                    error_msg = raw_data.get("errorMessage", "Unknown API error")
                    logger.warning("API returned error: %s", error_msg, extra=log_context)
                    return None
                
                if "hits" in raw_data and raw_data["hits"] is not None and "hits" in raw_data["hits"] and raw_data["hits"]["hits"]:
                    content_str = raw_data["hits"]["hits"][0]["_source"]["content"]
                    try:
                        detailed_data = json.loads(content_str)
                        logger.info(f"Detailed entity data fetched and parsed successfully ({entity_type})",
                                   extra=log_context)
                        return detailed_data
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse content JSON ({entity_type})",
                                    extra={**log_context, "error": str(e)})
                        return None
                else:
                    logger.warning(f"No hits found in detailed response ({entity_type})", extra=log_context)
                    return None
            elif response.status_code == 403:
                logger.error(f"Rate limit exceeded ({entity_type})", extra=log_context)
                raise RateLimitExceeded(f"Rate limit exceeded for CRD {crd_number} ({entity_type}).")
            else:
                logger.error(f"Unexpected status code ({entity_type})", 
                            extra={**log_context, "status_code": response.status_code})
                return None

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error during fetch ({entity_type})", 
                        extra={**log_context, "error": str(e)})
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error during fetch ({entity_type})", 
                        extra={**log_context, "error": str(e)})
            return None
        except Exception as e:
            logger.error(f"Unexpected error during detailed entity search: {e}", extra=log_context)
            return None


# For backward compatibility with the functional API
def search_firm_by_crd(firm_crd: str, employee_number: Optional[str] = None) -> Optional[Dict]:
    """
    Search for a firm using its CRD number.
    
    Args:
        firm_crd (str): The Central Registration Depository (CRD) number of the firm.
        employee_number (Optional[str]): Optional identifier for logging.
    
    Returns:
        Optional[Dict]: A dictionary with firm info if successful, None if the fetch fails.
    """
    agent = FinraFirmBrokerCheckAgent(use_mock=True)  # Default to mock mode for backward compatibility
    results = agent.search_firm_by_crd(firm_crd, employee_number)
    return results[0] if results else None

def search_entity(crd_number: str, entity_type: str = "individual", 
                 employee_number: Optional[str] = None) -> Optional[Dict]:
    """
    Fetches basic information from FINRA BrokerCheck for an entity (individual or firm) using their CRD number.
    
    Args:
        crd_number (str): The Central Registration Depository (CRD) number of the entity.
        entity_type (str): Type of entity ('individual' or 'firm'). Defaults to 'individual'.
        employee_number (Optional[str]): An optional identifier for logging context.
    
    Returns:
        Optional[Dict]: A dictionary with basic entity info if successful, None if the fetch fails.
    """
    agent = FinraFirmBrokerCheckAgent(use_mock=True)  # Default to mock mode for backward compatibility
    return agent.search_entity(crd_number, entity_type, employee_number)

def search_entity_detailed_info(crd_number: str, entity_type: str = "individual", 
                               employee_number: Optional[str] = None) -> Optional[Dict]:
    """
    Fetches detailed information from FINRA BrokerCheck for an entity (individual or firm) using their CRD number.
    
    Args:
        crd_number (str): The Central Registration Depository (CRD) number of the entity.
        entity_type (str): Type of entity ('individual' or 'firm'). Defaults to 'individual'.
        employee_number (Optional[str]): An optional identifier for logging context.
    
    Returns:
        Optional[Dict]: A dictionary with detailed entity info if successful, None if the fetch or parsing fails.
    """
    agent = FinraFirmBrokerCheckAgent(use_mock=True)  # Default to mock mode for backward compatibility
    return agent.search_entity_detailed_info(crd_number, entity_type, employee_number)

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
        print("\nFINRA BrokerCheck Agent Test Menu")
        print("================================")
        print("1. Select from sample entities")
        print("2. Search firm by name")
        print("3. Search firm by CRD number")
        print("4. Get firm details by CRD number")
        print("5. Search entity (firm) by CRD number")
        print("6. Get detailed entity (firm) info by CRD number")
        print("0. Exit")
        print("================================")
        return input("Enter your choice (0-6): ")
    
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
    parser = argparse.ArgumentParser(description='FINRA BrokerCheck Agent CLI')
    parser.add_argument('--mock', action='store_true', help='Use mock data instead of real API')
    args = parser.parse_args()
    
    # Create an agent
    agent = FinraFirmBrokerCheckAgent(use_mock=args.mock)
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
                                          "4. Search entity (firm)\n"
                                          "5. Get detailed entity info\n"
                                          "Choice (1-5): ")
                        
                        if sub_choice == '1':
                            results = agent.search_firm(selected_entity['name'])
                            if results:
                                print(f"Found {len(results)} results:")
                                print(json.dumps(results, indent=2))
                            else:
                                print(f"No firms found with name: {selected_entity['name']}")
                                
                        elif sub_choice == '2':
                            results = agent.search_firm_by_crd(selected_entity['organizationCRD'], employee)
                            if results:
                                print(f"Firm Data retrieved: {json.dumps(results, indent=2)}")
                            else:
                                print(f"No firm data retrieved for CRD {selected_entity['organizationCRD']}")
                                
                        elif sub_choice == '3':
                            details = agent.get_firm_details(selected_entity['organizationCRD'], employee)
                            if details:
                                print(f"Firm Details retrieved: {json.dumps(details, indent=2)}")
                            else:
                                print(f"No firm details retrieved for CRD {selected_entity['organizationCRD']}")
                                
                        elif sub_choice == '4':
                            data = agent.search_entity(selected_entity['organizationCRD'], entity_type="firm", employee_number=employee)
                            if data:
                                print(f"Entity (Firm) Data retrieved: {json.dumps(data, indent=2)}")
                            else:
                                print(f"No entity data retrieved for CRD {selected_entity['organizationCRD']}")
                                
                        elif sub_choice == '5':
                            data = agent.search_entity_detailed_info(selected_entity['organizationCRD'], entity_type="firm", employee_number=employee)
                            if data:
                                print(f"Detailed Entity (Firm) Data retrieved: {json.dumps(data, indent=2)}")
                            else:
                                print(f"No detailed entity data retrieved for CRD {selected_entity['organizationCRD']}")
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
                results = agent.search_firm_by_crd(firm_crd, employee)
                if results:
                    print(f"Firm Data retrieved: {json.dumps(results, indent=2)}")
                else:
                    print(f"No firm data retrieved for CRD {firm_crd}")
                    
            elif choice == '4':
                firm_crd = get_input("Enter firm CRD number: ", "131940")
                details = agent.get_firm_details(firm_crd, employee)
                if details:
                    print(f"Firm Details retrieved: {json.dumps(details, indent=2)}")
                else:
                    print(f"No firm details retrieved for CRD {firm_crd}")
                    
            elif choice == '5':
                firm_crd = get_input("Enter firm CRD number: ", "131940")
                data = agent.search_entity(firm_crd, entity_type="firm", employee_number=employee)
                if data:
                    print(f"Entity (Firm) Data retrieved: {json.dumps(data, indent=2)}")
                else:
                    print(f"No entity data retrieved for CRD {firm_crd}")
                    
            elif choice == '6':
                firm_crd = get_input("Enter firm CRD number: ", "131940")
                data = agent.search_entity_detailed_info(firm_crd, entity_type="firm", employee_number=employee)
                if data:
                    print(f"Detailed Entity (Firm) Data retrieved: {json.dumps(data, indent=2)}")
                else:
                    print(f"No detailed entity data retrieved for CRD {firm_crd}")
                    
            else:
                print("Invalid choice. Please try again.")
                
        except RateLimitExceeded as e:
            print(f"Rate limit error: {e}")
        except FinraAPIError as e:
            print(f"FINRA API error: {e}")
        
        input("\nPress Enter to continue...")

__all__ = [
    'FinraFirmBrokerCheckAgent',
    'search_firm_by_crd',
    'search_entity',
    'search_entity_detailed_info',
    'RATE_LIMIT_DELAY',
    'BROKERCHECK_CONFIG'
]