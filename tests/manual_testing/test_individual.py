#!/usr/bin/env python3
"""
Test script for fetching individual information by CRD number.
This is separate from the firm services since the current implementation
focuses on firms rather than individuals.
"""

import sys
import json
import requests
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from utils.logging_config import setup_logging

# Initialize logging
loggers = setup_logging(debug=True)
logger = loggers.get('test_individual', None)

def fetch_individual_by_crd(crd_number):
    """
    Fetch information about an individual by CRD number directly from the SEC IAPD API.
    
    Args:
        crd_number: The individual's CRD number
        
    Returns:
        Dictionary containing individual information or None if not found
    """
    url = f"https://api.adviserinfo.sec.gov/search/individual/{crd_number}"
    params = {
        "includePrevious": "true",
        "hl": "true",
        "nrows": "12",
        "start": "0",
        "r": "25",
        "sort": "score+desc",
        "wt": "json"
    }
    
    try:
        print(f"Fetching individual information for CRD: {crd_number}")
        response = requests.get(url, params=params, timeout=(10, 30))
        
        if response.status_code == 200:
            data = response.json()
            
            # Check for API error messages
            if "errorCode" in data and data["errorCode"] != 0:
                error_msg = data.get("errorMessage", "Unknown API error")
                print(f"API returned error: {error_msg}")
                return None
            
            # Handle different response formats
            if "hits" in data and data["hits"] is not None and "hits" in data["hits"] and data["hits"]["hits"]:
                hit = data["hits"]["hits"][0]
                if "_source" in hit and "iacontent" in hit["_source"]:
                    try:
                        # Parse the JSON string into a dictionary
                        iacontent = hit["_source"]["iacontent"]
                        if isinstance(iacontent, str):
                            details = json.loads(iacontent)
                        else:
                            details = iacontent
                            
                        print(f"Successfully retrieved individual details for CRD: {crd_number}")
                        return details
                    except Exception as e:
                        print(f"Failed to parse content for CRD: {crd_number}, error: {e}")
                        return None
            
            print(f"No details found for individual CRD: {crd_number}")
            return None
        else:
            print(f"Error getting individual details for CRD: {crd_number}, status code: {response.status_code}")
            return None
    
    except Exception as e:
        print(f"Unexpected error during individual details fetch: {e}")
        return None

def format_name(first_name, middle_name=None, last_name=None, suffix=None):
    """Format a full name from components."""
    if not first_name or not last_name:
        return None
        
    full_name = f"{first_name}"
    if middle_name:
        full_name += f" {middle_name}"
    full_name += f" {last_name}"
    if suffix:
        full_name += f", {suffix}"
    return full_name

def extract_employer_info(employer_data):
    """Extract standardized employer information from employer data."""
    if not isinstance(employer_data, dict):
        return {}
        
    return {
        "firm_name": employer_data.get("firmName", ""),
        "firm_crd": str(employer_data.get("firmId", "")),
        "city": employer_data.get("city", ""),
        "state": employer_data.get("state", ""),
        "country": employer_data.get("country", "United States"),
        "start_date": employer_data.get("registrationBeginDate", ""),
        "end_date": employer_data.get("registrationEndDate", ""),
        "is_active": not bool(employer_data.get("registrationEndDate", "")),
        "sec_number": employer_data.get("iaSECNumber", employer_data.get("bdSECNumber", "")),
        "sec_number_type": employer_data.get("iaSECNumberType", ""),
        "is_ia_only": employer_data.get("iaOnly", "N") == "Y"
    }

def extract_disclosure_info(disclosure_data):
    """Extract standardized disclosure information from disclosure data."""
    if not isinstance(disclosure_data, dict):
        return {}
        
    return {
        "type": disclosure_data.get("disclosureType", ""),
        "date": disclosure_data.get("eventDate", ""),
        "resolution": disclosure_data.get("disclosureResolution", ""),
        "details": disclosure_data.get("disclosureDetail", {})
    }

def extract_exam_info(exam_data):
    """Extract standardized exam information from exam data."""
    if not isinstance(exam_data, dict):
        return {}
        
    return {
        "category": exam_data.get("examCategory", ""),
        "name": exam_data.get("examName", ""),
        "date": exam_data.get("examTakenDate", ""),
        "scope": exam_data.get("examScope", "")
    }

