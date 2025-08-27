#!/usr/bin/env python3
"""
Test script to verify the fix for SEC number extraction from search results.
This test confirms that the SEC number is correctly extracted from sec_search_result
when it's missing from basic_result (CN-2061).
"""

import sys
import json
from pathlib import Path
import logging
import unittest
from datetime import datetime

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent))

from evaluation.firm_evaluation_report_builder import FirmEvaluationReportBuilder

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestSECNumberExtraction(unittest.TestCase):
    """Test cases for SEC number extraction from search results."""

    def test_sec_number_from_basic_result(self):
        """Test that SEC number is correctly extracted from basic_result."""
        # Create a builder
        builder = FirmEvaluationReportBuilder("test-ref-001")
        
        # Create a search evaluation with SEC number in basic_result
        search_evaluation = {
            "source": "SEC",
            "compliance": True,
            "basic_result": {
                "firm_name": "Test Firm",
                "crd_number": "123456",
                "sec_number": "801-123456",
                "registration_status": "APPROVED"
            }
        }
        
        # Set the search evaluation
        builder.set_search_evaluation(search_evaluation)
        
        # Build the report
        report = builder.build()
        
        # Verify that the SEC number is correctly extracted
        self.assertEqual(report["entity"]["sec_number"], "801-123456")
        logger.info("SEC number correctly extracted from basic_result")

    def test_sec_number_from_full_sec_number(self):
        """Test that SEC number is correctly extracted from firm_ia_full_sec_number when missing from basic_result."""
        # Create a builder
        builder = FirmEvaluationReportBuilder("test-ref-002")
        
        # Create a search evaluation with SEC number missing from basic_result but present in sec_search_result
        search_evaluation = {
            "source": "SEC",
            "compliance": True,
            "basic_result": {
                "firm_name": "Test Firm",
                "crd_number": "123456",
                "sec_number": "",  # SEC number is missing
                "registration_status": "APPROVED"
            },
            "sec_search_result": {
                "org_name": "Test Firm",
                "org_crd": "123456",
                "firm_ia_full_sec_number": "802-654321",
                "registration_status": "APPROVED"
            }
        }
        
        # Set the search evaluation
        builder.set_search_evaluation(search_evaluation)
        
        # Build the report
        report = builder.build()
        
        # Verify that the SEC number is correctly extracted from sec_search_result
        self.assertEqual(report["entity"]["sec_number"], "802-654321")
        logger.info("SEC number correctly extracted from firm_ia_full_sec_number")

    def test_sec_number_constructed_from_sec_number(self):
        """Test that SEC number is correctly constructed from firm_ia_sec_number when full_sec_number is missing."""
        # Create a builder
        builder = FirmEvaluationReportBuilder("test-ref-003")
        
        # Create a search evaluation with SEC number missing from basic_result and full_sec_number
        # but present as firm_ia_sec_number
        search_evaluation = {
            "source": "SEC",
            "compliance": True,
            "basic_result": {
                "firm_name": "Test Firm",
                "crd_number": "123456",
                "sec_number": "",  # SEC number is missing
                "registration_status": "APPROVED"
            },
            "sec_search_result": {
                "org_name": "Test Firm",
                "org_crd": "123456",
                "firm_ia_sec_number": "987654",  # Only the number part
                "firm_ia_sec_number_type": "801",  # The prefix
                "registration_status": "APPROVED"
            }
        }
        
        # Set the search evaluation
        builder.set_search_evaluation(search_evaluation)
        
        # Build the report
        report = builder.build()
        
        # Verify that the SEC number is correctly constructed
        self.assertEqual(report["entity"]["sec_number"], "801-987654")
        logger.info("SEC number correctly constructed from firm_ia_sec_number and firm_ia_sec_number_type")

    def test_real_world_example(self):
        """Test with a real-world example from the issue report."""
        # Create a builder
        builder = FirmEvaluationReportBuilder("test-ref-004")
        
        # Create a search evaluation based on the real-world example
        search_evaluation = {
            "source": "SEC",
            "compliance": True,
            "basic_result": {
                "firm_name": "MONTROSE LANE, LP",
                "crd_number": "289504",
                "sec_number": "",  # SEC number is missing
                "registration_status": "",
                "firm_status": "inactive"
            },
            "sec_search_result": {
                "org_name": "MONTROSE LANE, LP",
                "org_crd": "289504",
                "firm_ia_sec_number": "115072",
                "firm_ia_full_sec_number": "802-115072",
                "firm_other_names": [
                    "COTTONWOOD VENTURE PARTNERS LLC",
                    "MONTROSE LANE, LP",
                    "COTTONWOOD VENTURE PARTNERS, LP",
                    "COTTONWOOD VENTURE PARTNERS, LLC"
                ],
                "registration_status": ""
            }
        }
        
        # Set the search evaluation
        builder.set_search_evaluation(search_evaluation)
        
        # Build the report
        report = builder.build()
        
        # Verify that the SEC number is correctly extracted
        self.assertEqual(report["entity"]["sec_number"], "802-115072")
        logger.info("SEC number correctly extracted in real-world example")

def main():
    """Run the tests."""
    unittest.main()

if __name__ == "__main__":
    main()