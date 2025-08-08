import os
import sys
import json
import logging
import time
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent))

# Import the simplified ADV processing agent
from agents.adv_processing_agent_simplified import ADVProcessingAgentSimplified

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Disable verbose pdfminer logging
logging.getLogger('pdfminer').setLevel(logging.ERROR)

def test_simplified_adv_processing_with_openai():
    """Test the simplified ADV processing functionality with OpenAI API."""
    
    # Initialize the simplified ADV Processing Agent
    adv_agent = ADVProcessingAgentSimplified(cache_dir="cache")
    
    # Test parameters
    subject_id = "test-subject"
    crd_number = "174346"  # Using a smaller 1MB PDF file
    
    # Create cache directory if it doesn't exist
    cache_path = adv_agent.get_cache_path(subject_id, crd_number)
    os.makedirs(cache_path, exist_ok=True)
    
    # Check if the PDF already exists
    pdf_path = os.path.join(cache_path, f"adv_{crd_number}.pdf")
    if not os.path.exists(pdf_path):
        # Download the ADV PDF
        logger.info(f"Downloading ADV PDF for CRD {crd_number}")
        success, error_message = adv_agent.download_adv_pdf(subject_id, crd_number)
        
        if not success:
            logger.error(f"Failed to download ADV PDF: {error_message}")
            return
    else:
        logger.info(f"Using existing ADV PDF for CRD {crd_number}")
    
    # Extract AUM information using OpenAI API
    if adv_agent.openai_client:
        logger.info("Extracting AUM information using OpenAI API (single attempt)")
        start_time = time.time()
        aum_info = adv_agent.extract_aum_info(pdf_path)
        extraction_time = time.time() - start_time
        logger.info(f"AUM extraction completed in {extraction_time:.2f} seconds")
        
        # Save the results to a JSON file
        output_path = os.path.join(cache_path, f"adv_{crd_number}_test_result.json")
        with open(output_path, 'w') as f:
            json.dump(aum_info, f, indent=2)
        
        # Print the results
        logger.info(f"AUM information extracted and saved to {output_path}")
        logger.info(f"Reported AUM: {aum_info.get('reported_aum', 'unknown')}")
        logger.info(f"AUM Range: {aum_info.get('aum_range', 'unknown')}")
        logger.info(f"As of Date: {aum_info.get('as_of_date', 'unknown')}")
        logger.info(f"AUM Type: {aum_info.get('aum_type', 'unknown')}")
        
        return aum_info
    else:
        logger.warning("OpenAI client not initialized, skipping AUM extraction")
        return None

if __name__ == "__main__":
    logger.info("Starting simplified ADV processing test with OpenAI")
    
    # Test the simplified extraction with OpenAI
    start_time = time.time()
    aum_info = test_simplified_adv_processing_with_openai()
    total_time = time.time() - start_time
    
    logger.info(f"Simplified ADV processing test with OpenAI completed in {total_time:.2f} seconds")