import os
import sys
import json
import logging
import time
import signal
from pathlib import Path
from dotenv import load_dotenv
from contextlib import contextmanager
from functools import partial

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent))

# Import the ADV processing agent
from agents.adv_processing_agent import ADVProcessingAgent

# Load environment variables
load_dotenv()

# Configure logging - reduce verbosity
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Disable verbose pdfminer logging
logging.getLogger('pdfminer').setLevel(logging.ERROR)

class TimeoutException(Exception):
    """Exception raised when a function times out."""
    pass

@contextmanager
def timeout(seconds, error_message="Function call timed out"):
    """Context manager for timing out function calls."""
    def handler(signum, frame):
        raise TimeoutException(error_message)
    
    # Set the timeout handler
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        # Cancel the timeout
        signal.alarm(0)

def extract_text_with_timeout(pdf_path, timeout_seconds=60):
    """Extract text from PDF with a timeout."""
    try:
        import PyPDF2
        
        logger.info(f"Extracting text from {pdf_path} using PyPDF2 (timeout: {timeout_seconds}s)")
        
        with timeout(timeout_seconds, f"PDF text extraction timed out after {timeout_seconds} seconds"):
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                
                # Get total number of pages
                total_pages = len(reader.pages)
                logger.info(f"PDF has {total_pages} pages")
                
                # Process only the first 20 pages or all if less than 20
                pages_to_process = min(20, total_pages)
                logger.info(f"Processing first {pages_to_process} pages")
                
                for i in range(pages_to_process):
                    logger.info(f"Extracting text from page {i+1}/{pages_to_process}")
                    page = reader.pages[i]
                    page_text = page.extract_text() or ""
                    text += page_text + "\n\n"
                
                logger.info(f"Extracted {len(text)} characters from PDF")
                return text
    
    except TimeoutException as e:
        logger.error(f"Timeout during PDF extraction: {str(e)}")
        return "PDF EXTRACTION TIMED OUT - PARTIAL TEXT MAY BE AVAILABLE"
    
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        return ""

