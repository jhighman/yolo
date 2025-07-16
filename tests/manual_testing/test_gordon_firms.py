import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from services.firm_services import FirmServicesFacade
from evaluation.firm_evaluation_report_director import FirmEvaluationReportDirector
from evaluation.firm_evaluation_report_builder import FirmEvaluationReportBuilder

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_firm(crd_number, firm_name):
    """Test generating a compliance report for a firm with the given CRD number."""
    print(f"\nGenerating compliance report for {firm_name} (CRD #{crd_number})")
    
    # Initialize services
    firm_services = FirmServicesFacade()
    
    # Get firm details
    subject_id = f"TEST_{crd_number}"
    firm_details = firm_services.get_firm_details(subject_id, crd_number)
    
    # Print firm status information
    if firm_details and 'firm_status' in firm_details:
        print(f"\nFirm Status: {firm_details['firm_status'].upper()}")
        
    if firm_details and 'status_message' in firm_details:
        print(f"\nStatus Message: {firm_details['status_message']}")
    
    # Create a reference ID for the report
    reference_id = f"TEST_REF_{crd_number}"
    
    # Initialize the builder and director
    report_builder = FirmEvaluationReportBuilder(reference_id)
    report_director = FirmEvaluationReportDirector(report_builder)
    
    # Create a claim dictionary
    claim = {
        "business_ref": f"TEST_BIZ_{crd_number}",
        "business_name": firm_name,
        "organization_crd": crd_number,
        "referenceId": reference_id,
        "crdNumber": crd_number,
        "entityName": firm_name
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
    
    # Generate evaluation report
    report = report_director.construct_evaluation_report(claim, extracted_info)
    
    # Check overall compliance
    print(f"\nOverall Compliance: {report['final_evaluation']['overall_compliance']}")
    
    # Print alerts from final evaluation
    print("\nFinal Evaluation Alerts:")
    if 'alerts' in report['final_evaluation'] and report['final_evaluation']['alerts']:
        for i, alert in enumerate(report['final_evaluation']['alerts'], 1):
            print(f"\nAlert {i}:")
            print(f"  Type: {alert.get('alert_type', '')}")
            print(f"  Severity: {alert.get('severity', '')}")
            print(f"  Description: {alert.get('description', '')}")
            print(f"  Category: {alert.get('alert_category', '')}")
            
            # Print metadata if available
            if 'metadata' in alert and alert['metadata']:
                print("\n  Metadata:")
                for key, value in alert['metadata'].items():
                    print(f"    {key}: {value}")
    else:
        print("  No alerts found in final evaluation.")
    
    # Check for duplicate alerts
    if 'alerts' in report['final_evaluation']:
        alerts = report['final_evaluation']['alerts']
        unique_alerts = []
        for alert in alerts:
            # Create a tuple of key alert properties to check for duplicates
            alert_key = (
                alert.get('alert_type', ''),
                alert.get('description', ''),
                alert.get('severity', '')
            )
            if alert_key not in unique_alerts:
                unique_alerts.append(alert_key)
        
        print(f"\nTotal alerts in final_evaluation: {len(alerts)}")
        print(f"Unique alerts in final_evaluation: {len(unique_alerts)}")
        
        if len(alerts) == len(unique_alerts):
            print("\nSUCCESS: No duplicate alerts found in final_evaluation!")
        else:
            print("\nWARNING: Duplicate alerts found in final_evaluation!")
    
    # Print report structure (keys only, not values)
    print("\nReport Structure:")
    def print_structure(obj, prefix=''):
        if isinstance(obj, dict):
            for key in obj:
                if isinstance(obj[key], (dict, list)):
                    print(f"{prefix}{key}:")
                    print_structure(obj[key], prefix + '  ')
                else:
                    print(f"{prefix}{key}: [...]")
        elif isinstance(obj, list):
            print(f"{prefix}[{len(obj)} items]")
            if obj and isinstance(obj[0], (dict, list)):
                print_structure(obj[0], prefix + '  ')
    
    print_structure(report)
    
    return report

if __name__ == "__main__":
    # Test Gordon Financial
    test_firm("104", "Gordon Financial")
    
    # Test Gordon Dyal & Co., LLC
    test_firm("153518", "Gordon Dyal & Co., LLC")