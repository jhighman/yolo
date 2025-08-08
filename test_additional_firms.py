import json
import logging
from services.firm_services import FirmServicesFacade
from evaluation.firm_evaluation_report_director import FirmEvaluationReportDirector
from evaluation.firm_evaluation_report_builder import FirmEvaluationReportBuilder

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_firm_report(firm_name, crd_number):
    """Test generating a compliance report for a specific firm"""
    print(f"\nGenerating compliance report for {firm_name} (CRD #{crd_number})")
    
    # Initialize services
    firm_services = FirmServicesFacade()
    
    # Get firm details
    subject_id = "TEST_ADDITIONAL_FIRMS"
    firm_details = firm_services.get_firm_details(subject_id, crd_number)
    
    if firm_details is None:
        print(f"\nFirm not found: {firm_name} (CRD #{crd_number})!")
        return None
    
    # Create a reference ID for the report
    reference_id = f"TEST-{crd_number}"
    
    # Initialize the builder and director
    report_builder = FirmEvaluationReportBuilder(reference_id)
    report_director = FirmEvaluationReportDirector(report_builder)
    
    print(f"\nFirm Status: {firm_details.get('firm_status', 'UNKNOWN').upper()}")
    print(f"\nStatus Message: {firm_details.get('status_message', 'N/A')}")
    
    # Create a claim dictionary
    claim = {
        "business_ref": f"TEST-{crd_number}",
        "business_name": firm_name,
        "organization_crd": crd_number
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
    
    # Check for alerts in final_evaluation
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
    
    return report

if __name__ == "__main__":
    # Test the firms from the feedback
    test_firm_report("Gordon Financial", "174196")
    test_firm_report("Gordon Dyal & Co., LLC", "284175")
    
    # Also test the original case for comparison
    test_firm_report("BROOKSTONE SECURITIES, INC", "29116")