# Firm Compliance Reporting Service Integration Guide

## Table of Contents
1. [Service Overview](#service-overview)
2. [Integration Methods](#integration-methods)
3. [Input Requirements](#input-requirements)
4. [Output Structure](#output-structure)
5. [Error Handling](#error-handling)
6. [Alert System](#alert-system)
7. [Compliance Rules](#compliance-rules)
8. [Examples](#examples)

## Service Overview

The Firm Compliance Reporting Service provides comprehensive regulatory compliance evaluations for financial firms. It aggregates data from multiple regulatory sources (SEC, FINRA), evaluates compliance across various dimensions, and generates detailed reports with risk assessments and recommendations.

Key features:
- Firm search and verification
- Registration status evaluation
- Disclosure review
- Disciplinary action assessment
- Arbitration case review
- Risk level determination
- Compliance recommendations

## Integration Methods

### REST API

The service can be integrated via a RESTful API with the following endpoints:

#### 1. Firm Search

```
POST /api/v1/firms/search
```

Search for a firm by name or CRD number.

**Request Body:**
```json
{
  "subject_id": "EN-123456",
  "search_type": "name|crd",
  "search_value": "ACME Investments|123456"
}
```

**Response:**
```json
{
  "status": "success",
  "results": [
    {
      "firm_name": "ACME INVESTMENTS LLC",
      "crd_number": "123456",
      "sec_number": "801-12345",
      "registration_status": "Approved",
      "address": {
        "street": "123 WALL ST",
        "city": "NEW YORK",
        "state": "NY",
        "zip": "10001",
        "country": "United States"
      }
    }
  ]
}
```

#### 2. Generate Compliance Report

```
POST /api/v1/firms/compliance-report
```

Generate a comprehensive compliance report for a firm.

**Request Body:**
```json
{
  "subject_id": "EN-123456",
  "claim": {
    "referenceId": "EN-123456",
    "crdNumber": "123456",
    "entityName": "ACME Investments",
    "business_ref": "123456"
  }
}
```

**Response:**
A complete compliance report JSON as detailed in the [Output Structure](#output-structure) section.

### Command Line Interface

The service can also be invoked via command line:

```bash
# Evaluate a firm
python -m firm_evaluation_processor evaluate "ACME Investments" --crd 123456 --subject-id EN-123456

# Generate a report
python -m firm_evaluation_processor report "ACME Investments" --crd 123456 --subject-id EN-123456 --output report.json
```

## Input Requirements

### Required Fields

#### Claim Object
| Field | Type | Description | Required |
|-------|------|-------------|----------|
| referenceId | String | Unique identifier for the claim | Yes |
| crdNumber | String | CRD number of the firm | Yes |
| entityName | String | Name of the firm | Yes |
| business_ref | String | Business reference identifier | Yes |

#### Extracted Info Object
| Field | Type | Description | Required |
|-------|------|-------------|----------|
| search_evaluation | Object | Results of the firm search | Yes |
| disclosures | Array | List of disclosure records | No |
| disciplinary_actions | Array | List of disciplinary actions | No |
| arbitration_cases | Array | List of arbitration cases | No |

## Output Structure

The compliance report is a JSON document with the following structure:

```json
{
  "reference_id": "EN-123456",
  "claim": {
    "referenceId": "EN-123456",
    "crdNumber": "123456",
    "entityName": "ACME Investments"
  },
  "entity": {
    "firm_name": "ACME INVESTMENTS LLC",
    "crd_number": "123456",
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
  "disclosure_review": {
    "source": "SEC",
    "compliance": true,
    "compliance_explanation": "No disclosures found",
    "alerts": []
  },
  "disciplinary_evaluation": {
    "source": "SEC",
    "compliance": true,
    "compliance_explanation": "No disciplinary actions found.",
    "alerts": []
  },
  "arbitration_review": {
    "source": "SEC",
    "compliance": true,
    "compliance_explanation": "No arbitration cases found.",
    "alerts": []
  },
  "final_evaluation": {
    "overall_compliance": true,
    "overall_risk_level": "Low",
    "recommendations": "No immediate action required, monitor for changes.",
    "description": "All compliance checks passed",
    "alerts": []
  }
}
```

### Key Sections

1. **reference_id**: Unique identifier for the report
2. **claim**: Original claim data
3. **entity**: Comprehensive firm information
4. **search_evaluation**: Results of the firm search
5. **status_evaluation**: Evaluation of registration status
6. **disclosure_review**: Review of firm disclosures
7. **disciplinary_evaluation**: Evaluation of disciplinary actions
8. **arbitration_review**: Review of arbitration cases
9. **final_evaluation**: Overall compliance assessment and risk level

## Error Handling

The service uses a structured approach to error handling:

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid input parameters |
| 404 | Not Found - Firm not found |
| 500 | Internal Server Error |

### Error Response Format

```json
{
  "status": "error",
  "error_code": "INVALID_DATA",
  "message": "Missing required claim fields: business_ref",
  "details": {
    "missing_fields": ["business_ref"]
  }
}
```

### Common Error Codes

| Error Code | Description |
|------------|-------------|
| INVALID_DATA | Input data is invalid or missing required fields |
| FIRM_NOT_FOUND | Firm could not be found in regulatory databases |
| EVALUATION_ERROR | Error occurred during evaluation process |
| SYSTEM_ERROR | Unexpected system error |

## Alert System

Alerts are generated when potential compliance issues are detected. Each alert has:

- **alert_type**: Specific issue identified
- **severity**: Impact level (HIGH, MEDIUM, LOW, INFO)
- **description**: Human-readable explanation
- **metadata**: Additional context
- **alert_category**: Categorization of the alert

### Alert Severity Levels

| Level | Description |
|-------|-------------|
| HIGH | Critical issues requiring immediate attention |
| MEDIUM | Important issues that should be addressed |
| LOW | Minor issues that should be monitored |
| INFO | Informational notices, no action required |

### Alert Categories

| Category | Description |
|----------|-------------|
| REGISTRATION | Issues with firm registration status |
| REGULATORY | Issues with regulatory oversight |
| DISCLOSURE | Issues with firm disclosures |
| FINANCIAL | Issues with financial filings or stability |
| LEGAL | Issues with legal actions or jurisdiction |
| QUALIFICATION | Issues with professional qualifications |
| DATA_INTEGRITY | Issues with data quality or freshness |

### Common Alert Types

| Alert Type | Category | Description |
|------------|----------|-------------|
| NoActiveRegistration | REGISTRATION | Firm has no active registrations with any regulatory body |
| TerminatedRegistration | REGISTRATION | Firm's registration has been terminated |
| PendingRegistration | REGISTRATION | Firm's registration is pending approval |
| InactiveScope | REGISTRATION | Firm's IA scope is inactive |
| NoRegulatoryOversight | REGULATORY | No regulatory authorities found for the firm |
| TerminatedNoticeFiling | REGULATORY | Notice filing terminated in a state |
| UnresolvedDisclosure | DISCLOSURE | Unresolved disclosure found |
| RecentDisclosure | DISCLOSURE | Recently resolved disclosure found |
| SanctionsImposed | DISCLOSURE | Active sanctions from disclosure |
| OutdatedFinancialFiling | FINANCIAL | ADV filing is more than 1 year old |
| FinancialDisclosure | FINANCIAL | Financial disclosure or distress indicator found |
| PendingLegalAction | LEGAL | Unresolved legal action found |
| JurisdictionMismatch | LEGAL | SEC registered firm located outside United States |
| FailedAccountantExam | QUALIFICATION | Failed accountant exam |
| OutdatedQualification | QUALIFICATION | Qualification is more than 10 years old |
| OutdatedData | DATA_INTEGRITY | Data is more than 6 months old |
| NoDataSources | DATA_INTEGRITY | No data sources specified |

## Compliance Rules

The service evaluates compliance across multiple dimensions:

### 1. Registration Status

Evaluates if the firm has proper registration with regulatory bodies.

**Rules:**
- Firm must have active registration with SEC, FINRA, or state authorities
- Registration status must not be "Terminated" or "Pending"
- Firm's IA scope must be "ACTIVE" if applicable

**Failure Conditions:**
- Terminated registration
- No active registrations found
- Inactive IA scope

### 2. Disclosure Review

Evaluates the firm's disclosure history for compliance issues.

**Rules:**
- All disclosures should be resolved
- Recent disclosures (within 2 years) are flagged
- Active sanctions are flagged as high severity

**Failure Conditions:**
- Unresolved disclosures
- Active sanctions

### 3. Disciplinary Evaluation

Evaluates disciplinary actions against the firm.

**Rules:**
- No disciplinary actions should be present

**Failure Conditions:**
- Any disciplinary actions found

### 4. Arbitration Review

Evaluates arbitration cases involving the firm.

**Rules:**
- No arbitration cases should be present

**Failure Conditions:**
- Any arbitration cases found

### 5. Financial Evaluation

Evaluates financial stability and filings.

**Rules:**
- ADV filing should be less than 1 year old
- ADV PDF document should be available
- No financial distress indicators

**Failure Conditions:**
- Missing ADV filing
- Outdated ADV filing with missing PDF
- Financial disclosures present

### 6. Data Integrity

Evaluates the reliability of the data used for compliance assessment.

**Rules:**
- Data should be less than 6 months old
- Data sources should be specified

**Failure Conditions:**
- Missing last update timestamp
- No data sources specified

## Examples

### Example 1: Compliant Firm

**Input:**
```json
{
  "subject_id": "EN-128261",
  "claim": {
    "referenceId": "EN-128261",
    "crdNumber": "282487",
    "entityName": "YIELDSTREET",
    "business_ref": "282487"
  }
}
```

**Output Highlights:**
```json
{
  "status_evaluation": {
    "source": "SEC",
    "compliance": true,
    "compliance_explanation": "Firm is has active IA scope",
    "alerts": []
  },
  "final_evaluation": {
    "overall_compliance": true,
    "overall_risk_level": "Low",
    "recommendations": "No immediate action required, monitor for changes.",
    "description": "All compliance checks passed",
    "alerts": []
  }
}
```

### Example 2: Non-Compliant Firm (Terminated Registration)

**Input:**
```json
{
  "subject_id": "EN-123457",
  "claim": {
    "referenceId": "EN-123457",
    "crdNumber": "654321",
    "entityName": "TERMINATED INVESTMENTS LLC",
    "business_ref": "654321"
  }
}
```

**Output Highlights:**
```json
{
  "status_evaluation": {
    "source": "SEC",
    "compliance": false,
    "compliance_explanation": "Registration is terminated",
    "alerts": [
      {
        "alert_type": "TerminatedRegistration",
        "severity": "HIGH",
        "metadata": {
          "registration_status": "TERMINATED"
        },
        "description": "Firm's registration has been terminated",
        "alert_category": "REGISTRATION"
      }
    ]
  },
  "final_evaluation": {
    "overall_compliance": false,
    "overall_risk_level": "High",
    "recommendations": "Immediate action required due to critical compliance issues.",
    "description": "One or more compliance checks failed",
    "alerts": [
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
    ]
  }
}
```

### Example 3: Firm with Disclosures

**Input:**
```json
{
  "subject_id": "EN-123458",
  "claim": {
    "referenceId": "EN-123458",
    "crdNumber": "789012",
    "entityName": "DISCLOSURE ADVISORS LLC",
    "business_ref": "789012"
  }
}
```

**Output Highlights:**
```json
{
  "disclosure_review": {
    "source": "SEC",
    "compliance": false,
    "compliance_explanation": "Issues found: 2 unresolved disclosure(s), 1 active sanction(s)",
    "alerts": [
      {
        "alert_type": "UnresolvedDisclosure",
        "severity": "HIGH",
        "metadata": {
          "date": "2024-05-15",
          "status": "PENDING",
          "description": "Failure to supervise"
        },
        "description": "Unresolved disclosure from 2024-05-15",
        "alert_category": "DISCLOSURE"
      },
      {
        "alert_type": "SanctionsImposed",
        "severity": "HIGH",
        "metadata": {
          "date": "2024-05-15",
          "sanctions": [
            {
              "type": "MONETARY",
              "amount": 50000,
              "status": "ACTIVE"
            }
          ]
        },
        "description": "Active sanctions from disclosure dated 2024-05-15",
        "alert_category": "DISCLOSURE"
      }
    ]
  },
  "final_evaluation": {
    "overall_compliance": false,
    "overall_risk_level": "High",
    "recommendations": "Immediate action required due to critical compliance issues.",
    "description": "One or more compliance checks failed",
    "alerts": [
      {
        "eventDate": "2025-07-07",
        "severity": "HIGH",
        "alert_category": "DISCLOSURE",
        "alert_type": "UnresolvedDisclosure",
        "description": "Unresolved disclosure from 2024-05-15",
        "source": "SEC",
        "metadata": {
          "date": "2024-05-15",
          "status": "PENDING",
          "description": "Failure to supervise"
        }
      }
    ]
  }
}