"""
services.py

This module provides the FirmServicesFacade class, which consolidates access to
external financial regulatory services (FINRA BrokerCheck and SEC IAPD firm data)
and provides a unified interface for business logic to retrieve and store normalized data.
"""

import json
import logging
import argparse
import time
from typing import Optional, Dict, Any, List, Union
import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from utils.logging_config import setup_logging
from services.firm_marshaller import (
    FirmMarshaller,
    fetch_finra_firm_search,
    fetch_finra_firm_by_crd,
    fetch_finra_firm_details,
    fetch_sec_firm_search,
    fetch_sec_firm_by_crd,
    fetch_sec_firm_details,
    ResponseStatus
)
from agents.firm_compliance_report_agent import save_compliance_report

# Initialize logging
loggers = setup_logging(debug=True)
logger = loggers.get('services', logging.getLogger(__name__))

class FirmServicesFacade:
    """Facade for accessing firm-related financial regulatory services."""
    
    def __init__(self):
        """Initialize the facade with required services."""
        self.firm_marshaller = FirmMarshaller()
        self.last_api_call_time = 0
        self.service_delay = 4  # 4 second delay between API calls at service level
        logger.debug("FirmServicesFacade initialized")
    
    def _apply_service_delay(self):
        """Apply a delay between API calls to prevent rate limiting issues."""
        current_time = time.time()
        elapsed = current_time - self.last_api_call_time
        if elapsed < self.service_delay:
            delay = self.service_delay - elapsed
            logger.debug(f"Applying service-level delay of {delay:.2f}s")
            time.sleep(delay)
        self.last_api_call_time = time.time()

    def search_firm(self, subject_id: str, firm_name: str) -> List[Dict[str, Any]]:
        """
        Search for a firm across both FINRA and SEC databases.
        
        Args:
            subject_id: The ID of the subject/client making the request
            firm_name: Name of the firm to search for
            
        Returns:
            List of matching firm records with normalized data
        """
        logger.info(f"Searching for firm: {firm_name}")
        results = []
        firm_id = f"search_{firm_name}"  # Create a unique ID for caching
        
        # Search FINRA
        try:
            # Apply delay before FINRA API call
            self._apply_service_delay()
            finra_response = fetch_finra_firm_search(subject_id, firm_id, {"firm_name": firm_name})
            if finra_response.status == ResponseStatus.SUCCESS and finra_response.data:
                if isinstance(finra_response.data, list):
                    logger.debug(f"Found {len(finra_response.data)} FINRA results for {firm_name}")
                    for result in finra_response.data:
                        if isinstance(result, dict):
                            normalized = self.firm_marshaller.normalize_finra_result(result)
                            results.append(normalized)
                elif isinstance(finra_response.data, dict):
                    normalized = self.firm_marshaller.normalize_finra_result(finra_response.data)
                    results.append(normalized)
        except Exception as e:
            logger.error(f"Error searching FINRA for {firm_name}: {str(e)}")
            
        # Search SEC
        try:
            # Apply delay before SEC API call
            self._apply_service_delay()
            sec_response = fetch_sec_firm_search(subject_id, firm_id, {"firm_name": firm_name})
            if sec_response.status == ResponseStatus.SUCCESS and sec_response.data:
                if isinstance(sec_response.data, list):
                    logger.debug(f"Found {len(sec_response.data)} SEC results for {firm_name}")
                    for result in sec_response.data:
                        if isinstance(result, dict):
                            normalized = self.firm_marshaller.normalize_sec_result(result)
                            results.append(normalized)
                elif isinstance(sec_response.data, dict):
                    normalized = self.firm_marshaller.normalize_sec_result(sec_response.data)
                    results.append(normalized)
        except Exception as e:
            logger.error(f"Error searching SEC for {firm_name}: {str(e)}")
            
        return results

    def get_firm_details(self, subject_id: str, crd_number: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed firm information from both FINRA and SEC using CRD number.
        
        Precedence rules:
        1. First check FINRA BrokerCheck to determine if found by CRD
        2. Then check SEC to see if found there
        3. If found in both places, SEC wins
        4. If neither is found, use the not found result of SEC
        5. If firm exists in search but detailed information is unavailable, return partial information
           with a status indicating the firm is inactive/expelled
        
        Args:
            subject_id: The ID of the subject/client making the request
            crd_number: The firm's CRD number
            
        Returns:
            Combined firm details or None if not found. May include a 'firm_status' field
            with values like 'active', 'inactive', or 'expelled' to indicate the firm's status.
        """
        logger.info(f"Getting firm details for CRD: {crd_number}")
        firm_id = f"details_{crd_number}"  # Create a unique ID for caching
        
        finra_details = None
        sec_details = None
        
        # First check if firm exists in FINRA by CRD
        finra_exists = False
        search_firm_id = f"search_crd_{crd_number}"
        try:
            # Apply delay before FINRA API call
            self._apply_service_delay()
            finra_search_response = fetch_finra_firm_by_crd(subject_id, search_firm_id, {"crd_number": crd_number})
            if finra_search_response.status == ResponseStatus.SUCCESS and finra_search_response.data:
                finra_exists = True
                logger.debug(f"Firm exists in FINRA for CRD {crd_number}")
        except Exception as e:
            logger.error(f"Error checking if firm exists in FINRA for CRD {crd_number}: {str(e)}")
        
        # Then check if firm exists in SEC by CRD
        sec_exists = False
        try:
            # Apply delay before SEC API call
            self._apply_service_delay()
            sec_search_response = fetch_sec_firm_by_crd(subject_id, search_firm_id, {"crd_number": crd_number})
            if sec_search_response.status == ResponseStatus.SUCCESS and sec_search_response.data:
                sec_exists = True
                logger.debug(f"Firm exists in SEC for CRD {crd_number}")
        except Exception as e:
            logger.error(f"Error checking if firm exists in SEC for CRD {crd_number}: {str(e)}")
        
        # Get FINRA details if it exists in FINRA
        if finra_exists:
            try:
                # Apply delay before FINRA details API call
                self._apply_service_delay()
                finra_response = fetch_finra_firm_details(subject_id, firm_id, {"crd_number": crd_number})
                if finra_response.status == ResponseStatus.SUCCESS and finra_response.data:
                    logger.debug(f"Found FINRA details for CRD {crd_number}")
                    if isinstance(finra_response.data, dict):
                        finra_details = self.firm_marshaller.normalize_finra_details(finra_response.data)
                    elif isinstance(finra_response.data, list) and finra_response.data:
                        finra_details = self.firm_marshaller.normalize_finra_details(finra_response.data[0])
            except Exception as e:
                logger.error(f"Error getting FINRA details for CRD {crd_number}: {str(e)}")
        
        # Get SEC details if it exists in SEC
        if sec_exists:
            try:
                # Apply delay before SEC details API call
                self._apply_service_delay()
                sec_response = fetch_sec_firm_details(subject_id, firm_id, {"crd_number": crd_number})
                if sec_response.status == ResponseStatus.SUCCESS and sec_response.data:
                    logger.debug(f"Found SEC details for CRD {crd_number}")
                    if isinstance(sec_response.data, dict):
                        sec_details = self.firm_marshaller.normalize_sec_details(sec_response.data)
                    elif isinstance(sec_response.data, list) and sec_response.data:
                        sec_details = self.firm_marshaller.normalize_sec_details(sec_response.data[0])
            except Exception as e:
                logger.error(f"Error getting SEC details for CRD {crd_number}: {str(e)}")
        
        # Apply precedence rules
        if finra_details and sec_details:
            # If found in both places, SEC wins, but combine the data
            logger.debug(f"Found in both FINRA and SEC, combining with SEC precedence for CRD {crd_number}")
            # Start with FINRA details as base
            combined = finra_details.copy()
            # Add SEC-specific fields
            combined.update({
                'sec_number': sec_details.get('sec_number'),
                'other_names': sec_details.get('other_names', []),
                'notice_filings': sec_details.get('notice_filings', []),
                'registration_date': sec_details.get('registration_date'),
                'is_sec_registered': sec_details.get('is_sec_registered', False),
                'is_state_registered': sec_details.get('is_state_registered', False),
                'is_era_registered': sec_details.get('is_era_registered', False),
                'is_sec_era_registered': sec_details.get('is_sec_era_registered', False),
                'is_state_era_registered': sec_details.get('is_state_era_registered', False),
                'adv_filing_date': sec_details.get('adv_filing_date'),
                'has_adv_pdf': sec_details.get('has_adv_pdf', False),
                'accountant_exams': sec_details.get('accountant_exams', []),
                'brochures': sec_details.get('brochures', []),
                'source': 'SEC',
                'firm_status': 'active'
            })
            
            # Ensure registration flags are properly set
            if not combined.get('is_sec_registered') and sec_details.get('is_sec_registered'):
                combined['is_sec_registered'] = True
            
            # Always set is_finra_registered to True if firm exists in FINRA
            if finra_exists:
                combined['is_finra_registered'] = True
                
            # If firm_ia_scope is available in either source, include it
            if 'firm_ia_scope' in sec_details and not combined.get('firm_ia_scope'):
                combined['firm_ia_scope'] = sec_details.get('firm_ia_scope')
            elif 'firm_ia_scope' in finra_details and not combined.get('firm_ia_scope'):
                combined['firm_ia_scope'] = finra_details.get('firm_ia_scope')
                
            return combined
        elif finra_details:
            # If only found in FINRA, use FINRA details
            logger.debug(f"Found only in FINRA for CRD {crd_number}")
            finra_details['source'] = 'FINRA'
            finra_details['firm_status'] = 'active'
            
            # Always set is_finra_registered to True if firm exists in FINRA
            finra_details['is_finra_registered'] = True
                
            return finra_details
        elif sec_details:
            # If only found in SEC, use SEC details
            logger.debug(f"Found only in SEC for CRD {crd_number}")
            sec_details['source'] = 'SEC'
            sec_details['firm_status'] = 'active'
            
            # Ensure SEC registration flag is set
            if not sec_details.get('is_sec_registered'):
                sec_details['is_sec_registered'] = True
                
            return sec_details
        else:
            # Check if firm exists in search but details are unavailable
            # This is the case for inactive/expelled firms
            if finra_exists or sec_exists:
                logger.debug(f"Firm exists in search but details unavailable for CRD {crd_number}, likely inactive/expelled")
                
                # Create a partial record with available information
                partial_info = {
                    'crd_number': crd_number,
                    'firm_status': 'inactive',
                    'source': 'SEC' if sec_exists else 'FINRA'
                }
                
                # Try to get the firm name from search results
                if sec_exists and hasattr(sec_search_response, 'data') and sec_search_response.data:
                    try:
                        sec_search_data = sec_search_response.data
                        if isinstance(sec_search_data, dict):
                            # Extract firm name from available fields
                            firm_name = sec_search_data.get('org_name') or sec_search_data.get('firm_name')
                            if firm_name:
                                partial_info['firm_name'] = firm_name
                            else:
                                partial_info['firm_name'] = f"Unknown Firm (CRD #{crd_number})"
                            
                            # Get other names if available
                            if 'firm_other_names' in sec_search_data:
                                partial_info['other_names'] = sec_search_data.get('firm_other_names', [])
                        elif isinstance(sec_search_data, list) and sec_search_data:
                            first_result = sec_search_data[0]
                            firm_name = first_result.get('org_name') or first_result.get('firm_name')
                            if firm_name:
                                partial_info['firm_name'] = firm_name
                            else:
                                partial_info['firm_name'] = f"Unknown Firm (CRD #{crd_number})"
                            
                            # Get other names if available
                            if 'firm_other_names' in first_result:
                                partial_info['other_names'] = first_result.get('firm_other_names', [])
                    except Exception as e:
                        logger.error(f"Error extracting firm name from SEC search for CRD {crd_number}: {str(e)}")
                
                # Try FINRA search results if SEC didn't provide a name
                if 'firm_name' not in partial_info and finra_exists and hasattr(finra_search_response, 'data') and finra_search_response.data:
                    try:
                        finra_search_data = finra_search_response.data
                        if isinstance(finra_search_data, dict) and 'firm_name' in finra_search_data:
                            firm_name = finra_search_data.get('firm_name')
                            if firm_name is not None:
                                partial_info['firm_name'] = firm_name
                        elif isinstance(finra_search_data, list) and finra_search_data and 'firm_name' in finra_search_data[0]:
                            firm_name = finra_search_data[0].get('firm_name')
                            if firm_name is not None:
                                partial_info['firm_name'] = firm_name
                    except Exception as e:
                        logger.error(f"Error extracting firm name from FINRA search for CRD {crd_number}: {str(e)}")
                
                # If we still don't have a firm name, use a generic one
                if 'firm_name' not in partial_info:
                    partial_info['firm_name'] = f"Unknown Firm (CRD #{crd_number})"
                
                # Add a message about the firm status
                partial_info['status_message'] = "This firm exists but appears to be inactive or expelled. Limited information is available."
                
                # Add registration status if available
                if sec_exists and hasattr(sec_search_response, 'data') and sec_search_response.data:
                    try:
                        sec_search_data = sec_search_response.data
                        if isinstance(sec_search_data, dict) and 'registration_status' in sec_search_data:
                            registration_status = sec_search_data.get('registration_status')
                            if registration_status is not None:
                                partial_info['registration_status'] = registration_status
                    except Exception:
                        pass
                
                return partial_info
            
            # Check if we have search results but no details
            # This is a more reliable way to determine if a firm is inactive/expelled
            if finra_exists or sec_exists:
                logger.debug(f"Firm exists in search but details unavailable for CRD {crd_number}, likely inactive/expelled")
                
                # Create a partial record with available information
                partial_info = {
                    'crd_number': crd_number,
                    'firm_status': 'inactive',
                    'source': 'SEC' if sec_exists else 'FINRA'
                }
                
                # Try to get the firm name from search results
                if sec_exists and hasattr(sec_search_response, 'data') and sec_search_response.data:
                    try:
                        sec_search_data = sec_search_response.data
                        if isinstance(sec_search_data, dict) and 'org_name' in sec_search_data:
                            firm_name = sec_search_data.get('org_name')
                            if firm_name is not None:
                                partial_info['firm_name'] = firm_name
                        elif isinstance(sec_search_data, list) and sec_search_data and 'org_name' in sec_search_data[0]:
                            firm_name = sec_search_data[0].get('org_name')
                            if firm_name is not None:
                                partial_info['firm_name'] = firm_name
                    except Exception as e:
                        logger.error(f"Error extracting firm name from SEC search for CRD {crd_number}: {str(e)}")
                
                if finra_exists and hasattr(finra_search_response, 'data') and finra_search_response.data:
                    try:
                        finra_search_data = finra_search_response.data
                        if isinstance(finra_search_data, dict) and 'firm_name' in finra_search_data:
                            firm_name = finra_search_data.get('firm_name')
                            if firm_name is not None:
                                partial_info['firm_name'] = firm_name
                        elif isinstance(finra_search_data, list) and finra_search_data and 'firm_name' in finra_search_data[0]:
                            firm_name = finra_search_data[0].get('firm_name')
                            if firm_name is not None:
                                partial_info['firm_name'] = firm_name
                    except Exception as e:
                        logger.error(f"Error extracting firm name from FINRA search for CRD {crd_number}: {str(e)}")
                
                # If we still don't have a firm name, use a generic one
                if 'firm_name' not in partial_info:
                    partial_info['firm_name'] = f"Unknown Firm (CRD #{crd_number})"
                
                # Add a message about the firm status
                partial_info['status_message'] = "This firm exists but appears to be inactive or expelled. Limited information is available."
                
                return partial_info
            
            # If not found in either, return None
            logger.debug(f"Not found in either FINRA or SEC for CRD {crd_number}")
            return None

    def search_firm_by_crd(self, subject_id: str, crd_number: str, entity_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Search for a firm by CRD number across both FINRA and SEC databases,
        then fetch detailed information if found.
        
        Args:
            subject_id: The ID of the subject/client making the request
            crd_number: The firm's CRD number
            entity_name: Optional entity name for logging and verification
            
        Returns:
            Detailed firm information or None if not found
        """
        log_context = {
            "crd_number": crd_number,
            "entity_name": entity_name
        }
        
        logger.info(f"Searching for firm by CRD: {crd_number}", extra=log_context)
        firm_id = f"search_crd_{crd_number}"  # Create a unique ID for caching
        
        # First, check if we can find the firm in either database
        found_firm = False
        source = None
        
        # Try SEC
        sec_found = False
        try:
            # Apply delay before SEC API call
            self._apply_service_delay()
            sec_response = fetch_sec_firm_by_crd(subject_id, firm_id, {"crd_number": crd_number})
            if sec_response.status == ResponseStatus.SUCCESS and sec_response.data:
                logger.debug(f"Found SEC result for CRD {crd_number}", extra=log_context)
                found_firm = True
                sec_found = True
                source = "SEC"
        except Exception as e:
            logger.error(f"Error searching SEC by CRD {crd_number}: {str(e)}", extra=log_context)
                
        # Always try FINRA too, regardless of SEC result
        try:
            # Apply delay before FINRA API call
            self._apply_service_delay()
            finra_response = fetch_finra_firm_by_crd(subject_id, firm_id, {"crd_number": crd_number})
            if finra_response.status == ResponseStatus.SUCCESS and finra_response.data:
                logger.debug(f"Found FINRA result for CRD {crd_number}", extra=log_context)
                found_firm = True
                if not sec_found:  # Only change source if SEC didn't find it
                    source = "FINRA"
        except Exception as e:
            logger.error(f"Error searching FINRA by CRD {crd_number}: {str(e)}", extra=log_context)
        
        # If we found the firm in either database, get detailed information
        if found_firm:
            logger.info(f"Found firm with CRD {crd_number} in {source}, fetching detailed information", extra=log_context)
            return self.get_firm_details(subject_id, crd_number)
                
        return None

    def save_business_report(self, report: Dict[str, Any], business_ref: str) -> None:
        """
        Save a business report to the cache.
        
        Args:
            report: The report to save
            business_ref: Reference ID for the business
        """
        logger.info(f"Saving business report for business_ref: {business_ref}")
        try:
            # For now, we'll just log the report since we don't have persistent storage
            logger.debug(f"Report content: {json.dumps(report, indent=2)}")
        except Exception as e:
            logger.error(f"Error saving report: {str(e)}")
            raise

    def save_compliance_report(self, report: Dict[str, Any], employee_number: Optional[str] = None) -> bool:
        """
        Save a compliance report with optional employee number.
        
        Args:
            report: The compliance report to save
            employee_number: Optional employee number for reference
            
        Returns:
            bool: True if save was successful, False otherwise
        """
        logger.info(f"Saving compliance report for employee_number={employee_number}")
        success = save_compliance_report(report, employee_number)
        if success:
            logger.debug(f"Compliance report saved: {json.dumps(report, indent=2)}")
        else:
            logger.error("Failed to save compliance report")
        return success

def print_results(results: Union[Dict[str, Any], List[Dict[str, Any]], None], indent: int = 2) -> None:
    """Print results in a formatted JSON structure."""
    if results is None or (isinstance(results, list) and len(results) == 0):
        print("\nNo results found.")
    else:
        print("\nResults:")
        print(json.dumps(results, indent=indent))

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Firm Services CLI - Search and retrieve firm information from FINRA and SEC"
    )
    
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless (non-interactive) mode with CLI arguments"
    )
    
    parser.add_argument(
        "--subject-id",
        required=False,
        help="ID of the subject/client making the request (required in headless mode)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level (default: INFO)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Search firm by name
    search_parser = subparsers.add_parser(
        "search",
        help="Search for firms by name"
    )
    search_parser.add_argument(
        "firm_name",
        help="Name of the firm to search for"
    )
    
    # Get firm details
    details_parser = subparsers.add_parser(
        "details",
        help="Get detailed firm information by CRD number"
    )
    details_parser.add_argument(
        "crd_number",
        help="CRD number of the firm"
    )
    
    # Search firm by CRD
    crd_parser = subparsers.add_parser(
        "search-crd",
        help="Search for a firm by CRD number"
    )
    crd_parser.add_argument(
        "crd_number",
        help="CRD number of the firm"
    )
    
    return parser.parse_args()

def interactive_menu(subject_id: str, log_level: str) -> None:
    """Run an interactive menu for testing firm services."""
    facade = FirmServicesFacade()

    # Prompt for subject_id and crd_number at the start
    print("\n=== Firm Services Interactive Session ===")
    current_subject_id = input(f"Enter subject ID [{subject_id}]: ").strip() or subject_id
    current_crd_number = input("Enter CRD number: ").strip()

    while True:
        print("\n=== Firm Services Testing Menu ===")
        print("1. Search firm by name")
        print("2. Get firm details by CRD")
        print("3. Search firm by CRD")
        print("4. Example: Search 'Baker Avenue Asset Management'")
        print("5. Example: Search CRD '131940'")
        print("6. Change subject ID or CRD number")
        print("7. Exit")
        
        choice = input("\nEnter your choice (1-7): ").strip()
        
        if choice == "1":
            firm_name = input("Enter firm name to search: ").strip()
            if firm_name:
                results = facade.search_firm(current_subject_id, firm_name)
                print_results(results)
        
        elif choice == "2":
            # Use stored CRD number
            if current_crd_number:
                results = facade.get_firm_details(current_subject_id, current_crd_number)
                print_results(results)
            else:
                print("\nNo CRD number set. Please set it using option 6.")
        
        elif choice == "3":
            # Use stored CRD number
            if current_crd_number:
                results = facade.search_firm_by_crd(current_subject_id, current_crd_number)
                print_results(results)
            else:
                print("\nNo CRD number set. Please set it using option 6.")
                
        elif choice == "4":
            print("\nSearching for: Baker Avenue Asset Management...")
            results = facade.search_firm(current_subject_id, "Baker Avenue Asset Management")
            print_results(results)
            
        elif choice == "5":
            print("\nSearching for CRD: 131940...")
            results = facade.search_firm_by_crd(current_subject_id, "131940")
            print_results(results)
        
        elif choice == "6":
            # Change subject ID or CRD number
            new_subject_id = input(f"Enter new subject ID [{current_subject_id}]: ").strip()
            if new_subject_id:
                current_subject_id = new_subject_id
            new_crd_number = input(f"Enter new CRD number [{current_crd_number}]: ").strip()
            if new_crd_number:
                current_crd_number = new_crd_number
            print("\nSubject ID and CRD number updated.")
        
        elif choice == "7":
            print("\nExiting...")
            break
        
        else:
            print("\nInvalid choice. Please try again.")
        
        input("\nPress Enter to continue...")

def main():
    """Main entry point for the CLI."""
    args = parse_args()
    
    # Configure logging with user-specified level
    log_level = getattr(logging, args.log_level)
    loggers = setup_logging(debug=(log_level == logging.DEBUG))
    logger = loggers.get('services', logging.getLogger(__name__))
    
    # Set log level for all loggers
    for logger_name in loggers:
        if isinstance(logger_name, str) and not logger_name.startswith('_'):
            loggers[logger_name].setLevel(log_level)
    
    facade = FirmServicesFacade()
    
    if not args.headless:
        # Always run interactive menu unless --headless is specified
        interactive_menu(args.subject_id or "", args.log_level)
        return

    # Headless mode: require subject-id and command
    if not args.subject_id:
        print("\nError: --subject-id is required in headless mode.")
        sys.exit(1)

    if not args.command:
        print("\nError: command is required in headless mode. Use --help for usage information.")
        sys.exit(1)

    try:
        if args.command == "search":
            results = facade.search_firm(args.subject_id, args.firm_name)
            print_results(results)
        
        elif args.command == "details":
            results = facade.get_firm_details(args.subject_id, args.crd_number)
            print_results(results)
        
        elif args.command == "search-crd":
            results = facade.search_firm_by_crd(args.subject_id, args.crd_number)
            print_results(results)
        
        else:
            print("\nNo command specified. Use --help for usage information.")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error in main: {str(e)}", exc_info=True)
        print(f"\nError: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()