"""
firm_evaluation_processor.py

This module provides functionality for evaluating a firm's regulatory compliance
and generating compliance reports with risk assessments.
"""

import json
import logging
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from utils.logging_config import setup_logging

# Initialize logging
loggers = setup_logging(debug=True)
logger = loggers.get('evaluation', logging.getLogger(__name__))

class AlertSeverity(Enum):
    """Defines severity levels for compliance alerts."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    INFO = "INFO"

@dataclass
class Alert:
    """Represents a compliance alert with severity and context."""
    alert_type: str
    severity: AlertSeverity
    metadata: Dict[str, Any]
    description: str
    alert_category: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary format for reporting."""
        return {
            "alert_type": self.alert_type,
            "severity": self.severity.value,
            "metadata": self.metadata,
            "description": self.description,
            "alert_category": self.alert_category or determine_alert_category(self.alert_type)
        }

def determine_alert_category(alert_type: str) -> str:
    """Map alert types to standardized categories."""
    category_mapping = {
        # Registration alerts
        "NoActiveRegistration": "REGISTRATION",
        "TerminatedRegistration": "REGISTRATION",
        "PendingRegistration": "REGISTRATION",
        
        # Regulatory oversight alerts
        "NoRegulatoryOversight": "REGULATORY",
        "TerminatedNoticeFiling": "REGULATORY",
        
        # Disclosure alerts
        "UnresolvedDisclosure": "DISCLOSURE",
        "RecentDisclosure": "DISCLOSURE",
        "SanctionsImposed": "DISCLOSURE",
        
        # Financial alerts
        "FinancialDisclosure": "FINANCIAL",
        "OutdatedFinancialFiling": "FINANCIAL",
        
        # Legal alerts
        "PendingLegalAction": "LEGAL",
        "JurisdictionMismatch": "LEGAL",
        "LegalSearchInfo": "LEGAL",
        
        # Qualification alerts
        "FailedAccountantExam": "QUALIFICATION",
        "OutdatedQualification": "QUALIFICATION",
        
        # Data integrity alerts
        "OutdatedData": "DATA_INTEGRITY",
        "NoDataSources": "DATA_INTEGRITY"
    }
    
    return category_mapping.get(alert_type, "GENERAL")

def evaluate_registration_status(business_info: Dict[str, Any]) -> Tuple[bool, str, List[Alert]]:
    """
    Evaluate the firm's registration status with regulatory bodies.
    
    Args:
        business_info: Dictionary containing registration information
        
    Returns:
        Tuple containing:
        - bool: Compliance status
        - str: Explanation of the evaluation
        - List[Alert]: List of generated alerts
    """
    logger.debug("Evaluating registration status")
    alerts = []
    
    # Extract registration flags
    is_sec_registered = business_info.get('is_sec_registered', False)
    is_finra_registered = business_info.get('is_finra_registered', False)
    is_state_registered = business_info.get('is_state_registered', False)
    registration_status = business_info.get('registration_status', '').upper()
    registration_date_str = business_info.get('registration_date')
    
    # Check if any registration is active
    has_active_registration = any([is_sec_registered, is_finra_registered, is_state_registered])
    
    if not has_active_registration:
        alerts.append(Alert(
            alert_type="NoActiveRegistration",
            severity=AlertSeverity.HIGH,
            metadata={"registration_status": registration_status},
            description="No active registrations found with any regulatory body"
        ))
        return False, "No active registrations found", alerts
    
    # Check registration status
    if registration_status == "TERMINATED":
        alerts.append(Alert(
            alert_type="TerminatedRegistration",
            severity=AlertSeverity.HIGH,
            metadata={"registration_status": registration_status},
            description="Firm's registration has been terminated"
        ))
        return False, "Registration is terminated", alerts
    
    if registration_status == "PENDING":
        alerts.append(Alert(
            alert_type="PendingRegistration",
            severity=AlertSeverity.MEDIUM,
            metadata={"registration_status": registration_status},
            description="Firm's registration is pending approval"
        ))
        return False, "Registration is pending", alerts
    
    # Check registration date if available
    if registration_date_str:
        try:
            # Handle potential Z suffix in ISO format
            date_str = registration_date_str
            if date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'
            registration_date = datetime.fromisoformat(date_str)
            
            if registration_date > datetime.now():
                alerts.append(Alert(
                    alert_type="InvalidRegistrationDate",
                    severity=AlertSeverity.HIGH,
                    metadata={"registration_date": registration_date_str},
                    description="Registration date is in the future"
                ))
                return False, "Invalid registration date", alerts
            
            # Check if registration is older than 20 years
            if datetime.now() - registration_date > timedelta(days=365*20):
                alerts.append(Alert(
                    alert_type="OldRegistration",
                    severity=AlertSeverity.LOW,
                    metadata={"registration_date": registration_date_str},
                    description="Registration is more than 20 years old"
                ))
        except ValueError as e:
            logger.error(f"Invalid registration date format: {registration_date_str}")
            alerts.append(Alert(
                alert_type="InvalidDateFormat",
                severity=AlertSeverity.MEDIUM,
                metadata={"registration_date": registration_date_str},
                description="Invalid registration date format"
            ))
    
    # Build explanation based on active registrations
    registration_types = []
    if is_sec_registered:
        registration_types.append("SEC")
    if is_finra_registered:
        registration_types.append("FINRA")
    if is_state_registered:
        registration_types.append("state")
    
    explanation = f"Firm is actively registered with {', '.join(registration_types)}"
    return True, explanation, alerts

