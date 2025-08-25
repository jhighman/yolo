#!/usr/bin/env python3
"""
Test script to verify the connection resilience improvements.

This script tests the SEC and FINRA agents' ability to handle connection reset errors
by making multiple API calls in sequence and reporting success rates.
"""

import sys
import time
import logging
import argparse
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent))

from agents.sec_firm_iapd_agent import SECFirmIAPDAgent
from agents.finra_firm_broker_check_agent import FinraFirmBrokerCheckAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_sec_agent(crd_numbers, iterations=3, delay=1.0):
    """Test the SEC agent with multiple CRD numbers."""
    logger.info(f"Testing SEC agent with {len(crd_numbers)} CRD numbers, {iterations} iterations each")
    
    agent = SECFirmIAPDAgent(use_mock=False)
    results = {
        "total_calls": 0,
        "successful_calls": 0,
        "failed_calls": 0,
        "connection_resets": 0,
        "other_errors": 0
    }
    
    for iteration in range(iterations):
        logger.info(f"Starting iteration {iteration+1}/{iterations}")
        
        for crd in crd_numbers:
            results["total_calls"] += 1
            try:
                logger.info(f"Searching for CRD: {crd}")
                result = agent.search_firm_by_crd(crd)
                
                if result:
                    logger.info(f"Successfully found CRD {crd}: {result.get('firm_name', 'Unknown')}")
                    results["successful_calls"] += 1
                else:
                    logger.warning(f"No results found for CRD {crd}")
                    results["failed_calls"] += 1
                    
            except ConnectionResetError:
                logger.error(f"Connection reset error for CRD {crd}")
                results["connection_resets"] += 1
                results["failed_calls"] += 1
                
            except Exception as e:
                logger.error(f"Error searching for CRD {crd}: {str(e)}")
                results["other_errors"] += 1
                results["failed_calls"] += 1
                
            # Add delay between calls
            time.sleep(delay)
    
    # Calculate success rate
    success_rate = (results["successful_calls"] / results["total_calls"]) * 100 if results["total_calls"] > 0 else 0
    
    logger.info(f"SEC Agent Test Results:")
    logger.info(f"Total calls: {results['total_calls']}")
    logger.info(f"Successful calls: {results['successful_calls']}")
    logger.info(f"Failed calls: {results['failed_calls']}")
    logger.info(f"Connection resets: {results['connection_resets']}")
    logger.info(f"Other errors: {results['other_errors']}")
    logger.info(f"Success rate: {success_rate:.2f}%")
    
    return results

def test_finra_agent(crd_numbers, iterations=3, delay=1.0):
    """Test the FINRA agent with multiple CRD numbers."""
    logger.info(f"Testing FINRA agent with {len(crd_numbers)} CRD numbers, {iterations} iterations each")
    
    agent = FinraFirmBrokerCheckAgent(use_mock=False)
    results = {
        "total_calls": 0,
        "successful_calls": 0,
        "failed_calls": 0,
        "connection_resets": 0,
        "other_errors": 0
    }
    
    for iteration in range(iterations):
        logger.info(f"Starting iteration {iteration+1}/{iterations}")
        
        for crd in crd_numbers:
            results["total_calls"] += 1
            try:
                logger.info(f"Searching for CRD: {crd}")
                result = agent.search_firm_by_crd(crd)
                
                if result:
                    logger.info(f"Successfully found CRD {crd}")
                    results["successful_calls"] += 1
                else:
                    logger.warning(f"No results found for CRD {crd}")
                    results["failed_calls"] += 1
                    
            except ConnectionResetError:
                logger.error(f"Connection reset error for CRD {crd}")
                results["connection_resets"] += 1
                results["failed_calls"] += 1
                
            except Exception as e:
                logger.error(f"Error searching for CRD {crd}: {str(e)}")
                results["other_errors"] += 1
                results["failed_calls"] += 1
                
            # Add delay between calls
            time.sleep(delay)
    
    # Calculate success rate
    success_rate = (results["successful_calls"] / results["total_calls"]) * 100 if results["total_calls"] > 0 else 0
    
    logger.info(f"FINRA Agent Test Results:")
    logger.info(f"Total calls: {results['total_calls']}")
    logger.info(f"Successful calls: {results['successful_calls']}")
    logger.info(f"Failed calls: {results['failed_calls']}")
    logger.info(f"Connection resets: {results['connection_resets']}")
    logger.info(f"Other errors: {results['other_errors']}")
    logger.info(f"Success rate: {success_rate:.2f}%")
    
    return results

