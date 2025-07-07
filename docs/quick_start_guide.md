# Firm Compliance Reporting Service: Quick Start Guide

This guide provides a quick overview of how to integrate with the internal Firm Compliance Reporting Service. For detailed information, please refer to the [Integration Guide](integration_guide.md).

## Integration Methods

### 1. Direct Integration via FirmServicesFacade

The primary way to integrate with the service is through the `FirmServicesFacade` class:

```python
from services.firm_services import FirmServicesFacade

# Initialize the facade
facade = FirmServicesFacade()

# Search for a firm by name
subject_id = "SPID_EntityBioId"
firm_name = "CLEAR STREET LLC"
search_results = facade.search_firm(subject_id, firm_name)

# Or get firm details directly by CRD number
crd_number = "288933"
business_info = facade.get_firm_details(subject_id, crd_number)

# Process the results
if business_info:
    # Use the business_info to generate a compliance report
    from evaluation.firm_evaluation_report_builder import FirmEvaluationReportBuilder
    from evaluation.firm_evaluation_report_director import FirmEvaluationReportDirector
    
    # Create builder and director
    builder = FirmEvaluationReportBuilder(subject_id)
    director = FirmEvaluationReportDirector(builder)
    
    # Construct the report with required fields
    claim = {
        "referenceId": "SPID_EntityBioId",
        "crdNumber": "288933",
        "entityName": "CLEAR STREET LLC",
        "business_ref": "288933"  # Required field
    }
    
    report = director.construct_evaluation_report(claim, business_info)
    
    # Use the report
    print(f"Compliance status: {report['final_evaluation']['overall_compliance']}")
    print(f"Risk level: {report['final_evaluation']['overall_risk_level']}")
```

### 2. Command Line Interface

The service can also be invoked via command line:

```bash
# Evaluate a firm
python -m firm_evaluation_processor evaluate "CLEAR STREET LLC" --crd 288933 --subject-id SPID_EntityBioId

# Generate a report
python -m firm_evaluation_processor report "CLEAR STREET LLC" --crd 288933 --subject-id SPID_EntityBioId --output report.json
```

## Required Input Fields

### Claim Object
| Field | Type | Description | Required |
|-------|------|-------------|----------|
| referenceId | String | Unique identifier for the claim | Yes |
| crdNumber | String | CRD number of the firm | Yes |
| entityName | String | Name of the firm | Yes |
| business_ref | String | Business reference identifier (typically the CRD number) | Yes |

Example claim object:
```json
{
    "referenceId": "SPID_EntityBioId",
    "crdNumber": "288933",
    "entityName": "CLEAR STREET LLC",
    "business_ref": "288933"
}
```

## Understanding the Compliance Report

### Compliance Report Structure

```json
{
  "reference_id": "SPID_EntityBioId",
  "claim": {
    "referenceId": "SPID_EntityBioId",
    "crdNumber": "288933",
    "entityName": "CLEAR STREET LLC"
  },
  "entity": {
    "firm_name": "CLEAR STREET LLC",
    "crd_number": "288933",
    "sec_number": "801-12345",
    "registration_status": "Approved",
    "address": { ... },
    "registration_date": "4/6/2016",
    "other_names": [ ... ],
    "is_sec_registered": true,
    "is_state_registered": false,
    "is_era_registered": false,
    "adv_filing_date": "06/04/2025",
    "has_adv_pdf": true
  },
  "search_evaluation": {
    "source": "SEC",
    "compliance": true,
    "compliance_explanation": "Search completed successfully with SEC data, individual found.",
    "basic_result": { ... },
    "sec_search_result": { ... },
    "finra_search_result": { ... }
  },
  "status_evaluation": {
    "source": "SEC",
    "compliance": true,
    "compliance_explanation": "Firm is has active IA scope",
    "alerts": []
  },
  "disclosure_review": { ... },
  "disciplinary_evaluation": { ... },
  "arbitration_review": { ... },
  "final_evaluation": {
    "overall_compliance": true,
    "overall_risk_level": "Low",
    "recommendations": "No immediate action required, monitor for changes.",
    "description": "All compliance checks passed",
    "alerts": []
  }
}
```

### Key Fields to Check

1. `final_evaluation.overall_compliance`: Boolean indicating overall compliance status
2. `final_evaluation.overall_risk_level`: Risk assessment ("Low", "Medium", or "High")
3. `final_evaluation.alerts`: List of compliance issues that need attention

## Handling Alerts

Alerts indicate potential compliance issues. Each alert has:

- `alert_type`: The specific issue identified
- `severity`: Impact level (HIGH, MEDIUM, LOW, INFO)
- `description`: Human-readable explanation
- `alert_category`: Category of the alert (REGISTRATION, REGULATORY, etc.)

### Example Alert

```json
{
  "eventDate": "2025-07-07",
  "severity": "HIGH",
  "alert_category": "REGULATORY",
  "alert_type": "Regulatory Disclosure",
  "description": "Firm's registration has been terminated",
  "source": "SEC",
  "metadata": {
    "registration_status": "TERMINATED"
  }
}
```

## Common Error Types

| Error Type | Description |
|------------|-------------|
| InvalidDataError | Input data is invalid or missing required fields |
| EvaluationProcessError | Error occurred during evaluation process |
| FirmEvaluationError | Base exception for firm evaluation errors |

## Internal Support

For issues or questions about the service, contact the Compliance Systems team.