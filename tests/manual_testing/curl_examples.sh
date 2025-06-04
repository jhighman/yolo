#!/bin/bash
# Curl examples for testing the Firm Compliance Claim Processing API

# Example 1: Process a claim with basic mode - Able Wealth Management
curl -X POST "http://localhost:8000/process-claim-basic" \
  -H "Content-Type: application/json" \
  -d '{
    "_id": {"$oid":"67bcdac22e749a352e23befe"},
    "type": "Thing/Other",
    "workProduct": "WP24-0037036",
    "entity": "EN-114236",
    "entityName": "Able Wealth Management, LLC",
    "name": "Able Wealth Management, LLC",
    "normalizedName": "ablewealthmanagementllc",
    "principal": "Able Wealth Management, LLC,",
    "street1": "695 Cross Street",
    "city": "Lakewood",
    "state": "New Jersey",
    "zip": "8701",
    "taxID": "",
    "organizationCRD": "298085",
    "status": "",
    "notes": "",
    "reference_id": "test-ref-001",
    "business_ref": "BIZ_001",
    "business_name": "Able Wealth Management, LLC",
    "tax_id": "123456789"
  }'

# Example 2: Process a claim with basic mode - Adell, Harriman & Carpenter
curl -X POST "http://localhost:8000/process-claim-basic" \
  -H "Content-Type: application/json" \
  -d '{
    "_id": {"$oid":"67bcdac22e749a352e23beff"},
    "type": "Thing/Other",
    "workProduct": "WP24-0037424",
    "entity": "EN-017252",
    "entityName": "Adell, Harriman & Carpenter, Inc.",
    "name": "Adell, Harriman & Carpenter, Inc.",
    "normalizedName": "adellharrimancarpenterinc",
    "principal": "Adell, Harriman & Carpenter, Inc.,",
    "street1": "2700 Post Oak Blvd. Suite 1200",
    "city": "Houston",
    "state": "Texas",
    "zip": "77056",
    "taxID": "",
    "organizationCRD": "107488",
    "status": "",
    "notes": "",
    "reference_id": "test-ref-002",
    "business_ref": "BIZ_002",
    "business_name": "Adell, Harriman & Carpenter, Inc.",
    "tax_id": "987654321"
  }'

# Example 3: Process a claim with basic mode - ALLIANCE GLOBAL PARTNERS
curl -X POST "http://localhost:8000/process-claim-basic" \
  -H "Content-Type: application/json" \
  -d '{
    "_id": {"$oid":"67bcdac22e749a352e23bf00"},
    "type": "Thing/Other",
    "workProduct": "WP24-0036284",
    "entity": "EN-109946",
    "entityName": "ALLIANCE GLOBAL PARTNERS, LLC",
    "name": "ALLIANCE GLOBAL PARTNERS, LLC",
    "normalizedName": "allianceglobalpartnersllc",
    "principal": "ALLIANCE GLOBAL PARTNERS, LLC,",
    "street1": "88 Post Road West",
    "city": "Westport",
    "state": "Connecticut",
    "zip": "6880",
    "taxID": "",
    "organizationCRD": "8361",
    "status": "",
    "notes": "",
    "reference_id": "test-ref-003",
    "business_ref": "BIZ_003",
    "business_name": "ALLIANCE GLOBAL PARTNERS, LLC",
    "tax_id": "456789123"
  }'

# Get available processing modes
curl -X GET "http://localhost:8000/processing-modes"

# List cache for a specific business
curl -X GET "http://localhost:8000/cache/list?business_ref=BIZ_001"

# Get the latest compliance report for a business
curl -X GET "http://localhost:8000/compliance/latest/BIZ_001"

# Get a compliance report by reference ID
curl -X GET "http://localhost:8000/compliance/by-ref/BIZ_001/test-ref-001"

# List all compliance reports
curl -X GET "http://localhost:8000/compliance/list"

# Clear cache for a specific business
curl -X POST "http://localhost:8000/cache/clear/BIZ_001"