"""SEC IAPD (Investment Adviser Public Disclosure) Agent.

This module provides an agent for interacting with the SEC's IAPD API, which offers
public access to professional information about investment adviser firms registered
with the SEC. The agent fetches data without handling caching, leaving that to the
calling client.

Key Features:
- Two services: Basic search and detailed profile retrieval
- Uses CRD numbers to identify firms
- Structured logging with optional reference ID for traceability
- No caching; clients manage persistence

Terminology:
- CRD Number: A unique identifier assigned to firms
- Investment Adviser (IA): A firm registered under the Investment Advisers Act
- IAPD: Investment Adviser Public Disclosure system
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import json
import logging
from logging import Logger
from typing import Dict, List, Optional, Any, cast, Union
import requests
from datetime import datetime
import time
from functools import wraps
from requests.exceptions import RequestException, HTTPError, ConnectionError, Timeout
from utils.logging_config import setup_logging

# Get module logger
logger = logging.getLogger('sec_iapd_agent')

class SECAPIError(Exception):
    """Base exception for SEC API related errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(self.message)

class SECResponseError(SECAPIError):
    """Exception for invalid or malformed API responses."""
    pass

class SECRequestError(SECAPIError):
    """Exception for API request failures."""
    pass

class SECRateLimitError(SECAPIError):
    """Exception for rate limit related errors."""
    pass

# Configuration for SEC IAPD API
IAPD_CONFIG: Dict[str, Any] = {
    "base_search_url": "https://api.adviserinfo.sec.gov/search/firm",
    "default_params": {
        "hl": "true",  # Highlight search terms in results
        "nrows": "12",  # Number of rows per response
        "start": "0",  # Starting index for pagination
        "r": "25",  # Results per page
        "sort": "score+desc",  # Sort by relevance score descending
        "wt": "json"  # Response format (JSON)
    },
    "max_retries": 3,  # Maximum number of retry attempts
    "retry_delay": 1,  # Initial delay between retries (seconds)
    "retry_backoff": 2,  # Multiplicative factor for retry delay
    "retry_status_codes": {408, 429, 500, 502, 503, 504}  # Status codes to retry on
}

# Rate limiting configuration
RATE_LIMIT_DELAY = 5  # seconds between API calls

