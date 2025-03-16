"""
Configuration module for batch processing of business entity compliance claims.
Defines canonical fields for business data and default settings for claim evaluation.
"""

import json
import logging
import os
from typing import Dict, Any

logger = logging.getLogger('firm_main_config')

DEFAULT_WAIT_TIME = 7.0

# Canonical fields for business entities, updated with new fields from sample data
canonical_fields = {
    'reference_id': ['referenceId', 'Reference ID', 'reference_id', 'ref_id', 'RefID'],
    'work_product': ['workProduct', 'Work Product', 'work_product', 'workProductNo', 'WP'],  # New: from "workProduct"
    'business_ref': ['businessRef', 'Business Ref', 'business_ref', 'biz_id', 'BusinessID', 'entity'],  # Updated: added 'entity'
    'business_name': ['businessName', 'Business Name', 'business_name', 'firm_name', 'company_name', 'entityName', 'name'],  # Updated: added 'entityName', 'name'
    'normalized_name': ['normalizedName', 'Normalized Name', 'normalized_name'],  # New: from "normalizedName"
    'principal': ['principal', 'Principal', 'principal_name'],  # New: from "principal"
    'tax_id': ['taxId', 'Tax ID', 'tax_id', 'ein', 'EIN', 'taxID'],  # Updated: added 'taxID'
    'organization_crd': ['orgCRD', 'Organization CRD', 'org_crd_number', 'firm_crd', 'organizationCRD', 'organization_crd', 'organizationCrdNumber', 'crd_number'],  # Updated: added 'crd_number' as an alias
    'organization_name': ['orgName', 'Organization Name', 'organization_name', 'firm_name', 'organizationName'],
    'address_line1': ['addressLine1', 'Address Line 1', 'address_line1', 'addressLineOne', 'street1'],  # Updated: added 'street1'
    'address_line2': ['addressLine2', 'Address Line 2', 'address_line2', 'addressLineTwo'],
    'city': ['city', 'City'],
    'state': ['state', 'State', 'state_code', 'stateCode', 'StateName'],  # Updated: added 'StateName' for "New Jersey"
    'zip': ['zip', 'Zip', 'zipcode', 'postalCode', 'postal_code'],
    'country': ['country', 'Country'],
    'status': ['status', 'Status', 'business_status'],  # New: from "status"
    'notes': ['notes', 'Notes', 'comments'],  # New: from "notes"
    'business_unit': ['businessUnit', 'Business Unit', 'business_unit'],
    'location': ['location', 'Location', 'businessLocation', 'business_location'],
    'email': ['email', 'Email', 'emailAddress', 'email_address'],
    'phone': ['phone', 'Phone', 'phoneNumber', 'phone_number']
}

# Default configuration tailored to business entity compliance
DEFAULT_CONFIG = {
    "evaluate_search": True,          # Evaluate search results
    "evaluate_registration": True,    # Evaluate registration status
    "evaluate_disclosures": True,     # Evaluate disclosures
    "evaluate_financials": False,     # Skipped in basic mode
    "evaluate_legal": False,          # Skipped in basic mode
    "skip_financials": True,          # Maps to API's basic mode
    "skip_legal": True,               # Maps to API's basic mode
    "enabled_logging_groups": ["core"],
    "logging_levels": {"core": "INFO"}
}

INPUT_FOLDER = "drop"
OUTPUT_FOLDER = "output"
ARCHIVE_FOLDER = "archive"
CHECKPOINT_FILE = os.path.join(OUTPUT_FOLDER, "checkpoint.json")
CONFIG_FILE = "config.json"

def load_config(config_path: str = CONFIG_FILE) -> Dict[str, Any]:
    """
    Load configuration from a JSON file, falling back to defaults if not found.

    Args:
        config_path (str): Path to the config file (default: "config.json").

    Returns:
        Dict[str, Any]: Configuration dictionary with defaults merged with file settings.
    """
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            return {**DEFAULT_CONFIG, **config}
    except FileNotFoundError:
        logger.warning("Config file not found, using defaults")
        return DEFAULT_CONFIG
    except Exception as e:
        logger.error(f"Error loading config file {config_path}: {str(e)}")
        return DEFAULT_CONFIG

def save_config(config: Dict[str, Any], config_path: str = CONFIG_FILE):
    """
    Save configuration to a JSON file.

    Args:
        config (Dict[str, Any]): Configuration dictionary to save.
        config_path (str): Path to save the config file (default: "config.json").
    """
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"Saved settings to {config_path}: {config}")
    except Exception as e:
        logger.error(f"Error saving config to {config_path}: {str(e)}")