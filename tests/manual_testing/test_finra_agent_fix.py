#!/usr/bin/env python3
"""
Test script for the modified FINRA BrokerCheck API agent.
This script demonstrates how to properly handle the "Search unavailable" response.
"""

import sys
import json
import logging
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from agents.finra_firm_broker_check_agent import FinraFirmBrokerCheckAgent, BROKERCHECK_CONFIG
from utils.logging_config import setup_logging

# Initialize logging
loggers = setup_logging(debug=True)
logger = loggers.get('test_finra_agent') or logging.getLogger('test_finra_agent')

class EnhancedFinraAgent(FinraFirmBrokerCheckAgent):
    """Enhanced FINRA agent that properly handles 'Search unavailable' responses."""
    
    def search_firm(self, firm_name: str) -> list:
        """
        Search for firms by name with proper handling of 'Search unavailable' responses.
        
        Args:
            firm_name: Name of the firm to search for.
            
        Returns:
            List of dictionaries containing firm information or an empty list if no results found.
        """
        try:
            logger.info("Searching for firm: %s", firm_name)
            
            if self.use_mock:
                results = super().search_firm(firm_name)
                return results
            
            url = BROKERCHECK_CONFIG["firm_search_url"]
            params = {**BROKERCHECK_CONFIG["default_params"], "query": firm_name}
            
            logger.debug("Fetching firm info from BrokerCheck API")
            
            response = self.session.get(url, params=params, timeout=(10, 30))
            if response.status_code == 200:
                data = response.json()
                
                # Log the raw response for debugging
                logger.debug("API response: %s", json.dumps(data))
                
                # Check for API error messages
                if "errorCode" in data and data["errorCode"] != 0:
                    error_msg = data.get("errorMessage", "Unknown API error")
                    
                    # Handle "Search unavailable" as a normal "no results" condition
                    if "Search unavailable" in error_msg:
                        logger.info("FINRA search unavailable for firm: %s - treating as no results", firm_name)
                        return []
                    
                    # Handle other errors as warnings
                    logger.warning("API returned error: %s", error_msg)
                    return []
                
                # Process results as normal
                results = []
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
            else:
                logger.error("Error searching for firm: %s, status code: %d", 
                            firm_name, response.status_code)
                return []
        
        except Exception as e:
            logger.error("Error during firm search: %s", e)
            return []

    def search_firm_by_crd(self, crd_number: str, employee_number=None) -> list:
        """
        Search for a firm by CRD number with proper handling of 'Search unavailable' responses.
        
        Args:
            crd_number: CRD number of the firm.
            employee_number: Optional identifier for logging.
            
        Returns:
            List of dictionaries containing firm information or an empty list if no results found.
        """
        log_context = {
            "firm_crd": crd_number,
            "employee_number": employee_number
        }
        
        try:
            logger.info("Searching for firm by CRD: %s", crd_number, extra=log_context)
            
            if self.use_mock:
                results = super().search_firm_by_crd(crd_number, employee_number)
                return results
            
            url = BROKERCHECK_CONFIG["firm_search_url"]
            params = {**BROKERCHECK_CONFIG["default_params"], "query": crd_number}
            
            logger.debug("Fetching firm info from BrokerCheck API", 
                        extra={**log_context, "url": url, "params": params})
            
            response = self.session.get(url, params=params, timeout=(10, 30))
            if response.status_code == 200:
                data = response.json()
                
                # Log the raw response for debugging
                logger.debug("API response: %s", json.dumps(data))
                
                # Check for API error messages
                if "errorCode" in data and data["errorCode"] != 0:
                    error_msg = data.get("errorMessage", "Unknown API error")
                    
                    # Handle "Search unavailable" as a normal "no results" condition
                    if "Search unavailable" in error_msg:
                        logger.info("FINRA search unavailable for CRD: %s - treating as no results", 
                                   crd_number, extra=log_context)
                        return []
                    
                    # Handle other errors as warnings
                    logger.warning("API returned error: %s", error_msg, extra=log_context)
                    return []
                
                # Process results as normal
                results = []
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
            else:
                logger.error("Error searching for firm by CRD: %s, status code: %d", 
                            crd_number, response.status_code, extra=log_context)
                return []
        
        except Exception as e:
            logger.error("Error during firm CRD search: %s", e, extra=log_context)
            return []

def test_search_firm(agent, firm_name):
    """Test searching for a firm by name."""
    print(f"\nTesting search_firm: {firm_name}")
    results = agent.search_firm(firm_name)
    print(f"Results from agent.search_firm:")
    print(json.dumps(results, indent=2))
    return results

def test_search_firm_by_crd(agent, crd_number):
    """Test searching for a firm by CRD number."""
    print(f"\nTesting search_firm_by_crd: {crd_number}")
    results = agent.search_firm_by_crd(crd_number)
    print(f"Results from agent.search_firm_by_crd:")
    print(json.dumps(results, indent=2))
    return results

def test_get_firm_details(agent, crd_number):
    """Test getting detailed information about a firm by CRD number."""
    print(f"\nTesting get_firm_details: {crd_number}")
    details = agent.get_firm_details(crd_number)
    print(f"Results from agent.get_firm_details:")
    print(json.dumps(details, indent=2))
    return details

def main():
    """Main entry point for the script."""
    # Test data
    firm_name = "Baker Avenue Asset Management"
    crd_number = "131940"  # Baker Avenue Asset Management
    
    # Test with enhanced agent
    print("\n=== TESTING WITH ENHANCED FINRA AGENT ===")
    enhanced_agent = EnhancedFinraAgent(use_mock=False)
    test_search_firm(enhanced_agent, firm_name)
    test_search_firm_by_crd(enhanced_agent, crd_number)
    test_get_firm_details(enhanced_agent, crd_number)
    
    # Test with standard agent for comparison
    print("\n=== TESTING WITH STANDARD FINRA AGENT ===")
    standard_agent = FinraFirmBrokerCheckAgent(use_mock=False)
    test_search_firm(standard_agent, firm_name)
    test_search_firm_by_crd(standard_agent, crd_number)
    test_get_firm_details(standard_agent, crd_number)

if __name__ == "__main__":
    main()