def evaluate_regulatory_oversight(business_info: Dict[str, Any], business_name: str) -> Tuple[bool, str, List[Alert]]:
    """
    Evaluate compliance with regulatory oversight and notice filings.
    
    Args:
        business_info: Dictionary containing regulatory information
        business_name: Name of the business for reporting
        
    Returns:
        Tuple containing:
        - bool: Compliance status
        - str: Explanation of the evaluation
        - List[Alert]: List of generated alerts
    """
    logger.debug(f"Evaluating regulatory oversight for {business_name}")
    alerts = []
    
    regulatory_authorities = business_info.get('regulatory_authorities', [])
    notice_filings = business_info.get('notice_filings', [])
    
    # Check for regulatory oversight
    if not regulatory_authorities:
        alerts.append(Alert(
            alert_type="NoRegulatoryOversight",
            severity=AlertSeverity.HIGH,
            metadata={"business_name": business_name},
            description=f"No regulatory authorities found for {business_name}"
        ))
        return False, "No regulatory oversight detected", alerts
    
    # Evaluate notice filings
    active_filings = []
    terminated_filings = []
    
    for filing in notice_filings:
        status = filing.get('status', '').upper()
        effective_date_str = filing.get('effective_date')
        termination_date_str = filing.get('termination_date')
        state = filing.get('state', 'Unknown')
        
        if not effective_date_str:
            logger.error(f"Missing effective date in notice filing for {state}")
            alerts.append(Alert(
                alert_type="MissingFilingDate",
                severity=AlertSeverity.MEDIUM,
                metadata={"state": state},
                description=f"Missing effective date in notice filing for {state}"
            ))
            continue
            
        try:
            # Handle potential Z suffix in ISO format
            date_str = effective_date_str
            if date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'
            effective_date = datetime.fromisoformat(date_str)
            
            # Check if filing is terminated
            if termination_date_str:
                terminated_filings.append(state)
                alerts.append(Alert(
                    alert_type="TerminatedNoticeFiling",
                    severity=AlertSeverity.MEDIUM,
                    metadata={
                        "state": state,
                        "termination_date": termination_date_str
                    },
                    description=f"Notice filing terminated in {state}"
                ))
            elif status in ["ACTIVE", "APPROVED"]:
                # Check if filing is older than 5 years
                if datetime.now() - effective_date > timedelta(days=365*5):
                    alerts.append(Alert(
                        alert_type="OldNoticeFiling",
                        severity=AlertSeverity.LOW,
                        metadata={
                            "state": state,
                            "effective_date": effective_date_str
                        },
                        description=f"Notice filing in {state} is more than 5 years old"
                    ))
                active_filings.append(state)
            
        except ValueError as e:
            logger.error(f"Invalid date format in notice filing: {effective_date_str}")
            alerts.append(Alert(
                alert_type="InvalidFilingDate",
                severity=AlertSeverity.MEDIUM,
                metadata={"state": state, "date": effective_date_str},
                description=f"Invalid date format in notice filing for {state}"
            ))
    
    # Build explanation
    if active_filings:
        explanation = f"Firm has active notice filings in {', '.join(active_filings)}"
        if terminated_filings:
            explanation += f" and terminated filings in {', '.join(terminated_filings)}"
        return len(alerts) == 0, explanation, alerts
    else:
        return False, "No active notice filings found", alerts

