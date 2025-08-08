import json
import logging
import os
import sys
from pathlib import Path

# Add parent directory to Python path to import evaluation module
sys.path.append(str(Path(__file__).parent))

from evaluation.firm_evaluation_processor import evaluate_registration_status

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_registration_status')

def load_json_file(file_path):
    """Load a JSON file and return its contents."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        return None

def test_registration_status_evaluation():
    """Test the evaluate_registration_status function with real data."""
    
    # Define the cache directory
    cache_dir = "cache"
    
    # List of entity IDs to test
    entity_ids = ["EN-013069", "EN-013098", "EN-013111", "EN-013134"]
    
    for entity_id in entity_ids:
        logger.info(f"Testing entity {entity_id}")
        
        # Try to load the compliance report
        report_path = os.path.join(cache_dir, entity_id, f"FirmComplianceReport_{entity_id}_v1_20250706.json")
        if os.path.exists(report_path):
            report_data = load_json_file(report_path)
            if report_data:
                logger.info(f"Found compliance report for {entity_id}")
                
                # Extract business_info from the report
                business_info = report_data.get("business_info", {})
                
                # Check if there's a CRD number
                crd_number = business_info.get("crd_number")
                if crd_number:
                    logger.info(f"CRD number for {entity_id}: {crd_number}")
                    
                    # Look for SEC search results
                    sec_search_path = os.path.join(
                        cache_dir, 
                        entity_id, 
                        "SEC_FirmIAPD_Agent", 
                        "search_firm_by_crd", 
                        f"search_crd_{crd_number}", 
                        f"SEC_FirmIAPD_Agent_search_crd_{crd_number}_search_firm_by_crd_20250706.json"
                    )
                    
                    if os.path.exists(sec_search_path):
                        sec_search_data = load_json_file(sec_search_path)
                        if sec_search_data:
                            logger.info(f"Found SEC search data for {entity_id}")
                            
                            # Add SEC search result to business_info for testing
                            business_info["sec_search_result"] = sec_search_data
                    
                    # Look for FINRA search results
                    finra_search_path = os.path.join(
                        cache_dir, 
                        entity_id, 
                        "FINRA_FirmBrokerCheck_Agent", 
                        "search_firm_by_crd", 
                        f"search_crd_{crd_number}", 
                        f"FINRA_FirmBrokerCheck_Agent_search_crd_{crd_number}_search_firm_by_crd_20250706.json"
                    )
                    
                    if os.path.exists(finra_search_path):
                        finra_search_data = load_json_file(finra_search_path)
                        if finra_search_data:
                            logger.info(f"Found FINRA search data for {entity_id}")
                            
                            # Add FINRA search result to business_info for testing
                            business_info["finra_search_result"] = finra_search_data
                
                # Now test the evaluate_registration_status function
                logger.info(f"Testing evaluate_registration_status for {entity_id}")
                is_compliant, explanation, alerts = evaluate_registration_status(business_info)
                
                # Log the result and any alerts
                logger.info(f"Registration status evaluation result for {entity_id}: {is_compliant}")
                logger.info(f"Explanation: {explanation}")
                if alerts:
                    logger.info(f"Alerts for {entity_id}:")
                    for alert in alerts:
                        logger.info(f"  - {alert}")
                
                # Check if firm_ia_scope was found and where
                if "firm_ia_scope" in business_info:
                    logger.info(f"firm_ia_scope found in main business_info: {business_info['firm_ia_scope']}")
                elif "sec_search_result" in business_info and "firm_ia_scope" in business_info["sec_search_result"]:
                    logger.info(f"firm_ia_scope found in sec_search_result: {business_info['sec_search_result']['firm_ia_scope']}")
                elif "finra_search_result" in business_info and "firm_ia_scope" in business_info["finra_search_result"]:
                    logger.info(f"firm_ia_scope found in finra_search_result: {business_info['finra_search_result']['firm_ia_scope']}")
                else:
                    logger.warning(f"firm_ia_scope not found for {entity_id}")
                
                # Check registration_status
                if "registration_status" in business_info:
                    logger.info(f"registration_status in main business_info: {business_info['registration_status']}")
                else:
                    logger.warning(f"registration_status not found for {entity_id}")
                
                logger.info("-" * 50)
            else:
                logger.warning(f"Could not load compliance report for {entity_id}")
        else:
            logger.warning(f"No compliance report found for {entity_id}")

if __name__ == "__main__":
    test_registration_status_evaluation()