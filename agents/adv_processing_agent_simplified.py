import os
import logging
import requests
import json
import re
from pathlib import Path
import sys
from typing import Dict, Any, Optional, Tuple
from dotenv import load_dotenv
import PyPDF2  # Using PyPDF2 instead of pdfplumber
from openai import OpenAI

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from utils.logging_config import setup_logging

# Initialize logging
loggers = setup_logging(debug=False)  # Set debug to False to reduce verbosity
logger = loggers.get('adv_processing_agent', logging.getLogger(__name__))

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    logger.warning("OpenAI API key not found in environment variables")

class ADVProcessingAgentSimplified:
    """Simplified agent for downloading and processing ADV PDF files from the SEC."""
    
    def __init__(self, cache_dir: str = "cache"):
        """Initialize the ADV Processing Agent.
        
        Args:
            cache_dir: Directory to store cached files
        """
        self.cache_dir = cache_dir
        self.base_url = "https://reports.adviserinfo.sec.gov/reports/ADV"
        self.openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else None
        logger.debug("ADVProcessingAgentSimplified initialized")
    
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
    
    def extract_aum_text(self, pdf_path: str, max_pages: int = 20) -> str:
        """Extract text from a PDF file, focusing specifically on AUM-relevant sections.
        
        This enhanced parser uses PyPDF2 instead of pdfplumber for faster extraction.
        It processes only the first max_pages pages to avoid excessive processing time.
        
        Args:
            pdf_path: Path to the PDF file
            max_pages: Maximum number of pages to process
            
        Returns:
            Extracted text containing AUM information
        """
        try:
            logger.info(f"Extracting AUM-relevant text from {pdf_path} (max pages: {max_pages})")
            
            # Extract text using PyPDF2
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                
                # Get total number of pages
                total_pages = len(reader.pages)
                logger.info(f"PDF has {total_pages} pages")
                
                # Process only up to max_pages
                pages_to_process = min(max_pages, total_pages)
                logger.info(f"Processing first {pages_to_process} pages")
                
                for i in range(pages_to_process):
                    logger.info(f"Extracting text from page {i+1}/{pages_to_process}")
                    page = reader.pages[i]
                    page_text = page.extract_text() or ""
                    text += page_text + "\n\n"
            
            logger.debug(f"Extracted {len(text)} characters from PDF")
            
            # Define precise regex patterns for AUM-relevant sections
            primary_patterns = [
                # Item 5.F - Regulatory Assets Under Management section (most common location)
                r"Item 5\.F\.(?:.*?\n){0,10}.*?Regulatory Assets Under Management.*?(?=\nItem 6|$)",
                
                # Item 1.Q - Another common location for AUM information
                r"Item 1\.Q\.(?:.*?\n){0,5}.*?assets.*?(\$\d{1,3}(?:,\d{3})*(?:\.\d+)?|\$[a-zA-Z\s]+ to less than \$[a-zA-Z\s]+).*?(?=\nItem 2|$)",
                
                # Specific table patterns that often contain AUM data
                r"(Regulatory Assets Under Management|Total Assets)[\s\S]{0,500}(Discretionary|Non-Discretionary)[\s\S]{0,500}(\$\d{1,3}(?:,\d{3})*(?:\.\d+)?)",
                
                # Schedule D section with AUM information
                r"Schedule D Section (?:5\.F\.|7\.A\.).*?assets under management.*?(?=\nSchedule|$)"
            ]
            
            # Secondary patterns as fallbacks
            secondary_patterns = [
                r"Regulatory Assets Under Management.*?(?=\nItem 6|$)",
                r"Item 5.*?Information About Your Advisory Business.*?(?=\nItem 6|$)",
                r"assets under management.*?(\$\d{1,3}(?:,\d{3})*(?:\.\d+)?)",
                r"total assets.*?(\$\d{1,3}(?:,\d{3})*(?:\.\d+)?)"
            ]
            
            # Try primary patterns first
            relevant_text = ""
            for pattern in primary_patterns:
                matches = re.finditer(pattern, text, re.DOTALL | re.IGNORECASE)
                for match in matches:
                    match_text = match.group(0)
                    logger.debug(f"Found primary match: {match_text[:100]}...")
                    relevant_text += match_text + "\n\n"
            
            # If primary patterns didn't find anything, try secondary patterns
            if not relevant_text:
                logger.info("No matches found with primary patterns, trying secondary patterns")
                for pattern in secondary_patterns:
                    matches = re.finditer(pattern, text, re.DOTALL | re.IGNORECASE)
                    for match in matches:
                        match_text = match.group(0)
                        logger.debug(f"Found secondary match: {match_text[:100]}...")
                        relevant_text += match_text + "\n\n"
            
            # If no specific sections found, use a targeted approach with key paragraphs
            if not relevant_text:
                logger.info("No specific AUM sections found, extracting key paragraphs")
                # Look for paragraphs containing AUM-related keywords
                aum_keywords = [
                    r"assets under management",
                    r"regulatory assets",
                    r"discretionary assets",
                    r"non-discretionary assets",
                    r"\$[0-9,.]+\s+(?:million|billion|trillion)"
                ]
                
                for keyword in aum_keywords:
                    pattern = f"[^\n]+{keyword}[^\n]+"
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    for match in matches:
                        relevant_text += match.group(0) + "\n\n"
                
                # If still no matches, fall back to first 10,000 characters
                if not relevant_text:
                    logger.warning("No AUM-related content found, using first part of document")
                    relevant_text = text[:10000]
            
            # Ensure text is within token limits (~4,000 tokens ≈ 16,000 chars)
            max_chars = 16000
            if len(relevant_text) > max_chars:
                logger.info(f"Truncating AUM text from {len(relevant_text)} to {max_chars} characters")
                relevant_text = relevant_text[:max_chars]
            
            estimated_tokens = len(relevant_text) // 4
            logger.info(f"Extracted AUM text, approximately {estimated_tokens} tokens")
            
            # Add a header to help ChatGPT understand the context
            header = "EXTRACTED SEC FORM ADV SECTIONS RELATED TO ASSETS UNDER MANAGEMENT:\n\n"
            return header + relevant_text
        
        except Exception as e:
            logger.error(f"Error extracting AUM text from PDF: {str(e)}")
            return ""
    
    def extract_aum_info(self, pdf_path: str) -> Dict[str, Any]:
        """Extract AUM information from the ADV PDF using OpenAI API.
        
        This simplified method uses a targeted approach to extract only the most relevant
        AUM information from SEC Form ADV PDFs. It only tries once with no retries.
        
        Args:
            pdf_path: Path to the ADV PDF file
            
        Returns:
            Dictionary with extracted AUM information
        """
        # Default error response template
        default_error_response = {
            "reported_aum": "unknown",
            "aum_range": "unknown",
            "as_of_date": "unknown",
            "aum_type": "unknown",
            "source_section": "unknown",
            "compliance_rationale": "unknown",
            "registration_implication": "unknown",
            "update_trigger": "unknown"
        }
        
        # Check if OpenAI client is initialized
        if not self.openai_client:
            error_msg = "OpenAI client not initialized, cannot extract AUM information"
            logger.error(error_msg)
            return {**default_error_response, "error": error_msg}
        
        # Extract AUM-relevant text from PDF using the enhanced parser
        logger.info(f"Extracting AUM information from {pdf_path}")
        aum_text = self.extract_aum_text(pdf_path)
        
        if not aum_text:
            error_msg = "Failed to extract AUM text from PDF"
            logger.error(error_msg)
            return {**default_error_response, "error": error_msg}
        
        # Log the length of extracted text for monitoring token usage
        text_length = len(aum_text)
        estimated_tokens = text_length // 4
        logger.info(f"Sending {text_length} characters (~{estimated_tokens} tokens) to OpenAI API")
        
        # Prepare focused prompt for OpenAI
        prompt = """
You are a financial compliance assistant specializing in SEC Form ADV analysis. Extract the Assets Under Management (AUM) information from the provided text and return a structured JSON response.

IMPORTANT: The text provided contains ONLY the relevant sections from a Form ADV filing that mention AUM. Focus on finding the most accurate and up-to-date AUM information.

Return your response using EXACTLY this JSON schema:

{
  "reported_aum": "<exact numeric value in USD, e.g., '$1,234,567,890'>",
  "aum_range": "<range if exact value not given, e.g., '$1B–$10B'>",
  "as_of_date": "<YYYY-MM-DD or 'unknown'>",
  "aum_type": "<'discretionary' | 'non-discretionary' | 'both' | 'unknown'>",
  "source_section": "<brief quoted excerpt containing the AUM information>",
  "compliance_rationale": "<brief reason why this AUM must be disclosed and tracked>",
  "registration_implication": "<SEC registration threshold status, e.g., 'above $110M, SEC-registered'>",
  "update_trigger": "<reason this update was filed, e.g., 'Annual amendment', 'Material change in AUM'>"
}

Look specifically for:
1. Item 5.F sections about "Regulatory Assets Under Management"
2. Item 1.Q sections about total firm assets
3. Any dollar amounts associated with discretionary or non-discretionary assets
4. The date as of which the AUM was calculated

If you can't find exact values, provide the best estimate or range based on the available information.

Now extract this information from the following Form ADV text:

"""
        
        try:
            # Call OpenAI API - ONLY ONE ATTEMPT, NO RETRIES
            logger.info("Calling OpenAI API (single attempt)")
            
            # Use GPT-3.5-turbo for faster processing
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",  # Use a faster model
                messages=[
                    {"role": "system", "content": "You are a financial compliance assistant specializing in SEC Form ADV analysis."},
                    {"role": "user", "content": prompt + aum_text}
                ],
                temperature=0.1,  # Low temperature for consistent, factual responses
                max_tokens=500
            )
            
            # Process the API response
            if not response or not hasattr(response, 'choices') or not response.choices:
                error_msg = "Empty or invalid response from OpenAI API"
                logger.error(error_msg)
                return {**default_error_response, "error": error_msg}
            
            # Extract JSON from response
            response_text = response.choices[0].message.content if response and hasattr(response, 'choices') and response.choices else None
            
            if response_text:
                logger.debug(f"Received response from OpenAI: {response_text[:200]}...")
            else:
                logger.warning("Received empty response from OpenAI API")
            
            try:
                # Parse the JSON response
                if response_text:
                    # First try to parse the response directly as JSON
                    try:
                        aum_info = json.loads(response_text)
                        logger.info("Successfully parsed JSON response directly")
                    except json.JSONDecodeError:
                        # If direct parsing fails, try to extract JSON from markdown code blocks
                        logger.info("Direct JSON parsing failed, trying to extract from markdown")
                        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
                        
                        if json_match:
                            json_str = json_match.group(1)
                            logger.info("Found JSON in markdown code block")
                        else:
                            # Last resort: try to find JSON object in the text
                            json_start = response_text.find('{')
                            json_end = response_text.rfind('}') + 1
                            
                            if json_start >= 0 and json_end > json_start:
                                json_str = response_text[json_start:json_end]
                                logger.info(f"Extracted JSON object from position {json_start} to {json_end}")
                            else:
                                raise ValueError("No JSON found in response")
                        
                        aum_info = json.loads(json_str)
                    
                    # Validate and ensure all required fields are present
                    required_fields = [
                        "reported_aum", "aum_range", "as_of_date", "aum_type",
                        "source_section", "compliance_rationale",
                        "registration_implication", "update_trigger"
                    ]
                    
                    missing_fields = []
                    for field in required_fields:
                        if field not in aum_info:
                            missing_fields.append(field)
                            logger.warning(f"Missing field in OpenAI response: {field}")
                            aum_info[field] = "unknown"
                    
                    if missing_fields:
                        logger.warning(f"Added {len(missing_fields)} missing fields to response: {', '.join(missing_fields)}")
                    
                    # Add metadata about the extraction process
                    aum_info["extraction_metadata"] = {
                        "text_length": text_length,
                        "estimated_tokens": estimated_tokens,
                        "extraction_timestamp": self._get_current_timestamp()
                    }
                    
                    logger.info(f"Successfully extracted AUM information: {aum_info.get('reported_aum', 'unknown')} as of {aum_info.get('as_of_date', 'unknown')}")
                    return aum_info
                
                error_msg = "Empty response from OpenAI API"
                logger.error(error_msg)
                return {**default_error_response, "error": error_msg}
                
            except json.JSONDecodeError as e:
                error_msg = f"Error parsing JSON from OpenAI response: {str(e)}"
                if response_text:
                    logger.error(f"{error_msg}\nResponse text: {response_text[:500]}...")
                else:
                    logger.error(f"{error_msg}\nNo response text available")
                return {**default_error_response, "error": error_msg}
                
            except ValueError as e:
                error_msg = f"Error extracting JSON from OpenAI response: {str(e)}"
                if response_text:
                    logger.error(f"{error_msg}\nResponse text: {response_text[:500]}...")
                else:
                    logger.error(f"{error_msg}\nNo response text available")
                return {**default_error_response, "error": error_msg}
                
        except Exception as e:
            error_msg = f"Error in AUM extraction process: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {**default_error_response, "error": error_msg}
    
    def _get_current_timestamp(self) -> str:
        """Get the current timestamp in ISO format.
        
        Returns:
            Current timestamp string in ISO format
        """
        from datetime import datetime
        return datetime.utcnow().isoformat()
    
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
        json_path = os.path.join(cache_path, "adv_simplified.json")
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
adv_processing_agent_simplified = ADVProcessingAgentSimplified()

def process_adv(subject_id: str, crd_number: str, entity_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process the ADV for a firm and return evaluation results.
    
    This is a convenience function that uses the singleton instance of ADVProcessingAgentSimplified.
    
    Args:
        subject_id: The ID of the subject/client making the request
        crd_number: The firm's CRD number
        entity_data: Dictionary containing entity information
        
    Returns:
        Dictionary with evaluation results
    """
    return adv_processing_agent_simplified.process_adv(subject_id, crd_number, entity_data)