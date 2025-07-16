import json
import logging
from services.firm_services import FirmServicesFacade
from evaluation.firm_evaluation_report_director import FirmEvaluationReportDirector
from evaluation.firm_evaluation_report_builder import FirmEvaluationReportBuilder

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_brookstone_report():
    """Test generating a compliance report for BROOKSTONE SECURITIES, INC (CRD #29116)"""
    print("\nGenerating compliance report for BROOKSTONE SECURITIES, INC (CRD #29116)")
    
    # Initialize services
    firm_services = FirmServicesFacade()
    
    # Define CRD number
    crd_number = "29116"
    
    # Get firm details
    subject_id = "TEST_BROOKSTONE"
    firm_details = firm_services.get_firm_details(subject_id, crd_number)
    
    if firm_details is None:
        print("\nFirm not found!")
        return None
    
    # Create a reference ID for the report
    reference_id = "TEST-BROOKSTONE-29116"
    
    # Initialize the builder and director
    report_builder = FirmEvaluationReportBuilder(reference_id)
    report_director = FirmEvaluationReportDirector(report_builder)
    
    print(f"\nFirm Status: {firm_details.get('firm_status', 'UNKNOWN').upper()}")
    print(f"\nStatus Message: {firm_details.get('status_message', 'N/A')}")
    
    # Create a claim dictionary
    claim = {
        "business_ref": "TEST-BROOKSTONE-29116",
        "business_name": "BROOKSTONE SECURITIES, INC",
        "organization_crd": "29116"
    }
    
    # Create extracted_info dictionary with the firm details
    extracted_info = {
        "search_evaluation": {
            "compliance": True,
            "source": "SEC"
        }
    }
    
    # Only update if firm_details is not None
    if firm_details:
        extracted_info.update(firm_details)
    
    # Generate compliance report
    report = report_director.construct_evaluation_report(claim, extracted_info)
    
    # Check for duplicate alerts in final_evaluation
    if 'final_evaluation' in report:
        # Print overall compliance status
        overall_compliance = report['final_evaluation'].get('overall_compliance', None)
        print(f"\nOverall Compliance: {overall_compliance}")
        
        # Get alerts
        alerts = report['final_evaluation'].get('alerts', [])
        
        # Print alert details
        print("\nFinal Evaluation Alerts:")
        if alerts:
            for i, alert in enumerate(alerts):
                print(f"\nAlert {i+1}:")
                print(f"  Type: {alert.get('alert_type', 'N/A')}")
                print(f"  Severity: {alert.get('severity', 'N/A')}")
                print(f"  Description: {alert.get('description', 'N/A')}")
                print(f"  Category: {alert.get('alert_category', 'N/A')}")
        else:
            print("  No alerts found in final_evaluation!")
        
        # Check for duplicates
        alert_texts = [alert.get('description', '') for alert in alerts]
        unique_alerts = set(alert_texts)
        
        print(f"\nTotal alerts in final_evaluation: {len(alerts)}")
        print(f"Unique alerts in final_evaluation: {len(unique_alerts)}")
        
        if len(alerts) == len(unique_alerts):
            print("\nSUCCESS: No duplicate alerts found in final_evaluation!")
        else:
            print("\nWARNING: Duplicate alerts found in final_evaluation!")
            # Print the duplicates
            from collections import Counter
            alert_counts = Counter(alert_texts)
            duplicates = {alert: count for alert, count in alert_counts.items() if count > 1}
            print(f"Duplicate alerts: {json.dumps(duplicates, indent=2)}")
    
    # Print the report structure
    print("\nReport Structure:")
    print_report_structure(report)
    
    return report

def print_report_structure(report, indent=0):
    """Print the structure of the report without all the details"""
    if isinstance(report, dict):
        for key, value in report.items():
            if isinstance(value, (dict, list)):
                print("  " * indent + f"{key}:")
                print_report_structure(value, indent + 1)
            else:
                if key in ['alert_text', 'title', 'name']:
                    print("  " * indent + f"{key}: {value}")
                else:
                    print("  " * indent + f"{key}: [...]")
    elif isinstance(report, list):
        if report and isinstance(report[0], dict):
            print("  " * indent + f"[{len(report)} items]")
            if len(report) > 0:
                print_report_structure(report[0], indent + 1)
        else:
            print("  " * indent + f"{report}")

if __name__ == "__main__":
    test_brookstone_report()