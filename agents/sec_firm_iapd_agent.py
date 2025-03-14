"""Mock SEC IAPD API agent for testing and development.

This module provides a mock implementation of the SEC IAPD API agent
for testing and development purposes.
"""

import logging
from typing import Dict, List, Optional

from .mock_data import (
    get_mock_sec_search_results,
    get_mock_sec_firm_details,
    get_mock_sec_firm_by_crd
)

logger = logging.getLogger(__name__)

class SECAPIError(Exception):
    """Base exception for SEC API errors."""
    pass

class SECResponseError(SECAPIError):
    """Exception raised when SEC API returns an error response."""
    pass

class SECRequestError(SECAPIError):
    """Exception raised when there is an error making a request to SEC API."""
    pass

class SECFirmIAPDAgent:
    """Mock SEC IAPD API agent for testing and development.

    This agent provides public access to professional information about investment adviser firms
    through a mock implementation of the SEC IAPD API.
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialize the SEC IAPD API agent.

        Args:
            config: Optional configuration dictionary.
        """
        self.config = config or {}
        logger.info("Initialized SEC IAPD API agent with config: %s", self.config)

    def search_firm(self, firm_name: str) -> List[Dict]:
        """Search for firms by name.

        Args:
            firm_name: Name of the firm to search for.

        Returns:
            List of dictionaries containing firm information.

        Raises:
            SECAPIError: If there is an error with the SEC API.
        """
        try:
            logger.info("Searching for firm: %s", firm_name)
            results = get_mock_sec_search_results(firm_name)
            logger.info("Found %d results for firm: %s", len(results), firm_name)
            return results
        except Exception as e:
            logger.error("Error searching for firm: %s", e)
            raise SECAPIError(f"Error searching for firm: {e}")

    def get_firm_details(self, crd_number: str) -> Dict:
        """Get detailed information about a firm by CRD number.

        Args:
            crd_number: CRD number of the firm.

        Returns:
            Dictionary containing firm details.

        Raises:
            SECAPIError: If there is an error with the SEC API.
        """
        try:
            logger.info("Getting firm details for CRD: %s", crd_number)
            details = get_mock_sec_firm_details(crd_number)
            if not details:
                logger.warning("No details found for CRD: %s", crd_number)
            return details
        except Exception as e:
            logger.error("Error getting firm details: %s", e)
            raise SECAPIError(f"Error getting firm details: {e}")

    def search_firm_by_crd(self, crd_number: str) -> Dict:
        """Search for a firm by CRD number.

        Args:
            crd_number: CRD number of the firm.

        Returns:
            Dictionary containing firm information.

        Raises:
            SECAPIError: If there is an error with the SEC API.
        """
        try:
            logger.info("Searching for firm by CRD: %s", crd_number)
            result = get_mock_sec_firm_by_crd(crd_number)
            if not result:
                logger.warning("No firm found for CRD: %s", crd_number)
            return result
        except Exception as e:
            logger.error("Error searching for firm by CRD: %s", e)
            raise SECAPIError(f"Error searching for firm by CRD: {e}") 