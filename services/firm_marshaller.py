"""Service for marshalling firm data between different formats.

This module handles the conversion and transformation of firm data between different formats
and representations, with caching support and rate limiting.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import json
import logging
from logging import Logger
from typing import Dict, List, Optional, Any, Callable, Union, TypeVar, Generic
import time
from datetime import datetime, timedelta
from functools import wraps, partial
from dataclasses import dataclass
from enum import Enum

from utils.logging_config import setup_logging
from agents.finra_firm_broker_check_agent import FinraFirmBrokerCheckAgent
from agents.sec_firm_iapd_agent import SECFirmIAPDAgent

# Initialize logging
loggers = setup_logging(debug=True)
logger = loggers.get('firm_marshaller', logging.getLogger(__name__))

# Configuration
CACHE_FOLDER = Path(__file__).parent.parent / "cache"
CACHE_TTL_DAYS = 90
DATE_FORMAT = "%Y%m%d"
MANIFEST_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
REQUEST_LOG_FILE = "request_log.txt"

# Agent service mapping
AGENT_SERVICES: Dict[str, Dict[str, Callable]] = {
    "FINRA_FirmBrokerCheck_Agent": {
        "search_firm": FinraFirmBrokerCheckAgent().search_firm,
        "search_firm_by_crd": FinraFirmBrokerCheckAgent().search_firm_by_crd,
        "get_firm_details": FinraFirmBrokerCheckAgent().get_firm_details
    },
    "SEC_FirmIAPD_Agent": {
        "search_firm": SECFirmIAPDAgent().search_firm,
        "search_firm_by_crd": SECFirmIAPDAgent().search_firm_by_crd,
        "get_firm_details": SECFirmIAPDAgent().get_firm_details
    }
}

T = TypeVar('T')

class ResponseStatus(Enum):
    """Standard response status codes following HTTP conventions."""
    SUCCESS = "success"  # 200 equivalent
    NOT_FOUND = "not_found"  # 404 equivalent
    ERROR = "error"  # 500 equivalent

@dataclass
class ResponseModel(Generic[T]):
    """Standard response model following REST conventions.
    
    Args:
        status: The status of the response (success, not_found, error)
        data: The actual data payload (if any)
        message: str: Human readable message about the response
        metadata: Optional metadata about the response (e.g. cache info)
    """
    status: ResponseStatus
    data: Optional[T]
    message: str
    metadata: Optional[Dict[str, Any]] = None

    def with_data(self, new_data: T) -> 'ResponseModel[T]':
        """Create a new response with updated data."""
        return ResponseModel(
            status=self.status,
            data=new_data,
            message=self.message,
            metadata=self.metadata
        )

    def to_search_response(self) -> 'FirmSearchResponse':
        """Convert this response to a search response type."""
        # Cast the data to the expected type for FirmSearchResponse
        search_data: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None
        if isinstance(self.data, dict):
            search_data = self.data
        elif isinstance(self.data, list):
            search_data = self.data
            
        return FirmSearchResponse(
            status=self.status,
            data=search_data,
            message=self.message,
            metadata=self.metadata
        )

# Type aliases for common response types
FirmResponse = ResponseModel[Dict[str, Any]]
FirmListResponse = ResponseModel[List[Dict[str, Any]]]
FirmSearchResponse = ResponseModel[Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]]

# Pure functions
def get_current_date() -> str:
    return datetime.now().strftime(DATE_FORMAT)

def get_manifest_timestamp() -> str:
    return datetime.now().strftime(MANIFEST_DATE_FORMAT)

def is_cache_valid(cached_date: str) -> bool:
    try:
        cached_datetime = datetime.strptime(cached_date, DATE_FORMAT)
        return (datetime.now() - cached_datetime) <= timedelta(days=CACHE_TTL_DAYS)
    except ValueError:
        logger.warning(f"Invalid date format in cache manifest: {cached_date}")
        return False

def build_cache_path(subject_id: str, firm_id: str, agent_name: str, service: str) -> Path:
    """
    Build the cache path for a given request.
    
    Args:
        subject_id: The ID of the subject/client making the request
        firm_id: The ID of the firm being queried
        agent_name: The name of the agent service
        service: The service being called
        
    Returns:
        Path object representing the cache location
    
    The cache is organized in the following hierarchy:
    cache/
    └── subject_id/
        └── agent_name/
            └── service/
                └── firm_id/
                    └── data files
    """
    return CACHE_FOLDER / subject_id / agent_name / service / firm_id

def build_file_name(agent_name: str, firm_id: str, service: str, date: str, ordinal: Optional[int] = None) -> str:
    base = f"{agent_name}_{firm_id}_{service}_{date}"
    return f"{base}_{ordinal}.json" if ordinal is not None else f"{base}.json"

def read_manifest(cache_path: Path) -> Optional[str]:
    manifest_path = cache_path / "manifest.txt"
    if manifest_path.exists():
        with manifest_path.open("r") as f:
            line = f.readline().strip()
            if line and "Cached on: " in line:
                try:
                    return line.split("Cached on: ")[1].split(" ")[0].replace("-", "")
                except IndexError:
                    logger.warning(f"Malformed manifest file at {manifest_path}: {line}")
                    return None
    return None

def write_manifest(cache_path: Path, timestamp: str) -> None:
    cache_path.mkdir(parents=True, exist_ok=True)
    manifest_path = cache_path / "manifest.txt"
    with manifest_path.open("w") as f:
        f.write(f"Cached on: {timestamp}")

def load_cached_data(cache_path: Path, is_multiple: bool = False) -> Union[Optional[Dict], List[Dict]]:
    if not cache_path.exists():
        logger.debug(f"Cache directory not found: {cache_path}")
        return None if not is_multiple else []
    try:
        if is_multiple:
            results = []
            json_files = sorted(cache_path.glob("*.json"))
            if not json_files:
                logger.debug(f"No JSON files in cache directory: {cache_path}")
                return []
            for file_path in json_files:
                with file_path.open("r") as f:
                    content = f.read().strip()
                    if not content:
                        logger.warning(f"Empty cache file: {file_path}")
                        continue
                    results.append(json.loads(content))
            return results if results else []
        else:
            json_files = list(cache_path.glob("*.json"))
            if not json_files:
                logger.debug(f"No JSON files in cache directory: {cache_path}")
                return None
            with json_files[0].open("r") as f:
                content = f.read().strip()
                if not content:
                    logger.warning(f"Empty cache file: {json_files[0]}")
                    return None
                return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON in cache file at {cache_path}: {e}")
        return None if not is_multiple else []
    except Exception as e:
        logger.error(f"Error reading cache file at {cache_path}: {e}")
        return None if not is_multiple else []

def save_cached_data(cache_path: Path, file_name: str, data: Dict) -> None:
    cache_path.mkdir(parents=True, exist_ok=True)
    file_path = cache_path / file_name
    with file_path.open("w") as f:
        json.dump(data, f, indent=2)

def save_multiple_results(cache_path: Path, agent_name: str, firm_id: str, service: str, date: str, results: List[Dict]) -> None:
    if not results:
        file_name = build_file_name(agent_name, firm_id, service, date, 1)
        save_cached_data(cache_path, file_name, {
            "result": "No Results Found",
            "status": "not_found",
            "message": "No results found for the search criteria",
            "timestamp": get_manifest_timestamp()
        })
    else:
        for i, result in enumerate(results, 1):
            file_name = build_file_name(agent_name, firm_id, service, date, i)
            save_cached_data(cache_path, file_name, result)

def log_request(subject_id: str, firm_id: str, agent_name: str, service: str, status: str, duration: Optional[float] = None) -> None:
    """Log a request to the request log file.
    
    Args:
        subject_id: The ID of the subject/client making the request
        firm_id: The ID of the firm being queried
        agent_name: The name of the agent service
        service: The service being called
        status: The status of the request (e.g. "Cached", "Fetched")
        duration: Optional duration of the request in seconds
    """
    # Place request logs at the agent level for better auditability
    log_path = CACHE_FOLDER / subject_id / agent_name / REQUEST_LOG_FILE
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {service}/{firm_id} - {status}"
    if duration is not None:
        log_entry += f" (fetch duration: {duration:.2f}s)"
    log_entry += "\n"
    with log_path.open("a") as f:
        f.write(log_entry)

def fetch_agent_data(agent_name: str, service: str, params: Dict[str, Any]) -> tuple[FirmListResponse, Optional[float]]:
    try:
        agent_fn = AGENT_SERVICES[agent_name][service]
        start_time = time.time()
        
        result = agent_fn(**params)
        duration = time.time() - start_time
        
        if isinstance(result, list):
            if result:
                logger.debug(f"Fetched {agent_name}/{service}: result size = {len(result)}")
                return ResponseModel(
                    status=ResponseStatus.SUCCESS,
                    data=result,
                    message=f"Successfully fetched {len(result)} results",
                ), duration
            else:
                logger.debug(f"Fetched {agent_name}/{service}: no results")
                return ResponseModel(
                    status=ResponseStatus.NOT_FOUND,
                    data=[],
                    message=f"No results found for {service}",
                ), duration
        elif result and isinstance(result, dict):
            logger.debug(f"Fetched {agent_name}/{service}: single result")
            return ResponseModel(
                status=ResponseStatus.SUCCESS,
                data=[result],
                message="Successfully fetched single result",
            ), duration
        else:
            logger.debug(f"Fetched {agent_name}/{service}: no results")
            return ResponseModel(
                status=ResponseStatus.NOT_FOUND,
                data=[],
                message=f"No results found for {service}",
            ), duration
            
    except Exception as e:
        logger.error(f"Agent {agent_name} service {service} failed: {str(e)}")
        return ResponseModel(
            status=ResponseStatus.ERROR,
            data=[],
            message=f"Error fetching data: {str(e)}",
        ), None

def check_cache_or_fetch(
    subject_id: str,
    agent_name: str, 
    service: str, 
    firm_id: str, 
    params: Dict[str, Any]
) -> FirmSearchResponse:
    if not firm_id or firm_id.strip() == "":
        logger.error(f"Invalid firm_id: '{firm_id}' for agent {agent_name}/{service}")
        return ResponseModel(
            status=ResponseStatus.ERROR,
            data=None,
            message=f"firm_id must be a non-empty string, got '{firm_id}'",
        )
    
    if not subject_id or subject_id.strip() == "":
        logger.error(f"Invalid subject_id: '{subject_id}' for agent {agent_name}/{service}")
        return ResponseModel(
            status=ResponseStatus.ERROR,
            data=None,
            message=f"subject_id must be a non-empty string, got '{subject_id}'",
        )
    
    cache_path = build_cache_path(subject_id, firm_id, agent_name, service)
    date = get_current_date()
    cache_path.mkdir(parents=True, exist_ok=True)

    cached_date = read_manifest(cache_path)
    is_multiple = service == "search_firm"
    
    if cached_date and is_cache_valid(cached_date):
        cached_data = load_cached_data(cache_path, is_multiple)
        if cached_data is not None:
            logger.info(f"Cache hit for {agent_name}/{service}/{firm_id}")
            log_request(subject_id, firm_id, agent_name, service, "Cached")
            
            # Handle empty results from cache
            if is_multiple and not cached_data:
                return ResponseModel(
                    status=ResponseStatus.NOT_FOUND,
                    data=None,
                    message=f"No results found for {service}",
                    metadata={"cache": "hit", "cached_date": cached_date}
                )
            
            # Check if this is a cached "not found" result for multiple results
            if is_multiple and len(cached_data) == 1 and isinstance(cached_data[0], dict) and cached_data[0].get("result") == "Not Found":
                return ResponseModel(
                    status=ResponseStatus.NOT_FOUND,
                    data=None,
                    message=cached_data[0].get("message", f"No results found for {service}"),
                    metadata={"cache": "hit", "cached_date": cached_date, "original_status": cached_data[0].get("status")}
                )
            
            # Check if this is a cached "not found" result
            if not is_multiple and isinstance(cached_data, dict) and cached_data.get("result") == "Not Found":
                return ResponseModel(
                    status=ResponseStatus.NOT_FOUND,
                    data=None,
                    message=cached_data.get("message", f"No results found for {service}"),
                    metadata={"cache": "hit", "cached_date": cached_date, "original_status": cached_data.get("status")}
                )
            
            return ResponseModel(
                status=ResponseStatus.SUCCESS,
                data=cached_data,
                message=f"Successfully retrieved {'results' if is_multiple else 'result'} from cache",
                metadata={"cache": "hit", "cached_date": cached_date}
            )

    logger.info(f"Cache miss or stale for {agent_name}/{service}/{firm_id}")
    response, fetch_duration = fetch_agent_data(agent_name, service, params)
    log_request(subject_id, firm_id, agent_name, service, "Fetched", fetch_duration)
    
    # Cache both successful and not found responses for audit purposes
    if response.status in [ResponseStatus.SUCCESS, ResponseStatus.NOT_FOUND]:
        file_name = build_file_name(agent_name, firm_id, service, date)
        if response.status == ResponseStatus.NOT_FOUND:
            # Cache not found results with a special indicator
            save_cached_data(cache_path, file_name, {
                "result": "Not Found",
                "status": response.status.value,
                "message": response.message,
                "timestamp": get_manifest_timestamp()
            })
        elif not is_multiple and response.data:
            save_cached_data(cache_path, file_name, response.data[0])
        else:
            save_multiple_results(cache_path, agent_name, firm_id, service, date, response.data or [])
        write_manifest(cache_path, get_manifest_timestamp())
    
    # Add cache metadata
    response.metadata = {
        "cache": "miss",
        "fetch_duration": fetch_duration
    }
    
    # Convert list response to single item if needed
    if not is_multiple and response.status == ResponseStatus.SUCCESS and response.data:
        return ResponseModel(
            status=response.status,
            data=response.data[0],
            message=response.message,
            metadata=response.metadata
        )
    
    return response.to_search_response()

# Higher-order function to create service-specific fetchers
def create_fetcher(agent_name: str, service: str) -> Callable[[str, str, Dict[str, Any]], FirmSearchResponse]:
    return lambda subject_id, firm_id, params: check_cache_or_fetch(subject_id, agent_name, service, firm_id, params)

# Fetcher functions for all agent services
fetch_finra_firm_search = create_fetcher("FINRA_FirmBrokerCheck_Agent", "search_firm")
fetch_finra_firm_by_crd = create_fetcher("FINRA_FirmBrokerCheck_Agent", "search_firm_by_crd")
fetch_finra_firm_details = create_fetcher("FINRA_FirmBrokerCheck_Agent", "get_firm_details")
fetch_sec_firm_search = create_fetcher("SEC_FirmIAPD_Agent", "search_firm")
fetch_sec_firm_by_crd = create_fetcher("SEC_FirmIAPD_Agent", "search_firm_by_crd")
fetch_sec_firm_details = create_fetcher("SEC_FirmIAPD_Agent", "get_firm_details")

def main():
    """Example usage of the firm marshaller."""
    # Example firm search
    firm_name = "Goldman Sachs"
    firm_id = "FIRM001"
    subject_id = "TEST_USER"  # Using a proper subject ID
    
    print(f"\nSearching for firm: {firm_name}")
    finra_response = fetch_finra_firm_search(subject_id, firm_id, {"firm_name": firm_name})
    print("\nFINRA Search Response:")
    print(f"Status: {finra_response.status.value}")
    print(f"Message: {finra_response.message}")
    if finra_response.metadata:
        print(f"Metadata: {json.dumps(finra_response.metadata, indent=2)}")
    print(f"Data: {json.dumps(finra_response.data, indent=2) if finra_response.data else 'None'}")
    
    sec_response = fetch_sec_firm_search(subject_id, firm_id, {"firm_name": firm_name})
    print("\nSEC Search Response:")
    print(f"Status: {sec_response.status.value}")
    print(f"Message: {sec_response.message}")
    if sec_response.metadata:
        print(f"Metadata: {json.dumps(sec_response.metadata, indent=2)}")
    print(f"Data: {json.dumps(sec_response.data, indent=2) if sec_response.data else 'None'}")
    
    # Example firm details lookup
    if (finra_response.status == ResponseStatus.SUCCESS and 
        isinstance(finra_response.data, list) and 
        finra_response.data):
        
        crd_number = finra_response.data[0].get("crd_number")
        if crd_number:
            print(f"\nGetting details for CRD: {crd_number}")
            finra_details = fetch_finra_firm_details(subject_id, firm_id, {"crd_number": crd_number})
            print("\nFINRA Firm Details Response:")
            print(f"Status: {finra_details.status.value}")
            print(f"Message: {finra_details.message}")
            if finra_details.metadata:
                print(f"Metadata: {json.dumps(finra_details.metadata, indent=2)}")
            print(f"Data: {json.dumps(finra_details.data, indent=2) if finra_details.data else 'None'}")

class FirmMarshaller:
    """Service for normalizing firm data from different sources into a consistent format."""
    
    def normalize_finra_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a FINRA search result into the standard format.
        
        Args:
            result: Raw FINRA search result
            
        Returns:
            Normalized firm data
        """
        return {
            'firm_name': result.get('org_name'),
            'crd_number': result.get('org_source_id'),
            'source': 'FINRA',
            'raw_data': result
        }
        
    def normalize_sec_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize an SEC search result into the standard format.
        
        Args:
            result: Raw SEC search result
            
        Returns:
            Normalized firm data with additional SEC-specific fields
        """
        return {
            'firm_name': result.get('org_name'),
            'crd_number': result.get('org_crd'),
            'sec_number': result.get('firm_ia_full_sec_number'),
            'source': 'SEC',
            'other_names': result.get('firm_other_names', []),
            'registration_scope': result.get('firm_ia_scope'),
            'has_disclosures': result.get('firm_ia_disclosure_fl') == 'Y',
            'branch_count': result.get('firm_branches_count'),
            'raw_data': result
        }
        
    def normalize_finra_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize FINRA firm details into the standard format.
        
        Args:
            details: Raw FINRA firm details
            
        Returns:
            Normalized firm details
        """
        logger.debug(f"Normalizing FINRA details: {type(details)}")
        
        if not details:
            logger.warning("Empty details provided to normalize_finra_details")
            return {}
            
        # Extract content based on response format
        try:
            # Check if the response has a content field that needs to be parsed
            content = details.get('content', details)
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                    logger.debug("Successfully parsed content JSON string")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse content JSON: {e}")
                    content = details
            
            # Extract basic information
            basic_info = {}
            if 'basicInformation' in content and isinstance(content['basicInformation'], dict):
                basic_info = content['basicInformation']
            
            # Get firm name and CRD number
            firm_name = basic_info.get('firmName') or details.get('org_name')
            firm_id = basic_info.get('firmId') or details.get('org_source_id')
            crd_number = str(firm_id) if firm_id is not None else None
            
            return {
                'firm_name': firm_name,
                'crd_number': crd_number,
                'source': 'FINRA',
                'registration_status': details.get('registration_status') or basic_info.get('iaScope'),
                'addresses': details.get('addresses', []),
                'disclosures': details.get('disclosures', []),
                'raw_data': content
            }
        except Exception as e:
            logger.error(f"Error normalizing FINRA details: {e}")
            return {
                'firm_name': details.get('org_name'),
                'crd_number': details.get('org_source_id'),
                'source': 'FINRA',
                'registration_status': details.get('registration_status'),
                'addresses': details.get('addresses', []),
                'disclosures': details.get('disclosures', []),
                'raw_data': details
            }
        
    def normalize_sec_details(self, details: dict) -> dict:
        """
        Normalize SEC firm details response into a standard format.
        
        This method handles various response formats from the SEC API and extracts
        firm details into a consistent structure. It's designed to be robust against
        different response structures and missing fields.
        
        Args:
            details (dict): Raw SEC firm details response
            
        Returns:
            dict: Normalized firm details with fields:
                - firm_name (str): Name of the firm
                - crd_number (str): CRD number
                - sec_number (str): SEC number in format "{type}-{number}"
                - registration_status (str): Registration status
                - address (dict): Office address details
                - notice_filings (list): State notice filings
                - registration_date (str): Initial registration date
                - other_names (list): Alternative firm names
                - is_sec_registered (bool): Whether firm is SEC registered
                - is_state_registered (bool): Whether firm is state registered
                - is_era_registered (bool): Whether firm is ERA registered
                - adv_filing_date (str): Latest ADV filing date
                - has_adv_pdf (bool): Whether firm has ADV PDF
                - accountant_exams (list): Surprise accountant examinations
                - brochures (list): ADV brochure details
        """
        logger.debug(f"Normalizing SEC details: {type(details)}")
        
        if not details:
            logger.warning("Empty details provided to normalize_sec_details")
            return {}
            
        # Extract content based on response format
        content = {}
        try:
            # Format 1: Elasticsearch-like response with hits
            if 'hits' in details:
                hits = details.get('hits', {}).get('hits', [])
                if hits and len(hits) > 0:
                    source = hits[0].get('_source', {})
                    iacontent = source.get('iacontent', {})
                    
                    # Handle iacontent as string (needs parsing) or dict
                    if isinstance(iacontent, str):
                        try:
                            content = json.loads(iacontent)
                            logger.debug("Successfully parsed iacontent JSON string")
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse iacontent JSON: {e}")
                            return {}
                    else:
                        content = iacontent
            
            # Format 2: Direct content in response
            elif 'basicInformation' in details:
                content = details
                
            # Format 3: Content in 'data' field
            elif 'data' in details and isinstance(details['data'], dict):
                content = details['data']
                
            # Format 4: Results array with first item
            elif 'results' in details and isinstance(details['results'], list) and details['results']:
                content = details['results'][0]
                
            else:
                logger.warning(f"Unrecognized SEC details format: {list(details.keys())}")
                return {}
                
        except Exception as e:
            logger.error(f"Error extracting content from SEC details: {e}")
            return {}
            
        # Now extract fields from the content
        try:
            # Get nested objects with safe fallbacks
            basic_info = content.get('basicInformation', {})
            if not isinstance(basic_info, dict):
                basic_info = {}
                
            address_details = content.get('iaFirmAddressDetails', {})
            if not isinstance(address_details, dict):
                address_details = {}
                
            address_info = address_details.get('officeAddress', {})
            if not isinstance(address_info, dict):
                address_info = {}
                
            reg_statuses = content.get('registrationStatus', [])
            reg_status = reg_statuses[0] if isinstance(reg_statuses, list) and reg_statuses else {}
            if not isinstance(reg_status, dict):
                reg_status = {}
                
            org_status = content.get('orgScopeStatusFlags', {})
            if not isinstance(org_status, dict):
                org_status = {}
            
            # Extract firm ID and convert to string if present
            firm_id = basic_info.get('firmId')
            crd_number = str(firm_id) if firm_id is not None else None
            
            # Build normalized response
            # Handle SEC number - use IA SEC number if available, otherwise use BD SEC number
            ia_sec_number = basic_info.get('iaSECNumber')
            ia_sec_number_type = basic_info.get('iaSECNumberType')
            bd_sec_number = basic_info.get('bdSECNumber')
            
            # Determine the SEC number to use
            if ia_sec_number and ia_sec_number_type:
                sec_number = f"{ia_sec_number_type}-{ia_sec_number}"
            elif bd_sec_number:
                sec_number = f"8-{bd_sec_number}"  # BD SEC numbers use "8-" prefix
            else:
                sec_number = "-"  # Default if no SEC number is available
                
            return {
                'firm_name': basic_info.get('firmName'),
                'crd_number': crd_number,
                'sec_number': sec_number,
                'registration_status': reg_status.get('status'),
                'address': {
                    'street': f"{address_info.get('street1', '')} {address_info.get('street2', '')}".strip(),
                    'city': address_info.get('city'),
                    'state': address_info.get('state'),
                    'zip': address_info.get('postalCode'),
                    'country': address_info.get('country')
                },
                'notice_filings': [
                    {
                        'jurisdiction': filing.get('jurisdiction'),
                        'status': filing.get('status'),
                        'effective_date': filing.get('effectiveDate')
                    }
                    for filing in content.get('noticeFilings', [])
                    if isinstance(filing, dict)
                ],
                'registration_date': reg_status.get('effectiveDate'),
                'other_names': basic_info.get('otherNames', []),
                'is_sec_registered': org_status.get('isSECRegistered') == 'Y',
                'is_state_registered': org_status.get('isStateRegistered') == 'Y',
                'is_era_registered': org_status.get('isERARegistered') == 'Y',
                'is_sec_era_registered': org_status.get('isSECERARegistered') == 'Y',
                'is_state_era_registered': org_status.get('isStateERARegistered') == 'Y',
                'adv_filing_date': basic_info.get('advFilingDate'),
                'has_adv_pdf': basic_info.get('hasPdf') == 'Y',
                'accountant_exams': [
                    {
                        'firm_name': exam.get('accountantFirmName'),
                        'filing_date': exam.get('filingDate'),
                        'status': exam.get('fileStatus')
                    }
                    for exam in content.get('accountantSurpriseExams', [])
                    if isinstance(exam, dict)
                ],
                'brochures': [
                    {
                        'name': brochure.get('brochureName'),
                        'version_id': brochure.get('brochureVersionID'),
                        'date_submitted': brochure.get('dateSubmitted'),
                        'last_confirmed': brochure.get('lastConfirmed')
                    }
                    for brochure in content.get('brochures', {}).get('brochuredetails', [])
                    if isinstance(brochure, dict)
                ]
            }
        except Exception as e:
            logger.error(f"Error normalizing SEC details: {e}")
            return {}

if __name__ == "__main__":
    main()