# Services Package

This package provides a layered architecture for accessing and processing firm data from various financial regulatory services (FINRA BrokerCheck and SEC IAPD).

## Architecture Overview

The services package follows a layered architecture pattern:

```
┌─────────────────┐
│  Firm Services  │  High-level facade for accessing firm data
├─────────────────┤
│  Marshaller     │  Handles data fetching, caching, and normalization
├─────────────────┤
│    Agents       │  Direct interaction with external APIs
└─────────────────┘
```

### Components

#### 1. Firm Services (`firm_services.py`)

The `FirmServicesFacade` provides a high-level interface for accessing firm data. It:
- Consolidates access to multiple data sources (FINRA, SEC)
- Handles error cases and logging
- Returns normalized data in a consistent format
- Delegates actual data fetching to the marshaller

Example usage:
```python
from services.firm_services import FirmServicesFacade

facade = FirmServicesFacade()

# Search for firms by name
results = facade.search_firm("Fidelity")

# Get detailed firm information
details = facade.get_firm_details("7784")

# Search by CRD number
firm = facade.search_firm_by_crd("7784")
```

#### 2. Marshaller (`firm_marshaller.py`)

The `FirmMarshaller` handles the complexity of:
- Fetching data from agents
- Caching responses
- Rate limiting requests
- Normalizing data formats

It provides fetcher functions that abstract away these details:
```python
from services.firm_marshaller import fetch_finra_firm_search

# The marshaller handles caching and rate limiting
results = fetch_finra_firm_search("FIRM001", {"firm_name": "Fidelity"})
```

Data normalization ensures consistent field names:
- FINRA: `org_name` → `firm_name`, `org_source_id` → `crd_number`
- SEC: Already uses `firm_name` and `crd_number`

#### 3. Agents (in `agents/` package)

Agents handle direct interaction with external APIs:
- `FinraFirmBrokerCheckAgent`: FINRA BrokerCheck API
- `SecFirmIapdAgent`: SEC IAPD API

The agents are not used directly by client code - they are always accessed through the marshaller.

## Data Flow

1. Client code calls `FirmServicesFacade` methods
2. Facade uses marshaller's fetcher functions
3. Marshaller checks cache, handles rate limiting
4. If cache miss, marshaller calls appropriate agent
5. Agent makes API request and returns raw data
6. Marshaller caches response and normalizes data
7. Facade returns normalized data to client

## Error Handling

- Facade methods catch and log all exceptions
- Failed FINRA requests fall back to SEC where appropriate
- Cache errors are logged but don't prevent live API calls
- Type checking ensures data consistency

## Caching

The marshaller implements caching with:
- File-based cache in `cache/` directory
- TTL of 90 days for cached data
- Cache key based on firm ID and service
- Cache manifest tracks timestamps
- Request logging for debugging

## Future Extensions

The architecture supports future additions like:
- Additional data sources/agents
- Enhanced data normalization
- Business logic layer
- Name matching services
- Result merging/deduplication

## Development Guidelines

When extending the services:
1. Add new agents to handle API interactions
2. Update marshaller to support new data sources
3. Add normalization logic for new data formats
4. Extend facade interface as needed
5. Maintain backward compatibility 