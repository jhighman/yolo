# Firm Services and Business Logic

This repository contains tools and services for handling firm-related financial regulatory data, including search strategies and logging infrastructure.

For detailed documentation, please refer to the [docs](./docs) folder:
- [Integration Guide](./docs/integration_guide.md)
- [Quick Start Guide](./docs/quick_start_guide.md)
- [Compliance Rules and Alerts](./docs/compliance_rules_and_alerts.md)
- [Sample Integration](./docs/sample_integration.py)

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

## Contact
- GitHub: [@jhighman](https://github.com/jhighman)