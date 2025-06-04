"""
Exceptions for the agents module.

This module contains custom exceptions used by the various agents.
"""

class AgentError(Exception):
    """Base exception for all agent errors."""
    pass

class RateLimitExceeded(AgentError):
    """Exception raised when an API rate limit is exceeded."""
    pass

class APIError(AgentError):
    """Exception raised when an API returns an error."""
    pass

class RequestError(AgentError):
    """Exception raised when there is an error making a request to an API."""
    pass

class ParseError(AgentError):
    """Exception raised when there is an error parsing API response data."""
    pass