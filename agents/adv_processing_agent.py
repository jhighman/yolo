import os
import logging
import requests
import json
import re
from pathlib import Path
import sys
from typing import Dict, Any, Optional, Tuple, Union
from dotenv import load_dotenv
import PyPDF2  # Using PyPDF2 for text extraction
import pdfplumber  # Using pdfplumber for targeted extraction of complex layouts
from openai import OpenAI
import importlib.util

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

# Try to load the prompts module
try:
    from prompts.adv_prompts import get_aum_prompt, get_disclosure_prompt
    logger.info("Successfully loaded prompts from prompts.adv_prompts module")
    EXTERNAL_PROMPTS_AVAILABLE = True
except ImportError:
    logger.warning("Could not import prompts.adv_prompts module, will use default prompts")
    EXTERNAL_PROMPTS_AVAILABLE = False

class ADVProcessingAgent:
    """Agent for downloading and processing ADV PDF files from the SEC."""
    
    def __init__(self, cache_dir: str = "cache", prompt_version: str = "standard"):
        """Initialize the ADV Processing Agent.
        
        Args:
            cache_dir: Directory to store cached files
            prompt_version: Version of prompts to use ("standard" or "simplified")
        """
        self.cache_dir = cache_dir
        self.base_url = "https://reports.adviserinfo.sec.gov/reports/ADV"
        self.openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else None
        self.prompt_version = prompt_version
        logger.debug(f"ADVProcessingAgent initialized with prompt_version={prompt_version}")
    
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
        pdf_path = os.path.join(cache_path, f"adv-{crd_number}.pdf")
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
        pdf_path = os.path.join(cache_path, f"adv-{crd_number}.pdf")
        
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
    
    def extract_aum_text(self, pdf_path: str, max_pages: int = 1000) -> str:
        """Extract text from a PDF file, focusing specifically on AUM-relevant sections.
        
        This enhanced parser uses PyPDF2 instead of pdfplumber for faster extraction.
        It processes only the first max_pages pages to avoid excessive processing time.
        The extracted text is saved to a file for auditing purposes.
        
        If the extracted text file already exists, it will be read instead of re-processing the PDF.
        
        Args:
            pdf_path: Path to the PDF file
            max_pages: Maximum number of pages to process
            
        Returns:
            Extracted text containing AUM information
        """
        try:
            # Get the CRD number from the PDF path
            cache_dir = os.path.dirname(pdf_path)
            crd_number = os.path.basename(cache_dir)
            if crd_number.startswith("crd_"):
                crd_number = crd_number[4:]  # Remove "crd_" prefix
            
            # Check if the extracted text file already exists
            extracted_text_path = os.path.join(cache_dir, f"adv-{crd_number}-aum-source.txt")
            if os.path.exists(extracted_text_path):
                logger.info(f"Found existing AUM extracted text file: {extracted_text_path}")
                with open(extracted_text_path, 'r', encoding='utf-8') as f:
                    return f.read()
            
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
            # Primary patterns target the specific sections that contain AUM information
            primary_patterns = [
                # Item 5.F - Regulatory Assets Under Management section (most common location)
                r"Item 5\.F.*?Regulatory Assets Under Management.*?(?=\nItem 6|$)",
                
                # Item 5.F.(2)(a) - Discretionary AUM
                r"Item 5\.F\.\(2\)\(a\).*?Discretionary Amount.*?(?=\nItem 5\.F|$)",
                
                # Item 5.F.(2)(b) - Non-Discretionary AUM
                r"Item 5\.F\.\(2\)\(b\).*?Non-Discretionary Amount.*?(?=\nItem 5\.F|$)",
                
                # Item 1.Q - Another common location for AUM information
                r"Item 1\.Q.*?assets.*?(\$\d{1,3}(?:,\d{3})*(?:\.\d+)?|\$[a-zA-Z\s]+ to less than \$[a-zA-Z\s]+|more than \$?[a-zA-Z\s]+ (billion|million)).*?(?=\nItem 2|$)",
                
                # AUM Range patterns
                r"Item 5\.F.*?Regulatory Assets Under Management.*?(\$\d{1,3}(?:,\d{3})*(?:\.\d+)?|\$[a-zA-Z\s]+ to less than \$[a-zA-Z\s]+|[a-zA-Z\s]+ (?:billion|million))",
                
                # As of Date patterns
                r"(?:Item 5\.F|Item 1\.Q).*?(?:as of|fiscal year end|date.*?):?\s*(\d{1,2}/\d{1,2}/\d{4}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}|\d{4})",
                
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
                r"total assets.*?(\$\d{1,3}(?:,\d{3})*(?:\.\d+)?)",
                r"(discretionary|non-discretionary|both).*?management",
                r"fiscal year end\s*(?:\w+\s+)?(\d{4})"
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
            # Reduced from previous 24,000 chars to minimize token usage
            max_chars = 16000
            if len(relevant_text) > max_chars:
                logger.info(f"Truncating AUM text from {len(relevant_text)} to {max_chars} characters")
                relevant_text = relevant_text[:max_chars]
            
            estimated_tokens = len(relevant_text) // 4
            logger.info(f"Extracted AUM text, approximately {estimated_tokens} tokens")
            
            # Add a header to help ChatGPT understand the context
            header = "EXTRACTED SEC FORM ADV SECTIONS RELATED TO ASSETS UNDER MANAGEMENT:\n\n"
            
            # Get the CRD number from the PDF path
            cache_dir = os.path.dirname(pdf_path)
            crd_number = os.path.basename(cache_dir)
            if crd_number.startswith("crd_"):
                crd_number = crd_number[4:]  # Remove "crd_" prefix
            
            # Save the extracted text to a file for auditing
            extracted_text = header + relevant_text
            extracted_text_path = os.path.join(cache_dir, f"adv-{crd_number}-aum-source.txt")
            try:
                with open(extracted_text_path, 'w', encoding='utf-8') as f:
                    f.write(extracted_text)
                logger.info(f"Saved extracted text to {extracted_text_path}")
            except Exception as e:
                logger.error(f"Error saving extracted text: {str(e)}")
            
            return extracted_text
        
        except Exception as e:
            logger.error(f"Error extracting AUM text from PDF: {str(e)}")
            return ""
    
    def extract_disclosure_text(self, pdf_path: str, max_pages: int = 1000) -> str:
        """Extract text from a PDF file, targeting regulatory disclosure sections.
        
        This method uses PyPDF2 for fast initial extraction, then applies targeted
        regex patterns to identify disclosure-related content.
        
        If the extracted text file already exists, it will be read instead of re-processing the PDF.
        
        Args:
            pdf_path: Path to the PDF file
            max_pages: Maximum number of pages to process
            
        Returns:
            Extracted text potentially containing disclosure information
        """
        try:
            # Get the CRD number from the PDF path
            cache_dir = os.path.dirname(pdf_path)
            crd_number = os.path.basename(cache_dir)
            if crd_number.startswith("crd_"):
                crd_number = crd_number[4:]  # Remove "crd_" prefix
            
            # Check if the extracted text file already exists
            extracted_text_path = os.path.join(cache_dir, f"adv-{crd_number}-disclosure-source.txt")
            if os.path.exists(extracted_text_path):
                logger.info(f"Found existing disclosure extracted text file: {extracted_text_path}")
                with open(extracted_text_path, 'r', encoding='utf-8') as f:
                    return f.read()
            
            logger.info(f"Extracting disclosure text from {pdf_path} (max pages: {max_pages})")
            
            # Use PyPDF2 for faster initial extraction
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                
                total_pages = len(reader.pages)
                logger.info(f"PDF has {total_pages} pages")
                
                pages_to_process = min(max_pages, total_pages)
                logger.info(f"Processing first {pages_to_process} pages")
                
                for i in range(pages_to_process):
                    logger.info(f"Extracting text from page {i+1}/{pages_to_process}")
                    page = reader.pages[i]
                    page_text = page.extract_text() or ""
                    text += page_text + "\n\n"
            
            logger.debug(f"Extracted {len(text)} characters from PDF")
            
            # Expanded patterns to capture disclosure sections
            primary_patterns = [
                # Item 9: Disciplinary Information (highest priority)
                r"Item 9\.(?:[A-Z]|\([0-9]+\)).*?Disciplinary Information.*?(?=\nItem 10|$)",
                
                # Item 11: Part 2A Disciplinary Information (high priority)
                r"Item 11\.(?:[A-Z]|\([0-9]+\)).*?Disciplinary Information.*?(?=\nItem 12|$)",
                
                # Specific Item 9 sections with yes/no responses
                r"Item 9\.(?:[A-Z]|\([0-9]+\)).*?(?:Yes|No).*?(?=\nItem|$)",
                
                # Specific Item 11 sections with yes/no responses
                r"Item 11\.(?:[A-Z]|\([0-9]+\)).*?(?:Yes|No).*?(?=\nItem|$)",
                
                # Specific disciplinary sections in Schedule D
                r"Schedule D Section (?:9|11).*?disciplinary.*?(?=\nSchedule|$)",
                
                # Specific disciplinary sections in Schedule R
                r"Schedule R.*?disciplinary.*?(?=\nSchedule|$)",
                
                # Highly specific disciplinary keywords in context
                r"[^\n]*(?:disciplinary action|customer complaint|criminal conviction|civil action|judgment|lien|bankruptcy|regulatory violation|SEC enforcement|arbitration|settlement with client|lawsuit|fine|censure)[^\n]*"
            ]
            
            # Expanded disclosure keywords for more comprehensive coverage
            disclosure_keywords = [
                # Regulatory keywords
                "disciplinary action", "regulatory violation", "SEC enforcement", "administrative proceeding",
                "fine", "censure", "sanction", "cease and desist", "consent order",
                
                # Customer Dispute keywords
                "customer complaint", "arbitration", "settlement with client", "client dispute",
                "customer allegation", "client complaint",
                
                # Criminal keywords
                "criminal", "felony", "misdemeanor", "conviction", "indictment", "plea",
                
                # Civil keywords
                "civil action", "lawsuit", "injunction", "civil litigation", "civil proceeding",
                
                # Judgment/Lien keywords
                "judgment", "lien", "tax lien", "creditor", "debt",
                
                # Financial keywords
                "bankruptcy", "financial disclosure", "insolvency", "financial difficulty"
            ]
            
            relevant_text = ""
            for pattern in primary_patterns:
                matches = re.finditer(pattern, text, re.DOTALL | re.IGNORECASE)
                for match in matches:
                    match_text = match.group(0)
                    logger.debug(f"Found disclosure match: {match_text[:100]}...")
                    relevant_text += match_text + "\n\n"
            
            # If no matches, fall back to broader keyword search
            if not relevant_text:
                logger.info("No specific disclosure sections found, extracting paragraphs with keywords")
                for keyword in disclosure_keywords:
                    pattern = f"[^\n]*{keyword}[^\n]*"
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    for match in matches:
                        relevant_text += match.group(0) + "\n\n"
            
            # If still no matches, use first 10,000 characters as a fallback
            if not relevant_text:
                logger.warning("No disclosure-related content found, using first part of document")
                relevant_text = text[:10000]
            
            # Increase to 20,000 characters (~5,000 tokens) to ensure Item 9/11 is included
            max_chars = 20000
            if len(relevant_text) > max_chars:
                logger.info(f"Truncating disclosure text from {len(relevant_text)} to {max_chars} characters")
                relevant_text = relevant_text[:max_chars]
            
            estimated_tokens = len(relevant_text) // 4
            logger.info(f"Extracted disclosure text, approximately {estimated_tokens} tokens")
            
            header = "EXTRACTED SEC FORM ADV SECTIONS POTENTIALLY RELATED TO DISCLOSURES:\n\n"
            extracted_text = header + relevant_text
            
            cache_dir = os.path.dirname(pdf_path)
            crd_number = os.path.basename(cache_dir)
            if crd_number.startswith("crd_"):
                crd_number = crd_number[4:]  # Remove "crd_" prefix
            
            extracted_text_path = os.path.join(cache_dir, f"adv-{crd_number}-disclosure-source.txt")
            try:
                with open(extracted_text_path, 'w', encoding='utf-8') as f:
                    f.write(extracted_text)
                logger.info(f"Saved disclosure text to {extracted_text_path}")
            except Exception as e:
                logger.error(f"Error saving disclosure text: {str(e)}")
            
            return extracted_text
        
        except Exception as e:
            logger.error(f"Error extracting disclosure text from PDF: {str(e)}")
            return ""
    
    def extract_aum_info(self, pdf_path: str, aum_text: Optional[str] = None, max_pages: int = 1000, force_extract: bool = False) -> Dict[str, Any]:
        """Extract AUM information from the ADV PDF using OpenAI API.
        
        This simplified method uses a targeted approach to extract only the most relevant
        AUM information from SEC Form ADV PDFs. It only tries once with no retries.
        
        If the OpenAI API is unreachable, it will attempt to use cached GPT results if available.
        
        Args:
            pdf_path: Path to the ADV PDF file
            aum_text: Pre-extracted text (optional). If provided, skips the text extraction step.
            max_pages: Maximum number of pages to process if extracting text
            force_extract: If True, force re-extraction of text even if cached text exists
            
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
        
        # Get the cache directory from the PDF path
        cache_dir = os.path.dirname(pdf_path)
        
        # Extract AUM-relevant text from PDF using the enhanced parser if not provided
        if aum_text is None:
            logger.info(f"Extracting AUM information from {pdf_path}")
            # Extract text from PDF or use cached text
            aum_text = self.extract_aum_text(pdf_path, max_pages=max_pages)
            
            # Get the CRD number from the PDF path for logging purposes
            crd_number = os.path.basename(os.path.dirname(pdf_path))
            if crd_number.startswith("crd_"):
                crd_number = crd_number[4:]  # Remove "crd_" prefix
            
            # The extracted text file path (for reference in logs)
            extracted_text_path = os.path.join(cache_dir, f"adv-{crd_number}-aum-source.txt")
            try:
                with open(extracted_text_path, 'w', encoding='utf-8') as f:
                    f.write(aum_text)
                logger.info(f"Saved extracted text to {extracted_text_path}")
            except Exception as e:
                logger.error(f"Error saving extracted text: {str(e)}")
        else:
            logger.info("Using pre-extracted AUM text")
            
            # Get the CRD number from the PDF path
            crd_number = os.path.basename(os.path.dirname(pdf_path))
            if crd_number.startswith("crd_"):
                crd_number = crd_number[4:]  # Remove "crd_" prefix
            
            # Save the pre-extracted text to a file for auditing
            extracted_text_path = os.path.join(cache_dir, f"adv-{crd_number}-aum-source.txt")
            try:
                with open(extracted_text_path, 'w', encoding='utf-8') as f:
                    f.write(aum_text)
                logger.info(f"Saved pre-extracted text to {extracted_text_path}")
            except Exception as e:
                logger.error(f"Error saving pre-extracted text: {str(e)}")
        
        
        if not aum_text:
            error_msg = "Failed to extract AUM text from PDF"
            logger.error(error_msg)
            return {**default_error_response, "error": error_msg}
        
        # Log the length of extracted text for monitoring token usage
        text_length = len(aum_text)
        estimated_tokens = text_length // 4
        logger.info(f"Sending {text_length} characters (~{estimated_tokens} tokens) to OpenAI API")
        
        # Prepare focused prompt for OpenAI
        if EXTERNAL_PROMPTS_AVAILABLE:
            prompt = get_aum_prompt(self.prompt_version)
            logger.info(f"Using external AUM prompt (version: {self.prompt_version})")
        else:
            # Default prompt if external prompts are not available
            prompt = """
You are a financial compliance assistant specializing in SEC Form ADV analysis. Extract the Regulatory Assets Under Management (RAUM), AUM Range, As of Date, and AUM Type from the provided Form ADV text, returning the result as structured JSON. Return *only* valid JSON, with no markdown, code blocks, or additional text, to ensure proper parsing.

Use the following schema:
{
  "reported_aum": "<numeric value in USD, e.g., '$1000000000', or 'unknown' if only a range is provided>",
  "aum_range": "<range, e.g., '$1B–$10B', or 'unknown'>",
  "as_of_date": "<YYYY-MM-DD, or 'unknown' if not specified>",
  "aum_type": "<'discretionary' | 'non-discretionary' | 'both' | 'unknown'>",
  "source_section": "<quoted excerpt from Form ADV, max 200 characters>",
  "compliance_rationale": "<why AUM must be disclosed>",
  "registration_implication": "<SEC registration status>",
  "update_trigger": "<reason for update>"
}

Instructions:
- **Reported AUM**: Extract the Regulatory Assets Under Management (RAUM) from Item 5.F, per SEC Rule 203A-3 (gross assets, including discretionary and non-discretionary accounts). Format as '$<number>' with no commas (e.g., '$1000000000'). If only a range is provided (e.g., in Item 1.Q), set to 'unknown'.
- **AUM Range**:
  - If Item 5.F provides an exact RAUM, derive the range using SEC thresholds:
    - < $25,000,000: '$0–$25M'
    - $25,000,001–$100,000,000: '$25M–$100M'
    - $100,000,001–$1,000,000,000: '$100M–$1B'
    - $1,000,000,001–$10,000,000,000: '$1B–$10B'
    - $10,000,000,001–$50,000,000,000: '$10B–$50B'
    - > $50,000,000,000: '> $50B'
  - If Item 1.Q or other sections provide a range (e.g., '$1 billion to less than $10 billion'), use it directly, reformatted as '$1B–$10B'.
  - If no range or exact value is found, set to 'unknown'.
- **As of Date**: Extract from Item 5.F, Item 1.Q, or Item 3.B (fiscal year-end), e.g., 'as of 09/30/2024' or 'fiscal year end September 2024'. Convert textual dates to YYYY-MM-DD, assuming the last day of the month (e.g., 'September 2024' → '2024-09-30'). If no date is found, use Item 3.B or the filing date (e.g., '01/14/2025'). Set to 'unknown' if no date is available.
- **AUM Type**: Identify from Item 5.F.(2)(a) (Discretionary Amount) or 5.F.(2)(b) (Non-Discretionary Amount). Set to 'discretionary' if only discretionary is mentioned, 'non-discretionary' if only non-discretionary, 'both' if both are present, or 'unknown' if unclear.
- **Source Section**: Provide a concise excerpt (max 200 characters) from the primary source (e.g., Item 5.F or Item 1.Q). If data is missing, note the issue (e.g., 'Item 5.F not found, used Item 1.Q').
- **Compliance Rationale**: Use 'Required for SEC registration eligibility under Advisers Act'.
- **Registration Implication**: Based on AUM: '< $25M, state-registered', '$25M–$110M, SEC optional', '> $110M, SEC-registered'.
- **Update Trigger**: Infer from context, e.g., 'Annual amendment' for fiscal year-end filings, 'Material change in AUM' if specified, or 'unknown'.
- If data is ambiguous or missing, set fields to 'unknown' and explain in 'source_section'.

Extract from the following Form ADV text:
"""
            logger.info("Using default AUM prompt (external prompts not available)")
        
        # Get the cache paths
        cache_dir = os.path.dirname(pdf_path)
        crd_number = os.path.basename(cache_dir)
        if crd_number.startswith("crd_"):
            crd_number = crd_number[4:]  # Remove "crd_" prefix
        gpt_result_path = os.path.join(cache_dir, f"adv-{crd_number}-aum-gpt.json")
        
        # Check if cached GPT result exists
        if os.path.exists(gpt_result_path) and not force_extract:
            try:
                logger.info(f"Found existing AUM GPT result file: {gpt_result_path}")
                with open(gpt_result_path, 'r', encoding='utf-8') as f:
                    cached_result = json.load(f)
                # If the cached result doesn't have an error, return it
                if "error" not in cached_result:
                    logger.info(f"Using cached AUM GPT result")
                    return cached_result
                else:
                    logger.info(f"Cached AUM GPT result contains an error, attempting to call API again")
            except Exception as e:
                logger.error(f"Error reading cached AUM GPT result: {str(e)}")
        
        try:
            # Check if OpenAI API is reachable
            try:
                # Simple ping to check connectivity
                import socket
                socket.create_connection(("api.openai.com", 443), timeout=5)
                logger.info("OpenAI API is reachable")
            except Exception as e:
                logger.error(f"OpenAI API is unreachable: {str(e)}")
                # If we have a cached result with an error, return it
                if os.path.exists(gpt_result_path):
                    try:
                        with open(gpt_result_path, 'r', encoding='utf-8') as f:
                            cached_result = json.load(f)
                        logger.info(f"Using cached AUM GPT result despite error")
                        return cached_result
                    except Exception as read_err:
                        logger.error(f"Error reading cached AUM GPT result: {str(read_err)}")
                # Return default error response
                return {**default_error_response, "error": f"OpenAI API is unreachable: {str(e)}"}
            
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
                    
                    # Get the CRD number from the PDF path
                    cache_dir = os.path.dirname(pdf_path)
                    crd_number = os.path.basename(cache_dir)
                    if crd_number.startswith("crd_"):
                        crd_number = crd_number[4:]  # Remove "crd_" prefix
                    
                    # Save the GPT result to a standardized filename
                    gpt_result_path = os.path.join(cache_dir, f"adv-{crd_number}-aum-gpt.json")
                    try:
                        with open(gpt_result_path, 'w', encoding='utf-8') as f:
                            json.dump(aum_info, f, indent=2)
                        logger.info(f"Saved GPT result to {gpt_result_path}")
                    except Exception as e:
                        logger.error(f"Error saving GPT result: {str(e)}")
                    
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
    
    def extract_disclosure_info(self, pdf_path: str, disclosure_text: Optional[str] = None, max_pages: int = 1000, force_extract: bool = False) -> Dict[str, Any]:
        """Summarize regulatory disclosure information from the ADV PDF using OpenAI API.
        
        If the OpenAI API is unreachable, it will attempt to use cached GPT results if available.
        
        Args:
            pdf_path: Path to the ADV PDF file
            disclosure_text: Pre-extracted disclosure text (optional)
            max_pages: Maximum number of pages to process if extracting text
            force_extract: If True, force re-extraction of text even if cached text exists
            
        Returns:
            Dictionary with summarized disclosure information
        """
        default_error_response = {
            "has_disclosures": False,
            "disclosure_count": 0,
            "disclosures": [],
            "source_section": "unknown",
            "compliance_rationale": "unknown"
        }
        
        if not self.openai_client:
            error_msg = "OpenAI client not initialized, cannot extract disclosure information"
            logger.error(error_msg)
            return {**default_error_response, "error": error_msg}
        
        if disclosure_text is None:
            logger.info(f"Extracting disclosure information from {pdf_path}")
            # Extract text from PDF or use cached text
            disclosure_text = self.extract_disclosure_text(pdf_path, max_pages=max_pages)
            
            cache_dir = os.path.dirname(pdf_path)
            crd_number = os.path.basename(cache_dir)
            if crd_number.startswith("crd_"):
                crd_number = crd_number[4:]  # Remove "crd_" prefix
            
            extracted_text_path = os.path.join(cache_dir, f"adv-{crd_number}-disclosure-source.txt")
            try:
                with open(extracted_text_path, 'w', encoding='utf-8') as f:
                    f.write(disclosure_text)
                logger.info(f"Saved disclosure text to {extracted_text_path}")
            except Exception as e:
                logger.error(f"Error saving disclosure text: {str(e)}")
        else:
            logger.info("Using pre-extracted disclosure text")
            
            cache_dir = os.path.dirname(pdf_path)
            crd_number = os.path.basename(cache_dir)
            if crd_number.startswith("crd_"):
                crd_number = crd_number[4:]  # Remove "crd_" prefix
            extracted_text_path = os.path.join(cache_dir, f"adv-{crd_number}-disclosure-source.txt")
            try:
                with open(extracted_text_path, 'w', encoding='utf-8') as f:
                    f.write(disclosure_text)
                logger.info(f"Saved pre-extracted disclosure text to {extracted_text_path}")
            except Exception as e:
                logger.error(f"Error saving pre-extracted disclosure text: {str(e)}")
        
        if not disclosure_text:
            error_msg = "Failed to extract disclosure text from PDF"
            logger.error(error_msg)
            return {**default_error_response, "error": error_msg}
        
        text_length = len(disclosure_text)
        estimated_tokens = text_length // 4
        logger.info(f"Sending {text_length} characters (~{estimated_tokens} tokens) to OpenAI API for disclosure summarization")
        
        if EXTERNAL_PROMPTS_AVAILABLE:
            prompt = get_disclosure_prompt(self.prompt_version)
            logger.info(f"Using external disclosure prompt (version: {self.prompt_version})")
        else:
            # Default prompt if external prompts are not available
            prompt = """
You are a financial compliance assistant specializing in SEC Form ADV analysis. Summarize disclosure information from the provided Form ADV text, identifying events across Item 9, Item 11, Schedule D, Schedule R, and related sections. Map disclosures to one of six types: Regulatory, Customer Dispute, Criminal, Civil, Judgment/Lien, or Financial. Extract multiple distinct events when present. Return *only* valid JSON, with no markdown, code blocks, or additional text, to ensure proper parsing.

Use the following schema:
{
  "has_disclosures": "<true if any disclosures are reported, false otherwise>",
  "disclosure_count": "<number of distinct disclosure events>",
  "disclosures": [
    {
      "disclosureType": "<'Regulatory' | 'Customer Dispute' | 'Criminal' | 'Civil' | 'Judgment/Lien' | 'Financial' | 'unknown'>",
      "eventDate": "<YYYY-MM-DD or 'unknown'>",
      "disclosureResolution": "<'settled' | 'pending' | 'dismissed' | 'ongoing' | 'unknown'>",
      "disclosureDetail": {
        "<type-specific fields>": "<values based on disclosure type>"
      },
      "source_item": "<e.g., '9.A', '9.B', '11', 'Schedule D', 'unknown'>"
    }
  ],
  "source_section": "<quoted excerpt from Form ADV, max 200 characters>",
  "compliance_rationale": "<why disclosures must be reported>"
}

Instructions:
- **Has Disclosures**: Set to true if text indicates any disclosure events (e.g., 'Yes' in Item 9/11, or keywords like 'disciplinary', 'customer complaint', 'lawsuit', 'judgment', 'lien', 'bankruptcy'). Set to false if all responses are 'No' or no events are found.
- **Disclosure Count**: Count distinct events based on separate section entries (e.g., 9.A, 9.B, 11) or narrative descriptions. Treat each unique event (e.g., different dates, allegations) as a separate disclosure.
- **Disclosures**: For each event, extract:
  - **disclosureType**: Classify based on context:
    - **Regulatory**: Regulatory actions by SEC, FINRA, or other authorities. Keywords: 'disciplinary action', 'regulatory violation', 'SEC enforcement', 'administrative proceeding', 'fine', 'censure'.
    - **Customer Dispute**: Client complaints or arbitrations. Keywords: 'customer complaint', 'arbitration', 'settlement with client', 'client dispute'.
    - **Criminal**: Criminal charges or convictions. Keywords: 'criminal', 'felony', 'misdemeanor', 'conviction', 'indictment'.
    - **Civil**: Civil lawsuits or judicial actions. Keywords: 'civil action', 'lawsuit', 'injunction', 'civil litigation'.
    - **Judgment/Lien**: Judgments or liens against the firm. Keywords: 'judgment', 'lien', 'tax lien', 'creditor'.
    - **Financial**: Financial issues like bankruptcies. Keywords: 'bankruptcy', 'financial disclosure', 'insolvency', 'creditor'.
    - Use 'unknown' if type is unclear but an event is indicated.
  - **eventDate**: Extract from context (e.g., 'as of 09/30/2024', 'filed 2020', 'September 2020'). Convert to YYYY-MM-DD:
    - For partial dates (e.g., '2020'), use 'YYYY-12-31'.
    - For month-year (e.g., 'September 2020'), use last day of the month (e.g., '2020-09-30').
    - If no date, use Item 3.B (fiscal year-end) or filing date (e.g., '2025-01-14'). Set to 'unknown' if unavailable.
  - **disclosureResolution**: Determine from context:
    - 'settled': Mentions of 'settled', 'settlement', 'paid', 'resolved'.
    - 'pending': Mentions of 'pending', 'ongoing', 'not resolved'.
    - 'dismissed': Mentions of 'dismissed', 'dropped', 'no action'.
    - 'ongoing': Mentions of 'continuing', 'in progress'.
    - 'unknown': If resolution is unclear.
  - **disclosureDetail**: Include type-specific fields:
    - **Regulatory**:
      - InitiatedBy: "<e.g., 'SEC', 'FINRA', 'State Regulator', 'unknown'>"
      - Allegations: "<specific allegations, e.g., 'Misleading fee disclosures', max 200 characters>"
      - SanctionDetails: [{ "Sanctions": "<e.g., 'Fine $5,000,000', 'Suspension', 'unknown'>" }], flag civil sanctions (e.g., 'Civil Penalty') in Sanctions
    - **Customer Dispute**:
      - Allegations: "<complaint details, e.g., 'Unauthorized trading', max 200 characters>"
      - DamageAmountRequested: "<e.g., '$100,000', 'unknown'>"
      - SettlementAmount: "<e.g., '$50,000', 'unknown'>"
    - **Criminal**:
      - criminalCharges: [{ "Charges": "<e.g., 'Fraud', 'unknown'>", "Disposition": "<e.g., 'Convicted', 'Dismissed', 'unknown'>" }]
    - **Civil**:
      - Allegations: "<lawsuit details, e.g., 'Breach of fiduciary duty', max 200 characters>"
      - Disposition: "<e.g., 'Settled', 'Dismissed', 'unknown'>"
    - **Judgment/Lien**:
      - JudgmentLienAmount: "<e.g., '$200,000', 'unknown'>"
      - JudgmentLienType: "<e.g., 'Tax Lien', 'Judgment', 'unknown'>"
    - **Financial**:
      - Disposition: "<e.g., 'Filed', 'Discharged', 'unknown'>"
      - Type: "<e.g., 'Bankruptcy', 'Insolvency', 'unknown'>"
  - **source_item**: Identify the source (e.g., '9.A', '9.B', '11', 'Schedule D', 'Schedule R'). Use 'unknown' if unclear but an event is indicated.
- **Source Section**: Quote a specific excerpt (max 200 characters) describing the event (e.g., 'Settled SEC fine for $5M'). If no disclosures, use 'No disclosure events found'.
- **Compliance Rationale**: Use 'Required to disclose material disciplinary and financial events under Advisers Act Section 203'.
- **Handling Ambiguity**:
  - If text lacks clear section markers, use keywords to infer events and types.
  - For multiple disclosures in one section (e.g., Item 9.A listing multiple fines), separate into distinct entries based on unique dates or allegations.
  - If details are missing, set fields to 'unknown' and note in disclosureDetail (e.g., {'Note': 'Details not specified'}).
- **Handling Tables**: If text includes table-like structures (e.g., 'Fine: $5,000,000 | Date: 2020'), parse as separate fields.
- **Token Optimization**: Prioritize extracting specific details over generic text. Limit excerpts to relevant sentences.

Extract from the following Form ADV text:
"""
            logger.info("Using default disclosure prompt (external prompts not available)")
        
        try:
            logger.info("Calling OpenAI API for disclosure summarization (single attempt)")
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a financial compliance assistant specializing in SEC Form ADV analysis."},
                    {"role": "user", "content": prompt + disclosure_text}
                ],
                temperature=0.3,  # Slightly higher for summarization flexibility
                max_tokens=500
            )
            
            if not response or not hasattr(response, 'choices') or not response.choices:
                error_msg = "Empty or invalid response from OpenAI API"
                logger.error(error_msg)
                return {**default_error_response, "error": error_msg}
            
            response_text = response.choices[0].message.content if response and hasattr(response, 'choices') and response.choices else None
            
            if response_text:
                logger.debug(f"Received disclosure response from OpenAI: {response_text[:200]}...")
            else:
                logger.warning("Received empty response from OpenAI API")
            
            try:
                if not response_text:
                    error_msg = "Empty response text from OpenAI API"
                    logger.error(error_msg)
                    return {**default_error_response, "error": error_msg}
                
                disclosure_info = json.loads(response_text)
                
                required_fields = ["has_disclosures", "disclosure_count", "disclosures", "source_section", "compliance_rationale"]
                missing_fields = [field for field in required_fields if field not in disclosure_info]
                for field in missing_fields:
                    logger.warning(f"Missing disclosure field in OpenAI response: {field}")
                    disclosure_info[field] = default_error_response[field]
                
                # Validate disclosures array
                if not isinstance(disclosure_info.get("disclosures", []), list):
                    logger.warning("Invalid disclosures format, setting to empty list")
                    disclosure_info["disclosures"] = []
                    disclosure_info["has_disclosures"] = False
                    disclosure_info["disclosure_count"] = 0
                
                # Validate each disclosure entry
                valid_types = ["Regulatory", "Customer Dispute", "Criminal", "Civil", "Judgment/Lien", "Financial", "unknown"]
                valid_resolutions = ["settled", "pending", "dismissed", "ongoing", "unknown"]
                for disclosure in disclosure_info["disclosures"]:
                    if disclosure.get("disclosureType") not in valid_types:
                        logger.warning(f"Invalid disclosure type: {disclosure.get('disclosureType')}")
                        disclosure["disclosureType"] = "unknown"
                    if disclosure.get("disclosureResolution") not in valid_resolutions:
                        logger.warning(f"Invalid disclosure resolution: {disclosure.get('disclosureResolution')}")
                        disclosure["disclosureResolution"] = "unknown"
                    if not re.match(r"\d{4}-\d{2}-\d{2}|unknown", disclosure.get("eventDate", "unknown")):
                        logger.warning(f"Invalid disclosure date format: {disclosure.get('eventDate')}")
                        disclosure["eventDate"] = "unknown"
                
                # Refined fallback: Check for disclosure-specific keywords in context
                disclosure_keywords = [
                    # Regulatory keywords
                    "disciplinary action", "regulatory violation", "SEC enforcement", "administrative proceeding",
                    "fine", "censure", "sanction", "cease and desist", "consent order",
                    
                    # Customer Dispute keywords
                    "customer complaint", "arbitration", "settlement with client", "client dispute",
                    "customer allegation", "client complaint",
                    
                    # Criminal keywords
                    "criminal", "felony", "misdemeanor", "conviction", "indictment", "plea",
                    
                    # Civil keywords
                    "civil action", "lawsuit", "injunction", "civil litigation", "civil proceeding",
                    
                    # Judgment/Lien keywords
                    "judgment", "lien", "tax lien", "creditor", "debt",
                    
                    # Financial keywords
                    "bankruptcy", "financial disclosure", "insolvency", "financial difficulty"
                ]
                
                # Check for "yes" only in context of Item 9 or Item 11
                item9_or_11_yes_pattern = re.search(r"Item (?:9|11)\.(?:[A-Z]|\([0-9]+\)).*?\s+Yes\s", disclosure_text, re.IGNORECASE)
                
                # Check for disclosure keywords
                found_keywords = [keyword for keyword in disclosure_keywords if keyword in disclosure_text.lower()]
                
                # Check for stronger evidence: either a "Yes" in Item 9/11, multiple keywords, or keywords in context
                strong_evidence = item9_or_11_yes_pattern or len(found_keywords) >= 2 or any(
                    re.search(rf"\b{keyword}\b.*?(filed|settled|pending|dismissed|ongoing)", disclosure_text, re.IGNORECASE)
                    for keyword in disclosure_keywords
                )
                
                if not disclosure_info["has_disclosures"] and strong_evidence:
                    trigger = "Item 9/11 'Yes' response" if item9_or_11_yes_pattern else f"Keywords: {', '.join(found_keywords)}"
                    logger.info(f"Fallback: Detected strong disciplinary indicators ({trigger}), setting has_disclosures to true")
                    disclosure_info["has_disclosures"] = True
                    disclosure_info["disclosure_count"] = 1
                    disclosure_info["disclosures"] = [{
                        "disclosureType": "unknown",
                        "eventDate": "unknown",
                        "disclosureResolution": "unknown",
                        "disclosureDetail": {
                            "Note": f"Potential disclosure event indicated, triggered by: {trigger}"
                        },
                        "source_item": "unknown"
                    }]
                    disclosure_info["source_section"] = f"Detected potential disclosure keywords: {trigger}"[:200]
                
                disclosure_info["extraction_metadata"] = {
                    "text_length": text_length,
                    "estimated_tokens": estimated_tokens,
                    "extraction_timestamp": self._get_current_timestamp()
                }
                
                gpt_result_path = os.path.join(cache_dir, f"adv-{crd_number}-disclosure-gpt.json")
                try:
                    with open(gpt_result_path, 'w', encoding='utf-8') as f:
                        json.dump(disclosure_info, f, indent=2)
                    logger.info(f"Saved disclosure GPT result to {gpt_result_path}")
                except Exception as e:
                    logger.error(f"Error saving disclosure GPT result: {str(e)}")
                
                logger.info(f"Successfully summarized disclosure information: {disclosure_info['disclosure_count']} disclosures found")
                return disclosure_info
            
            except json.JSONDecodeError as e:
                error_msg = f"Error parsing JSON from OpenAI disclosure response: {str(e)}"
                if response_text:
                    logger.error(f"{error_msg}\nResponse text: {response_text[:500]}...")
                else:
                    logger.error(f"{error_msg}\nNo response text available")
                return {**default_error_response, "error": error_msg}
            
            except ValueError as e:
                error_msg = f"Error processing OpenAI disclosure response: {str(e)}"
                if response_text:
                    logger.error(f"{error_msg}\nResponse text: {response_text[:500]}...")
                else:
                    logger.error(f"{error_msg}\nNo response text available")
                return {**default_error_response, "error": error_msg}
        
        except Exception as e:
            error_msg = f"Error in disclosure summarization process: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {**default_error_response, "error": error_msg}
    
    def _get_current_timestamp(self) -> str:
        """Get the current timestamp in ISO format.
        
        Returns:
            Current timestamp string in ISO format
        """
        from datetime import datetime
        return datetime.utcnow().isoformat()
    
    def process_adv(self, subject_id: str, crd_number: str, entity_data: Dict[str, Any], force_extract: bool = False, prompt_version: Optional[str] = None) -> Dict[str, Any]:
        """Process the ADV for a firm and return evaluation results.
        
        Args:
            subject_id: The ID of the subject/client making the request
            crd_number: The firm's CRD number
            entity_data: Dictionary containing entity information
            force_extract: If True, force re-extraction of text even if cached text exists
            prompt_version: Optional override for the prompt version to use
            
        Returns:
            Dictionary with evaluation results
        """
        # Use the provided prompt_version if specified, otherwise use the instance's prompt_version
        current_prompt_version = prompt_version if prompt_version else self.prompt_version
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
        pdf_path = os.path.join(cache_path, f"adv_{crd_number}.pdf")
        
        # Extract AUM information from the ADV PDF
        aum_info = self.extract_aum_info(pdf_path, force_extract=force_extract)
        
        # Extract disclosure information from the ADV PDF
        disclosure_info = self.extract_disclosure_info(pdf_path, force_extract=force_extract)
        
        # Save combined results to JSON file
        json_path = os.path.join(cache_path, f"adv-{crd_number}-result.json")
        combined_result = {
            "aum_info": aum_info,
            "disclosure_info": disclosure_info
        }
        try:
            with open(json_path, 'w') as f:
                json.dump(combined_result, f, indent=2)
            logger.info(f"Saved combined AUM and disclosure information to {json_path}")
        except Exception as e:
            logger.error(f"Error saving combined information to JSON: {str(e)}")
        
        # Create evaluation result
        result = {
            "compliance": True,
            "compliance_explanation": "ADV filing is available and has been retrieved",
            "adv_status": "available",
            "adv_path": pdf_path,
            "adv_json_path": json_path,
            "adv_extracted_text_path": os.path.join(cache_path, f"adv-{crd_number}-aum-source.txt"),
            "adv_disclosure_text_path": os.path.join(cache_path, f"adv-{crd_number}-disclosure-source.txt"),
            "adv_gpt_result_path": os.path.join(cache_path, f"adv-{crd_number}-aum-gpt.json"),
            "adv_disclosure_result_path": os.path.join(cache_path, f"adv-{crd_number}-disclosure-gpt.json"),
            "aum_info": aum_info,
            "disclosure_info": disclosure_info,
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
        
        # Add alert if there was an error extracting disclosure information
        if "error" in disclosure_info:
            result["alerts"].append({
                "alert_type": "DisclosureExtractionFailed",
                "severity": "LOW",
                "description": f"Failed to extract disclosure information: {disclosure_info['error']}",
                "metadata": {
                    "crd_number": crd_number,
                    "firm_name": entity_data.get("firm_name", "Unknown"),
                    "error": disclosure_info["error"]
                }
            })
        
        return result

# Singleton instance for use throughout the application
adv_processing_agent = ADVProcessingAgent()

def process_adv(subject_id: str, crd_number: str, entity_data: Dict[str, Any], force_extract: bool = False, prompt_version: Optional[str] = None) -> Dict[str, Any]:
    """Process the ADV for a firm and return evaluation results.
    
    This is a convenience function that uses the singleton instance of ADVProcessingAgent.
    
    Args:
        subject_id: The ID of the subject/client making the request
        crd_number: The firm's CRD number
        entity_data: Dictionary containing entity information
        force_extract: If True, force re-extraction of text even if cached text exists
        prompt_version: Optional override for the prompt version to use
        
    Returns:
        Dictionary with evaluation results
    """
    return adv_processing_agent.process_adv(subject_id, crd_number, entity_data, force_extract, prompt_version)