def rate_limit(func):
    """Decorator to enforce rate limiting between API calls"""
    last_call = {}  # Dictionary to track last call time per function
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get current time
        current_time = time.time()
        
        # Check if we need to wait
        if func.__name__ in last_call:
            elapsed = current_time - last_call[func.__name__]
            if elapsed < RATE_LIMIT_DELAY:
                wait_time = RATE_LIMIT_DELAY - elapsed
                logger.debug(f"Rate limiting: waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
        
        # Update last call time and execute function
        last_call[func.__name__] = time.time()
        return func(*args, **kwargs)
    
    return wrapper

def retry_on_error(func):
    """Decorator to implement retry logic with exponential backoff."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = IAPD_CONFIG["max_retries"]
        retry_delay = IAPD_CONFIG["retry_delay"]
        retry_backoff = IAPD_CONFIG["retry_backoff"]
        retry_status_codes = IAPD_CONFIG["retry_status_codes"]

        last_error = None
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except HTTPError as e:
                if e.response.status_code in retry_status_codes:
                    wait_time = retry_delay * (retry_backoff ** attempt)
                    logger.warning(
                        f"Request failed with status {e.response.status_code}, "
                        f"retrying in {wait_time} seconds (attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                    last_error = e
                else:
                    raise SECRequestError(
                        f"HTTP error occurred: {str(e)}", 
                        status_code=e.response.status_code,
                        response_text=e.response.text
                    )
            except ConnectionError as e:
                wait_time = retry_delay * (retry_backoff ** attempt)
                logger.warning(
                    f"Connection error occurred, retrying in {wait_time} seconds "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(wait_time)
                last_error = e
            except Timeout as e:
                wait_time = retry_delay * (retry_backoff ** attempt)
                logger.warning(
                    f"Request timed out, retrying in {wait_time} seconds "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(wait_time)
                last_error = e

        # If we get here, we've exhausted our retries
        if last_error:
            if isinstance(last_error, HTTPError):
                raise SECRequestError(
                    f"Max retries exceeded. Last error: {str(last_error)}",
                    status_code=last_error.response.status_code,
                    response_text=last_error.response.text
                )
            raise SECRequestError(f"Max retries exceeded. Last error: {str(last_error)}")

    return wrapper

class SECFirmIAPDAgent:
    """Agent for interacting with SEC's IAPD system for investment adviser firms.

    This agent is responsible for searching and extracting information about
    investment adviser firms from SEC's IAPD website.
    """

    def __init__(self, logger: Optional[Logger] = None):
        """Initialize the SEC IAPD agent.

        Args:
            logger: Optional logger instance. If not provided, a default logger
                   will be created.
        """
        self.logger = logger or logging.getLogger(__name__)
        self.session = requests.Session()
        # Set up headers to match the actual SEC API request
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://adviserinfo.sec.gov',
            'Priority': 'u=1, i',
            'Referer': 'https://adviserinfo.sec.gov/',
            'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site'
        })

    def validate_response(self, response: requests.Response, log_context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and parse API response.

        Args:
            response: Response object from requests
            log_context: Logging context dictionary

        Returns:
            Parsed JSON response data

        Raises:
            SECResponseError: If response validation fails
        """
        try:
            response.raise_for_status()
            data = response.json()
            
            if not isinstance(data, dict):
                raise SECResponseError(
                    "Invalid response format: expected JSON object",
                    status_code=response.status_code,
                    response_text=response.text
                )
            
            hits = data.get("hits")
            if not isinstance(hits, dict):
                raise SECResponseError(
                    "Invalid response structure: missing or invalid 'hits' object",
                    status_code=response.status_code,
                    response_text=response.text
                )
            
            hit_list = hits.get("hits")
            if not isinstance(hit_list, list):
                raise SECResponseError(
                    "Invalid response structure: missing or invalid 'hits.hits' array",
                    status_code=response.status_code,
                    response_text=response.text
                )
            
            return data
            
        except json.JSONDecodeError as e:
            raise SECResponseError(
                f"Failed to parse JSON response: {str(e)}",
                status_code=response.status_code,
                response_text=response.text
            )
        except requests.exceptions.HTTPError as e:
            raise SECRequestError(
                f"HTTP error occurred: {str(e)}",
                status_code=response.status_code,
                response_text=response.text
            )

    @rate_limit
    @retry_on_error
    def search_firm(self, firm_name: str, reference_id: Optional[str] = None) -> List[Dict[str, str]]:
        """Search for a firm in SEC's IAPD system.

        Args:
            firm_name: The name of the firm to search for.
            reference_id: Optional identifier for logging context.

        Returns:
            A list of dictionaries containing information about matching firms.
            Each dictionary contains basic information such as:
            - firm_name: The name of the firm
            - crd_number: The firm's CRD number
            - firm_url: URL to the firm's detailed page

        Raises:
            SECRequestError: If there's an error with the HTTP request
            SECResponseError: If the response is invalid or malformed
            SECRateLimitError: If rate limiting is encountered
        """
        log_context = {
            "firm_name": firm_name,
            "reference_id": reference_id
        }
        self.logger.info("Starting SEC IAPD firm search", extra=log_context)

        try:
            # Construct search parameters
            params = dict(IAPD_CONFIG["default_params"])
            params.update({
                'query': firm_name
            })

            # Log the complete request details
            request_details = {
                "url": IAPD_CONFIG["base_search_url"],
                "method": "GET",
                "params": params,
                "headers": dict(self.session.headers)
            }
            self.logger.debug("Outgoing request details", extra={**log_context, "request": request_details})

            response = self.session.get(
                IAPD_CONFIG["base_search_url"], 
                params=params,
                timeout=(10, 30)  # (connect timeout, read timeout)
            )

            # Log response details
            response_details = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "url": response.url,
                "elapsed": str(response.elapsed)
            }
            self.logger.debug("Response details", extra={**log_context, "response": response_details})

            # Validate and parse response
            data = self.validate_response(response, log_context)
            self.logger.debug("Raw API response", extra={**log_context, "raw_response": data})

            results = []
            total_hits = data["hits"]["total"]

            for hit in data["hits"]["hits"]:
                source = hit.get("_source", {})
                if not isinstance(source, dict):
                    self.logger.warning(
                        "Invalid hit source format",
                        extra={**log_context, "hit": hit}
                    )
                    continue

                result = {
                    'firm_name': source.get('org_name', ''),
                    'crd_number': source.get('org_pk', ''),
                    'firm_url': f"https://adviserinfo.sec.gov/firm/summary/{source.get('org_pk', '')}",
                    'sec_number': source.get('sec_number', ''),
                    'firm_type': source.get('firm_type', ''),
                    'registration_status': source.get('registration_status', '')
                }

                # Include highlight information if available
                if "highlight" in hit:
                    result['highlight'] = hit['highlight']

                results.append(result)

            self.logger.info(
                "IAPD search completed successfully",
                extra={**log_context, "total_hits": total_hits, "results_count": len(results)}
            )

            # Add total_hits to the first result if we have any results
            if results:
                results[0]['total_hits'] = total_hits

            return results

        except SECAPIError:
            # Re-raise any of our custom exceptions
            raise
        except Timeout as e:
            raise SECRequestError(f"Request timed out: {str(e)}")
        except ConnectionError as e:
            raise SECRequestError(f"Connection error: {str(e)}")
        except Exception as e:
            raise SECRequestError(f"Unexpected error: {str(e)}")

    @rate_limit
    @retry_on_error
    def get_firm_details(self, crd_number: str, reference_id: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed information about a specific firm.

        Args:
            crd_number: The firm's CRD number.
            reference_id: Optional identifier for logging context.

        Returns:
            A dictionary containing detailed information about the firm.

        Raises:
            SECRequestError: If there's an error with the HTTP request
            SECResponseError: If the response is invalid or malformed
        """
        log_context = {
            "crd_number": crd_number,
            "reference_id": reference_id
        }
        self.logger.info("Starting SEC IAPD detailed firm search", extra=log_context)

        try:
            url = f"{IAPD_CONFIG['base_search_url']}/{crd_number}"
            params = dict(IAPD_CONFIG["default_params"])

            # Log the complete request details
            request_details = {
                "url": url,
                "method": "GET",
                "params": params,
                "headers": dict(self.session.headers)
            }
            self.logger.debug("Outgoing request details", extra={**log_context, "request": request_details})

            response = self.session.get(
                url, 
                params=params,
                timeout=(10, 30)  # (connect timeout, read timeout)
            )

            # Log response details
            response_details = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "url": response.url,
                "elapsed": str(response.elapsed)
            }
            self.logger.debug("Response details", extra={**log_context, "response": response_details})

            # Validate and parse response
            data = self.validate_response(response, log_context)
            self.logger.debug("Raw API response", extra={**log_context, "raw_response": data})

            if data["hits"]["hits"]:
                content = data["hits"]["hits"][0].get("_source", {})
                self.logger.info(
                    "Detailed data fetched successfully",
                    extra={**log_context, "content_keys": list(content.keys())}
                )
                return content
            else:
                self.logger.warning("No details found for the specified CRD", extra=log_context)
                return {}

        except SECAPIError:
            # Re-raise any of our custom exceptions
            raise
        except Timeout as e:
            raise SECRequestError(f"Request timed out: {str(e)}")
        except ConnectionError as e:
            raise SECRequestError(f"Connection error: {str(e)}")
        except Exception as e:
            raise SECRequestError(f"Unexpected error: {str(e)}")

    @rate_limit
    @retry_on_error
    def search_firm_by_crd(self, organization_crd: str, reference_id: Optional[str] = None) -> List[Dict[str, str]]:
        """Search for a firm in SEC's IAPD system using CRD number.

        Args:
            organization_crd: The firm's CRD number to search for.
            reference_id: Optional identifier for logging context.

        Returns:
            A list of dictionaries containing information about matching firms.
            Each dictionary contains basic information such as:
            - firm_name: The name of the firm
            - crd_number: The firm's CRD number
            - firm_url: URL to the firm's detailed page
            - sec_number: SEC registration number
            - firm_type: Type of firm
            - registration_status: Current registration status

        Raises:
            SECRequestError: If there's an error with the HTTP request
            SECResponseError: If the response is invalid or malformed
            SECRateLimitError: If rate limiting is encountered
        """
        log_context = {
            "organization_crd": organization_crd,
            "reference_id": reference_id
        }
        self.logger.info("Starting SEC IAPD firm search by CRD", extra=log_context)

        try:
            # Construct search parameters
            params = dict(IAPD_CONFIG["default_params"])
            params.update({
                'query': organization_crd
            })

            # Log the complete request details
            request_details = {
                "url": IAPD_CONFIG["base_search_url"],
                "method": "GET",
                "params": params,
                "headers": dict(self.session.headers)
            }
            self.logger.debug("Outgoing request details", extra={**log_context, "request": request_details})

            response = self.session.get(
                IAPD_CONFIG["base_search_url"], 
                params=params,
                timeout=(10, 30)  # (connect timeout, read timeout)
            )

            # Log response details
            response_details = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "url": response.url,
                "elapsed": str(response.elapsed)
            }
            self.logger.debug("Response details", extra={**log_context, "response": response_details})

            # Validate and parse response
            data = self.validate_response(response, log_context)
            self.logger.debug("Raw API response", extra={**log_context, "raw_response": data})

            results = []
            total_hits = data["hits"]["total"]

            for hit in data["hits"]["hits"]:
                source = hit.get("_source", {})
                if not isinstance(source, dict):
                    self.logger.warning(
                        "Invalid hit source format",
                        extra={**log_context, "hit": hit}
                    )
                    continue

                result = {
                    'firm_name': source.get('org_name', ''),
                    'crd_number': source.get('org_pk', ''),
                    'firm_url': f"https://adviserinfo.sec.gov/firm/summary/{source.get('org_pk', '')}",
                    'sec_number': source.get('sec_number', ''),
                    'firm_type': source.get('firm_type', ''),
                    'registration_status': source.get('registration_status', '')
                }

                # Include highlight information if available
                if "highlight" in hit:
                    result['highlight'] = hit['highlight']

                results.append(result)

            self.logger.info(
                "IAPD search completed successfully",
                extra={**log_context, "total_hits": total_hits, "results_count": len(results)}
            )

            # Add total_hits to the first result if we have any results
            if results:
                results[0]['total_hits'] = total_hits

            return results

        except SECAPIError:
            # Re-raise any of our custom exceptions
            raise
        except Timeout as e:
            raise SECRequestError(f"Request timed out: {str(e)}")
        except ConnectionError as e:
            raise SECRequestError(f"Connection error: {str(e)}")
        except Exception as e:
            raise SECRequestError(f"Unexpected error: {str(e)}")

    def save_results(self, results: Dict[str, Any], output_path: str) -> None:
        """Save the search results to a file.

        Args:
            results: Dictionary containing the search results.
            output_path: Path where to save the results.
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{output_path}/sec_iapd_results_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2)
                
            self.logger.info(f"Results saved to {filename}")
            
        except Exception as e:
            self.logger.error(f"Error saving results to {output_path}: {str(e)}")
            raise

