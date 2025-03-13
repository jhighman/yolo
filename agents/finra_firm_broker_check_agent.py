"""FINRA Firm Broker Check Agent.

This module implements an agent for searching and extracting information
from FINRA's BrokerCheck system (https://brokercheck.finra.org/).
"""

import logging
from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup
from datetime import datetime

class FinraFirmBrokerCheckAgent:
    """Agent for interacting with FINRA's BrokerCheck system.

    This agent is responsible for searching and extracting information about
    firms and brokers from FINRA's BrokerCheck website.
    """

    BASE_URL = "https://brokercheck.finra.org"
    SEARCH_URL = f"{BASE_URL}/search/firms"

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the FINRA BrokerCheck agent.

        Args:
            logger: Optional logger instance. If not provided, a default logger
                   will be created.
        """
        self.logger = logger or logging.getLogger(__name__)
        self.session = requests.Session()
        # Set up common headers to mimic browser behavior
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5'
        })

    def search_firm(self, firm_name: str) -> List[Dict]:
        """Search for a firm in FINRA's BrokerCheck system.

        Args:
            firm_name: The name of the firm to search for.

        Returns:
            A list of dictionaries containing information about matching firms.
            Each dictionary contains basic information such as:
            - firm_name: The name of the firm
            - crd_number: The firm's CRD number
            - firm_url: URL to the firm's detailed page

        Raises:
            requests.RequestException: If there's an error with the HTTP request.
        """
        try:
            # Construct search parameters
            params = {
                'q': firm_name,
                'type': 'firm'
            }

            # Make the search request
            response = self.session.get(self.SEARCH_URL, params=params)
            response.raise_for_status()

            # Parse the response
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []

            # Extract firm information from the search results
            # Note: This is a placeholder implementation. The actual parsing logic
            # would need to be updated based on the actual HTML structure of the site
            for firm in soup.find_all('div', class_='firm-result'):
                firm_info = {
                    'firm_name': firm.find('h3', class_='firm-name').text.strip(),
                    'crd_number': firm.find('span', class_='crd-number').text.strip(),
                    'firm_url': self.BASE_URL + firm.find('a')['href']
                }
                results.append(firm_info)

            self.logger.info(f"Found {len(results)} results for firm: {firm_name}")
            return results

        except requests.RequestException as e:
            self.logger.error(f"Error searching for firm {firm_name}: {str(e)}")
            raise

    def get_firm_details(self, firm_url: str) -> Dict:
        """Get detailed information about a specific firm.

        Args:
            firm_url: The URL to the firm's detailed page.

        Returns:
            A dictionary containing detailed information about the firm.

        Raises:
            requests.RequestException: If there's an error with the HTTP request.
        """
        try:
            response = self.session.get(firm_url)
            response.raise_for_status()

            # Parse the response
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract detailed firm information
            # Note: This is a placeholder implementation. The actual parsing logic
            # would need to be updated based on the actual HTML structure of the site
            details = {
                'name': '',
                'crd_number': '',
                'sec_number': '',
                'main_office_location': '',
                'website': '',
                'firm_type': '',
                'registration_status': '',
                'registration_date': '',
                'disclosures': []
            }

            self.logger.info(f"Successfully retrieved details for firm at {firm_url}")
            return details

        except requests.RequestException as e:
            self.logger.error(f"Error getting firm details from {firm_url}: {str(e)}")
            raise

    def save_results(self, results: Dict, output_path: str) -> None:
        """Save the search results to a file.

        Args:
            results: Dictionary containing the search results.
            output_path: Path where to save the results.
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{output_path}/finra_results_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2)
                
            self.logger.info(f"Results saved to {filename}")
            
        except Exception as e:
            self.logger.error(f"Error saving results to {output_path}: {str(e)}")
            raise