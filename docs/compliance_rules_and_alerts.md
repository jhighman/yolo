# Compliance Rules and Alerts Reference Guide

This document provides detailed information about the compliance rules and alerts used in the Firm Compliance Reporting Service.

## Table of Contents
1. [Compliance Rules Overview](#compliance-rules-overview)
2. [Alert System](#alert-system)
3. [Registration Status Rules](#registration-status-rules)
4. [Disclosure Review Rules](#disclosure-review-rules)
5. [Disciplinary Evaluation Rules](#disciplinary-evaluation-rules)
6. [Arbitration Review Rules](#arbitration-review-rules)
7. [Financial Evaluation Rules](#financial-evaluation-rules)
8. [Data Integrity Rules](#data-integrity-rules)
9. [Alert Categories and Types](#alert-categories-and-types)
10. [Example Scenarios](#example-scenarios)

## Compliance Rules Overview

The Firm Compliance Reporting Service evaluates financial firms across multiple dimensions to determine overall compliance status and risk level. Each dimension has specific rules that generate alerts when potential issues are detected.

The primary evaluation dimensions are:
- Registration Status
- Disclosure Review
- Disciplinary Evaluation
- Arbitration Review
- Financial Evaluation
- Data Integrity

## Alert System

### Alert Structure

Each alert contains the following information:

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

### Alert Severity Levels

| Level | Description |
|-------|-------------|
| HIGH | Critical issues requiring immediate attention. These issues typically result in compliance failure and high risk assessment. |
| MEDIUM | Important issues that should be addressed but may not immediately fail compliance. These contribute to elevated risk assessment. |
| LOW | Minor issues that should be monitored. These generally don't affect compliance status but may contribute to risk assessment. |
| INFO | Informational notices with no compliance impact. These provide context but don't affect compliance or risk assessment. |

## Registration Status Rules

Registration status evaluation checks if the firm has proper registration with regulatory bodies.

### Key Fields Evaluated
- `registration_status`: Current registration status with regulatory bodies
- `firm_ia_scope`: Investment Adviser scope status
- `is_sec_registered`: SEC registration flag
- `is_finra_registered`: FINRA registration flag
- `is_state_registered`: State registration flag
- `registration_date`: Date of initial registration

### Rules

| Rule | Description | Compliance Impact |
|------|-------------|-------------------|
| Active Registration | Firm must have active registration with SEC, FINRA, or state authorities | Required for compliance |
| Registration Status | Status must not be "Terminated" or "Pending" | "Terminated" fails compliance, "Pending" generates alert |
| IA Scope | Firm's IA scope must be "ACTIVE" if applicable | "INACTIVE" fails compliance |
| Registration Date | Registration date must be valid and not in the future | Invalid date fails compliance |

### Alerts

| Alert Type | Severity | Description | Compliance Impact |
|------------|----------|-------------|-------------------|
| TerminatedRegistration | HIGH | Firm's registration has been terminated | Fails compliance |
| PendingRegistration | MEDIUM | Firm's registration is pending approval | Fails compliance |
| InactiveScope | HIGH | Firm's IA scope is inactive | Fails compliance |
| NoActiveRegistration | HIGH | No active registrations found with any regulatory body | Fails compliance |
| FailureToRenew | HIGH | Firm failed to renew registration | Fails compliance |
| InvalidRegistrationDate | HIGH | Registration date is in the future | Fails compliance |
| OldRegistration | LOW | Registration is more than 20 years old | Warning only |

## Disclosure Review Rules

Disclosure review evaluates the firm's disclosure history for compliance issues.

### Key Fields Evaluated
- `disclosures`: Array of disclosure records
- `disclosure.status`: Status of each disclosure
- `disclosure.date`: Date of each disclosure
- `disclosure.sanctions`: Sanctions associated with disclosures

### Rules

| Rule | Description | Compliance Impact |
|------|-------------|-------------------|
| Resolved Disclosures | All disclosures should be resolved | Unresolved disclosures fail compliance |
| Recent Disclosures | Recent disclosures (within 2 years) are flagged | Warning only |
| Active Sanctions | No active sanctions should be present | Active sanctions fail compliance |

### Alerts

| Alert Type | Severity | Description | Compliance Impact |
|------------|----------|-------------|-------------------|
| UnresolvedDisclosure | HIGH | Unresolved disclosure found | Fails compliance |
| RecentDisclosure | MEDIUM | Recently resolved disclosure found | Warning only |
| SanctionsImposed | HIGH | Active sanctions from disclosure | Fails compliance |
| InvalidDisclosureDate | MEDIUM | Invalid date format in disclosure | Warning only |

## Disciplinary Evaluation Rules

Disciplinary evaluation checks for disciplinary actions against the firm.

### Key Fields Evaluated
- `disciplinary_actions`: Array of disciplinary action records

### Rules

| Rule | Description | Compliance Impact |
|------|-------------|-------------------|
| No Disciplinary Actions | No disciplinary actions should be present | Any disciplinary actions fail compliance |

## Arbitration Review Rules

Arbitration review evaluates arbitration cases involving the firm.

### Key Fields Evaluated
- `arbitration_cases`: Array of arbitration case records

### Rules

| Rule | Description | Compliance Impact |
|------|-------------|-------------------|
| No Arbitration Cases | No arbitration cases should be present | Any arbitration cases fail compliance |

## Financial Evaluation Rules

Financial evaluation assesses financial stability and filings.

### Key Fields Evaluated
- `adv_filing_date`: Date of the latest ADV filing
- `has_adv_pdf`: Flag indicating if ADV PDF document is available
- Financial disclosures in the disclosures array

### Rules

| Rule | Description | Compliance Impact |
|------|-------------|-------------------|
| ADV Filing | ADV filing should be less than 1 year old | Outdated filing generates alert |
| ADV Document | ADV PDF document should be available | Missing document generates alert |
| Financial Disclosures | No financial distress indicators should be present | Financial disclosures fail compliance |

### Alerts

| Alert Type | Severity | Description | Compliance Impact |
|------------|----------|-------------|-------------------|
| NoADVFiling | HIGH | No ADV filing date found | Fails compliance |
| OutdatedFinancialFiling | MEDIUM | ADV filing is more than 1 year old | Warning, fails if combined with missing PDF |
| MissingADVDocument | MEDIUM | ADV PDF document is not available | Warning, fails if combined with outdated filing |
| FinancialDisclosure | HIGH | Financial disclosure or distress indicator found | Fails compliance |
| InvalidADVDate | MEDIUM | Invalid ADV filing date format | Warning only |

## Data Integrity Rules

Data integrity evaluation assesses the reliability of the data used for compliance assessment.

### Key Fields Evaluated
- `last_updated`: Timestamp of the last data update
- `data_sources`: Array of data source identifiers
- `cache_status`: Information about data caching

### Rules

| Rule | Description | Compliance Impact |
|------|-------------|-------------------|
| Data Freshness | Data should be less than 6 months old | Outdated data generates alert |
| Data Sources | Data sources should be specified | Missing sources fail compliance |
| Cache Status | Cache should not be expired | Expired cache generates low-severity alert |

### Alerts

| Alert Type | Severity | Description | Compliance Impact |
|------------|----------|-------------|-------------------|
| NoLastUpdateDate | HIGH | No last update timestamp found | Fails compliance |
| OutdatedData | MEDIUM | Data is more than 6 months old | Warning only |
| NoDataSources | HIGH | No data sources specified | Fails compliance |
| ExpiredCache | LOW | Cache data has expired | Warning only |
| InvalidLastUpdateDate | HIGH | Invalid last update date format | Fails compliance |

## Alert Categories and Types

Alerts are organized into categories for easier management and reporting.

### Categories

| Category | Description | Examples |
|----------|-------------|----------|
| REGISTRATION | Issues with firm registration status | TerminatedRegistration, NoActiveRegistration |
| REGULATORY | Issues with regulatory oversight | NoRegulatoryOversight, TerminatedNoticeFiling |
| DISCLOSURE | Issues with firm disclosures | UnresolvedDisclosure, RecentDisclosure |
| FINANCIAL | Issues with financial filings or stability | OutdatedFinancialFiling, FinancialDisclosure |
| LEGAL | Issues with legal actions or jurisdiction | PendingLegalAction, JurisdictionMismatch |
| QUALIFICATION | Issues with professional qualifications | FailedAccountantExam, OutdatedQualification |
| DATA_INTEGRITY | Issues with data quality or freshness | OutdatedData, NoDataSources |

### Alert Type Mapping

Some alert types are mapped to standardized types for consistency in reporting:

| Original Alert Type | Standardized Type | Category |
|---------------------|-------------------|----------|
| NoActiveRegistration | Regulatory Disclosure | REGULATORY |
| NoRegulatoryOversight | Regulatory Disclosure | REGULATORY |
| NoADVFiling | Compliance Disclosure | COMPLIANCE |
| NoLastUpdateDate | Compliance Disclosure | COMPLIANCE |
| BusinessNotFound | Compliance Disclosure | COMPLIANCE |
| RecordSkipped | Compliance Disclosure | COMPLIANCE |
| EvaluationError | System Disclosure | SYSTEM |

## Example Scenarios

### Scenario 1: Compliant Firm

A firm with the following characteristics would be compliant with low risk:
- Active registration with SEC
- Active IA scope
- No disclosures or all disclosures resolved and older than 2 years
- No disciplinary actions
- No arbitration cases
- Current ADV filing (less than 1 year old) with PDF available
- Current data (less than 6 months old) with specified sources

**Example Report Excerpt:**
```json
{
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
  "final_evaluation": {
    "overall_compliance": true,
    "overall_risk_level": "Low",
    "recommendations": "No immediate action required, monitor for changes.",
    "description": "All compliance checks passed",
    "alerts": []
  }
}
```

### Scenario 2: Non-Compliant Firm (Terminated Registration)

A firm with terminated registration would fail compliance with high risk:

**Example Report Excerpt:**
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

### Scenario 3: Medium Risk Firm (Outdated Filings)

A firm with outdated ADV filing but otherwise compliant would have medium risk:

**Example Report Excerpt:**
```json
{
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
  "final_evaluation": {
    "overall_compliance": true,
    "overall_risk_level": "Medium",
    "recommendations": "Review and address compliance concerns within standard timeframes.",
    "description": "All compliance checks passed with minor concerns",
    "alerts": [
      {
        "eventDate": "2025-07-07",
        "severity": "MEDIUM",
        "alert_category": "FINANCIAL",
        "alert_type": "OutdatedFinancialFiling",
        "description": "ADV filing is more than 1 year old",
        "source": "SEC",
        "metadata": {
          "filing_date": "2023-05-15"
        }
      }
    ]
  }
}
```

### Scenario 4: Non-Compliant Firm (Unresolved Disclosures)

A firm with unresolved disclosures would fail compliance with high risk:

**Example Report Excerpt:**
```json
{
  "disclosure_review": {
    "source": "SEC",
    "compliance": false,
    "compliance_explanation": "Issues found: 2 unresolved disclosure(s)",
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