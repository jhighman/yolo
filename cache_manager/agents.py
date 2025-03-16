"""
agents.py

This module defines standardized agent names for cache operations in the business
compliance domain.
"""

from enum import Enum

class AgentName(Enum):
    """Standardized agent names for cache operations."""
    
    FIRM_COMPLIANCE_REPORT = "FirmComplianceReport"
    SEC_SEARCH_AGENT = "SEC_Search_Agent"
    FINRA_SEARCH_AGENT = "FINRA_Search_Agent"
    SEC_DETAILS_AGENT = "SEC_Details_Agent"
    FINRA_DETAILS_AGENT = "FINRA_Details_Agent"
    LEGAL_SEARCH_AGENT = "Legal_Search_Agent"
    REGULATORY_AGENT = "Regulatory_Agent" 