def extract_registration_info(reg_data):
    """Extract standardized registration information from registration data."""
    if not isinstance(reg_data, dict):
        return {}
        
    return {
        "state": reg_data.get("state", ""),
        "scope": reg_data.get("regScope", ""),
        "status": reg_data.get("status", ""),
        "date": reg_data.get("regDate", "")
    }

def normalize_individual_details(details):
    """
    Normalize individual details response into a standard format.
    
    Args:
        details: Raw individual details response
        
    Returns:
        Normalized individual details
    """
    if not details:
        print("Empty details provided to normalize_individual_details")
        return {}
    
    try:
        # Initialize with default values
        normalized = {
            "individual_name": None,
            "crd_number": None,
            "current_employers": [],
            "previous_employers": [],
            "registrations": [],
            "exams": [],
            "disclosures": [],
            "disclosure_count": 0,
            "has_disclosures": False,
            "raw_data": details
        }
        
        # Extract basic information
        basic_info = details.get('basicInformation', {})
        if isinstance(basic_info, dict):
            # Extract name components
            first_name = basic_info.get("firstName", "")
            middle_name = basic_info.get("middleName", "")
            last_name = basic_info.get("lastName", "")
            suffix = basic_info.get("nameSuffix", "")
            
            # Format full name
            normalized["individual_name"] = format_name(first_name, middle_name, last_name, suffix)
            
            # Extract CRD number
            if "individualId" in basic_info:
                normalized["crd_number"] = str(basic_info["individualId"])
        
        # Extract current employers (both regular and IA)
        current_employers = details.get("currentEmployments", [])
        current_ia_employers = details.get("currentIAEmployments", [])
        
        if isinstance(current_employers, list):
            for employer in current_employers:
                if isinstance(employer, dict):
                    normalized["current_employers"].append(extract_employer_info(employer))
        
        if isinstance(current_ia_employers, list):
            for employer in current_ia_employers:
                if isinstance(employer, dict):
                    normalized["current_employers"].append(extract_employer_info(employer))
        
        # Extract previous employers (both regular and IA)
        previous_employers = details.get("previousEmployments", [])
        previous_ia_employers = details.get("previousIAEmployments", [])
        
        if isinstance(previous_employers, list):
            for employer in previous_employers:
                if isinstance(employer, dict):
                    normalized["previous_employers"].append(extract_employer_info(employer))
        
        if isinstance(previous_ia_employers, list):
            for employer in previous_ia_employers:
                if isinstance(employer, dict):
                    normalized["previous_employers"].append(extract_employer_info(employer))
        
        # Extract disclosures
        disclosures = details.get("disclosures", [])
        if isinstance(disclosures, list):
            for disclosure in disclosures:
                if isinstance(disclosure, dict):
                    normalized["disclosures"].append(extract_disclosure_info(disclosure))
        
        normalized["disclosure_count"] = len(normalized["disclosures"])
        normalized["has_disclosures"] = (normalized["disclosure_count"] > 0 or
                                        details.get("disclosureFlag", "N") == "Y" or
                                        details.get("iaDisclosureFlag", "N") == "Y")
        
        # Extract exams
        state_exams = details.get("stateExamCategory", [])
        principal_exams = details.get("principalExamCategory", [])
        product_exams = details.get("productExamCategory", [])
        
        for exam_list in [state_exams, principal_exams, product_exams]:
            if isinstance(exam_list, list):
                for exam in exam_list:
                    if isinstance(exam, dict):
                        normalized["exams"].append(extract_exam_info(exam))
        
        # Extract registrations
        registrations = details.get("registeredStates", []) + details.get("registeredSROs", [])
        if isinstance(registrations, list):
            for reg in registrations:
                if isinstance(reg, dict):
                    normalized["registrations"].append(extract_registration_info(reg))
        
        return normalized
    except Exception as e:
        print(f"Error normalizing individual details: {e}")
        return {}

def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("Usage: python test_individual.py <crd_number>")
        sys.exit(1)
    
    crd_number = sys.argv[1]
    details = fetch_individual_by_crd(crd_number)
    
    if details:
        normalized = normalize_individual_details(details)
        print("\nNormalized Individual Details:")
        print(json.dumps(normalized, indent=2))
    else:
        print(f"No details found for individual CRD: {crd_number}")

if __name__ == "__main__":
    main()