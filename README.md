# Firm Services CLI

A command-line interface for retrieving and managing firm information from FINRA BrokerCheck and SEC IAPD databases.

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