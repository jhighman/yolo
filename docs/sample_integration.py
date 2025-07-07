#!/usr/bin/env python3
"""
Sample Integration with Firm Compliance Reporting Service

This script demonstrates how to integrate with the Firm Compliance Reporting Service
to search for firms, retrieve firm details, and generate compliance reports.
"""

import json
import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from services.firm_services import FirmServicesFacade
from evaluation.firm_evaluation_report_builder import FirmEvaluationReportBuilder
from evaluation.firm_evaluation_report_director import FirmEvaluationReportDirector
from evaluation.firm_evaluation_processor import Alert, AlertSeverity


def search_firm_by_name(subject_id, firm_name):
    """
    Search for a firm by name.
    
    Args:
        subject_id: String identifier for the subject making the request
        firm_name: Name of the firm to search for
        
    Returns:
        List of matching firm records
    """
    print(f"Searching for firm: {firm_name}")
    
    # Initialize the facade
    facade = FirmServicesFacade()
    
    # Search for the firm
    results = facade.search_firm(subject_id, firm_name)
    
    if not results:
        print(f"No firms found matching name: {firm_name}")
        return []
    
    print(f"Found {len(results)} matching firms")
    return results


def get_firm_details(subject_id, crd_number):
    """
    Get detailed information for a firm by CRD number.
    
    Args:
        subject_id: String identifier for the subject making the request
        crd_number: CRD number of the firm
        
    Returns:
        Dictionary containing firm details or None if not found
    """
    print(f"Getting details for firm with CRD: {crd_number}")
    
    # Initialize the facade
    facade = FirmServicesFacade()
    
    # Get firm details
    business_info = facade.get_firm_details(subject_id, crd_number)
    
    if not business_info:
        print(f"Could not retrieve firm information for CRD: {crd_number}")
        return None
    
    print(f"Retrieved details for {business_info.get('firm_name', 'Unknown Firm')}")
    return business_info


def generate_compliance_report(subject_id, claim, business_info):
    """
    Generate a compliance report for a firm.
    
    Args:
        subject_id: String identifier for the subject making the request
        claim: Dictionary containing claim data
        business_info: Dictionary containing business information
        
    Returns:
        Dictionary containing the compliance report
    """
    print(f"Generating compliance report for {claim.get('entityName', 'Unknown Firm')}")
    
    # Create builder and director
    builder = FirmEvaluationReportBuilder(subject_id)
    director = FirmEvaluationReportDirector(builder)
    
    try:
        # Construct the report
        report = director.construct_evaluation_report(claim, business_info)
        
        # Extract key information
        overall_compliance = report['final_evaluation']['overall_compliance']
        risk_level = report['final_evaluation']['overall_risk_level']
        recommendations = report['final_evaluation']['recommendations']
        
        print(f"Report generated successfully:")
        print(f"  Compliance: {'PASS' if overall_compliance else 'FAIL'}")
        print(f"  Risk Level: {risk_level}")
        print(f"  Recommendations: {recommendations}")
        
        # Check for alerts
        alerts = report['final_evaluation'].get('alerts', [])
        if alerts:
            print(f"  Alerts: {len(alerts)}")
            for i, alert in enumerate(alerts, 1):
                print(f"    {i}. [{alert.get('severity', 'UNKNOWN')}] {alert.get('description', 'No description')}")
        else:
            print("  No alerts found")
            
        return report
        
    except Exception as e:
        print(f"Error generating compliance report: {str(e)}")
        raise


def save_report_to_file(report, output_path):
    """
    Save a compliance report to a JSON file.
    
    Args:
        report: Dictionary containing the compliance report
        output_path: Path to save the report to
    """
    try:
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Report saved to: {output_path}")
    except Exception as e:
        print(f"Error saving report: {str(e)}")


def process_alerts(alerts):
    """
    Process and categorize alerts from a compliance report.
    
    Args:
        alerts: List of alert dictionaries
        
    Returns:
        Dictionary with alerts categorized by severity
    """
    categorized_alerts = {
        "HIGH": [],
        "MEDIUM": [],
        "LOW": [],
        "INFO": []
    }
    
    for alert in alerts:
        severity = alert.get('severity', 'UNKNOWN')
        if severity in categorized_alerts:
            categorized_alerts[severity].append(alert)
    
    return categorized_alerts


def main():
    """Main entry point for the sample integration."""
    # Example usage
    subject_id = "SPID_EntityBioId"
    firm_name = "CLEAR STREET LLC"
    crd_number = "288933"
    
    # Option 1: Search for a firm by name, then get details
    search_results = search_firm_by_name(subject_id, firm_name)
    if search_results:
        # Use the first result
        first_result = search_results[0]
        result_crd = first_result.get('crd_number')
        if result_crd:
            business_info = get_firm_details(subject_id, result_crd)
        else:
            print("No CRD number found in search result")
            return
    else:
        # Option 2: Get firm details directly by CRD number
        business_info = get_firm_details(subject_id, crd_number)
    
    if not business_info:
        print("No business information available, cannot generate report")
        return
    
    # Prepare claim data
    claim = {
        "referenceId": subject_id,
        "crdNumber": crd_number,
        "entityName": firm_name,
        "business_ref": crd_number  # Required field
    }
    
    # Generate compliance report
    report = generate_compliance_report(subject_id, claim, business_info)
    
    # Save report to file
    if report:
        save_report_to_file(report, f"compliance_report_{crd_number}.json")
        
        # Process alerts
        alerts = report['final_evaluation'].get('alerts', [])
        if alerts:
            categorized_alerts = process_alerts(alerts)
            print("\nAlert Summary:")
            for severity, alert_list in categorized_alerts.items():
                if alert_list:
                    print(f"  {severity}: {len(alert_list)} alert(s)")


if __name__ == "__main__":
    main()