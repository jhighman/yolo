#!/usr/bin/env python3
"""
Test script to verify that "not found" search results are properly cached.
This test ensures that searches that return no results are cached for audit purposes.
"""

import sys
import os
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

import json
from services.firm_marshaller import (
    fetch_finra_firm_search,
    fetch_finra_firm_by_crd,
    fetch_sec_firm_search,
    fetch_sec_firm_by_crd,
    ResponseStatus,
    CACHE_FOLDER
)

def test_not_found_caching():
    """Test that 'not found' search results are properly cached."""
    print("\n=== Testing Not Found Result Caching ===\n")
    
    # Use a unique subject ID for this test to avoid cache conflicts
    subject_id = "TEST_NOT_FOUND_CACHE"
    
    # Test cases with firm names and CRD numbers that should not exist
    test_cases = [
        {
            "type": "name search",
            "firm_id": "nonexistent_firm_1",
            "params": {"firm_name": "XYZ123NonExistentFirmName"},
            "fetcher": fetch_finra_firm_search
        },
        {
            "type": "CRD search",
            "firm_id": "nonexistent_crd_1",
            "params": {"crd_number": "99999999"},
            "fetcher": fetch_finra_firm_by_crd
        },
        {
            "type": "SEC name search",
            "firm_id": "nonexistent_sec_firm_1",
            "params": {"firm_name": "XYZ123NonExistentSECFirmName"},
            "fetcher": fetch_sec_firm_search
        },
        {
            "type": "SEC CRD search",
            "firm_id": "nonexistent_sec_crd_1",
            "params": {"crd_number": "88888888"},
            "fetcher": fetch_sec_firm_by_crd
        }
    ]
    
    for case in test_cases:
        print(f"\nTesting {case['type']} with {case['params']}")
        
        # First search - should fetch from API and cache the not found result
        response = case["fetcher"](subject_id, case["firm_id"], case["params"])
        
        print(f"First search status: {response.status.value}")
        print(f"First search message: {response.message}")
        print(f"First search metadata: {response.metadata}")
        
        if response.status != ResponseStatus.NOT_FOUND:
            print(f"WARNING: Expected NOT_FOUND status, got {response.status.value}")
        
        # Second search - should retrieve from cache
        response2 = case["fetcher"](subject_id, case["firm_id"], case["params"])
        
        print(f"Second search status: {response2.status.value}")
        print(f"Second search message: {response2.message}")
        print(f"Second search metadata: {response2.metadata}")
        
        if response2.status != ResponseStatus.NOT_FOUND:
            print(f"WARNING: Expected NOT_FOUND status on cached result, got {response2.status.value}")
        
        if response2.metadata and response2.metadata.get("cache") == "hit":
            print("SUCCESS: Not found result was properly cached and retrieved")
        else:
            print("ERROR: Not found result was not cached properly")
        
        # Check the cache files directly
        agent_name = "FINRA_FirmBrokerCheck_Agent" if "finra" in str(case["fetcher"]).lower() else "SEC_FirmIAPD_Agent"
        service = "search_firm" if "name" in case["type"] else "search_firm_by_crd"
        cache_path = CACHE_FOLDER / subject_id / agent_name / service / case["firm_id"]
        
        if cache_path.exists():
            print(f"Cache directory exists: {cache_path}")
            json_files = list(cache_path.glob("*.json"))
            
            if json_files:
                print(f"Found {len(json_files)} cached JSON files")
                for file_path in json_files:
                    try:
                        with file_path.open("r") as f:
                            cached_data = json.load(f)
                            print(f"Cached data in {file_path.name}: {json.dumps(cached_data, indent=2)}")
                    except Exception as e:
                        print(f"Error reading cache file {file_path}: {e}")
            else:
                print("ERROR: No JSON files found in cache directory")
        else:
            print(f"ERROR: Cache directory does not exist: {cache_path}")

if __name__ == "__main__":
    test_not_found_caching()