import os
import sys
import json
import logging
import time
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent))

# Import the updated ADV processing agent
from agents.adv_processing_agent import ADVProcessingAgent

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_large_pdf_processing():
    """Test the updated ADV processing functionality with a large PDF."""
    
    # Initialize the ADV Processing Agent
    adv_agent = ADVProcessingAgent(cache_dir="cache")
    
    # Test parameters
    subject_id = "test-subject"
    crd_number = "25853"  # Using the large PDF file
    
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
    
    # Extract AUM information with increased page limit
    logger.info("Extracting AUM information from large PDF (processing all pages)")
    start_time = time.time()
    
    # First, extract text with increased page limit
    logger.info("Extracting text from all 80 pages")
    aum_text = adv_agent.extract_aum_text(pdf_path, max_pages=80)
    
    # Then use the extracted text to get AUM info
    logger.info("Analyzing extracted text with OpenAI")
    aum_info = adv_agent.extract_aum_info(pdf_path, aum_text=aum_text)
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

if __name__ == "__main__":
    logger.info("Starting large PDF processing test")
    
    # Test the large PDF processing
    start_time = time.time()
    aum_info = test_large_pdf_processing()
    total_time = time.time() - start_time
    
    logger.info(f"Large PDF processing test completed in {total_time:.2f} seconds")