#!/usr/bin/env python3
"""
Updated diagnostic script to test connections to FINRA and SEC APIs.
This script uses the correct URL format based on the actual code implementation.
"""

import requests
import json
import time
import logging
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration for SEC IAPD API
IAPD_CONFIG = {
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

# Configuration for FINRA BrokerCheck API
BROKERCHECK_CONFIG = {
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

def test_sec_api_search(crd_number: str, use_session: bool = True, timeout: Optional[tuple] = (10, 30)):
    """Test connection to SEC IAPD API for searching by CRD."""
    logger.info(f"Testing SEC IAPD API Search with CRD: {crd_number}")
    
    url = IAPD_CONFIG["firm_search_url"]
    params = {**IAPD_CONFIG["default_params"], "query": crd_number}
    
    logger.debug(f"Request URL: {url}")
    logger.debug(f"Request params: {params}")
    
    try:
        if use_session:
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            response = session.get(url, params=params, timeout=timeout)
        else:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
        
        logger.info(f"SEC API Search Response status code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                logger.debug(f"Response headers: {dict(response.headers)}")
                logger.info(f"Response data: {json.dumps(data, indent=2)}")
                return True
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.debug(f"Response content: {response.text[:500]}...")
                return False
        else:
            logger.error(f"Error response: {response.text}")
            return False
    
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: {e}")
        return False
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout error: {e}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

def test_sec_api_details(crd_number: str, use_session: bool = True, timeout: Optional[tuple] = (10, 30)):
    """Test connection to SEC IAPD API for getting firm details."""
    logger.info(f"Testing SEC IAPD API Details with CRD: {crd_number}")
    
    url = f"{IAPD_CONFIG['firm_search_url']}/{crd_number}"
    params = IAPD_CONFIG["default_params"]
    
    logger.debug(f"Request URL: {url}")
    logger.debug(f"Request params: {params}")
    
    try:
        if use_session:
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            response = session.get(url, params=params, timeout=timeout)
        else:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
        
        logger.info(f"SEC API Details Response status code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                logger.debug(f"Response headers: {dict(response.headers)}")
                logger.info(f"Response data: {json.dumps(data, indent=2)}")
                return True
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.debug(f"Response content: {response.text[:500]}...")
                return False
        else:
            logger.error(f"Error response: {response.text}")
            return False
    
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: {e}")
        return False
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout error: {e}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

def test_finra_api_search(crd_number: str, use_session: bool = True, timeout: Optional[tuple] = (10, 30)):
    """Test connection to FINRA BrokerCheck API for searching by CRD."""
    logger.info(f"Testing FINRA BrokerCheck API Search with CRD: {crd_number}")
    
    url = BROKERCHECK_CONFIG["firm_search_url"]
    params = {**BROKERCHECK_CONFIG["default_params"], "query": crd_number}
    
    logger.debug(f"Request URL: {url}")
    logger.debug(f"Request params: {params}")
    
    try:
        if use_session:
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            response = session.get(url, params=params, timeout=timeout)
        else:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
        
        logger.info(f"FINRA API Search Response status code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                logger.debug(f"Response headers: {dict(response.headers)}")
                logger.info(f"Response data: {json.dumps(data, indent=2)}")
                return True
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.debug(f"Response content: {response.text[:500]}...")
                return False
        else:
            logger.error(f"Error response: {response.text}")
            return False
    
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: {e}")
        return False
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout error: {e}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

def test_finra_api_details(crd_number: str, use_session: bool = True, timeout: Optional[tuple] = (10, 30)):
    """Test connection to FINRA BrokerCheck API for getting firm details."""
    logger.info(f"Testing FINRA BrokerCheck API Details with CRD: {crd_number}")
    
    url = f"{BROKERCHECK_CONFIG['firm_search_url']}/{crd_number}"
    params = BROKERCHECK_CONFIG["default_params"]
    
    logger.debug(f"Request URL: {url}")
    logger.debug(f"Request params: {params}")
    
    try:
        if use_session:
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            response = session.get(url, params=params, timeout=timeout)
        else:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
        
        logger.info(f"FINRA API Details Response status code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                logger.debug(f"Response headers: {dict(response.headers)}")
                logger.info(f"Response data: {json.dumps(data, indent=2)}")
                return True
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.debug(f"Response content: {response.text[:500]}...")
                return False
        else:
            logger.error(f"Error response: {response.text}")
            return False
    
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: {e}")
        return False
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout error: {e}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

def test_with_different_configs(crd_number: str):
    """Test with different configurations to identify what works."""
    logger.info("=== Testing SEC API Search with different configurations ===")
    
    # Test with session and timeout (like the actual code)
    logger.info("1. Testing SEC API Search with session and timeout")
    sec_search_result1 = test_sec_api_search(crd_number, use_session=True, timeout=(10, 30))
    
    # Wait a bit between tests
    time.sleep(2)
    
    # Test without session but with timeout
    logger.info("2. Testing SEC API Search without session but with timeout")
    sec_search_result2 = test_sec_api_search(crd_number, use_session=False, timeout=(10, 30))
    
    # Wait a bit between tests
    time.sleep(2)
    
    logger.info("=== Testing SEC API Details with different configurations ===")
    
    # Test with session and timeout (like the actual code)
    logger.info("1. Testing SEC API Details with session and timeout")
    sec_details_result1 = test_sec_api_details(crd_number, use_session=True, timeout=(10, 30))
    
    # Wait a bit between tests
    time.sleep(2)
    
    # Test without session but with timeout
    logger.info("2. Testing SEC API Details without session but with timeout")
    sec_details_result2 = test_sec_api_details(crd_number, use_session=False, timeout=(10, 30))
    
    # Wait a bit between tests
    time.sleep(5)
    
    logger.info("=== Testing FINRA API Search with different configurations ===")
    
    # Test with session and timeout (like the actual code)
    logger.info("1. Testing FINRA API Search with session and timeout")
    finra_search_result1 = test_finra_api_search(crd_number, use_session=True, timeout=(10, 30))
    
    # Wait a bit between tests
    time.sleep(2)
    
    # Test without session but with timeout
    logger.info("2. Testing FINRA API Search without session but with timeout")
    finra_search_result2 = test_finra_api_search(crd_number, use_session=False, timeout=(10, 30))
    
    # Wait a bit between tests
    time.sleep(2)
    
    logger.info("=== Testing FINRA API Details with different configurations ===")
    
    # Test with session and timeout (like the actual code)
    logger.info("1. Testing FINRA API Details with session and timeout")
    finra_details_result1 = test_finra_api_details(crd_number, use_session=True, timeout=(10, 30))
    
    # Wait a bit between tests
    time.sleep(2)
    
    # Test without session but with timeout
    logger.info("2. Testing FINRA API Details without session but with timeout")
    finra_details_result2 = test_finra_api_details(crd_number, use_session=False, timeout=(10, 30))
    
    # Print summary
    logger.info("=== Summary ===")
    logger.info(f"SEC API Search with session and timeout: {'SUCCESS' if sec_search_result1 else 'FAILED'}")
    logger.info(f"SEC API Search without session but with timeout: {'SUCCESS' if sec_search_result2 else 'FAILED'}")
    logger.info(f"SEC API Details with session and timeout: {'SUCCESS' if sec_details_result1 else 'FAILED'}")
    logger.info(f"SEC API Details without session but with timeout: {'SUCCESS' if sec_details_result2 else 'FAILED'}")
    logger.info(f"FINRA API Search with session and timeout: {'SUCCESS' if finra_search_result1 else 'FAILED'}")
    logger.info(f"FINRA API Search without session but with timeout: {'SUCCESS' if finra_search_result2 else 'FAILED'}")
    logger.info(f"FINRA API Details with session and timeout: {'SUCCESS' if finra_details_result1 else 'FAILED'}")
    logger.info(f"FINRA API Details without session but with timeout: {'SUCCESS' if finra_details_result2 else 'FAILED'}")

def print_curl_commands(crd_number: str):
    """Print curl commands for testing the APIs."""
    # SEC API Search
    sec_search_params = "&".join([f"{k}={v}" for k, v in IAPD_CONFIG["default_params"].items()])
    sec_search_curl = f'curl -v -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36" "{IAPD_CONFIG["firm_search_url"]}?{sec_search_params}&query={crd_number}"'
    
    # SEC API Details
    sec_details_params = "&".join([f"{k}={v}" for k, v in IAPD_CONFIG["default_params"].items()])
    sec_details_curl = f'curl -v -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36" "{IAPD_CONFIG["firm_search_url"]}/{crd_number}?{sec_details_params}"'
    
    # FINRA API Search
    finra_search_params = "&".join([f"{k}={v}" for k, v in BROKERCHECK_CONFIG["default_params"].items()])
    finra_search_curl = f'curl -v -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36" "{BROKERCHECK_CONFIG["firm_search_url"]}?{finra_search_params}&query={crd_number}"'
    
    # FINRA API Details
    finra_details_params = "&".join([f"{k}={v}" for k, v in BROKERCHECK_CONFIG["default_params"].items()])
    finra_details_curl = f'curl -v -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36" "{BROKERCHECK_CONFIG["firm_search_url"]}/{crd_number}?{finra_details_params}"'
    
    print("\n=== Curl Commands for Testing ===")
    print("\nSEC API Search:")
    print(sec_search_curl)
    print("\nSEC API Details:")
    print(sec_details_curl)
    print("\nFINRA API Search:")
    print(finra_search_curl)
    print("\nFINRA API Details:")
    print(finra_details_curl)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test connections to FINRA and SEC APIs")
    parser.add_argument("--crd", default="284175", help="CRD number to use for testing")
    parser.add_argument("--sec-search", action="store_true", help="Test only SEC API search")
    parser.add_argument("--sec-details", action="store_true", help="Test only SEC API details")
    parser.add_argument("--finra-search", action="store_true", help="Test only FINRA API search")
    parser.add_argument("--finra-details", action="store_true", help="Test only FINRA API details")
    parser.add_argument("--test-all-configs", action="store_true", help="Test with different configurations")
    parser.add_argument("--print-curl", action="store_true", help="Print curl commands for testing")
    
    args = parser.parse_args()
    
    if args.print_curl:
        print_curl_commands(args.crd)
    elif args.test_all_configs:
        test_with_different_configs(args.crd)
    else:
        if args.sec_search or (not args.sec_details and not args.finra_search and not args.finra_details):
            test_sec_api_search(args.crd)
        
        if args.sec_details or (not args.sec_search and not args.finra_search and not args.finra_details):
            test_sec_api_details(args.crd)
        
        if args.finra_search or (not args.sec_search and not args.sec_details and not args.finra_details):
            test_finra_api_search(args.crd)
        
        if args.finra_details or (not args.sec_search and not args.sec_details and not args.finra_search):
            test_finra_api_details(args.crd)