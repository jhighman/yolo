import os
import json
import logging
from agents.adv_processing_agent import ADVProcessingAgent

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_adv_processing():
    """Test the ADV processing agent with a sample CRD number."""
    
    # Initialize the ADV processing agent
    agent = ADVProcessingAgent(cache_dir="cache")
    
    # Test parameters
    subject_id = "TEST-001"
    crd_number = "8174"  # Using a known CRD number (Morgan Stanley)
    
    # Create a mock entity data dictionary
    entity_data = {
        "has_adv_pdf": True,
        "firm_name": "Test Firm",
        "crd_number": crd_number
    }
    
    logger.info(f"Testing ADV processing for CRD {crd_number}")
    
    # Step 1: Download the ADV PDF
    success, error_message = agent.download_adv_pdf(subject_id, crd_number)
    if not success:
        logger.error(f"Failed to download ADV PDF: {error_message}")
        return
    
    logger.info(f"Successfully downloaded or found ADV PDF for CRD {crd_number}")
    
    # Get the path to the ADV PDF
    cache_path = agent.get_cache_path(subject_id, crd_number)
    pdf_path = os.path.join(cache_path, f"adv-{crd_number}.pdf")
    
    # Step 2: Extract AUM information
    logger.info("Extracting AUM information...")
    aum_info = agent.extract_aum_info(pdf_path, force_extract=True)
    
    # Step 3: Extract disclosure information
    logger.info("Extracting disclosure information...")
    disclosure_info = agent.extract_disclosure_info(pdf_path, force_extract=True)
    
    # Step 4: Process ADV to create combined result
    logger.info("Processing ADV to create combined result...")
    result = agent.process_adv(subject_id, crd_number, entity_data, force_extract=True)
    
    # Step 5: Print results
    logger.info("Test completed. Results:")
    
    logger.info("\nAUM Information:")
    print(json.dumps(aum_info, indent=2))
    
    logger.info("\nDisclosure Information:")
    print(json.dumps(disclosure_info, indent=2))
    
    logger.info("\nCombined Result:")
    combined_result_path = os.path.join(cache_path, f"adv-{crd_number}-result.json")
    if os.path.exists(combined_result_path):
        with open(combined_result_path, 'r') as f:
            combined_result = json.load(f)
        print(json.dumps(combined_result, indent=2))
    else:
        logger.error(f"Combined result file not found: {combined_result_path}")
    
    # Check if the extraction was successful
    if "error" in aum_info:
        logger.error(f"AUM extraction error: {aum_info['error']}")
    else:
        logger.info(f"AUM extraction successful: {aum_info.get('reported_aum', 'unknown')} as of {aum_info.get('as_of_date', 'unknown')}")
    
    if "error" in disclosure_info:
        logger.error(f"Disclosure extraction error: {disclosure_info['error']}")
    else:
        logger.info(f"Disclosure extraction successful: {disclosure_info.get('disclosure_count', 0)} disclosures found")
    
    # Check if the cached files were created
    aum_text_path = os.path.join(cache_path, f"adv-{crd_number}-aum-source.txt")
    disclosure_text_path = os.path.join(cache_path, f"adv-{crd_number}-disclosure-source.txt")
    aum_gpt_path = os.path.join(cache_path, f"adv-{crd_number}-aum-gpt.json")
    disclosure_gpt_path = os.path.join(cache_path, f"adv-{crd_number}-disclosure-gpt.json")
    
    logger.info("\nChecking cached files:")
    logger.info(f"AUM text file exists: {os.path.exists(aum_text_path)}")
    logger.info(f"Disclosure text file exists: {os.path.exists(disclosure_text_path)}")
    logger.info(f"AUM GPT result file exists: {os.path.exists(aum_gpt_path)}")
    logger.info(f"Disclosure GPT result file exists: {os.path.exists(disclosure_gpt_path)}")
    logger.info(f"Combined result file exists: {os.path.exists(combined_result_path)}")

if __name__ == "__main__":
    test_adv_processing()