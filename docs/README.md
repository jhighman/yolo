# Firm Compliance Reporting Service Documentation

## Overview

The Firm Compliance Reporting Service provides comprehensive regulatory compliance evaluations for financial firms. This documentation set explains how to integrate with the service, understand the compliance rules, and interpret the results.

## Documentation Contents

1. **[Integration Guide](integration_guide.md)** - Comprehensive guide to integrating with the service
2. **[Quick Start Guide](quick_start_guide.md)** - Concise guide to get started quickly
3. **[Compliance Rules and Alerts](compliance_rules_and_alerts.md)** - Detailed explanation of compliance rules and alerts

## Key Features

- Firm search and verification
- Registration status evaluation
- Disclosure review
- Disciplinary action assessment
- Arbitration case review
- Risk level determination
- Compliance recommendations

## Getting Started

For new users, we recommend starting with the [Quick Start Guide](quick_start_guide.md) to understand the basic integration flow. Then refer to the [Integration Guide](integration_guide.md) for more detailed information.

If you need to understand the compliance rules and alerts in depth, refer to the [Compliance Rules and Alerts](compliance_rules_and_alerts.md) document.

## Integration Methods

The service can be integrated in two primary ways:

1. **Direct Integration via FirmServicesFacade** - For programmatic access from your application
2. **Command Line Interface** - For manual operations or scripting

## Example Usage

### Direct Integration

```python
from services.firm_services import FirmServicesFacade
from evaluation.firm_evaluation_report_builder import FirmEvaluationReportBuilder
from evaluation.firm_evaluation_report_director import FirmEvaluationReportDirector

# Initialize the facade
facade = FirmServicesFacade()

# Get firm details by CRD number
subject_id = "SPID_EntityBioId"
crd_number = "288933"
business_info = facade.get_firm_details(subject_id, crd_number)

# Generate compliance report
builder = FirmEvaluationReportBuilder(subject_id)
director = FirmEvaluationReportDirector(builder)

claim = {
    "referenceId": "SPID_EntityBioId",
    "crdNumber": "288933",
    "entityName": "CLEAR STREET LLC",
    "business_ref": "288933"  # Required field
}

report = director.construct_evaluation_report(claim, business_info)

# Check compliance status
is_compliant = report['final_evaluation']['overall_compliance']
risk_level = report['final_evaluation']['overall_risk_level']
```

### Command Line

```bash
# Generate a compliance report
python -m firm_evaluation_processor report "CLEAR STREET LLC" --crd 288933 --subject-id SPID_EntityBioId --output report.json
```

## Understanding Results

The compliance report includes several key sections:

- **search_evaluation** - Results of the firm search
- **status_evaluation** - Evaluation of registration status
- **disclosure_review** - Review of firm disclosures
- **disciplinary_evaluation** - Evaluation of disciplinary actions
- **arbitration_review** - Review of arbitration cases
- **final_evaluation** - Overall compliance assessment and risk level

The most important fields to check are:

- `final_evaluation.overall_compliance` - Boolean indicating overall compliance status
- `final_evaluation.overall_risk_level` - Risk assessment ("Low", "Medium", or "High")
- `final_evaluation.alerts` - List of compliance issues that need attention

## Support

For issues or questions about the service, contact the Compliance Systems team.