def run_cli():
    """Run the CLI menu system for testing the SEC IAPD agent."""
    # Initialize logging with the proper configuration and debug enabled
    loggers = setup_logging(debug=True)
    logger = loggers.get('sec_iapd_agent', logging.getLogger(__name__))
    
    agent = SECFirmIAPDAgent(logger=logger)
    last_results = []  # Store last search results for reuse
    
    def handle_api_error(e: Exception, operation: str) -> None:
        """Handle API errors in a consistent way.
        
        Args:
            e: The exception that occurred
            operation: Description of the operation that failed
        """
        if isinstance(e, SECResponseError):
            print(f"\nError: Invalid response from SEC API during {operation}")
            print(f"Details: {e.message}")
            if e.response_text:
                logger.debug(f"Raw response: {e.response_text}")
        elif isinstance(e, SECRequestError):
            print(f"\nError: Failed to communicate with SEC API during {operation}")
            print(f"Details: {e.message}")
            if hasattr(e, 'status_code'):
                print(f"Status code: {e.status_code}")
        elif isinstance(e, SECRateLimitError):
            print(f"\nError: Rate limit exceeded during {operation}")
            print("Please wait a moment before trying again")
        else:
            print(f"\nAn unexpected error occurred during {operation}: {str(e)}")
        
        logger.error(f"Error during {operation}", exc_info=True)

    def print_menu():
        print("\nSEC IAPD Agent CLI")
        print("=" * 35)
        print("1. Search for a firm by name")
        print("2. Search for a firm by CRD")
        print("3. Get detailed information for a firm")
        print("4. Save last results to file")
        print("5. View last search results")
        print("6. Exit")
        print("=" * 35)
    
    def print_json_result(data: Any, title: Optional[str] = None) -> None:
        """Helper function to print JSON data in a formatted way.
        
        Args:
            data: The data to print in JSON format
            title: Optional title to display above the JSON data
        """
        if title:
            print(f"\n{title}")
            print("=" * len(title))
        print(json.dumps(data, indent=2, sort_keys=True))
    
    def search_firm_by_name_menu():
        nonlocal last_results
        firm_name = input("\nEnter firm name to search: ").strip()
        if not firm_name:
            print("Firm name cannot be empty")
            return
        
        reference_id = input("Enter reference ID (optional, press Enter to skip): ").strip() or None
        
        try:
            results = agent.search_firm(firm_name, reference_id)
            last_results = results
            
            if results:
                print_json_result({
                    "search_query": firm_name,
                    "total_results": len(results),
                    "reference_id": reference_id,
                    "timestamp": datetime.now().isoformat(),
                    "results": results
                }, "Search Results")
            else:
                print(f"\nNo firms found matching '{firm_name}'")
        
        except Exception as e:
            handle_api_error(e, "firm name search")
    
    def search_firm_by_crd_menu():
        nonlocal last_results
        organization_crd = input("\nEnter firm CRD number to search: ").strip()
        if not organization_crd:
            print("CRD number cannot be empty")
            return
        
        reference_id = input("Enter reference ID (optional, press Enter to skip): ").strip() or None
        
        try:
            results = agent.search_firm_by_crd(organization_crd, reference_id)
            last_results = results
            
            if results:
                # Get total_hits from the first result if available
                total_hits = results[0].get('total_hits', len(results))
                # Remove total_hits from the result before displaying
                for result in results:
                    result.pop('total_hits', None)
                
                print_json_result({
                    "search_query_crd": organization_crd,
                    "total_results": total_hits,  # Use the actual total from API
                    "returned_results": len(results),
                    "reference_id": reference_id,
                    "timestamp": datetime.now().isoformat(),
                    "results": results
                }, "Search Results")
            else:
                print(f"\nNo firms found matching CRD '{organization_crd}'")
        
        except Exception as e:
            handle_api_error(e, "firm CRD search")
    
    def get_firm_details_menu():
        if not last_results:
            crd = input("\nEnter firm CRD number: ").strip()
        else:
            print("\nSelect a firm from last search results or enter a CRD number:")
            for i, firm in enumerate(last_results, 1):
                print(f"{i}. {firm['firm_name']} (CRD: {firm['crd_number']})")
            print("Or enter a CRD number directly")
            
            choice = input("\nEnter selection (number or CRD): ").strip()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(last_results):
                    crd = last_results[idx]['crd_number']
                else:
                    crd = choice
            except ValueError:
                crd = choice
        
        if not crd:
            print("CRD number cannot be empty")
            return
        
        reference_id = input("Enter reference ID (optional, press Enter to skip): ").strip() or None
        
        try:
            details = agent.get_firm_details(crd, reference_id)
            if details:
                print_json_result({
                    "crd_number": crd,
                    "reference_id": reference_id,
                    "timestamp": datetime.now().isoformat(),
                    "details": details
                }, f"Detailed Information for CRD {crd}")
            else:
                print(f"\nNo details found for CRD {crd}")
        
        except Exception as e:
            handle_api_error(e, "firm details fetch")
    
    def save_results_menu():
        if not last_results:
            print("\nNo results to save. Please perform a search first.")
            return
        
        output_path = input("\nEnter output directory path (default: 'output'): ").strip() or "output"
        
        try:
            # Ensure output directory exists
            Path(output_path).mkdir(parents=True, exist_ok=True)
            
            # Save results with metadata
            results_with_metadata = {
                "timestamp": datetime.now().isoformat(),
                "results": last_results
            }
            agent.save_results(results_with_metadata, output_path)
            
        except Exception as e:
            print(f"\nError saving results: {e}")
    
    def view_last_results():
        if not last_results:
            print("\nNo results available. Please perform a search first.")
            return
        
        print_json_result(last_results, "Last Search Results")
    
    # Main menu loop
    while True:
        try:
            print_menu()
            choice = input("\nEnter your choice (1-6): ").strip()
            
            if choice == '1':
                search_firm_by_name_menu()
            elif choice == '2':
                search_firm_by_crd_menu()
            elif choice == '3':
                get_firm_details_menu()
            elif choice == '4':
                save_results_menu()
            elif choice == '5':
                view_last_results()
            elif choice == '6':
                print("\nExiting SEC IAPD Agent CLI. Goodbye!")
                break
            else:
                print("\nInvalid choice. Please enter a number between 1 and 6.")
            
        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user.")
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    run_cli()

__all__ = [
    'SECFirmIAPDAgent',
    'IAPD_CONFIG',
    'RATE_LIMIT_DELAY',
    'run_cli'
] 