def evaluate_disclosures(disclosures: List[Dict[str, Any]], business_name: str) -> Tuple[bool, str, List[Alert]]:
    """
    Evaluate the firm's disclosure history for compliance and risk.
    
    Args:
        disclosures: List of disclosure records
        business_name: Name of the business for reporting
        
    Returns:
        Tuple containing:
        - bool: Compliance status
        - str: Explanation of the evaluation
        - List[Alert]: List of generated alerts
    """
    logger.debug(f"Evaluating disclosures for {business_name}")
    alerts = []
    
    if not disclosures:
        return True, "No disclosures found", alerts
    
    unresolved_count = 0
    recent_resolved_count = 0
    active_sanctions_count = 0
    
    for disclosure in disclosures:
        status = disclosure.get('status', '').upper()
        date_str = disclosure.get('date')
        sanctions = disclosure.get('sanctions', [])
        
        if not date_str:
            logger.error("Missing date in disclosure")
            alerts.append(Alert(
                alert_type="MissingDisclosureDate",
                severity=AlertSeverity.MEDIUM,
                metadata={"status": status},
                description="Missing date in disclosure record"
            ))
            continue
            
        try:
            # Handle potential Z suffix in ISO format
            if date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'
            disclosure_date = datetime.fromisoformat(date_str)
            
            if status != "RESOLVED":
                unresolved_count += 1
                alerts.append(Alert(
                    alert_type="UnresolvedDisclosure",
                    severity=AlertSeverity.HIGH,
                    metadata={
                        "date": date_str,
                        "status": status,
                        "description": disclosure.get('description', 'No description provided')
                    },
                    description=f"Unresolved disclosure from {date_str}"
                ))
            elif datetime.now() - disclosure_date <= timedelta(days=365*2):
                recent_resolved_count += 1
                alerts.append(Alert(
                    alert_type="RecentDisclosure",
                    severity=AlertSeverity.MEDIUM,
                    metadata={
                        "date": date_str,
                        "description": disclosure.get('description', 'No description provided')
                    },
                    description=f"Recently resolved disclosure from {date_str}"
                ))
            
            if sanctions:
                active_sanctions_count += 1
                alerts.append(Alert(
                    alert_type="SanctionsImposed",
                    severity=AlertSeverity.HIGH,
                    metadata={
                        "date": date_str,
                        "sanctions": sanctions
                    },
                    description=f"Active sanctions from disclosure dated {date_str}"
                ))
                
        except ValueError as e:
            logger.error(f"Invalid date format in disclosure: {date_str}")
            alerts.append(Alert(
                alert_type="InvalidDisclosureDate",
                severity=AlertSeverity.MEDIUM,
                metadata={"date": date_str},
                description="Invalid date format in disclosure"
            ))
    
    # Build explanation
    if unresolved_count == 0 and active_sanctions_count == 0:
        if recent_resolved_count == 0:
            return True, "All disclosures resolved with no recent incidents", alerts
        else:
            return True, f"{recent_resolved_count} recently resolved disclosure(s) found", alerts
    else:
        explanation = []
        if unresolved_count > 0:
            explanation.append(f"{unresolved_count} unresolved disclosure(s)")
        if active_sanctions_count > 0:
            explanation.append(f"{active_sanctions_count} active sanction(s)")
        return False, f"Issues found: {', '.join(explanation)}", alerts

