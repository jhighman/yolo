#!/usr/bin/env python3
"""
Test script to search for BROOKSTONE SECURITIES, INC with CRD #29116
using the FirmServicesFacade directly.
"""

import sys
import json
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from services.firm_services import FirmServicesFacade

def main():
    # Create a subject ID for testing
    subject_id = "TEST_BROOKSTONE"
    
    # Create the facade
    facade = FirmServicesFacade()
    
    # Search for BROOKSTONE SECURITIES, INC by CRD #29116
    print(f"\nSearching for firm by CRD: 29116")
    result = facade.search_firm_by_crd(subject_id, "29116")
    
    if result:
        print("\nSearch Result:")
        print(json.dumps(result, indent=2))
        
        # If found, get detailed information
        print("\nGetting detailed information:")
        details = facade.get_firm_details(subject_id, "29116")
        
        if details:
            print(json.dumps(details, indent=2))
            
            # Check for firm status and display appropriate message
            if 'firm_status' in details:
                print(f"\nFirm Status: {details['firm_status'].upper()}")
                
            if 'status_message' in details:
                print(f"\nStatus Message: {details['status_message']}")
        else:
            print("No details found")
    else:
        print("\nNo results found for CRD #29116")
    
    # Also try searching by name
    print("\nSearching for firm by name: BROOKSTONE SECURITIES, INC")
    name_results = facade.search_firm(subject_id, "BROOKSTONE SECURITIES, INC")
    
    if name_results:
        print("\nName Search Results:")
        print(json.dumps(name_results, indent=2))
    else:
        print("\nNo results found for name 'BROOKSTONE SECURITIES, INC'")

if __name__ == "__main__":
    main()