def main():
    """Main entry point for the test script."""
    parser = argparse.ArgumentParser(description="Test connection resilience for SEC and FINRA agents")
    
    parser.add_argument(
        "--sec-only",
        action="store_true",
        help="Test only the SEC agent"
    )
    
    parser.add_argument(
        "--finra-only",
        action="store_true",
        help="Test only the FINRA agent"
    )
    
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Number of iterations for each CRD number (default: 3)"
    )
    
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between API calls in seconds (default: 1.0)"
    )
    
    args = parser.parse_args()
    
    # Sample CRD numbers to test with
    crd_numbers = ["2841", "8361", "131940", "107488", "300903"]
    
    if not args.sec_only and not args.finra_only:
        # Test both agents
        sec_results = test_sec_agent(crd_numbers, args.iterations, args.delay)
        finra_results = test_finra_agent(crd_numbers, args.iterations, args.delay)
        
        # Compare results
        sec_success_rate = (sec_results["successful_calls"] / sec_results["total_calls"]) * 100 if sec_results["total_calls"] > 0 else 0
        finra_success_rate = (finra_results["successful_calls"] / finra_results["total_calls"]) * 100 if finra_results["total_calls"] > 0 else 0
        
        logger.info("\nComparison of Results:")
        logger.info(f"SEC Agent Success Rate: {sec_success_rate:.2f}%")
        logger.info(f"FINRA Agent Success Rate: {finra_success_rate:.2f}%")
        
    elif args.sec_only:
        # Test only SEC agent
        test_sec_agent(crd_numbers, args.iterations, args.delay)
        
    elif args.finra_only:
        # Test only FINRA agent
        test_finra_agent(crd_numbers, args.iterations, args.delay)

def test_specific_cases():
    """Test specific CRD numbers that have been problematic."""
    logger.info("Testing specific problematic CRD numbers")
    
    # Problematic CRD numbers
    crd_numbers = ["17409", "110966", "317700"]
    
    # Test SEC agent
    logger.info("Testing SEC agent with problematic CRD numbers")
    sec_agent = SECFirmIAPDAgent(use_mock=False)
    
    for crd in crd_numbers:
        try:
            logger.info(f"Searching for CRD: {crd}")
            result = sec_agent.search_firm_by_crd(crd)
            
            if result:
                logger.info(f"Successfully found CRD {crd}: {result.get('firm_name', 'Unknown')}")
            else:
                logger.warning(f"No results found for CRD {crd}")
                
        except Exception as e:
            logger.error(f"Error searching for CRD {crd}: {str(e)}")
            
        # Add delay between calls
        time.sleep(2.0)
    
    # Test FINRA agent
    logger.info("\nTesting FINRA agent with problematic CRD numbers")
    finra_agent = FinraFirmBrokerCheckAgent(use_mock=False)
    
    for crd in crd_numbers:
        try:
            logger.info(f"Searching for CRD: {crd}")
            result = finra_agent.search_firm_by_crd(crd)
            
            if result:
                logger.info(f"Successfully found CRD {crd}")
            else:
                logger.warning(f"No results found for CRD {crd}")
                
        except Exception as e:
            logger.error(f"Error searching for CRD {crd}: {str(e)}")
            
        # Add delay between calls
        time.sleep(2.0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test connection resilience for SEC and FINRA agents")
    
    parser.add_argument(
        "--specific-cases",
        action="store_true",
        help="Test only the specific problematic CRD numbers"
    )
    
    args, unknown = parser.parse_known_args()
    
    if args.specific_cases:
        test_specific_cases()
    else:
        main()