def evaluate_financials(business_info: Dict[str, Any], business_name: str) -> Tuple[bool, str, List[Alert]]:
    """
    Evaluate financial stability based on available data.
    
    Args:
        business_info: Dictionary containing financial information
        business_name: Name of the business for reporting
        
    Returns:
        Tuple containing:
        - bool: Compliance status
        - str: Explanation of the evaluation
        - List[Alert]: List of generated alerts
    """
    logger.debug(f"Evaluating financials for {business_name}")
    alerts = []
    
    # Check ADV filing status
    adv_filing_date_str = business_info.get('adv_filing_date')
    has_adv_pdf = business_info.get('has_adv_pdf', False)
    
    if not adv_filing_date_str:
        alerts.append(Alert(
            alert_type="NoADVFiling",
            severity=AlertSeverity.HIGH,
            metadata={"business_name": business_name},
            description="No ADV filing date found"
        ))
        return False, "No ADV filing information available", alerts
    
    try:
        # Handle potential Z suffix in ISO format
        date_str = adv_filing_date_str
        if date_str.endswith('Z'):
            date_str = date_str[:-1] + '+00:00'
        adv_filing_date = datetime.fromisoformat(date_str)
        
        if datetime.now() - adv_filing_date > timedelta(days=365):
            alerts.append(Alert(
                alert_type="OutdatedFinancialFiling",
                severity=AlertSeverity.MEDIUM,
                metadata={
                    "filing_date": adv_filing_date_str,
                    "business_name": business_name
                },
                description="ADV filing is more than 1 year old"
            ))
    except ValueError as e:
        logger.error(f"Invalid ADV filing date format: {adv_filing_date_str}")
        alerts.append(Alert(
            alert_type="InvalidADVDate",
            severity=AlertSeverity.MEDIUM,
            metadata={"date": adv_filing_date_str},
            description="Invalid ADV filing date format"
        ))
    
    if not has_adv_pdf:
        alerts.append(Alert(
            alert_type="MissingADVDocument",
            severity=AlertSeverity.MEDIUM,
            metadata={"business_name": business_name},
            description="ADV PDF document is not available"
        ))
    
    # Check for financial disclosures
    disclosures = business_info.get('disclosures', [])
    financial_disclosures = [
        d for d in disclosures 
        if d.get('type', '').upper() in ['FINANCIAL', 'BANKRUPTCY', 'FINANCIAL_DISTRESS']
    ]
    
    for disclosure in financial_disclosures:
        alerts.append(Alert(
            alert_type="FinancialDisclosure",
            severity=AlertSeverity.HIGH,
            metadata={
                "date": disclosure.get('date'),
                "description": disclosure.get('description', 'No description provided')
            },
            description="Financial disclosure or distress indicator found"
        ))
    
    # Determine overall financial compliance
    if not alerts:
        return True, "No financial issues detected", alerts
    elif any(a.severity == AlertSeverity.HIGH for a in alerts):
        return False, "Significant financial concerns detected", alerts
    else:
        return False, "Minor financial documentation issues found", alerts