def test_optimized_adv_processing():
    """Test the optimized ADV processing functionality with a real PDF."""
    
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
    
    # Extract text using optimized method with timeout
    logger.info("Extracting text using optimized method with timeout")
    start_time = time.time()
    extracted_text = extract_text_with_timeout(pdf_path, timeout_seconds=120)
    extraction_time = time.time() - start_time
    logger.info(f"Text extraction completed in {extraction_time:.2f} seconds")
    
    # Save the extracted text to a file
    text_path = os.path.join(cache_path, "optimized_text.txt")
    with open(text_path, 'w') as f:
        f.write(extracted_text)
    logger.info(f"Saved extracted text to {text_path}")
    
    # Use the ADV agent's regex patterns to find AUM information
    logger.info("Searching for AUM information in extracted text")
    
    # Define precise regex patterns for AUM-relevant sections (copied from ADVProcessingAgent)
    primary_patterns = [
        # Item 5.F - Regulatory Assets Under Management section
        r"Item 5\.F\.(?:.*?\n){0,10}.*?Regulatory Assets Under Management.*?(?=\nItem 6|$)",
        
        # Item 1.Q - Another common location for AUM information
        r"Item 1\.Q\.(?:.*?\n){0,5}.*?assets.*?(\$\d{1,3}(?:,\d{3})*(?:\.\d+)?|\$[a-zA-Z\s]+ to less than \$[a-zA-Z\s]+).*?(?=\nItem 2|$)",
        
        # Specific table patterns that often contain AUM data
        r"(Regulatory Assets Under Management|Total Assets)[\s\S]{0,500}(Discretionary|Non-Discretionary)[\s\S]{0,500}(\$\d{1,3}(?:,\d{3})*(?:\.\d+)?)",
        
        # Schedule D section with AUM information
        r"Schedule D Section (?:5\.F\.|7\.A\.).*?assets under management.*?(?=\nSchedule|$)"
    ]
    
    # Search for AUM information
    import re
    aum_text = ""
    for pattern in primary_patterns:
        matches = re.finditer(pattern, extracted_text, re.DOTALL | re.IGNORECASE)
        for match in matches:
            match_text = match.group(0)
            logger.info(f"Found AUM match: {match_text[:100]}...")
            aum_text += match_text + "\n\n"
    
    # If no matches found, use a simpler approach
    if not aum_text:
        logger.info("No specific AUM sections found, searching for key phrases")
        aum_keywords = [
            r"assets under management",
            r"regulatory assets",
            r"discretionary assets",
            r"non-discretionary assets",
            r"\$[0-9,.]+\s+(?:million|billion|trillion)"
        ]
        
        for keyword in aum_keywords:
            pattern = f"[^\n]+{keyword}[^\n]+"
            matches = re.finditer(pattern, extracted_text, re.IGNORECASE)
            for match in matches:
                aum_text += match.group(0) + "\n\n"
    
    # Save the AUM text to a file
    aum_path = os.path.join(cache_path, "optimized_aum_text.txt")
    with open(aum_path, 'w') as f:
        f.write(aum_text)
    logger.info(f"Saved AUM text to {aum_path}")
    
    # Create a sample JSON file with the extracted information
    # This would normally be generated by ChatGPT, but we're skipping that step
    logger.info("Creating sample AUM info JSON (skipping ChatGPT call)")
    
    # Try to extract some basic information using regex
    aum_info = {
        "reported_aum": "unknown",
        "aum_range": "unknown",
        "as_of_date": "unknown",
        "aum_type": "unknown"
    }
    
    # Look for discretionary AUM
    discretionary_match = re.search(r"Discretionary:.*?\$\s*([\d,]+)", aum_text)
    if discretionary_match:
        aum_info["reported_aum"] = f"${discretionary_match.group(1)}"
        aum_info["aum_type"] = "discretionary"
    
    # Look for AUM range
    range_match = re.search(r"\$([\w\s]+) to less than \$([\w\s]+)", aum_text)
    if range_match:
        aum_info["aum_range"] = f"${range_match.group(1)} to less than ${range_match.group(2)}"
    
    # Save the results to a JSON file
    output_path = os.path.join(cache_path, "optimized_aum_info.json")
    with open(output_path, 'w') as f:
        json.dump(aum_info, f, indent=2)
    
    # Print the results
    logger.info(f"AUM information extracted and saved to {output_path}")
    logger.info(f"Reported AUM: {aum_info.get('reported_aum', 'unknown')}")
    logger.info(f"AUM Range: {aum_info.get('aum_range', 'unknown')}")
    logger.info(f"As of Date: {aum_info.get('as_of_date', 'unknown')}")
    logger.info(f"AUM Type: {aum_info.get('aum_type', 'unknown')}")
    
    # Create a file with the prompt that would be sent to ChatGPT
    prompt = """
Extract the Assets Under Management (AUM) information from the provided text and return a structured JSON response.

Return your response using this JSON schema:
{
  "reported_aum": "<exact numeric value in USD>",
  "aum_range": "<range if exact value not given>",
  "as_of_date": "<date or 'unknown'>",
  "aum_type": "<'discretionary' | 'non-discretionary' | 'both' | 'unknown'>"
}

Text:
""" + aum_text
    
    prompt_path = os.path.join(cache_path, "chatgpt_prompt.txt")
    with open(prompt_path, 'w') as f:
        f.write(prompt)
    logger.info(f"Saved ChatGPT prompt to {prompt_path}")
    
    return aum_info

def compare_extraction_methods():
    """Compare the original and optimized extraction methods."""
    
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
    
    # Extract text using the optimized method
    logger.info("Extracting text using optimized method")
    start_time = time.time()
    optimized_text = extract_text_with_timeout(pdf_path, timeout_seconds=120)
    optimized_time = time.time() - start_time
    
    # Save the extracted text to files for comparison
    with open(os.path.join(cache_path, "optimized_text.txt"), 'w') as f:
        f.write(optimized_text)
    
    # Log the results
    logger.info(f"Optimized method extraction time: {optimized_time:.2f} seconds")
    logger.info(f"Optimized text length: {len(optimized_text)} characters")
    logger.info(f"Optimized text tokens (est.): {len(optimized_text) // 4}")
    
    # Return the results
    return {
        "optimized_extraction_time": optimized_time,
        "optimized_text_length": len(optimized_text),
        "optimized_text_tokens": len(optimized_text) // 4
    }

if __name__ == "__main__":
    logger.info("Starting optimized ADV processing test")
    
    # Test the optimized extraction
    start_time = time.time()
    aum_info = test_optimized_adv_processing()
    
    # Compare extraction methods
    comparison = compare_extraction_methods()
    
    total_time = time.time() - start_time
    logger.info(f"Optimized ADV processing test completed in {total_time:.2f} seconds")