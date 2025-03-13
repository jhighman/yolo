# Agents Module

This module contains various agent implementations that are designed to search and extract information from different URL-based resources.

## Available Agents

### FinraFirmBrokerCheckAgent

An agent for searching and extracting information from FINRA's BrokerCheck system (https://brokercheck.finra.org/).

#### Features:
- Search for firms by name
- Retrieve detailed firm information
- Save search results to JSON files

#### Usage Example:
```python
from agents import FinraFirmBrokerCheckAgent

# Initialize the agent
agent = FinraFirmBrokerCheckAgent()

# Search for a firm
results = agent.search_firm("Example Firm Name")

# Get detailed information for a specific firm
firm_details = agent.get_firm_details(results[0]['firm_url'])

# Save the results
agent.save_results(firm_details, 'output/')
```

## Adding New Agents

When adding new agents to this module:

1. Create a new Python file for your agent
2. Implement the agent class with appropriate methods
3. Update `__init__.py` to expose the new agent
4. Add documentation to this README.md
5. Include appropriate error handling and logging
6. Add any required dependencies to requirements.txt
