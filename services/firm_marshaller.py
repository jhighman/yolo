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
from typing import Dict, List, Optional, Any, Callable, Union
import time
from datetime import datetime, timedelta
from functools import wraps, partial

from agents.finra_firm_broker_check_agent import FinraFirmBrokerCheckAgent
from agents.sec_firm_iapd_agent import SECFirmIAPDAgent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("FirmMarshaller")

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
    """
    return CACHE_FOLDER / subject_id / firm_id / agent_name / service

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
        save_cached_data(cache_path, file_name, {"result": "No Results Found"})
    else:
        for i, result in enumerate(results, 1):
            file_name = build_file_name(agent_name, firm_id, service, date, i)
            save_cached_data(cache_path, file_name, result)

def log_request(firm_id: str, agent_name: str, service: str, status: str, duration: Optional[float] = None) -> None:
    log_path = CACHE_FOLDER / firm_id / REQUEST_LOG_FILE
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {agent_name}/{service} - {status}"
    if duration is not None:
        log_entry += f" (fetch duration: {duration:.2f}s)"
    log_entry += "\n"
    with log_path.open("a") as f:
        f.write(log_entry)

def fetch_agent_data(agent_name: str, service: str, params: Dict[str, Any]) -> tuple[List[Dict[str, Any]], Optional[float]]:
    try:
        agent_fn = AGENT_SERVICES[agent_name][service]
        start_time = time.time()
        
        result = agent_fn(**params)
        duration = time.time() - start_time
        
        if isinstance(result, list):
            logger.debug(f"Fetched {agent_name}/{service}: result size = {len(result)}")
            return result, duration
        elif result and isinstance(result, dict):
            logger.debug(f"Fetched {agent_name}/{service}: single result")
            return [result], duration
        else:
            logger.debug(f"Fetched {agent_name}/{service}: no results")
            return [], duration
            
    except Exception as e:
        logger.error(f"Agent {agent_name} service {service} failed: {str(e)}")
        return [], None

def check_cache_or_fetch(
    subject_id: str,
    agent_name: str, 
    service: str, 
    firm_id: str, 
    params: Dict[str, Any]
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    if not firm_id or firm_id.strip() == "":
        logger.error(f"Invalid firm_id: '{firm_id}' for agent {agent_name}/{service}")
        raise ValueError(f"firm_id must be a non-empty string, got '{firm_id}'")
    
    if not subject_id or subject_id.strip() == "":
        logger.error(f"Invalid subject_id: '{subject_id}' for agent {agent_name}/{service}")
        raise ValueError(f"subject_id must be a non-empty string, got '{subject_id}'")
    
    cache_path = build_cache_path(subject_id, firm_id, agent_name, service)
    date = get_current_date()
    cache_path.mkdir(parents=True, exist_ok=True)

    cached_date = read_manifest(cache_path)
    is_multiple = service == "search_firm"
    
    if cached_date and is_cache_valid(cached_date):
        cached_data = load_cached_data(cache_path, is_multiple)
        if cached_data is not None:
            logger.info(f"Cache hit for {agent_name}/{service}/{firm_id}")
            log_request(firm_id, agent_name, service, "Cached")
            return cached_data

    logger.info(f"Cache miss or stale for {agent_name}/{service}/{firm_id}")
    results, fetch_duration = fetch_agent_data(agent_name, service, params)
    log_request(firm_id, agent_name, service, "Fetched", fetch_duration)
    
    file_name = build_file_name(agent_name, firm_id, service, date)
    if not is_multiple and results:
        save_cached_data(cache_path, file_name, results[0])
    else:
        save_multiple_results(cache_path, agent_name, firm_id, service, date, results)
    write_manifest(cache_path, get_manifest_timestamp())
    
    return results[0] if len(results) == 1 and not is_multiple else results

# Higher-order function to create service-specific fetchers
def create_fetcher(agent_name: str, service: str) -> Callable[[str, str, Dict[str, Any]], Union[Optional[Dict], List[Dict]]]:
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
    
    print(f"\nSearching for firm: {firm_name}")
    finra_results = fetch_finra_firm_search("Goldman Sachs", firm_id, {"firm_name": firm_name})
    print("\nFINRA Search Results:", json.dumps(finra_results, indent=2))
    
    sec_results = fetch_sec_firm_search("Goldman Sachs", firm_id, {"firm_name": firm_name})
    print("\nSEC Search Results:", json.dumps(sec_results, indent=2))
    
    # Example firm details lookup
    if finra_results and isinstance(finra_results, list):
        crd_number = finra_results[0].get("crd_number")
        if crd_number:
            print(f"\nGetting details for CRD: {crd_number}")
            finra_details = fetch_finra_firm_details("Goldman Sachs", firm_id, {"crd_number": crd_number})
            print("\nFINRA Firm Details:", json.dumps(finra_details, indent=2))

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
            Normalized firm data
        """
        return {
            'firm_name': result.get('firm_name'),
            'crd_number': result.get('crd_number'),
            'sec_number': result.get('sec_number'),
            'source': 'SEC',
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
        return {
            'firm_name': details.get('org_name'),
            'crd_number': details.get('org_source_id'),
            'source': 'FINRA',
            'registration_status': details.get('registration_status'),
            'addresses': details.get('addresses', []),
            'disclosures': details.get('disclosures', []),
            'raw_data': details
        }
        
    def normalize_sec_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize SEC firm details into the standard format.
        
        Args:
            details: Raw SEC firm details
            
        Returns:
            Normalized firm details
        """
        return {
            'firm_name': details.get('firm_name'),
            'crd_number': details.get('crd_number'),
            'sec_number': details.get('sec_number'),
            'source': 'SEC',
            'registration_status': details.get('registration_status'),
            'addresses': details.get('addresses', []),
            'disclosures': details.get('disclosures', []),
            'raw_data': details
        }

if __name__ == "__main__":
    main()