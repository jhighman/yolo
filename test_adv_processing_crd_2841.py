#!/usr/bin/env python3

import os
import json
from agents.adv_processing_agent import adv_processing_agent

def test_adv_processing_crd_2841():
    """Test ADV PDF processing for CRD 2841."""
    print("Testing ADV PDF processing for CRD 2841...")
    
    # Set up test parameters
    subject_id = "TEST-ADV-PROCESSING-CRD-2841"
    crd_number = "2841"
    entity_data = {
        "has_adv_pdf": True,
        "firm_name": "Test Firm CRD 2841"
    }
    
    # Process the ADV
    result = adv_processing_agent.process_adv(subject_id, crd_number, entity_data)
    
    # Print the result
    print("\nADV Evaluation Results:")
    print(json.dumps(result, indent=2))
    
    # Check if the ADV PDF was downloaded successfully
    if result["adv_status"] == "available":
        print(f"\n✅ SUCCESS: ADV PDF downloaded to {result['adv_path']}")
        print(f"File size: {os.path.getsize(result['adv_path'])} bytes")
    else:
        print(f"\n❌ FAILURE: ADV PDF download failed: {result.get('compliance_explanation', 'Unknown error')}")
        return
    
    # Check if AUM information was extracted successfully
    if "aum_info" in result:
        print(f"\n✅ SUCCESS: AUM information saved to {result['adv_json_path']}")
        print("\nExtracted AUM Information:")
        print(json.dumps(result["aum_info"], indent=2))
        
        # Check if all required fields are present
        required_fields = [
            "reported_aum", "aum_range", "as_of_date", "aum_type",
            "source_section", "compliance_rationale",
            "registration_implication", "update_trigger"
        ]
        
        missing_fields = [field for field in required_fields if field not in result["aum_info"]]
        
        if missing_fields:
            print(f"\n❌ FAILURE: AUM information is missing fields: {', '.join(missing_fields)}")
        else:
            print("\n✅ SUCCESS: AUM information has all expected fields")
    else:
        print("\n❌ FAILURE: No AUM information extracted")

if __name__ == "__main__":
    test_adv_processing_crd_2841()