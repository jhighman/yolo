"""
agents.py

This module provides the AgentName class that enumerates valid agent names for cache operations
in the business compliance domain. It ensures consistency and prevents typos by defining a
fixed set of agent identifiers used by firm_cache_manager.py to organize and manage cached
data from regulatory searches and compliance reports.
"""

from enum import Enum

class AgentName(str, Enum):
    """Enumerates valid agent names for cache operations related to business entity compliance.
    
    This class provides standardized identifiers for various regulatory data sources and
    compliance reports, ensuring uniform naming across cache operations.
    
    Attributes:
        SEC_SEARCH: Agent for SEC-related searches (e.g., SEC registration data)
        FINRA_SEARCH: Agent for FINRA-related searches (e.g., FINRA registration data)
        STATE_SEARCH: Agent for state-level regulatory searches (e.g., state registrations)
        LEGAL_SEARCH: Agent for legal action searches (e.g., lawsuits, liens)
        FIRM_COMPLIANCE_REPORT: Special handling for compliance reports generated for business entities
    """
    SEC_SEARCH = "SEC_Search_Agent"
    FINRA_SEARCH = "FINRA_Search_Agent"
    STATE_SEARCH = "State_Search_Agent"
    LEGAL_SEARCH = "Legal_Search_Agent"
    FIRM_COMPLIANCE_REPORT = "FirmComplianceReport" 