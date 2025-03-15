# Firm Services and Business Logic

This repository contains tools and services for handling firm-related financial regulatory data, including search strategies and logging infrastructure.

## Command Line Tools

### Firm Business CLI

The `firm_business.py` CLI provides an interactive interface for testing search strategy determination. It helps verify how the system selects appropriate search strategies based on available business data.

#### Usage

```bash
python3 services/firm_business.py --interactive [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}]
```

Options:
- `--interactive`: Run in interactive menu mode
- `--log-level`: Set logging level (default: INFO)

#### Interactive Menu Options

1. Test with tax_id and CRD
2. Test with CRD only
3. Test with SEC number
4. Test with business name and location
5. Test with business name only
6. Test with empty claim
7. Show implemented strategies
8. Exit

#### Search Strategy Implementation

The system implements a hierarchical search strategy:

Currently Implemented:
- ✓ TAX_ID_AND_CRD: Highest priority when both tax ID and CRD are available
- ✓ CRD_ONLY: Used when only CRD number is available
- ✓ NAME_ONLY: Used when only business name is available
- ✓ DEFAULT: Fallback strategy when no other strategy is applicable

Not Yet Implemented:
- ✗ TAX_ID_ONLY: For tax ID-based searches
- ✗ SEC_NUMBER_ONLY: For SEC number-based searches
- ✗ NAME_AND_LOCATION: For name and location combined searches

### Firm Services CLI

The `firm_services.py` CLI provides access to external financial regulatory services (FINRA BrokerCheck and SEC IAPD firm data).

#### Usage

```bash
python3 services/firm_services.py [--interactive] [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}] --subject-id SUBJECT_ID {search,details,search-crd} ...
```

Options:
- `--interactive`: Run in interactive menu mode
- `--log-level`: Set logging level (default: INFO)
- `--subject-id`: ID of the subject/client making the request

Commands:
- `search`: Search for firms by name
- `details`: Get detailed firm information by CRD number
- `search-crd`: Search for a firm by CRD number

## Logging System

The application uses a structured logging system that organizes logs by service groups:

### Log Directory Structure

```
logs/
├── agents/
│   └── agents.log      # Agent-related logs (FINRA, SEC agents)
├── core/
│   └── core.log       # Core application logs
├── evaluation/
│   └── evaluation.log # Evaluation and report processing logs
└── services/
    └── services.log   # Service-related logs (firm business, normalizer)
```

### Logging Configuration

- Each service group has its own log file
- Log files rotate at 10MB with 5 backup files
- Logs include timestamp, logger name, level, and formatted messages
- JSON data is properly formatted in logs
- Console output is maintained for all logs
- Log levels can be configured per group

### Log Groups

1. Services:
   - firm_business
   - firm_normalizer
   - firm_marshaller
   - firm_name_matcher

2. Agents:
   - FINRA agents (disciplinary, arbitration, brokercheck)
   - SEC agents (disciplinary, arbitration, IAPD)
   - NFA basic agent
   - Agent manager

3. Evaluation:
   - Firm evaluation processor
   - Report builder
   - Report director

4. Core:
   - Main application
   - API
   - Core business logic

### Setting Log Levels

Log levels can be set via:
1. Command line arguments (`--log-level`)
2. Environment variables
3. Configuration files
4. Runtime reconfiguration using `reconfigure_logging()`

## Features

- Search firms by name or CRD number
- Retrieve detailed firm information
- Combined view of FINRA and SEC data
- Caching support for improved performance
- Configurable logging levels

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

The CLI provides several commands for interacting with firm data:

```bash
# Search for a firm by name
python services/firm_services.py --subject-id <id> search "Firm Name"

# Get detailed firm information by CRD number
python services/firm_services.py --subject-id <id> details "123456"

# Search for a firm by CRD number
python services/firm_services.py --subject-id <id> search-crd "123456"

# Run in interactive mode
python services/firm_services.py --subject-id <id> --interactive
```

### Logging Configuration

The CLI supports different logging levels to control the verbosity of output. Use the `--log-level` argument to set the desired level:

```bash
# For detailed debugging output
python services/firm_services.py --subject-id <id> --log-level DEBUG search "Firm Name"

# For standard operational logging (default)
python services/firm_services.py --subject-id <id> --log-level INFO search "Firm Name"

# For warnings and errors only
python services/firm_services.py --subject-id <id> --log-level WARNING search "Firm Name"

# For errors only
python services/firm_services.py --subject-id <id> --log-level ERROR search "Firm Name"

# For critical errors only
python services/firm_services.py --subject-id <id> --log-level CRITICAL search "Firm Name"
```

Log files are stored in the `logs` directory with the following characteristics:
- Rotating file handler with 10MB max file size
- Keeps up to 5 backup files
- Logs include timestamp, module name, log level, and message
- Organized by component (services, agents, etc.)

### Log Output Examples

DEBUG level includes all messages:
```
2025-03-15 09:06:32,569 - services - DEBUG - FirmServicesFacade initialized
2025-03-15 09:06:32,569 - services - INFO - Searching for firm: Baker Avenue Asset Management
2025-03-15 09:06:32,570 - firm_marshaller - DEBUG - Fetched FINRA_FirmBrokerCheck_Agent/search_firm: result size = 1
```

INFO level shows operational messages:
```
2025-03-15 09:06:42,389 - services - INFO - Searching for firm: Baker Avenue Asset Management
2025-03-15 09:06:42,391 - firm_marshaller - INFO - Cache miss or stale for FINRA_FirmBrokerCheck_Agent/search_firm
```

## Architecture

The application follows a layered architecture:

1. CLI Layer (`firm_services.py`)
   - Handles command-line arguments
   - Configures logging
   - Provides interactive mode

2. Service Layer (`firm_marshaller.py`)
   - Normalizes data from different sources
   - Implements caching
   - Handles rate limiting

3. Agent Layer
   - FINRA BrokerCheck API integration
   - SEC IAPD API integration
   - Mock data for testing

## Cache Structure

The cache is organized by agent and subject:

```
cache/
└── subject_id/
    └── agent_name/
        └── service/
            └── firm_id/
                └── data files
```

## Logging Structure

Logs are organized by component with configurable levels:

```
logs/
└── app.log  # Main log file with rotation
```

Logger groups:
- `services`: Core business logic and data processing
- `agents`: External API integrations
- `evaluation`: Report generation and analysis
- `core`: Application-wide components

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Contact
- GitHub: [@jhighman](https://github.com/jhighman)