def evaluate_legal(
    business_info: Dict[str, Any],
    business_name: str,
    due_diligence: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str, List[Alert]]:
    """
    Evaluate legal compliance based on disclosures and operational legitimacy.
    
    Args:
        business_info: Dictionary containing legal information
        business_name: Name of the business for reporting
        due_diligence: Optional additional legal review information
        
    Returns:
        Tuple containing:
        - bool: Compliance status
        - str: Explanation of the evaluation
        - List[Alert]: List of generated alerts
    """
    logger.debug(f"Evaluating legal compliance for {business_name}")
    alerts = []
    
    # Check headquarters location
    headquarters = business_info.get('headquarters', {})
    country = headquarters.get('country', '').upper()
    state = headquarters.get('state')
    
    # Verify jurisdiction alignment
    is_sec_registered = business_info.get('is_sec_registered', False)
    if is_sec_registered and country != 'UNITED STATES':
        alerts.append(Alert(
            alert_type="JurisdictionMismatch",
            severity=AlertSeverity.MEDIUM,
            metadata={
                "country": country,
                "registration_type": "SEC"
            },
            description="SEC registered firm located outside United States"
        ))
    
    # Check legal disclosures
    disclosures = business_info.get('disclosures', [])
    legal_disclosures = [
        d for d in disclosures
        if d.get('type', '').upper() in ['CIVIL', 'CRIMINAL', 'REGULATORY', 'JUDGMENT', 'LIEN']
    ]
    
    unresolved_legal = []
    for disclosure in legal_disclosures:
        status = disclosure.get('status', '').upper()
        if status != 'RESOLVED':
            unresolved_legal.append(disclosure)
            alerts.append(Alert(
                alert_type="PendingLegalAction",
                severity=AlertSeverity.HIGH,
                metadata={
                    "date": disclosure.get('date'),
                    "type": disclosure.get('type'),
                    "description": disclosure.get('description', 'No description provided')
                },
                description=f"Unresolved legal action: {disclosure.get('type', 'Unknown type')}"
            ))
    
    # Process additional due diligence if provided
    if due_diligence:
        filtered_records = due_diligence.get('filtered_records', 0)
        if filtered_records > 10:
            alerts.append(Alert(
                alert_type="LegalSearchInfo",
                severity=AlertSeverity.MEDIUM,
                metadata={"filtered_count": filtered_records},
                description=f"Large number ({filtered_records}) of filtered legal records found"
            ))
        elif filtered_records > 0:
            alerts.append(Alert(
                alert_type="LegalSearchInfo",
                severity=AlertSeverity.INFO,
                metadata={"filtered_count": filtered_records},
                description=f"{filtered_records} filtered legal record(s) found"
            ))
    
    # Determine overall legal compliance
    if not alerts:
        return True, "No legal issues found", alerts
    elif any(a.severity == AlertSeverity.HIGH for a in alerts):
        return False, f"Significant legal issues found: {len(unresolved_legal)} unresolved actions", alerts
    else:
        return False, "Minor legal concerns identified", alerts

def evaluate_qualifications(accountant_exams: List[Dict[str, Any]], business_name: str) -> Tuple[bool, str, List[Alert]]:
    """
    Evaluate accountant-related qualifications.
    
    Args:
        accountant_exams: List of accountant examination records
        business_name: Name of the business for reporting
        
    Returns:
        Tuple containing:
        - bool: Compliance status
        - str: Explanation of the evaluation
        - List[Alert]: List of generated alerts
    """
    logger.debug(f"Evaluating qualifications for {business_name}")
    alerts = []
    
    if not accountant_exams:
        return True, "No accountant exams required", alerts
    
    failed_exams = []
    outdated_exams = []
    current_exams = []
    
    for exam in accountant_exams:
        status = exam.get('status', '').upper()
        date_str = exam.get('date')
        exam_type = exam.get('exam_type', 'Unknown')
        
        if not date_str:
            logger.error(f"Missing date for {exam_type} exam")
            alerts.append(Alert(
                alert_type="MissingExamDate",
                severity=AlertSeverity.MEDIUM,
                metadata={
                    "exam_type": exam_type,
                    "status": status
                },
                description=f"Missing date for {exam_type} exam"
            ))
            continue
            
        try:
            # Handle potential Z suffix in ISO format
            if date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'
            exam_date = datetime.fromisoformat(date_str)
            
            if status == 'FAILED':
                failed_exams.append(exam_type)
                alerts.append(Alert(
                    alert_type="FailedAccountantExam",
                    severity=AlertSeverity.MEDIUM,
                    metadata={
                        "exam_type": exam_type,
                        "date": date_str
                    },
                    description=f"Failed {exam_type} exam on {date_str}"
                ))
            elif datetime.now() - exam_date > timedelta(days=365*10):
                outdated_exams.append(exam_type)
                alerts.append(Alert(
                    alert_type="OutdatedQualification",
                    severity=AlertSeverity.LOW,
                    metadata={
                        "exam_type": exam_type,
                        "date": date_str
                    },
                    description=f"Qualification for {exam_type} is more than 10 years old"
                ))
            else:
                current_exams.append(exam_type)
                
        except ValueError as e:
            logger.error(f"Invalid exam date format: {date_str}")
            alerts.append(Alert(
                alert_type="InvalidExamDate",
                severity=AlertSeverity.MEDIUM,
                metadata={
                    "exam_type": exam_type,
                    "date": date_str
                },
                description="Invalid exam date format"
            ))
    
    # Build explanation
    if current_exams:
        explanation = f"Current qualifications: {', '.join(current_exams)}"
        if outdated_exams:
            explanation += f"; Outdated: {', '.join(outdated_exams)}"
        if failed_exams:
            explanation += f"; Failed: {', '.join(failed_exams)}"
        return len(failed_exams) == 0, explanation, alerts
    elif outdated_exams:
        return False, f"All qualifications outdated: {', '.join(outdated_exams)}", alerts
    else:
        return False, f"Failed qualifications: {', '.join(failed_exams)}", alerts

