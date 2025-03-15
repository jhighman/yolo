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

# Services Module

This directory contains the core business logic and service layer components for processing and analyzing firm-related data.

## Recent Enhancements

### Firm Business Module (`firm_business.py`)

The firm business module has been enhanced with comprehensive search strategies and claim processing capabilities:

#### Search Strategy Implementation

- **Flexible Search Strategy Selection**: Implemented a dynamic search strategy determination system that selects the most appropriate search method based on available claim data.
- **Implemented Search Strategies**:
  - `TAX_ID_AND_CRD`: Uses both tax ID and CRD number for precise firm identification
  - `CRD_ONLY`: Searches using only the CRD number
  - `NAME_ONLY`: Performs a name-based search
  - `DEFAULT`: Fallback strategy when no other criteria are available

#### Claim Processing Pipeline

- **Enhanced Process Claim Function**:
  - Integrated search functionality with compliance evaluation
  - Added support for skip flags (`skip_financials`, `skip_legal`)
  - Improved error handling and logging
  - Implemented comprehensive report generation

#### Error Handling

- Robust error handling for:
  - Invalid data scenarios
  - Search failures
  - Evaluation process errors
  - Report generation issues
  - Save operation failures

#### Testing Coverage

The module now includes comprehensive unit tests covering:
- Search strategy determination
- Individual search implementations
- End-to-end claim processing
- Skip flag functionality
- Error scenarios
- Mock integrations with external services

### Firm Services Facade (`firm_services.py`)

The facade provides a unified interface for:
- Searching firms across multiple data sources
- Retrieving detailed firm information
- Saving business reports
- Normalizing data from different sources

## Usage Examples

### Basic Claim Processing
```python
from services.firm_business import process_claim
from services.firm_services import FirmServicesFacade

# Initialize facade
facade = FirmServicesFacade()

# Process a claim
claim = {
    "reference_id": "CLAIM123",
    "business_name": "Example Firm",
    "organization_crd": "123456"
}

# Standard processing
result = process_claim(claim, facade)

# Processing with skip flags
result = process_claim(
    claim,
    facade,
    skip_financials=True,
    skip_legal=True
)
```

### Search Strategy Usage
```python
from services.firm_business import determine_search_strategy

# Determine appropriate search strategy
claim = {
    "tax_id": "123456789",
    "organization_crd": "987654",
    "business_name": "Example Firm"
}
strategy = determine_search_strategy(claim)
```

## Configuration

The module uses the following configuration from the logging config:
- Debug logging enabled by default
- Structured logging with contextual information
- Timestamp and correlation ID tracking

## Dependencies

- Python 3.7+
- Internal dependencies:
  - `evaluation.firm_evaluation_processor`
  - `evaluation.firm_evaluation_report_builder`
  - `evaluation.firm_evaluation_report_director`
  - `utils.logging_config`

## Testing

Run the tests using:
```bash
python -m unittest tests/test_firm_business.py -v
```

The test suite includes:
- Unit tests for all search strategies
- Integration tests for claim processing
- Mock tests for external service interactions
- Error handling verification
- Skip flag functionality testing

## Error Handling

The module defines and handles the following error types:
- `InvalidDataError`: For invalid or missing required data
- `EvaluationProcessError`: For failures during evaluation process

## Logging

Comprehensive logging is implemented throughout the module:
- Strategy selection decisions
- Search execution and results
- Claim processing steps
- Error scenarios with stack traces
- Performance timing information

## Future Enhancements

Planned improvements include:
- Additional search strategies (SEC number, tax ID only)
- Enhanced caching mechanisms
- Batch processing capabilities
- Real-time status updates
- Extended skip conditions
- Performance optimizations 