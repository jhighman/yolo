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
            "firm_ia_sec_number": "69103",
            "firm_ia_full_sec_number": "801-69103",
            "firm_other_names": [
                "BAKER AVENUE ASSET MANAGEMENT, LP",
                "BAKERAVENUE WEALTH MANAGEMENT",
                "BAKERAVENUE"
            ],
            "firm_type": "Investment Adviser",
            "registration_status": "ACTIVE",
            "firm_ia_scope": "ACTIVE",
            "firm_ia_disclosure_fl": "N",
            "firm_branches_count": 1,
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
    },
    "Able Wealth Management, LLC": {
        "finra": {
            "org_name": "Able Wealth Management, LLC",
            "org_source_id": "298085",
            "registration_status": "APPROVED",
            "addresses": [
                {
                    "address_type": "MAIN",
                    "street_1": "695 Cross Street",
                    "street_2": "",
                    "city": "Lakewood",
                    "state": "NJ",
                    "zip": "8701",
                    "country": "UNITED STATES"
                }
            ],
            "disclosures": []
        },
        "sec": {
            "org_name": "Able Wealth Management, LLC",
            "org_crd": "298085",
            "firm_ia_sec_number": "123456",
            "firm_ia_full_sec_number": "801-123456",
            "firm_other_names": [],
            "firm_type": "Investment Adviser",
            "registration_status": "ACTIVE",
            "firm_ia_scope": "ACTIVE",
            "firm_ia_disclosure_fl": "N",
            "firm_branches_count": 1,
            "addresses": [
                {
                    "address_type": "MAIN OFFICE",
                    "street_1": "695 Cross Street",
                    "street_2": "",
                    "city": "Lakewood",
                    "state": "NJ",
                    "zip": "8701",
                    "country": "UNITED STATES"
                }
            ],
            "disclosures": []
        }
    },
    "Adell, Harriman & Carpenter, Inc.": {
        "finra": {
            "org_name": "Adell, Harriman & Carpenter, Inc.",
            "org_source_id": "107488",
            "registration_status": "APPROVED",
            "addresses": [
                {
                    "address_type": "MAIN",
                    "street_1": "2700 Post Oak Blvd.",
                    "street_2": "Suite 1200",
                    "city": "Houston",
                    "state": "TX",
                    "zip": "77056",
                    "country": "UNITED STATES"
                }
            ],
            "disclosures": []
        },
        "sec": {
            "org_name": "Adell, Harriman & Carpenter, Inc.",
            "org_crd": "107488",
            "firm_ia_sec_number": "234567",
            "firm_ia_full_sec_number": "801-234567",
            "firm_other_names": [],
            "firm_type": "Investment Adviser",
            "registration_status": "ACTIVE",
            "firm_ia_scope": "ACTIVE",
            "firm_ia_disclosure_fl": "N",
            "firm_branches_count": 1,
            "addresses": [
                {
                    "address_type": "MAIN OFFICE",
                    "street_1": "2700 Post Oak Blvd.",
                    "street_2": "Suite 1200",
                    "city": "Houston",
                    "state": "TX",
                    "zip": "77056",
                    "country": "UNITED STATES"
                }
            ],
            "disclosures": []
        }
    },
    "BAKER STREET ADVISORS, LLC": {
        "finra": {
            "org_name": "BAKER STREET ADVISORS, LLC",
            "org_source_id": "128066",
            "registration_status": "APPROVED",
            "addresses": [
                {
                    "address_type": "MAIN",
                    "street_1": "575 MARKET STREET",
                    "street_2": "SUITE 600",
                    "city": "SAN FRANCISCO",
                    "state": "CA",
                    "zip": "94105",
                    "country": "UNITED STATES"
                }
            ],
            "disclosures": []
        },
        "sec": {
            "org_name": "BAKER STREET ADVISORS, LLC",
            "org_crd": "128066",
            "firm_ia_sec_number": "62370",
            "firm_ia_full_sec_number": "801-62370",
            "firm_other_names": [
                "BAKER STREET ADVISORS, LLC"
            ],
            "firm_type": "Investment Adviser",
            "registration_status": "ACTIVE",
            "firm_ia_scope": "ACTIVE",
            "firm_ia_disclosure_fl": "N",
            "firm_branches_count": 1,
            "addresses": [
                {
                    "address_type": "MAIN OFFICE",
                    "street_1": "575 MARKET STREET",
                    "street_2": "SUITE 600",
                    "city": "SAN FRANCISCO",
                    "state": "CA",
                    "zip": "94105",
                    "country": "UNITED STATES"
                }
            ],
            "disclosures": []
        }
    },
    "ALLIANCE GLOBAL PARTNERS, LLC": {
        "finra": {
            "org_name": "ALLIANCE GLOBAL PARTNERS, LLC",
            "org_source_id": "8361",
            "registration_status": "APPROVED",
            "addresses": [
                {
                    "address_type": "MAIN",
                    "street_1": "88 Post Road West",
                    "street_2": "",
                    "city": "Westport",
                    "state": "CT",
                    "zip": "6880",
                    "country": "UNITED STATES"
                }
            ],
            "disclosures": []
        },
        "sec": {
            "org_name": "ALLIANCE GLOBAL PARTNERS, LLC",
            "org_crd": "8361",
            "firm_ia_sec_number": "345678",
            "firm_ia_full_sec_number": "801-345678",
            "firm_other_names": [],
            "firm_type": "Investment Adviser",
            "registration_status": "ACTIVE",
            "firm_ia_scope": "ACTIVE",
            "firm_ia_disclosure_fl": "N",
            "firm_branches_count": 1,
            "addresses": [
                {
                    "address_type": "MAIN OFFICE",
                    "street_1": "88 Post Road West",
                    "street_2": "",
                    "city": "Westport",
                    "state": "CT",
                    "zip": "6880",
                    "country": "UNITED STATES"
                }
            ],
            "disclosures": []
        }
    }
}

