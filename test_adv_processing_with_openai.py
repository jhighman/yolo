import os
import sys
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent))

# Import the ADV processing agent
from agents.adv_processing_agent import ADVProcessingAgent

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_enhanced_adv_processing():
    """Test the enhanced ADV processing functionality with a real PDF."""
    
    # Initialize the ADV Processing Agent
    adv_agent = ADVProcessingAgent(cache_dir="cache")
    
    # Test parameters
    subject_id = "test-subject"
    crd_number = "174346"  # Using a smaller 1MB PDF file
    
    # Create cache directory if it doesn't exist
    cache_path = adv_agent.get_cache_path(subject_id, crd_number)
    os.makedirs(cache_path, exist_ok=True)
    
    # Check if the PDF already exists
    pdf_path = os.path.join(cache_path, "adv.pdf")
    if not os.path.exists(pdf_path):
        # Download the ADV PDF
        logger.info(f"Downloading ADV PDF for CRD {crd_number}")
        success, error_message = adv_agent.download_adv_pdf(subject_id, crd_number)
        
        if not success:
            logger.error(f"Failed to download ADV PDF: {error_message}")
            return
    else:
        logger.info(f"Using existing ADV PDF for CRD {crd_number}")
    
    # Extract AUM information
    logger.info("Extracting AUM information using enhanced parser")
    aum_info = adv_agent.extract_aum_info(pdf_path)
    
    # Save the results to a JSON file
    output_path = os.path.join(cache_path, "enhanced_aum_info.json")
    with open(output_path, 'w') as f:
        json.dump(aum_info, f, indent=2)
    
    # Print the results
    logger.info(f"AUM information extracted and saved to {output_path}")
    logger.info(f"Reported AUM: {aum_info.get('reported_aum', 'unknown')}")
    logger.info(f"AUM Range: {aum_info.get('aum_range', 'unknown')}")
    logger.info(f"As of Date: {aum_info.get('as_of_date', 'unknown')}")
    logger.info(f"AUM Type: {aum_info.get('aum_type', 'unknown')}")
    
    # Return the results
    return aum_info

def compare_extraction_methods():
    """Compare the original and enhanced extraction methods."""
    
    # Initialize the ADV Processing Agent
    adv_agent = ADVProcessingAgent(cache_dir="cache")
    
    # Test parameters
    subject_id = "test-subject"
    crd_number = "174346"  # Using a smaller 1MB PDF file
    
    # Get the path to the ADV PDF
    cache_path = adv_agent.get_cache_path(subject_id, crd_number)
    pdf_path = os.path.join(cache_path, "adv.pdf")
    
    # Ensure the PDF exists
    if not os.path.exists(pdf_path):
        logger.error(f"ADV PDF not found at {pdf_path}")
        return
    
    # Extract text using the enhanced method
    logger.info("Extracting text using enhanced method")
    enhanced_text = adv_agent.extract_aum_text(pdf_path)
    
    # Save the extracted text to files for comparison
    with open(os.path.join(cache_path, "enhanced_text.txt"), 'w') as f:
        f.write(enhanced_text)
    
    # Log the results
    logger.info(f"Enhanced text length: {len(enhanced_text)} characters")
    logger.info(f"Enhanced text tokens (est.): {len(enhanced_text) // 4}")
    
    # Return the results
    return {
        "enhanced_text_length": len(enhanced_text),
        "enhanced_text_tokens": len(enhanced_text) // 4
    }

if __name__ == "__main__":
    logger.info("Starting ADV processing test")
    
    # Test the enhanced extraction
    aum_info = test_enhanced_adv_processing()
    
    # Compare extraction methods
    comparison = compare_extraction_methods()
    
    logger.info("ADV processing test completed")