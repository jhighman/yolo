#!/usr/bin/env python3
"""
Script to generate a full compliance report for a firm with CRD 133763.
This script tests the case where a firm should have disclosure alerts but no registration alerts.
"""

import sys
import json
from pathlib import Path
import logging
from datetime import datetime

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent))

from services.firm_services import FirmServicesFacade
from services.firm_business import process_claim
from evaluation.firm_evaluation_processor import evaluate_registration_status
from agents.finra_firm_broker_check_agent import FinraFirmBrokerCheckAgent
from agents.sec_firm_iapd_agent import SECFirmIAPDAgent

# Set up logging
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Generate a full compliance report for firm with CRD 133763 with additional diagnostics."""
    # Create facade
    facade = FirmServicesFacade()
    
    # Search parameters
    subject_id = "test_subject"
    crd_number = "133763"
    
    # Direct API calls to diagnose the issue
    logger.info("Directly testing SEC API for CRD: %s", crd_number)
    sec_agent = SECFirmIAPDAgent(use_mock=False)
    sec_result = sec_agent.search_firm_by_crd(crd_number)
    logger.info("SEC API direct result: %s", json.dumps(sec_result, indent=2, default=str) if sec_result else "No result")
    
    logger.info("Directly testing FINRA API for CRD: %s", crd_number)
    finra_agent = FinraFirmBrokerCheckAgent(use_mock=False)
    finra_result = finra_agent.search_firm_by_crd(crd_number)
    logger.info("FINRA API direct result: %s", json.dumps(finra_result, indent=2, default=str) if finra_result else "No result")
    
    # Search for firm by CRD using the facade
    logger.info("Searching for firm with CRD: %s using facade", crd_number)
    firm_details = facade.search_firm_by_crd(subject_id, crd_number)
    
    if firm_details:
        logger.info("Firm details found: %s", json.dumps(firm_details, indent=2, default=str))
        
        # Create a claim for processing
        claim = {
            "reference_id": f"test-ref-{crd_number}",
            "business_ref": f"BIZ_{crd_number}",
            "business_name": firm_details.get('firm_name', 'Unknown'),
            "organization_crd": crd_number
        }
        
        # Process the claim to generate a compliance report
        logger.info("Generating compliance report for %s (CRD: %s)", firm_details.get('firm_name', 'Unknown'), crd_number)
        report = process_claim(
            claim=claim,
            facade=facade,
            business_ref=claim["business_ref"],
            skip_financials=False,
            skip_legal=False
        )
        
        if report:
            # Add the claim to the report
            report["claim"] = claim
            
            # Add timestamp
            report["generated_at"] = datetime.now().isoformat()
            
            # Save the report to a file
            output_file = f"compliance_report_crd_{crd_number}.json"
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info("Compliance report saved to %s", output_file)
            
            # Evaluate registration status
            logger.info("Evaluating registration status")
            # Extract the entity information from the report for evaluation
            business_info = report.get('entity', {})
            # Add additional fields that might be in basic_result
            if 'basic_result' in report.get('search_evaluation', {}):
                basic_result = report['search_evaluation']['basic_result']
                # Add source information
                business_info['source'] = report.get('search_evaluation', {}).get('source')
                # Add raw_data if available
                if 'raw_data' in basic_result:
                    business_info['raw_data'] = basic_result['raw_data']
            
            is_compliant, explanation, alerts = evaluate_registration_status(business_info)
            
            logger.info("Registration status: %s", "Compliant" if is_compliant else "Non-compliant")
            logger.info("Explanation: %s", explanation)
            
            if alerts:
                logger.info("Alerts:")
                for alert in alerts:
                    logger.info("  - [%s] %s: %s", alert.severity.value, alert.alert_type, alert.description)
                    
                # Verify that we don't have any NoActiveRegistration alerts if the firm should be compliant
                has_no_registration_alert = any(
                    alert.alert_type == "NoActiveRegistration" for alert in alerts
                )
                
                # Check if the firm is registered with SEC or state
                is_sec_registered = business_info.get('is_sec_registered', False)
                is_state_registered = business_info.get('is_state_registered', False)
                
                if is_sec_registered or is_state_registered:
                    # Should be compliant
                    if not has_no_registration_alert:
                        logger.info("✅ TEST PASSED: No alerts for missing registration found")
                    else:
                        logger.error("❌ TEST FAILED: Unexpected alert for no registration found")
                else:
                    # Should be non-compliant
                    if has_no_registration_alert:
                        logger.info("✅ TEST PASSED: Alert for missing registration found")
                    else:
                        logger.error("❌ TEST FAILED: Expected alert for no registration not found")
            else:
                # If there are no alerts, the firm should be compliant
                is_sec_registered = business_info.get('is_sec_registered', False)
                is_state_registered = business_info.get('is_state_registered', False)
                
                if is_sec_registered or is_state_registered:
                    logger.info("✅ TEST PASSED: No alerts found, as expected for a compliant firm")
                else:
                    logger.error("❌ TEST FAILED: Expected alerts for non-compliant firm not found")
            
            # Check status_evaluation in the report
            status_evaluation = report.get('status_evaluation', {})
            is_sec_registered = business_info.get('is_sec_registered', False)
            is_state_registered = business_info.get('is_state_registered', False)
            
            if is_sec_registered or is_state_registered:
                # Should be compliant
                if status_evaluation.get('compliance', False):
                    logger.info("✅ Report correctly shows compliant status")
                else:
                    logger.error("❌ TEST FAILED: Report incorrectly shows non-compliant status")
            else:
                # Should be non-compliant
                if not status_evaluation.get('compliance', True):
                    logger.info("✅ Report correctly shows non-compliant status")
                else:
                    logger.error("❌ TEST FAILED: Report incorrectly shows compliant status")
                
            # Check for NoActiveRegistration alert in status_evaluation
            status_alerts = status_evaluation.get('alerts', [])
            has_no_registration_alert_in_report = any(
                alert.get('alert_type') == "NoActiveRegistration" for alert in status_alerts
            )
            
            if is_sec_registered or is_state_registered:
                # Should be compliant
                if not has_no_registration_alert_in_report:
                    logger.info("✅ Report correctly does not contain NoActiveRegistration alert")
                else:
                    logger.error("❌ TEST FAILED: Report incorrectly contains NoActiveRegistration alert")
            else:
                # Should be non-compliant
                if has_no_registration_alert_in_report:
                    logger.info("✅ Report correctly contains NoActiveRegistration alert")
                else:
                    logger.error("❌ TEST FAILED: Report does not contain NoActiveRegistration alert")
            
            # Check for disclosure alerts
            disclosure_review = report.get('disclosure_review', {})
            disclosure_alerts = disclosure_review.get('alerts', [])
            
            if disclosure_alerts:
                logger.info("Disclosure alerts found:")
                for alert in disclosure_alerts:
                    logger.info("  - [%s] %s: %s",
                               alert.get('severity', 'UNKNOWN'),
                               alert.get('type', 'UNKNOWN'),
                               alert.get('message', 'No message'))
                logger.info("✅ TEST PASSED: Disclosure alerts found as expected")
            else:
                logger.error("❌ TEST FAILED: No disclosure alerts found")
            
            # Print the report
            print(json.dumps(report, indent=2, default=str))
        else:
            logger.error("Failed to generate compliance report")
    else:
        logger.error("No firm found with CRD: %s", crd_number)
        
        # Try searching by name as a fallback
        logger.info("Attempting to search by name as a fallback")
        search_name = "Unknown Firm"  # You might want to replace this with a known name if available
        search_results = facade.search_firm(subject_id, search_name)
        
        if search_results:
            logger.info("Found %d results by name search", len(search_results))
            for idx, result in enumerate(search_results):
                logger.info("Result %d: %s", idx + 1, json.dumps(result, indent=2, default=str))
        else:
            logger.info("No results found by name search")


if __name__ == "__main__":
    main()