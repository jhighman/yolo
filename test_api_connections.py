#!/usr/bin/env python3
"""
Diagnostic script to test connections to FINRA and SEC APIs.
This script mimics the exact request configuration used in the actual code.
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

def test_sec_api(crd_number: str, use_session: bool = True, timeout: Optional[tuple] = (10, 30)):
    """Test connection to SEC IAPD API."""
    logger.info(f"Testing SEC IAPD API with CRD: {crd_number}")
    
    url = IAPD_CONFIG["firm_search_url"]
    params = {**IAPD_CONFIG["default_params"], "query": crd_number}
    
    logger.debug(f"Request URL: {url}")
    logger.debug(f"Request params: {params}")
    
    try:
        if use_session:
            session = requests.Session()
            response = session.get(url, params=params, timeout=timeout)
        else:
            response = requests.get(url, params=params, timeout=timeout)
        
        logger.info(f"SEC API Response status code: {response.status_code}")
        
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

def test_finra_api(crd_number: str, use_session: bool = True, timeout: Optional[tuple] = (10, 30)):
    """Test connection to FINRA BrokerCheck API."""
    logger.info(f"Testing FINRA BrokerCheck API with CRD: {crd_number}")
    
    url = BROKERCHECK_CONFIG["firm_search_url"]
    params = {**BROKERCHECK_CONFIG["default_params"], "query": crd_number}
    
    logger.debug(f"Request URL: {url}")
    logger.debug(f"Request params: {params}")
    
    try:
        if use_session:
            session = requests.Session()
            response = session.get(url, params=params, timeout=timeout)
        else:
            response = requests.get(url, params=params, timeout=timeout)
        
        logger.info(f"FINRA API Response status code: {response.status_code}")
        
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
    logger.info("=== Testing SEC API with different configurations ===")
    
    # Test with session and timeout (like the actual code)
    logger.info("1. Testing SEC API with session and timeout")
    sec_result1 = test_sec_api(crd_number, use_session=True, timeout=(10, 30))
    
    # Wait a bit between tests
    time.sleep(2)
    
    # Test without session but with timeout
    logger.info("2. Testing SEC API without session but with timeout")
    sec_result2 = test_sec_api(crd_number, use_session=False, timeout=(10, 30))
    
    # Wait a bit between tests
    time.sleep(2)
    
    # Test with session but without timeout
    logger.info("3. Testing SEC API with session but without timeout")
    sec_result3 = test_sec_api(crd_number, use_session=True, timeout=None)
    
    # Wait a bit between tests
    time.sleep(2)
    
    # Test without session and without timeout
    logger.info("4. Testing SEC API without session and without timeout")
    sec_result4 = test_sec_api(crd_number, use_session=False, timeout=None)
    
    # Wait a bit between tests
    time.sleep(5)
    
    logger.info("=== Testing FINRA API with different configurations ===")
    
    # Test with session and timeout (like the actual code)
    logger.info("1. Testing FINRA API with session and timeout")
    finra_result1 = test_finra_api(crd_number, use_session=True, timeout=(10, 30))
    
    # Wait a bit between tests
    time.sleep(2)
    
    # Test without session but with timeout
    logger.info("2. Testing FINRA API without session but with timeout")
    finra_result2 = test_finra_api(crd_number, use_session=False, timeout=(10, 30))
    
    # Wait a bit between tests
    time.sleep(2)
    
    # Test with session but without timeout
    logger.info("3. Testing FINRA API with session but without timeout")
    finra_result3 = test_finra_api(crd_number, use_session=True, timeout=None)
    
    # Wait a bit between tests
    time.sleep(2)
    
    # Test without session and without timeout
    logger.info("4. Testing FINRA API without session and without timeout")
    finra_result4 = test_finra_api(crd_number, use_session=False, timeout=None)
    
    # Print summary
    logger.info("=== Summary ===")
    logger.info(f"SEC API with session and timeout: {'SUCCESS' if sec_result1 else 'FAILED'}")
    logger.info(f"SEC API without session but with timeout: {'SUCCESS' if sec_result2 else 'FAILED'}")
    logger.info(f"SEC API with session but without timeout: {'SUCCESS' if sec_result3 else 'FAILED'}")
    logger.info(f"SEC API without session and without timeout: {'SUCCESS' if sec_result4 else 'FAILED'}")
    logger.info(f"FINRA API with session and timeout: {'SUCCESS' if finra_result1 else 'FAILED'}")
    logger.info(f"FINRA API without session but with timeout: {'SUCCESS' if finra_result2 else 'FAILED'}")
    logger.info(f"FINRA API with session but without timeout: {'SUCCESS' if finra_result3 else 'FAILED'}")
    logger.info(f"FINRA API without session and without timeout: {'SUCCESS' if finra_result4 else 'FAILED'}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test connections to FINRA and SEC APIs")
    parser.add_argument("--crd", default="284175", help="CRD number to use for testing")
    parser.add_argument("--sec-only", action="store_true", help="Test only SEC API")
    parser.add_argument("--finra-only", action="store_true", help="Test only FINRA API")
    parser.add_argument("--test-all-configs", action="store_true", help="Test with different configurations")
    
    args = parser.parse_args()
    
    if args.test_all_configs:
        test_with_different_configs(args.crd)
    else:
        if not args.finra_only:
            test_sec_api(args.crd)
        
        if not args.sec_only:
            test_finra_api(args.crd)