"""Tests for firm business logic and search strategies."""

import unittest
from typing import Dict, Any
import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from services.firm_business import (
    SearchStrategy,
    SearchImplementationStatus,
    determine_search_strategy
)

class TestSearchStrategyDetermination(unittest.TestCase):
    """Test cases for search strategy determination."""

    def setUp(self):
        """Reset the implementation registry before each test."""
        SearchImplementationStatus._implemented_strategies.clear()
        # Re-register the strategies that are implemented in the actual code
        SearchImplementationStatus.register_implementation(SearchStrategy.TAX_ID_AND_CRD.value)
        SearchImplementationStatus.register_implementation(SearchStrategy.CRD_ONLY.value)
        SearchImplementationStatus.register_implementation(SearchStrategy.NAME_ONLY.value)
        SearchImplementationStatus.register_implementation(SearchStrategy.DEFAULT.value)

    def test_implemented_strategies(self):
        """Test that the correct strategies are marked as implemented."""
        implemented = SearchImplementationStatus.get_implemented_strategies()
        
        # Verify implemented strategies
        self.assertIn(SearchStrategy.TAX_ID_AND_CRD.value, implemented)
        self.assertIn(SearchStrategy.CRD_ONLY.value, implemented)
        self.assertIn(SearchStrategy.NAME_ONLY.value, implemented)
        self.assertIn(SearchStrategy.DEFAULT.value, implemented)
        
        # Verify non-implemented strategies
        self.assertNotIn(SearchStrategy.TAX_ID_ONLY.value, implemented)
        self.assertNotIn(SearchStrategy.SEC_NUMBER_ONLY.value, implemented)
        self.assertNotIn(SearchStrategy.NAME_AND_LOCATION.value, implemented)

    def test_tax_id_and_crd_strategy(self):
        """Test that TAX_ID_AND_CRD strategy is selected when both fields are present."""
        claim = {
            "tax_id": "123456789",
            "organization_crd": "987654",
            "business_name": "Test Firm"
        }
        strategy = determine_search_strategy(claim)
        self.assertEqual(strategy, SearchStrategy.TAX_ID_AND_CRD)

    def test_crd_only_strategy(self):
        """Test that CRD_ONLY strategy is selected when only CRD is present."""
        claim = {
            "organization_crd": "987654",
            "business_name": "Test Firm"
        }
        strategy = determine_search_strategy(claim)
        self.assertEqual(strategy, SearchStrategy.CRD_ONLY)

    def test_name_only_strategy(self):
        """Test that NAME_ONLY strategy is selected when only business name is present."""
        claim = {
            "business_name": "Test Firm"
        }
        strategy = determine_search_strategy(claim)
        self.assertEqual(strategy, SearchStrategy.NAME_ONLY)

    def test_default_strategy(self):
        """Test that DEFAULT strategy is selected when no usable fields are present."""
        claim = {}
        strategy = determine_search_strategy(claim)
        self.assertEqual(strategy, SearchStrategy.DEFAULT)

    def test_fallback_to_implemented_strategy(self):
        """Test fallback to implemented strategies when optimal is not implemented."""
        # Case 1: SEC number should fall back to name if available
        claim = {
            "sec_number": "123-45678",
            "business_name": "Test Firm"
        }
        strategy = determine_search_strategy(claim)
        self.assertEqual(strategy, SearchStrategy.NAME_ONLY)
        
        # Case 2: Name and location should fall back to name only
        claim = {
            "business_name": "Test Firm",
            "business_location": "New York"
        }
        strategy = determine_search_strategy(claim)
        self.assertEqual(strategy, SearchStrategy.NAME_ONLY)
        
        # Case 3: Tax ID only should fall back to name if available
        claim = {
            "tax_id": "123456789",
            "business_name": "Test Firm"
        }
        strategy = determine_search_strategy(claim)
        self.assertEqual(strategy, SearchStrategy.NAME_ONLY)

    def test_unimplemented_strategies_not_selected(self):
        """Test that unimplemented strategies are never selected."""
        # SEC number only
        claim = {"sec_number": "123-45678"}
        strategy = determine_search_strategy(claim)
        self.assertNotEqual(strategy, SearchStrategy.SEC_NUMBER_ONLY)
        self.assertEqual(strategy, SearchStrategy.DEFAULT)
        
        # Tax ID only
        claim = {"tax_id": "123456789"}
        strategy = determine_search_strategy(claim)
        self.assertNotEqual(strategy, SearchStrategy.TAX_ID_ONLY)
        self.assertEqual(strategy, SearchStrategy.DEFAULT)
        
        # Name and location
        claim = {
            "business_name": "Test Firm",
            "business_location": "New York"
        }
        strategy = determine_search_strategy(claim)
        self.assertNotEqual(strategy, SearchStrategy.NAME_AND_LOCATION)
        self.assertEqual(strategy, SearchStrategy.NAME_ONLY)

if __name__ == '__main__':
    unittest.main() 