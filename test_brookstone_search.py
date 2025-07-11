import json
from services.firm_services import FirmServicesFacade

def test_brookstone_search():
    """Test searching for BROOKSTONE SECURITIES, INC (CRD #29116)"""
    # Initialize services
    firm_services = FirmServicesFacade()
    
    # Search for firm by CRD
    crd_number = "29116"
    print(f"\nSearching for firm by CRD: {crd_number}")
    subject_id = "TEST_BROOKSTONE"
    firm_details = firm_services.search_firm_by_crd(subject_id, crd_number)
    
    print("\nSearch Result:")
    print(json.dumps(firm_details, indent=2))
    
    # Get detailed information
    print("\nGetting detailed information:")
    firm_details = firm_services.get_firm_details(subject_id, crd_number)
    print(json.dumps(firm_details, indent=2))
    
    if firm_details:
        print(f"\nFirm Status: {firm_details.get('firm_status', 'UNKNOWN').upper()}")
        print(f"\nStatus Message: {firm_details.get('status_message', 'N/A')}")
    else:
        print("\nFirm not found!")
    
    # Search for firm by name
    firm_name = "BROOKSTONE SECURITIES, INC"
    print(f"\nSearching for firm by name: {firm_name}")
    name_results = firm_services.search_firm(subject_id, firm_name)
    
    print("\nName Search Results:")
    print(json.dumps(name_results, indent=2))
    
    return firm_details

if __name__ == "__main__":
    test_brookstone_search()