SEC_FIRM_DETAILS = {
    "hits": {
        "total": 1,
        "hits": [{
            "_type": "_doc",
            "_source": {
                "iacontent": {
                    "basicInformation": {
                        "firmId": 131940,
                        "firmName": "BAKERAVENUE",
                        "otherNames": [
                            "BAKER AVENUE ASSET MANAGEMENT, LP",
                            "SIMONBAKER & PARTNERS LLC (RELYING ADVISER)",
                            "IRONWOOD CAPITAL MANAGEMENT, LLC",
                            "BAKERAVENUE WEALTH MANAGEMENT",
                            "BAKERAVENUE"
                        ],
                        "iaScope": "ACTIVE",
                        "isIAFirm": "Y",
                        "advFilingDate": "11/19/2024",
                        "hasPdf": "Y",
                        "iaSECNumber": "69103",
                        "iaSECNumberType": "801"
                    },
                    "iaFirmAddressDetails": {
                        "officeAddress": {
                            "street1": "ONE EMBARCADERO CENTER",
                            "street2": "STE 2530",
                            "city": "SAN FRANCISCO",
                            "state": "CA",
                            "country": "United States",
                            "postalCode": "94111"
                        }
                    },
                    "accountantSurpriseExams": [{
                        "accountantFirmName": "LILLING & COMPANY LLP",
                        "filingDate": "08/28/2024",
                        "fileStatus": "FILE"
                    }],
                    "registrationStatus": [{
                        "secJurisdiction": "SEC",
                        "status": "Approved",
                        "effectiveDate": "10/18/2004"
                    }],
                    "noticeFilings": [
                        {
                            "jurisdiction": "California",
                            "status": "Notice Filed",
                            "effectiveDate": "10/18/2004"
                        },
                        {
                            "jurisdiction": "New York",
                            "status": "Notice Filed",
                            "effectiveDate": "10/27/2008"
                        }
                    ],
                    "orgScopeStatusFlags": {
                        "isSECRegistered": "Y",
                        "isStateRegistered": "N",
                        "isERARegistered": "N",
                        "isSECERARegistered": "N",
                        "isStateERARegistered": "N"
                    },
                    "brochures": {
                        "part2ExemptFlag": "N",
                        "brochuredetails": [{
                            "brochureVersionID": 915673,
                            "brochureName": "ADV PART 2",
                            "dateSubmitted": "6/6/2024",
                            "lastConfirmed": "3/28/2024"
                        }]
                    }
                }
            }
        }]
    }
}

