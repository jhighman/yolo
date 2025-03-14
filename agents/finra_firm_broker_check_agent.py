"""Mock FINRA BrokerCheck API agent for testing and development.

This module provides a mock implementation of the FINRA BrokerCheck API agent
for testing and development purposes.
"""

import logging
from typing import Dict, List, Optional

from .mock_data import (
    get_mock_finra_search_results,
    get_mock_finra_firm_details,
    get_mock_finra_firm_by_crd
)

logger = logging.getLogger(__name__)

class FinraAPIError(Exception):
    """Base exception for FINRA API errors."""
    pass

class FinraResponseError(FinraAPIError):
    """Exception raised when FINRA API returns an error response."""
    pass

class FinraRequestError(FinraAPIError):
    """Exception raised when there is an error making a request to FINRA API."""
    pass

class FinraFirmBrokerCheckAgent:
    """Mock FINRA BrokerCheck API agent for testing and development.

    This agent provides public access to professional information about registered firms
    through a mock implementation of the FINRA BrokerCheck API.
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialize the FINRA BrokerCheck API agent.

        Args:
            config: Optional configuration dictionary.
        """
        self.config = config or {}
        logger.info("Initialized FINRA BrokerCheck API agent with config: %s", self.config)

    def search_firm(self, firm_name: str) -> List[Dict]:
        """Search for firms by name.

        Args:
            firm_name: Name of the firm to search for.

        Returns:
            List of dictionaries containing firm information.

        Raises:
            FinraAPIError: If there is an error with the FINRA API.
        """
        try:
            logger.info("Searching for firm: %s", firm_name)
            results = get_mock_finra_search_results(firm_name)
            logger.info("Found %d results for firm: %s", len(results), firm_name)
            return results
        except Exception as e:
            logger.error("Error searching for firm: %s", e)
            raise FinraAPIError(f"Error searching for firm: {e}")

    def get_firm_details(self, crd_number: str) -> Dict:
        """Get detailed information about a firm by CRD number.

        Args:
            crd_number: CRD number of the firm.

        Returns:
            Dictionary containing firm details.

        Raises:
            FinraAPIError: If there is an error with the FINRA API.
        """
        try:
            logger.info("Getting firm details for CRD: %s", crd_number)
            details = get_mock_finra_firm_details(crd_number)
            if not details:
                logger.warning("No details found for CRD: %s", crd_number)
            return details
        except Exception as e:
            logger.error("Error getting firm details: %s", e)
            raise FinraAPIError(f"Error getting firm details: {e}")

    def search_firm_by_crd(self, crd_number: str) -> Dict:
        """Search for a firm by CRD number.

        Args:
            crd_number: CRD number of the firm.

        Returns:
            Dictionary containing firm information.

        Raises:
            FinraAPIError: If there is an error with the FINRA API.
        """
        try:
            logger.info("Searching for firm by CRD: %s", crd_number)
            result = get_mock_finra_firm_by_crd(crd_number)
            if not result:
                logger.warning("No firm found for CRD: %s", crd_number)
            return result
        except Exception as e:
            logger.error("Error searching for firm by CRD: %s", e)
            raise FinraAPIError(f"Error searching for firm by CRD: {e}")