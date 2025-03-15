# Firm Evaluation Module

This module provides comprehensive functionality for evaluating a firm's regulatory compliance and generating detailed compliance reports with risk assessments. It analyzes various aspects of a firm's operations including registration status, regulatory oversight, disclosures, financial filings, legal standing, qualifications, and data integrity.

## Table of Contents
- [Overview](#overview)
- [Installation](#installation)
- [Usage](#usage)
- [Evaluation Categories](#evaluation-categories)
- [Alert System](#alert-system)
- [Alert Categories](#alert-categories)
- [API Reference](#api-reference)

## Overview

The evaluation module processes firm data to assess compliance across multiple dimensions. Each evaluation returns:
- A boolean compliance status
- A descriptive explanation
- A list of alerts with varying severity levels

## Installation

```bash
# Clone the repository
git clone <repository-url>

# Install dependencies
pip install -r requirements.txt
```

## Usage

### As a Module

```python
from evaluation.firm_evaluation_processor import (
    evaluate_registration_status,
    evaluate_regulatory_oversight,
    evaluate_disclosures,
    evaluate_financials,
    evaluate_legal,
    evaluate_qualifications,
    evaluate_data_integrity
)

# Example usage
business_info = {
    "is_sec_registered": True,
    "registration_status": "ACTIVE",
    "registration_date": "2020-01-01T00:00:00Z"
}

compliant, explanation, alerts = evaluate_registration_status(business_info)
```

### Via Command Line

```bash
# Run evaluations on a firm
python -m evaluation.firm_evaluation_processor --subject-id <id> evaluate <firm-name>

# Get detailed evaluation report
python -m evaluation.firm_evaluation_processor --subject-id <id> report <firm-name>
```

## Evaluation Categories

### 1. Registration Status
Evaluates the firm's registration status with regulatory bodies.
- Checks active registrations with SEC, FINRA, and state authorities
- Validates registration dates
- Identifies terminated or pending registrations

### 2. Regulatory Oversight
Assesses compliance with regulatory oversight requirements.
- Verifies presence of regulatory authorities
- Evaluates notice filings across jurisdictions
- Tracks filing status and dates

### 3. Disclosures
Reviews the firm's disclosure history.
- Analyzes unresolved disclosures
- Tracks recent resolved disclosures
- Monitors sanctions and their status

### 4. Financial Compliance
Evaluates financial documentation and stability.
- Checks ADV filing status and currency
- Verifies presence of required documentation
- Reviews financial distress indicators

### 5. Legal Standing
Assesses legal compliance and issues.
- Reviews legal disclosures
- Checks jurisdiction alignment
- Evaluates pending legal actions

### 6. Qualifications
Reviews professional qualifications and certifications.
- Tracks accountant examination results
- Monitors qualification currency
- Identifies failed or outdated certifications

### 7. Data Integrity
Evaluates the reliability of compliance data.
- Checks data freshness
- Validates data sources
- Monitors cache status

## Alert System

Alerts are categorized by severity:

- **HIGH**: Critical issues requiring immediate attention
- **MEDIUM**: Important issues that should be addressed
- **LOW**: Minor concerns for monitoring
- **INFO**: Informational notices

## Alert Categories

### Registration Alerts
- `NoActiveRegistration` (HIGH)
- `TerminatedRegistration` (HIGH)
- `PendingRegistration` (MEDIUM)
- `InvalidRegistrationDate` (HIGH)
- `OldRegistration` (LOW)

### Regulatory Oversight Alerts
- `NoRegulatoryOversight` (HIGH)
- `TerminatedNoticeFiling` (MEDIUM)
- `MissingFilingDate` (MEDIUM)
- `OldNoticeFiling` (LOW)

### Disclosure Alerts
- `UnresolvedDisclosure` (HIGH)
- `RecentDisclosure` (MEDIUM)
- `SanctionsImposed` (HIGH)
- `MissingDisclosureDate` (MEDIUM)

### Financial Alerts
- `NoADVFiling` (HIGH)
- `OutdatedFinancialFiling` (MEDIUM)
- `MissingADVDocument` (MEDIUM)
- `FinancialDisclosure` (HIGH)

### Legal Alerts
- `PendingLegalAction` (HIGH)
- `JurisdictionMismatch` (MEDIUM)
- `LegalSearchInfo` (MEDIUM/INFO)

### Qualification Alerts
- `FailedAccountantExam` (MEDIUM)
- `OutdatedQualification` (LOW)
- `MissingExamDate` (MEDIUM)

### Data Integrity Alerts
- `OutdatedData` (MEDIUM)
- `NoDataSources` (HIGH)
- `ExpiredCache` (LOW)
- `InvalidLastUpdateDate` (HIGH)
- `InvalidCacheDate` (HIGH)

## API Reference

### evaluate_registration_status
```python
def evaluate_registration_status(business_info: Dict[str, Any]) -> Tuple[bool, str, List[Alert]]
```
Evaluates firm registration status. Returns compliance status, explanation, and alerts.

### evaluate_regulatory_oversight
```python
def evaluate_regulatory_oversight(business_info: Dict[str, Any], business_name: str) -> Tuple[bool, str, List[Alert]]
```
Evaluates regulatory oversight compliance. Returns compliance status, explanation, and alerts.

### evaluate_disclosures
```python
def evaluate_disclosures(disclosures: List[Dict[str, Any]], business_name: str) -> Tuple[bool, str, List[Alert]]
```
Evaluates disclosure history. Returns compliance status, explanation, and alerts.

### evaluate_financials
```python
def evaluate_financials(business_info: Dict[str, Any], business_name: str) -> Tuple[bool, str, List[Alert]]
```
Evaluates financial compliance. Returns compliance status, explanation, and alerts.

### evaluate_legal
```python
def evaluate_legal(
    business_info: Dict[str, Any],
    business_name: str,
    due_diligence: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str, List[Alert]]
```
Evaluates legal compliance. Returns compliance status, explanation, and alerts.

### evaluate_qualifications
```python
def evaluate_qualifications(accountant_exams: List[Dict[str, Any]], business_name: str) -> Tuple[bool, str, List[Alert]]
```
Evaluates professional qualifications. Returns compliance status, explanation, and alerts.

### evaluate_data_integrity
```python
def evaluate_data_integrity(business_info: Dict[str, Any]) -> Tuple[bool, str, List[Alert]]
```
Evaluates data reliability. Returns compliance status, explanation, and alerts.

## Contributing

Please read [CONTRIBUTING.md](../CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details. 