def evaluate_data_integrity(business_info: Dict[str, Any]) -> Tuple[bool, str, List[Alert]]:
    """
    Evaluate data reliability for compliance assessments.
    
    Args:
        business_info: Dictionary containing data metadata
        
    Returns:
        Tuple containing:
        - bool: Compliance status
        - str: Explanation of the evaluation
        - List[Alert]: List of generated alerts
    """
    logger.debug("Evaluating data integrity")
    alerts = []
    
    # Check last update timestamp
    last_updated_str = business_info.get('last_updated')
    if not last_updated_str:
        alerts.append(Alert(
            alert_type="NoLastUpdateDate",
            severity=AlertSeverity.HIGH,
            metadata={},
            description="No last update timestamp found"
        ))
    else:
        try:
            # Handle potential Z suffix in ISO format
            date_str = last_updated_str
            if date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'
            last_updated = datetime.fromisoformat(date_str)
            
            if datetime.now() - last_updated > timedelta(days=180):
                alerts.append(Alert(
                    alert_type="OutdatedData",
                    severity=AlertSeverity.MEDIUM,
                    metadata={"last_updated": last_updated_str},
                    description="Data is more than 6 months old"
                ))
        except ValueError as e:
            logger.error(f"Invalid last updated date format: {last_updated_str}")
            alerts.append(Alert(
                alert_type="InvalidLastUpdateDate",
                severity=AlertSeverity.MEDIUM,
                metadata={"date": last_updated_str},
                description="Invalid last update date format"
            ))
    
    # Check data sources
    data_sources = business_info.get('data_sources', [])
    if not data_sources:
        alerts.append(Alert(
            alert_type="NoDataSources",
            severity=AlertSeverity.HIGH,
            metadata={},
            description="No data sources specified"
        ))
    
    # Check cache status
    cache_status = business_info.get('cache_status', {})
    is_cached = cache_status.get('is_cached', False)
    cache_date_str = cache_status.get('cache_date')
    ttl = cache_status.get('ttl', 0)
    
    if is_cached and cache_date_str:
        try:
            # Handle potential Z suffix in ISO format
            date_str = cache_date_str
            if date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'
            cache_date = datetime.fromisoformat(date_str)
            cache_age = datetime.now() - cache_date
            
            if ttl > 0 and cache_age > timedelta(seconds=ttl):
                alerts.append(Alert(
                    alert_type="ExpiredCache",
                    severity=AlertSeverity.LOW,
                    metadata={
                        "cache_date": cache_date_str,
                        "ttl": ttl,
                        "age_seconds": int(cache_age.total_seconds())
                    },
                    description="Cache data has expired"
                ))
        except ValueError as e:
            logger.error(f"Invalid cache date format: {cache_date_str}")
            alerts.append(Alert(
                alert_type="InvalidCacheDate",
                severity=AlertSeverity.LOW,
                metadata={"date": cache_date_str},
                description="Invalid cache date format"
            ))
    
    # Determine overall data integrity
    if not alerts:
        return True, "Data is current and reliable", alerts
    elif any(a.severity == AlertSeverity.HIGH for a in alerts):
        return False, "Significant data integrity issues found", alerts
    else:
        return False, "Minor data integrity concerns identified", alerts