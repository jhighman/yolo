#!/usr/bin/env python3
"""
Script to fix the URL format in the FINRA BrokerCheck agent.

This script modifies the search_firm_by_crd and search_entity methods
to use the correct URL format with the CRD in the path instead of as a query parameter.
"""

import os
import re
import shutil
from pathlib import Path

def backup_file(file_path):
    """Create a backup of the file."""
    backup_path = f"{file_path}.bak"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")

def fix_search_firm_by_crd_method(content):
    """Fix the search_firm_by_crd method to use the correct URL format."""
    # Find the search_firm_by_crd method
    pattern = r"def search_firm_by_crd\(self, crd_number: str, employee_number: Optional\[str\] = None\) -> List\[Dict\]:.*?try:.*?url = BROKERCHECK_CONFIG\[\"firm_search_url\"\].*?params = \{\*\*BROKERCHECK_CONFIG\[\"default_params\"\], \"query\": crd_number\}"
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        old_code = match.group(0)
        new_code = old_code.replace(
            'url = BROKERCHECK_CONFIG["firm_search_url"]\n            params = {**BROKERCHECK_CONFIG["default_params"], "query": crd_number}',
            'url = f"{BROKERCHECK_CONFIG["firm_search_url"]}/{crd_number}"\n            params = BROKERCHECK_CONFIG["default_params"]'
        )
        content = content.replace(old_code, new_code)
        print("Fixed search_firm_by_crd method")
    else:
        print("Could not find search_firm_by_crd method")
    
    return content

def fix_search_entity_method(content):
    """Fix the search_entity method to use the correct URL format."""
    # Find the search_entity method
    pattern = r"def search_entity\(self, crd_number: str, entity_type: str = \"individual\".*?# Select appropriate endpoint based on entity type.*?url = BROKERCHECK_CONFIG\[\"firm_search_url\"\] if entity_type\.lower\(\) == \"firm\" else BROKERCHECK_CONFIG\[\"entity_search_url\"\].*?params = dict\(BROKERCHECK_CONFIG\[\"default_params\"\]).*?params\[\"query\"\] = crd_number"
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        old_code = match.group(0)
        new_code = old_code.replace(
            'url = BROKERCHECK_CONFIG["firm_search_url"] if entity_type.lower() == "firm" else BROKERCHECK_CONFIG["entity_search_url"]\n        \n        logger.info(f"Starting FINRA BrokerCheck basic entity search ({entity_type})", extra=log_context)\n\n        if self.use_mock:\n            if entity_type.lower() == "firm":\n                result = get_mock_finra_firm_by_crd(crd_number)\n                logger.info(f"Found mock result for entity CRD: {crd_number} ({entity_type})", extra=log_context)\n                return result\n            # For individuals, we don\'t have mock data yet, so return None\n            logger.warning(f"No mock data available for individual CRD: {crd_number}", extra=log_context)\n            return None\n\n        try:\n            params = dict(BROKERCHECK_CONFIG["default_params"])\n            params["query"] = crd_number',
            'base_url = f\'{BROKERCHECK_CONFIG["firm_search_url"]}/{crd_number}\' if entity_type.lower() == "firm" else \\\n                f\'{BROKERCHECK_CONFIG["entity_search_url"]}/{crd_number}\'\n        \n        logger.info(f"Starting FINRA BrokerCheck basic entity search ({entity_type})", extra=log_context)\n\n        if self.use_mock:\n            if entity_type.lower() == "firm":\n                result = get_mock_finra_firm_by_crd(crd_number)\n                logger.info(f"Found mock result for entity CRD: {crd_number} ({entity_type})", extra=log_context)\n                return result\n            # For individuals, we don\'t have mock data yet, so return None\n            logger.warning(f"No mock data available for individual CRD: {crd_number}", extra=log_context)\n            return None\n\n        try:\n            params = dict(BROKERCHECK_CONFIG["default_params"])'
        )
        
        # Also fix the response line to use base_url instead of url
        new_code = new_code.replace(
            'response = self.session.get(url, params=params)',
            'response = self.session.get(base_url, params=params)'
        )
        
        content = content.replace(old_code, new_code)
        print("Fixed search_entity method")
    else:
        print("Could not find search_entity method")
    
    return content

def add_user_agent_header(content):
    """Add User-Agent header to the session initialization."""
    pattern = r"self\.session = requests\.Session\(\)"
    replacement = """self.session = requests.Session()
        # Add User-Agent header to avoid potential blocking
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })"""
    
    content = content.replace(pattern, replacement)
    print("Added User-Agent header to session initialization")
    
    return content

def add_retry_logic(content):
    """Add retry logic for connection errors."""
    # Add retry decorator after rate_limit decorator
    retry_decorator = """
def retry_with_backoff(max_retries=3, backoff_factor=1.5):
    '''Retry decorator with exponential backoff.'''
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            max_wait = 30  # Maximum wait time in seconds
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except (requests.exceptions.ConnectionError, ConnectionResetError) as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}: {e}")
                        raise
                    
                    wait_time = min(backoff_factor * (2 ** (retries - 1)), max_wait)
                    logger.warning(f"Connection error in {func.__name__}, retrying in {wait_time:.2f}s (attempt {retries}/{max_retries}): {e}")
                    time.sleep(wait_time)
            return func(*args, **kwargs)  # This line should never be reached
        return wrapper
    return decorator
"""
    
    pattern = r"def rate_limit\(func\):.*?return wrapper\n"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        insert_pos = match.end()
        content = content[:insert_pos] + retry_decorator + content[insert_pos:]
        print("Added retry_with_backoff decorator")
    else:
        print("Could not find rate_limit decorator")
    
    # Add retry decorator to methods
    methods = [
        r"@rate_limit\n    def search_firm\(",
        r"@rate_limit\n    def search_firm_by_crd\(",
        r"@rate_limit\n    def get_firm_details\(",
        r"@rate_limit\n    def search_entity\(",
        r"@rate_limit\n    def search_entity_detailed_info\("
    ]
    
    for method in methods:
        content = content.replace(
            method,
            f"@rate_limit\n    @retry_with_backoff()\n    def {method.split('def ')[1]}"
        )
    
    print("Added retry decorators to all methods")
    
    return content

def main():
    """Main function."""
    file_path = "agents/finra_firm_broker_check_agent.py"
    
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found")
        return
    
    # Create backup
    backup_file(file_path)
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix the methods
    content = fix_search_firm_by_crd_method(content)
    content = fix_search_entity_method(content)
    
    # Add User-Agent header
    content = add_user_agent_header(content)
    
    # Add retry logic
    content = add_retry_logic(content)
    
    # Write the modified content back to the file
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"\nDone! The FINRA BrokerCheck agent has been updated to use the correct URL format.")
    print("The agent now also includes retry logic and User-Agent headers to handle connection errors.")

if __name__ == "__main__":
    main()