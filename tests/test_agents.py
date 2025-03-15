"""
test_agents.py

Unit tests for the AgentName class in agents.py.
Tests enum functionality, string values, and usage patterns.
"""

import unittest
from cache_manager.agents import AgentName

class TestAgentName(unittest.TestCase):
    """Test cases for the AgentName enum class."""

    def test_agent_name_values(self):
        """Test that all agent names have the expected string values."""
        self.assertEqual(AgentName.SEC_SEARCH.value, "SEC_Search_Agent")
        self.assertEqual(AgentName.FINRA_SEARCH.value, "FINRA_Search_Agent")
        self.assertEqual(AgentName.STATE_SEARCH.value, "State_Search_Agent")
        self.assertEqual(AgentName.LEGAL_SEARCH.value, "Legal_Search_Agent")
        self.assertEqual(AgentName.FIRM_COMPLIANCE_REPORT.value, "FirmComplianceReport")

    def test_agent_name_membership(self):
        """Test membership checking using 'in' operator."""
        # Test valid agent names
        self.assertIn(AgentName.SEC_SEARCH, AgentName)
        self.assertIn(AgentName.FINRA_SEARCH, AgentName)
        self.assertIn(AgentName.STATE_SEARCH, AgentName)
        self.assertIn(AgentName.LEGAL_SEARCH, AgentName)
        self.assertIn(AgentName.FIRM_COMPLIANCE_REPORT, AgentName)

        # Test that non-enum values are not members
        self.assertNotIn("InvalidAgent", {a.name for a in AgentName})
        self.assertNotIn("SEC_Search_Agent", {a.name for a in AgentName})

    def test_agent_name_comparison(self):
        """Test string comparison behavior."""
        # Direct enum comparison
        self.assertEqual(AgentName.SEC_SEARCH, AgentName.SEC_SEARCH)
        self.assertNotEqual(AgentName.SEC_SEARCH, AgentName.FINRA_SEARCH)

        # String value comparison
        self.assertEqual(AgentName.SEC_SEARCH.value, "SEC_Search_Agent")
        self.assertTrue(AgentName.SEC_SEARCH == "SEC_Search_Agent")
        self.assertFalse(AgentName.SEC_SEARCH == "FINRA_Search_Agent")

    def test_agent_name_iteration(self):
        """Test iteration over all agent names."""
        expected_agents = {
            "SEC_Search_Agent",
            "FINRA_Search_Agent",
            "State_Search_Agent",
            "Legal_Search_Agent",
            "FirmComplianceReport"
        }
        actual_agents = {agent.value for agent in AgentName}
        self.assertEqual(expected_agents, actual_agents)

    def test_agent_name_string_operations(self):
        """Test string operations on agent names."""
        # Test string concatenation
        self.assertEqual("prefix_" + AgentName.SEC_SEARCH.value, "prefix_SEC_Search_Agent")
        self.assertEqual(AgentName.SEC_SEARCH.value + "_suffix", "SEC_Search_Agent_suffix")

        # Test string methods
        self.assertTrue(AgentName.SEC_SEARCH.value.endswith("Agent"))
        self.assertTrue(AgentName.FIRM_COMPLIANCE_REPORT.value.startswith("Firm"))
        self.assertEqual(AgentName.STATE_SEARCH.value.lower(), "state_search_agent")

    def test_agent_name_type_checking(self):
        """Test type checking and conversion behavior."""
        # Test type checking
        self.assertIsInstance(AgentName.SEC_SEARCH, AgentName)
        self.assertIsInstance(AgentName.SEC_SEARCH.value, str)

        # Test string conversion
        self.assertEqual(str(AgentName.SEC_SEARCH.value), "SEC_Search_Agent")
        self.assertEqual(repr(AgentName.SEC_SEARCH), "<AgentName.SEC_SEARCH: 'SEC_Search_Agent'>")

if __name__ == '__main__':
    unittest.main() 