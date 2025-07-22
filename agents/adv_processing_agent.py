"""
adv_processing_agent.py

This module defines the ADVProcessingAgent class for downloading and processing
ADV PDF files from the SEC for financial firms.
"""

import os
import logging
import requests
import json
import re
from pathlib import Path
import sys
from typing import Dict, Any, Optional, Tuple
from dotenv import load_dotenv
import PyPDF2
from openai import OpenAI

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from utils.logging_config import setup_logging

# Initialize logging
loggers = setup_logging(debug=True)
logger = loggers.get('adv_processing_agent', logging.getLogger(__name__))

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    logger.warning("OpenAI API key not found in environment variables")

class ADVProcessingAgent:
    """Agent for downloading and processing ADV PDF files from the SEC."""
    
    def __init__(self, cache_dir: str = "cache"):
        """Initialize the ADV Processing Agent.
        
        Args:
            cache_dir: Directory to store cached files
        """
        self.cache_dir = cache_dir
        self.base_url = "https://reports.adviserinfo.sec.gov/reports/ADV"
        self.openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else None
        logger.debug("ADVProcessingAgent initialized")
    
    def get_cache_path(self, subject_id: str, crd_number: str) -> str:
        """Get the path to the cache directory for a specific subject and CRD number.
        
        Args:
            subject_id: The ID of the subject/client making the request
            crd_number: The firm's CRD number
            
        Returns:
            Path to the cache directory
        """
        return os.path.join(self.cache_dir, subject_id, "ADV_Processing_Agent", f"crd_{crd_number}")
    
    def check_adv_pdf_exists(self, subject_id: str, crd_number: str) -> bool:
        """Check if the ADV PDF file already exists in the cache.
        
        Args:
            subject_id: The ID of the subject/client making the request
            crd_number: The firm's CRD number
            
        Returns:
            True if the file exists, False otherwise
        """
        cache_path = self.get_cache_path(subject_id, crd_number)
        pdf_path = os.path.join(cache_path, "adv.pdf")
        return os.path.exists(pdf_path)
    
    def download_adv_pdf(self, subject_id: str, crd_number: str) -> Tuple[bool, Optional[str]]:
        """Download the ADV PDF file for a firm.
        
        Args:
            subject_id: The ID of the subject/client making the request
            crd_number: The firm's CRD number
            
        Returns:
            Tuple of (success, error_message)
        """
        # Check if the file already exists in the cache
        if self.check_adv_pdf_exists(subject_id, crd_number):
            logger.info(f"ADV PDF for CRD {crd_number} already exists in cache")
            return True, None
        
        # Create the cache directory if it doesn't exist
        cache_path = self.get_cache_path(subject_id, crd_number)
        os.makedirs(cache_path, exist_ok=True)
        
        # Construct the URL for the ADV PDF
        url = f"{self.base_url}/{crd_number}/PDF/{crd_number}.pdf"
        pdf_path = os.path.join(cache_path, "adv.pdf")
        
        try:
            logger.info(f"Downloading ADV PDF for CRD {crd_number} from {url}")
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                # Save the PDF to the cache
                with open(pdf_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"Successfully downloaded ADV PDF for CRD {crd_number}")
                return True, None
            else:
                error_msg = f"Failed to download ADV PDF for CRD {crd_number}: HTTP {response.status_code}"
                logger.error(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Error downloading ADV PDF for CRD {crd_number}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from a PDF file, focusing only on text content and removing images.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Extracted text from the PDF
        """
        try:
            text = ""
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                # Process each page
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    # Extract text from the page
                    page_text = page.extract_text()
                    
                    # Skip pages with very little text (likely image-heavy pages)
                    if len(page_text.strip()) < 50:
                        continue
                    
                    # Clean up the text
                    # Remove excessive whitespace
                    page_text = ' '.join(page_text.split())
                    # Add paragraph breaks for readability
                    page_text = page_text.replace('. ', '.\n')
                    
                    text += page_text + "\n\n"
            
            # Look for Form ADV specific sections that are likely to contain AUM information
            adv_sections = [
                "Item 5 Information About Your Advisory Business",
                "Regulatory Assets Under Management",
                "Assets Under Management"
            ]
            
            # If the text is very large, try to extract only relevant sections
            if len(text) > 100000:
                logger.info(f"PDF text is large ({len(text)} chars), extracting only relevant sections")
                extracted_sections = ""
                
                for section in adv_sections:
                    if section in text:
                        # Find the section start
                        section_start = text.find(section)
                        # Estimate section end (next major section or 10000 chars)
                        next_section_start = float('inf')
                        for next_section in ["Item 6", "Item 7", "Item 8", "Item 9"]:
                            pos = text.find(next_section, section_start + len(section))
                            if pos > section_start and pos < next_section_start:
                                next_section_start = pos
                        
                        # If no next section found, take a reasonable chunk
                        if next_section_start == float('inf'):
                            next_section_start = section_start + 10000
                        
                        # Extract the section with some context
                        section_text = text[max(0, section_start - 500):min(len(text), next_section_start + 500)]
                        extracted_sections += section_text + "\n\n"
                
                # If we found relevant sections, use only those
                if extracted_sections:
                    logger.info("Using extracted relevant sections instead of full PDF text")
                    return extracted_sections
            
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            return ""
    
    def extract_aum_info(self, pdf_path: str) -> Dict[str, Any]:
        """Extract AUM information from the ADV PDF using OpenAI API.
        
        Args:
            pdf_path: Path to the ADV PDF file
            
        Returns:
            Dictionary with extracted AUM information
        """
        if not self.openai_client:
            logger.error("OpenAI client not initialized, cannot extract AUM information")
            return {
                "error": "OpenAI client not initialized",
                "reported_aum": "unknown",
                "aum_range": "unknown",
                "as_of_date": "unknown",
                "aum_type": "unknown"
            }
        
        # Extract text from PDF
        pdf_text = self.extract_text_from_pdf(pdf_path)
        if not pdf_text:
            logger.error("Failed to extract text from PDF")
            return {
                "error": "Failed to extract text from PDF",
                "reported_aum": "unknown",
                "aum_range": "unknown",
                "as_of_date": "unknown",
                "aum_type": "unknown"
            }
        
        # Look for key sections that might contain AUM information
        # Common sections in Form ADV that contain AUM info
        aum_sections = [
            "Item 5 Information About Your Advisory Business - Regulatory Assets Under Management",
            "Item 5.F.(2) Regulatory Assets Under Management",
            "Regulatory Assets Under Management",
            "Assets Under Management",
            "Item 5.F. What is the amount of your regulatory assets under management",
            "Item 5.F.(1) Do you provide continuous and regular supervisory",
            "Item 5.F.(2)(a) Discretionary Amount",
            "Item 5.F.(2)(b) Non-Discretionary Amount",
            "Item 5.F.(3) Total Regulatory Assets Under Management"
        ]
        
        # Try to find and extract relevant sections first
        relevant_text = ""
        most_relevant_section = None
        most_relevant_index = -1
        
        # First, find the most relevant section (prioritize sections with "Regulatory Assets Under Management")
        for section in aum_sections:
            if section in pdf_text:
                section_index = pdf_text.find(section)
                if "Regulatory Assets Under Management" in section and (most_relevant_index == -1 or section_index > most_relevant_index):
                    most_relevant_section = section
                    most_relevant_index = section_index
        
        # If we found a highly relevant section, extract just that section with minimal context
        if most_relevant_section:
            logger.info(f"Found highly relevant section: {most_relevant_section}")
            start_idx = max(0, pdf_text.find(most_relevant_section) - 2000)
            end_idx = min(len(pdf_text), pdf_text.find(most_relevant_section) + 3000)
            relevant_text = pdf_text[start_idx:end_idx]
        else:
            # Otherwise, try to find any of the sections
            for section in aum_sections:
                if section in pdf_text:
                    # Extract the section with minimal context
                    start_idx = max(0, pdf_text.find(section) - 1000)
                    end_idx = min(len(pdf_text), pdf_text.find(section) + 2000)
                    relevant_text += pdf_text[start_idx:end_idx] + "\n\n"
        
        # If we found relevant sections, use those
        if relevant_text:
            logger.info("Found relevant AUM sections in the document")
            text_to_process = relevant_text
        else:
            # Otherwise, take a small part of the document
            # (ADV forms often have important info at the beginning)
            logger.info("No specific AUM sections found, using first part of document")
            text_to_process = pdf_text[:15000]  # First ~3750 tokens
        
        # Ensure we're within token limits (max ~6000 tokens for input to leave room for system prompt and completion)
        max_chars = 24000  # ~6000 tokens
        if len(text_to_process) > max_chars:
            logger.info(f"Truncating text from {len(text_to_process)} to {max_chars} characters")
            text_to_process = text_to_process[:max_chars]
        
        # Estimate tokens (rough approximation: 1 token ≈ 4 chars)
        estimated_tokens = len(text_to_process) / 4
        logger.info(f"Processing approximately {int(estimated_tokens)} tokens of ADV text")
        
        # Prepare prompt for OpenAI
        prompt = """
You are a financial compliance assistant. Given text from a Form ADV filing, extract the relevant AUM information and return the result as structured JSON. Always use the following schema and explanation structure:

{
  "reported_aum": "<numeric value in USD>",
  "aum_range": "<range if exact value not given, e.g., '$1B–$10B'>",
  "as_of_date": "<YYYY-MM-DD or 'unknown'>",
  "aum_type": "<'discretionary' | 'non-discretionary' | 'both' | 'unknown'>",
  "source_section": "<quoted excerpt from Form ADV>",
  "compliance_rationale": "<brief reason why this AUM must be disclosed and tracked>",
  "registration_implication": "<SEC registration threshold status, e.g., 'above $110M, SEC-registered'>",
  "update_trigger": "<reason this update was filed, e.g., 'Annual amendment', 'Material change in AUM'>"
}

Focus on finding the most accurate and up-to-date AUM information in the document. Look for sections related to "Regulatory Assets Under Management" or similar terms. If you can't find exact values, provide the best estimate or range based on the available information.

Now extract this information from the following Form ADV:

"""
        
        try:
            # Call OpenAI API with retry logic for rate limits
            max_retries = 2
            retry_count = 0
            
            while retry_count <= max_retries:
                try:
                    logger.info(f"Calling OpenAI API (attempt {retry_count + 1})")
                    response = self.openai_client.chat.completions.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": "You are a financial compliance assistant."},
                            {"role": "user", "content": prompt + text_to_process}
                        ],
                        temperature=0.1,
                        max_tokens=1000
                    )
                    break  # If successful, exit the retry loop
                except Exception as e:
                    retry_count += 1
                    if "rate limit" in str(e).lower() and retry_count <= max_retries:
                        # If it's a rate limit error and we have retries left
                        logger.warning(f"Rate limit error, retrying ({retry_count}/{max_retries})")
                        # If we hit rate limits, try with an even smaller chunk
                        if len(text_to_process) > 15000:
                            text_to_process = text_to_process[:15000]
                            logger.info(f"Reduced text size to {len(text_to_process)} characters")
                    else:
                        # If it's not a rate limit error or we're out of retries, re-raise
                        raise
            
            # Extract JSON from response
            response_text = response.choices[0].message.content if response and response.choices else None
            
            # Try to parse JSON from the response
            try:
                if response_text:
                    # Find JSON in the response (it might be surrounded by markdown code blocks)
                    # First try to find JSON in code blocks
                    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
                    if json_match:
                        json_str = json_match.group(1)
                    else:
                        # Otherwise look for JSON object directly
                        json_start = response_text.find('{')
                        json_end = response_text.rfind('}') + 1
                        if json_start >= 0 and json_end > json_start:
                            json_str = response_text[json_start:json_end]
                        else:
                            raise ValueError("No JSON found in response")
                    
                    aum_info = json.loads(json_str)
                    
                    # Ensure all required fields are present
                    required_fields = [
                        "reported_aum", "aum_range", "as_of_date", "aum_type",
                        "source_section", "compliance_rationale",
                        "registration_implication", "update_trigger"
                    ]
                    
                    for field in required_fields:
                        if field not in aum_info:
                            logger.warning(f"Missing field in OpenAI response: {field}")
                            aum_info[field] = "unknown"
                    
                    return aum_info
                
                # If we couldn't extract JSON, return an error
                logger.error("Could not find JSON in OpenAI response")
                return {
                    "error": "Could not find JSON in OpenAI response",
                    "reported_aum": "unknown",
                    "aum_range": "unknown",
                    "as_of_date": "unknown",
                    "aum_type": "unknown",
                    "source_section": "unknown",
                    "compliance_rationale": "unknown",
                    "registration_implication": "unknown",
                    "update_trigger": "unknown"
                }
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON from OpenAI response: {str(e)}")
                return {
                    "error": f"Error parsing JSON from OpenAI response: {str(e)}",
                    "reported_aum": "unknown",
                    "aum_range": "unknown",
                    "as_of_date": "unknown",
                    "aum_type": "unknown",
                    "source_section": "unknown",
                    "compliance_rationale": "unknown",
                    "registration_implication": "unknown",
                    "update_trigger": "unknown"
                }
            except ValueError as e:
                logger.error(f"Error extracting JSON from OpenAI response: {str(e)}")
                return {
                    "error": f"Error extracting JSON from OpenAI response: {str(e)}",
                    "reported_aum": "unknown",
                    "aum_range": "unknown",
                    "as_of_date": "unknown",
                    "aum_type": "unknown",
                    "source_section": "unknown",
                    "compliance_rationale": "unknown",
                    "registration_implication": "unknown",
                    "update_trigger": "unknown"
                }
                
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            return {
                "error": f"Error calling OpenAI API: {str(e)}",
                "reported_aum": "unknown",
                "aum_range": "unknown",
                "as_of_date": "unknown",
                "aum_type": "unknown",
                "source_section": "unknown",
                "compliance_rationale": "unknown",
                "registration_implication": "unknown",
                "update_trigger": "unknown"
            }
    
    def process_adv(self, subject_id: str, crd_number: str, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process the ADV for a firm and return evaluation results.
        
        Args:
            subject_id: The ID of the subject/client making the request
            crd_number: The firm's CRD number
            entity_data: Dictionary containing entity information
            
        Returns:
            Dictionary with evaluation results
        """
        # Check if the entity has an ADV PDF
        has_adv_pdf = entity_data.get("has_adv_pdf", False)
        
        if not has_adv_pdf:
            logger.info(f"Entity with CRD {crd_number} does not have an ADV PDF")
            return {
                "compliance": False,
                "compliance_explanation": "No ADV filing available for this entity",
                "adv_status": "not_available",
                "alerts": [{
                    "alert_type": "NoADVFiling",
                    "severity": "HIGH",
                    "description": "No ADV filing available for this entity",
                    "metadata": {
                        "crd_number": crd_number,
                        "firm_name": entity_data.get("firm_name", "Unknown")
                    }
                }]
            }
        
        # Try to download the ADV PDF
        success, error_message = self.download_adv_pdf(subject_id, crd_number)
        
        if not success:
            logger.warning(f"Failed to download ADV PDF for CRD {crd_number}: {error_message}")
            return {
                "compliance": False,
                "compliance_explanation": f"Failed to retrieve ADV filing: {error_message}",
                "adv_status": "download_failed",
                "alerts": [{
                    "alert_type": "ADVDownloadFailed",
                    "severity": "MEDIUM",
                    "description": f"Failed to download ADV filing: {error_message}",
                    "metadata": {
                        "crd_number": crd_number,
                        "firm_name": entity_data.get("firm_name", "Unknown"),
                        "error": error_message
                    }
                }]
            }
        
        # ADV PDF was successfully downloaded or already existed in cache
        logger.info(f"ADV PDF for CRD {crd_number} is available")
        
        # Get the path to the ADV PDF
        cache_path = self.get_cache_path(subject_id, crd_number)
        pdf_path = os.path.join(cache_path, "adv.pdf")
        
        # Extract AUM information from the ADV PDF
        aum_info = self.extract_aum_info(pdf_path)
        
        # Save AUM information to JSON file
        json_path = os.path.join(cache_path, "adv.json")
        try:
            with open(json_path, 'w') as f:
                json.dump(aum_info, f, indent=2)
            logger.info(f"Saved AUM information to {json_path}")
        except Exception as e:
            logger.error(f"Error saving AUM information to JSON: {str(e)}")
        
        # Create evaluation result
        result = {
            "compliance": True,
            "compliance_explanation": "ADV filing is available and has been retrieved",
            "adv_status": "available",
            "adv_path": pdf_path,
            "adv_json_path": json_path,
            "aum_info": aum_info,
            "alerts": []
        }
        
        # Add alert if there was an error extracting AUM information
        if "error" in aum_info:
            result["alerts"].append({
                "alert_type": "AUMExtractionFailed",
                "severity": "LOW",
                "description": f"Failed to extract AUM information: {aum_info['error']}",
                "metadata": {
                    "crd_number": crd_number,
                    "firm_name": entity_data.get("firm_name", "Unknown"),
                    "error": aum_info["error"]
                }
            })
        
        return result

# Singleton instance for use throughout the application
adv_processing_agent = ADVProcessingAgent()

def process_adv(subject_id: str, crd_number: str, entity_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process the ADV for a firm and return evaluation results.
    
    This is a convenience function that uses the singleton instance of ADVProcessingAgent.
    
    Args:
        subject_id: The ID of the subject/client making the request
        crd_number: The firm's CRD number
        entity_data: Dictionary containing entity information
        
    Returns:
        Dictionary with evaluation results
    """
    return adv_processing_agent.process_adv(subject_id, crd_number, entity_data)