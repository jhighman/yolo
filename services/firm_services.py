"""
services.py

This module provides the FirmServicesFacade class, which consolidates access to
external financial regulatory services (FINRA BrokerCheck and SEC IAPD firm data)
and provides a unified interface for business logic to retrieve and store normalized data.
"""

import json
import logging
from typing import Optional, Dict, Any, List, Union

from services.firm_marshaller import (
    FirmMarshaller,
    fetch_finra_firm_search,
    fetch_finra_firm_by_crd,
    fetch_finra_firm_details,
    fetch_sec_firm_search,
    fetch_sec_firm_by_crd,
    fetch_sec_firm_details
)

logger = logging.getLogger(__name__)

class FirmServicesFacade:
    """Facade for accessing firm-related financial regulatory services."""
    
    def __init__(self):
        """Initialize the facade with required services."""
        self.firm_marshaller = FirmMarshaller()
        logger.debug("FirmServicesFacade initialized")

    def search_firm(self, firm_name: str) -> List[Dict[str, Any]]:
        """
        Search for a firm across both FINRA and SEC databases.
        
        Args:
            firm_name: Name of the firm to search for
            
        Returns:
            List of matching firm records with normalized data
        """
        logger.info(f"Searching for firm: {firm_name}")
        results = []
        firm_id = f"search_{firm_name}"  # Create a unique ID for caching
        
        # Search FINRA
        try:
            finra_results = fetch_finra_firm_search(firm_id, {"firm_name": firm_name})
            if isinstance(finra_results, list):
                logger.debug(f"Found {len(finra_results)} FINRA results for {firm_name}")
                for result in finra_results:
                    if isinstance(result, dict):
                        normalized = self.firm_marshaller.normalize_finra_result(result)
                        results.append(normalized)
        except Exception as e:
            logger.error(f"Error searching FINRA for {firm_name}: {str(e)}")
            
        # Search SEC
        try:
            sec_results = fetch_sec_firm_search(firm_id, {"firm_name": firm_name})
            if isinstance(sec_results, list):
                logger.debug(f"Found {len(sec_results)} SEC results for {firm_name}")
                for result in sec_results:
                    if isinstance(result, dict):
                        normalized = self.firm_marshaller.normalize_sec_result(result)
                        results.append(normalized)
        except Exception as e:
            logger.error(f"Error searching SEC for {firm_name}: {str(e)}")
            
        return results

    def get_firm_details(self, crd_number: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed firm information from both FINRA and SEC using CRD number.
        
        Args:
            crd_number: The firm's CRD number
            
        Returns:
            Combined firm details or None if not found
        """
        logger.info(f"Getting firm details for CRD: {crd_number}")
        firm_id = f"details_{crd_number}"  # Create a unique ID for caching
        
        # Try FINRA first
        try:
            finra_details = fetch_finra_firm_details(firm_id, {"crd_number": crd_number})
            if isinstance(finra_details, dict):
                logger.debug(f"Found FINRA details for CRD {crd_number}")
                return self.firm_marshaller.normalize_finra_details(finra_details)
        except Exception as e:
            logger.error(f"Error getting FINRA details for CRD {crd_number}: {str(e)}")
            
        # If FINRA fails, try SEC
        try:
            sec_details = fetch_sec_firm_details(firm_id, {"crd_number": crd_number})
            if isinstance(sec_details, dict):
                logger.debug(f"Found SEC details for CRD {crd_number}")
                return self.firm_marshaller.normalize_sec_details(sec_details)
        except Exception as e:
            logger.error(f"Error getting SEC details for CRD {crd_number}: {str(e)}")
            
        return None

    def search_firm_by_crd(self, crd_number: str) -> Optional[Dict[str, Any]]:
        """
        Search for a firm by CRD number across both FINRA and SEC databases.
        
        Args:
            crd_number: The firm's CRD number
            
        Returns:
            Normalized firm record or None if not found
        """
        logger.info(f"Searching for firm by CRD: {crd_number}")
        firm_id = f"search_crd_{crd_number}"  # Create a unique ID for caching
        
        # Try FINRA first
        try:
            finra_result = fetch_finra_firm_by_crd(firm_id, {"crd_number": crd_number})
            if isinstance(finra_result, dict):
                logger.debug(f"Found FINRA result for CRD {crd_number}")
                return self.firm_marshaller.normalize_finra_result(finra_result)
        except Exception as e:
            logger.error(f"Error searching FINRA by CRD {crd_number}: {str(e)}")
            
        # If FINRA fails, try SEC
        try:
            sec_result = fetch_sec_firm_by_crd(firm_id, {"crd_number": crd_number})
            if isinstance(sec_result, dict):
                logger.debug(f"Found SEC result for CRD {crd_number}")
                return self.firm_marshaller.normalize_sec_result(sec_result)
        except Exception as e:
            logger.error(f"Error searching SEC by CRD {crd_number}: {str(e)}")
                
        return None

def main():
    """Example usage of the FirmServicesFacade."""
    facade = FirmServicesFacade()
    
    # Example searches
    firm_name = "Fidelity"
    print(f"\nSearching for firm: {firm_name}")
    results = facade.search_firm(firm_name)
    print(json.dumps(results, indent=2))
    
    crd_number = "7784"
    print(f"\nGetting details for CRD: {crd_number}")
    details = facade.get_firm_details(crd_number)
    print(json.dumps(details, indent=2))
    
    print(f"\nSearching for firm by CRD: {crd_number}")
    result = facade.search_firm_by_crd(crd_number)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()