def get_mock_finra_search_results(firm_name: str) -> list:
    """Get mock FINRA search results for a firm name."""
    # First try exact match
    if firm_name in MOCK_FIRMS:
        firm_data = MOCK_FIRMS[firm_name]["finra"]
        return [{
            "org_name": firm_data["org_name"],
            "org_source_id": firm_data["org_source_id"],
            "registration_status": firm_data["registration_status"]
        }]
    
    # Try case-insensitive match
    firm_name_lower = firm_name.lower()
    for key, value in MOCK_FIRMS.items():
        if key.lower() == firm_name_lower:
            firm_data = value["finra"]
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
                "registration_status": firm_data["registration_status"]
            }
    return {}

def get_mock_sec_search_results(firm_name: str) -> list:
    """Get mock SEC search results for a firm name."""
    # First try exact match
    if firm_name in MOCK_FIRMS:
        firm_data = MOCK_FIRMS[firm_name]["sec"]
        return [{
            "org_name": firm_data["org_name"],
            "org_crd": firm_data["org_crd"],
            "firm_ia_sec_number": firm_data["firm_ia_sec_number"],
            "firm_ia_full_sec_number": firm_data["firm_ia_full_sec_number"],
            "firm_other_names": firm_data["firm_other_names"],
            "firm_type": firm_data["firm_type"],
            "registration_status": firm_data["registration_status"],
            "firm_ia_scope": firm_data["firm_ia_scope"],
            "firm_ia_disclosure_fl": firm_data["firm_ia_disclosure_fl"],
            "firm_branches_count": firm_data["firm_branches_count"]
        }]
    
    # Try case-insensitive match
    firm_name_lower = firm_name.lower()
    for key, value in MOCK_FIRMS.items():
        if key.lower() == firm_name_lower:
            firm_data = value["sec"]
            return [{
                "org_name": firm_data["org_name"],
                "org_crd": firm_data["org_crd"],
                "firm_ia_sec_number": firm_data["firm_ia_sec_number"],
                "firm_ia_full_sec_number": firm_data["firm_ia_full_sec_number"],
                "firm_other_names": firm_data["firm_other_names"],
                "firm_type": firm_data["firm_type"],
                "registration_status": firm_data["registration_status"],
                "firm_ia_scope": firm_data["firm_ia_scope"],
                "firm_ia_disclosure_fl": firm_data["firm_ia_disclosure_fl"],
                "firm_branches_count": firm_data["firm_branches_count"]
            }]
    
    return []

def get_mock_sec_firm_details(crd_number: str) -> dict:
    """Get mock SEC firm details by CRD number."""
    # For now, return the same SEC_FIRM_DETAILS for all CRD numbers
    # In a real implementation, we would have different details for each CRD
    if crd_number in ["131940", "298085", "107488", "8361", "128066"]:
        return SEC_FIRM_DETAILS
    return {}

def get_mock_sec_firm_by_crd(crd_number: str) -> dict:
    """Get mock SEC firm by CRD number."""
    for firm_data in MOCK_FIRMS.values():
        if firm_data.get('sec', {}).get('org_crd') == crd_number:
            return firm_data['sec']
    return {} 