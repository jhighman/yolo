"""Mock data for FINRA and SEC agents.

This module contains mock data for testing and development purposes.
"""

MOCK_FIRMS = {
    "Baker Avenue Asset Management": {
        "finra": {
            "org_name": "Baker Avenue Asset Management",
            "org_source_id": "131940",
            "registration_status": "APPROVED",
            "addresses": [
                {
                    "address_type": "MAIN",
                    "street_1": "455 Market Street",
                    "street_2": "Suite 1870",
                    "city": "San Francisco",
                    "state": "CA",
                    "zip": "94105",
                    "country": "UNITED STATES"
                }
            ],
            "disclosures": []
        },
        "sec": {
            "org_name": "Baker Avenue Asset Management LP",
            "org_crd": "131940",
            "sec_number": "801-69103",
            "firm_type": "Investment Adviser",
            "registration_status": "ACTIVE",
            "addresses": [
                {
                    "address_type": "MAIN OFFICE",
                    "street_1": "455 Market Street",
                    "street_2": "Suite 1870",
                    "city": "San Francisco",
                    "state": "CA",
                    "zip": "94105",
                    "country": "UNITED STATES"
                }
            ],
            "disclosures": []
        }
    }
}

def get_mock_finra_search_results(firm_name: str) -> list:
    """Get mock FINRA search results for a firm name."""
    if firm_name in MOCK_FIRMS:
        firm_data = MOCK_FIRMS[firm_name]["finra"]
        return [{
            "org_name": firm_data["org_name"],
            "org_source_id": firm_data["org_source_id"],
            "registration_status": firm_data["registration_status"]
        }]
    return []

def get_mock_finra_firm_details(crd_number: str) -> dict:
    """Get mock FINRA firm details for a CRD number."""
    for firm_data in MOCK_FIRMS.values():
        if firm_data["finra"]["org_source_id"] == crd_number:
            return firm_data["finra"]
    return {}

def get_mock_finra_firm_by_crd(crd_number: str) -> dict:
    """Get mock FINRA firm search results by CRD number."""
    for firm_data in MOCK_FIRMS.values():
        if firm_data["finra"]["org_source_id"] == crd_number:
            return {
                "org_name": firm_data["finra"]["org_name"],
                "org_source_id": firm_data["finra"]["org_source_id"],
                "registration_status": firm_data["finra"]["registration_status"]
            }
    return {}

def get_mock_sec_search_results(firm_name: str) -> list:
    """Get mock SEC search results for a firm name."""
    if firm_name in MOCK_FIRMS:
        firm_data = MOCK_FIRMS[firm_name]["sec"]
        return [{
            "org_name": firm_data["org_name"],
            "org_crd": firm_data["org_crd"],
            "sec_number": firm_data["sec_number"],
            "firm_type": firm_data["firm_type"],
            "registration_status": firm_data["registration_status"]
        }]
    return []

def get_mock_sec_firm_details(crd_number: str) -> dict:
    """Get mock SEC firm details for a CRD number."""
    for firm_data in MOCK_FIRMS.values():
        if firm_data["sec"]["org_crd"] == crd_number:
            return firm_data["sec"]
    return {}

def get_mock_sec_firm_by_crd(crd_number: str) -> dict:
    """Get mock SEC firm search results by CRD number."""
    for firm_data in MOCK_FIRMS.values():
        if firm_data["sec"]["org_crd"] == crd_number:
            return {
                "org_name": firm_data["sec"]["org_name"],
                "org_crd": firm_data["sec"]["org_crd"],
                "sec_number": firm_data["sec"]["sec_number"],
                "firm_type": firm_data["firm_type"],
                "registration_status": firm_data["registration_status"]
            }
    return {} 