"""FINRA Firm Broker Check Agent.

This module provides an agent for interacting with the FINRA BrokerCheck API, which offers
public access to professional information about firms registered with FINRA (Financial
Industry Regulatory Authority). The agent fetches data without handling caching, leaving
that to the calling client.

Key Features:
- Two services: Basic search and detailed profile retrieval
- Uses CRD (Central Registration Depository) numbers to identify firms
- Structured logging with optional reference ID for traceability
- No caching; clients manage persistence

Terminology (from FINRA BrokerCheck):
- CRD Number: A unique identifier assigned to firms by FINRA
- Broker-Dealer: A firm registered to conduct securities transactions
- Investment Adviser (IA): A firm registered under the Investment Advisers Act
- BrokerCheck: FINRA's public tool for researching broker and firm backgrounds
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import json
import logging
from logging import Logger
from typing import Dict, List, Optional, Any, cast
import requests
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString
from datetime import datetime
import time
from functools import wraps
from utils.logging_config import setup_logging

# Get module logger
logger = logging.getLogger('finra_firm_brokercheck_agent')

# Configuration for FINRA BrokerCheck API
BROKERCHECK_CONFIG: Dict[str, Any] = {
    "base_search_url": "https://api.brokercheck.finra.org/search/firm",
    "default_params": {
        "filter": "active=true,prev=true",  # Filters for active/previously registered firms
        "includePrevious": "true",  # Include past registrations
        "hl": "true",  # Highlight search terms in results
        "nrows": "12",  # Number of rows per response
        "start": "0",  # Starting index for pagination
        "wt": "json"  # Response format (JSON)
    }
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
                time.sleep(RATE_LIMIT_DELAY - elapsed)
        
        # Update last call time and execute function
        last_call[func.__name__] = time.time()
        return func(*args, **kwargs)
    
    return wrapper

class FinraFirmBrokerCheckAgent:
    """Agent for interacting with FINRA's BrokerCheck system for firms.

    This agent is responsible for searching and extracting information about
    firms from FINRA's BrokerCheck website.
    """

    def __init__(self, logger: Optional[Logger] = None):
        """Initialize the FINRA BrokerCheck agent.

        Args:
            logger: Optional logger instance. If not provided, a default logger
                   will be created.
        """
        self.logger = logger or logging.getLogger(__name__)
        self.session = requests.Session()
        # Set up common headers to mimic browser behavior
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5'
        })

    @rate_limit
    def search_firm(self, firm_name: str, reference_id: Optional[str] = None) -> List[Dict[str, str]]:
        """Search for a firm in FINRA's BrokerCheck system.

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
            requests.RequestException: If there's an error with the HTTP request.
        """
        log_context = {
            "firm_name": firm_name,
            "reference_id": reference_id
        }
        self.logger.info("Starting FINRA BrokerCheck firm search", extra=log_context)

        try:
            # Construct search parameters
            params = dict(BROKERCHECK_CONFIG["default_params"])
            params.update({
                'query': firm_name,
                'type': 'Firm',
                'sortField': 'Relevance',
                'sortOrder': 'Desc',
                'brokerDealers': 'true',
                'investmentAdvisors': 'true',
                'isNlSearch': 'false',
                'size': '50'
            })

            self.logger.debug("Fetching from BrokerCheck API", 
                            extra={**log_context, "url": BROKERCHECK_CONFIG["base_search_url"], 
                                  "params": params})

            response = self.session.get(BROKERCHECK_CONFIG["base_search_url"], params=params)
            response.raise_for_status()

            if response.status_code == 200:
                data = response.json()
                self.logger.info("BrokerCheck search completed successfully", 
                               extra={**log_context, "response_data": data})
                
                results = []
                if "hits" in data and "hits" in data["hits"]:
                    for hit in data["hits"]["hits"]:
                        source = hit.get("_source", {})
                        results.append({
                            'firm_name': source.get('org_name', ''),
                            'crd_number': source.get('org_source_id', ''),
                            'firm_url': f"https://brokercheck.finra.org/firm/summary/{source.get('org_source_id', '')}"
                        })
                
                return results
            else:
                self.logger.error("Unexpected status code", 
                                extra={**log_context, "status_code": response.status_code})
                return []

        except requests.exceptions.RequestException as e:
            self.logger.error("Request error during fetch", 
                            extra={**log_context, "error": str(e)})
            raise

    @rate_limit
    def get_firm_details(self, crd_number: str, reference_id: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed information about a specific firm.

        Args:
            crd_number: The firm's CRD number.
            reference_id: Optional identifier for logging context.

        Returns:
            A dictionary containing detailed information about the firm.

        Raises:
            requests.RequestException: If there's an error with the HTTP request.
        """
        log_context = {
            "crd_number": crd_number,
            "reference_id": reference_id
        }
        self.logger.info("Starting FINRA BrokerCheck detailed firm search", extra=log_context)

        try:
            url = f'https://api.brokercheck.finra.org/search/firm/{crd_number}'
            params = dict(BROKERCHECK_CONFIG["default_params"])

            self.logger.debug("Fetching detailed info from BrokerCheck API", 
                            extra={**log_context, "url": url, "params": params})

            response = self.session.get(url, params=params)
            response.raise_for_status()

            if response.status_code == 200:
                raw_data = response.json()
                if "hits" in raw_data and raw_data["hits"]["hits"]:
                    content_str = raw_data["hits"]["hits"][0]["_source"]["content"]
                    try:
                        detailed_data = json.loads(content_str)
                        self.logger.info("Detailed data fetched and parsed successfully", 
                                       extra=log_context)
                        return detailed_data
                    except json.JSONDecodeError as e:
                        self.logger.error("Failed to parse content JSON", 
                                        extra={**log_context, "error": str(e)})
                        return {}
                else:
                    self.logger.warning("No hits found in detailed response", extra=log_context)
                    return {}
            else:
                self.logger.error("Unexpected status code", 
                                extra={**log_context, "status_code": response.status_code})
                return {}

        except requests.exceptions.RequestException as e:
            self.logger.error("Request error during fetch", 
                            extra={**log_context, "error": str(e)})
            raise

    @rate_limit
    def search_firm_by_crd(self, organization_crd: str, reference_id: Optional[str] = None) -> List[Dict[str, str]]:
        """Search for a firm in FINRA's BrokerCheck system using CRD number.

        Args:
            organization_crd: The firm's CRD number to search for.
            reference_id: Optional identifier for logging context.

        Returns:
            A list of dictionaries containing information about matching firms.
            Each dictionary contains basic information such as:
            - firm_name: The name of the firm
            - crd_number: The firm's CRD number
            - firm_url: URL to the firm's detailed page

        Raises:
            requests.RequestException: If there's an error with the HTTP request.
        """
        log_context = {
            "organization_crd": organization_crd,
            "reference_id": reference_id
        }
        self.logger.info("Starting FINRA BrokerCheck firm search by CRD", extra=log_context)

        try:
            # Construct search parameters
            params = dict(BROKERCHECK_CONFIG["default_params"])
            params.update({
                'query': organization_crd,  # Use query parameter instead of firm
                'type': 'Firm',
                'sortField': 'Relevance',
                'sortOrder': 'Desc',
                'brokerDealers': 'true',
                'investmentAdvisors': 'true',
                'isNlSearch': 'false',
                'size': '50'
            })

            self.logger.debug("Fetching from BrokerCheck API", 
                            extra={**log_context, "url": BROKERCHECK_CONFIG["base_search_url"], 
                                  "params": params})

            response = self.session.get(BROKERCHECK_CONFIG["base_search_url"], params=params)
            response.raise_for_status()

            if response.status_code == 200:
                try:
                    data = response.json()
                    self.logger.debug("Raw API response", extra={"response": data})
                    
                    results = []
                    total_hits = 0
                    
                    # Check if we have valid response data
                    if data and isinstance(data, dict):
                        hits = data.get("hits", {})
                        if isinstance(hits, dict):
                            # Get total hits count
                            total_hits = hits.get("total", 0)
                            hit_list = hits.get("hits", [])
                            if isinstance(hit_list, list):
                                for hit in hit_list:
                                    if isinstance(hit, dict):
                                        source = hit.get("_source", {})
                                        if source:
                                            results.append({
                                                'firm_name': source.get('org_name', ''),
                                                'crd_number': source.get('org_source_id', ''),
                                                'firm_url': f"https://brokercheck.finra.org/firm/summary/{source.get('org_source_id', '')}"
                                            })
                    
                    self.logger.info("BrokerCheck search completed successfully", 
                                   extra={**log_context, "total_hits": total_hits, "results_count": len(results)})
                    
                    # Add total_hits to the first result if we have any results
                    if results:
                        results[0]['total_hits'] = total_hits
                    
                    return results
                
                except (json.JSONDecodeError, AttributeError, TypeError) as e:
                    self.logger.error("Error parsing API response", 
                                    extra={**log_context, "error": str(e), "response_text": response.text})
                    return []
            else:
                self.logger.error("Unexpected status code", 
                                extra={**log_context, "status_code": response.status_code})
                return []

        except requests.RequestException as e:
            self.logger.error("Request error during fetch", 
                            extra={**log_context, "error": str(e)})
            raise

    def save_results(self, results: Dict[str, Any], output_path: str) -> None:
        """Save the search results to a file.

        Args:
            results: Dictionary containing the search results.
            output_path: Path where to save the results.
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{output_path}/finra_results_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2)
                
            self.logger.info(f"Results saved to {filename}")
            
        except Exception as e:
            self.logger.error(f"Error saving results to {output_path}: {str(e)}")
            raise

def run_cli():
    """Run the CLI menu system for testing the FINRA firm broker check agent."""
    # Initialize logging with the proper configuration
    loggers = setup_logging()  # Remove debug=False to use default level
    logger = loggers.get('finra_brokercheck', logging.getLogger(__name__))
    
    agent = FinraFirmBrokerCheckAgent(logger=logger)
    last_results = []  # Store last search results for reuse
    
    def print_menu():
        print("\nFINRA Firm BrokerCheck Agent CLI")
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
        
        except requests.RequestException as e:
            print(f"\nError searching for firm: {e}")
    
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
        
        except requests.RequestException as e:
            print(f"\nError searching for firm: {e}")
    
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
        
        except requests.RequestException as e:
            print(f"\nError getting firm details: {e}")
    
    def save_results_menu():
        if not last_results:
            print("\nNo results to save. Please perform a search first.")
            return
        
        output_path = input("\nEnter output directory path (press Enter for current directory): ").strip() or "."
        
        try:
            # Create a dictionary with search results and metadata
            data_to_save = {
                "timestamp": datetime.now().isoformat(),
                "results": last_results,
                "count": len(last_results)
            }
            
            agent.save_results(data_to_save, output_path)
            print(f"\nResults saved successfully to {output_path}")
            print_json_result(data_to_save, "Saved Data Preview")
        
        except Exception as e:
            print(f"\nError saving results: {e}")
    
    def view_last_results():
        if not last_results:
            print("\nNo previous search results available.")
            return
        
        print_json_result({
            "total_results": len(last_results),
            "timestamp": datetime.now().isoformat(),
            "results": last_results
        }, "Last Search Results")
    
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
                print("\nExiting FINRA Firm BrokerCheck Agent CLI. Goodbye!")
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
    'FinraFirmBrokerCheckAgent',
    'BROKERCHECK_CONFIG',
    'RATE_LIMIT_DELAY',
    'run_cli'
]