import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import unittest
from unittest.mock import patch, MagicMock
from services.firm_business import process_claim
from services.firm_name_matcher import FirmNameMatcher

class TestFirmNameMatching(unittest.TestCase):
    """Test case for firm name matching with CRD."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_facade = MagicMock()
        
        # Mock the search_firm_by_crd method to return a successful result
        self.mock_facade.search_firm_by_crd.return_value = {
            "firm_name": "Silver Oak Securities, Incorporated",
            "crd_number": "46947",
            "source": "FINRA"
        }
        
        # Mock the get_firm_details method to return a successful result
        self.mock_facade.get_firm_details.return_value = {
            "firm_name": "Silver Oak Securities, Incorporated",
            "crd_number": "46947",
            "source": "FINRA",
            "registration_status": "Approved",
            "addresses": [],
            "disclosures": []
        }
        
        # Mock the save_compliance_report method to return True
        self.mock_facade.save_compliance_report.return_value = True

    def test_crd_match_with_incorrect_name(self):
        """Test that a claim with correct CRD but incorrect name succeeds."""
        # Create a claim with correct CRD but incorrect name
        claim = {
            "reference_id": "test-ref-001",
            "business_ref": "BIZ_001",
            "organization_crd": "46947",
            "business_name": "Sliver Oak Securities Inc",  # Note the typo: "Sliver" instead of "Silver"
            "entityName": "Sliver Oak Securities Inc"
        }
        
        # Process the claim
        report = process_claim(claim, self.mock_facade)
        
        # Verify that the claim was processed successfully
        self.assertTrue(report is not None)
        self.assertTrue(self.mock_facade.search_firm_by_crd.called)
        self.assertTrue(self.mock_facade.get_firm_details.called)
        self.assertTrue(self.mock_facade.save_compliance_report.called)
        
        # Verify that the CRD was used for the search, along with the name
        self.mock_facade.search_firm_by_crd.assert_called_with("BIZ_001", "46947", "Sliver Oak Securities Inc")

    def test_name_matcher_integration(self):
        """Test that the FirmNameMatcher is used when needed."""
        # Create a name matcher instance
        matcher = FirmNameMatcher()
        
        # Test with similar names
        correct_name = "Silver Oak Securities, Incorporated"
        incorrect_name = "Sliver Oak Securities Inc"
        
        # The similarity should be high enough to match
        similarity = matcher._calculate_similarity(
            matcher._normalize_name(correct_name),
            matcher._normalize_name(incorrect_name)
        )
        
        # Print the similarity for debugging
        print(f"Similarity between '{correct_name}' and '{incorrect_name}': {similarity}")
        
        # The similarity should be above the default threshold (0.75)
        self.assertGreaterEqual(similarity, 0.75)

if __name__ == "__main__":
    unittest.main()