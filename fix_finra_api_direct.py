#!/usr/bin/env python3
"""
Direct script to fix the URL format in the FINRA BrokerCheck agent.
This script makes targeted changes to the search_firm_by_crd and search_entity methods.
"""

import os
import shutil

def backup_file(file_path):
    """Create a backup of the file."""
    backup_path = f"{file_path}.bak"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")

def fix_finra_agent():
    """Fix the FINRA agent code."""
    file_path = "agents/finra_firm_broker_check_agent.py"
    
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found")
        return
    
    # Create backup
    backup_file(file_path)
    
    # Read the file
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Fix search_firm_by_crd method
    in_search_firm_by_crd = False
    url_line_index = None
    params_line_index = None
    
    for i, line in enumerate(lines):
        if "def search_firm_by_crd" in line:
            in_search_firm_by_crd = True
        
        if in_search_firm_by_crd and 'url = BROKERCHECK_CONFIG["firm_search_url"]' in line:
            url_line_index = i
        
        if in_search_firm_by_crd and '"query": crd_number' in line:
            params_line_index = i
            break
    
    if url_line_index is not None and params_line_index is not None:
        # Replace the URL line with the correct format
        lines[url_line_index] = '            url = f"{BROKERCHECK_CONFIG[\\"firm_search_url\\"]}/{crd_number}"\n'
        # Replace the params line to remove the query parameter
        lines[params_line_index] = '            params = BROKERCHECK_CONFIG["default_params"]\n'
        print("Fixed search_firm_by_crd method")
    else:
        print("Could not find search_firm_by_crd method URL and params lines")
    
    # Fix search_entity method
    in_search_entity = False
    url_line_index = None
    params_line_index = None
    response_line_index = None
    
    for i, line in enumerate(lines):
        if "def search_entity" in line:
            in_search_entity = True
        
        if in_search_entity and 'url = BROKERCHECK_CONFIG["firm_search_url"] if entity_type.lower() == "firm" else BROKERCHECK_CONFIG["entity_search_url"]' in line:
            url_line_index = i
        
        if in_search_entity and '"query": crd_number' in line:
            params_line_index = i
        
        if in_search_entity and 'response = self.session.get(url, params=params)' in line:
            response_line_index = i
            break
    
    if url_line_index is not None and params_line_index is not None and response_line_index is not None:
        # Replace the URL line with the correct format
        lines[url_line_index] = '            base_url = f\'{BROKERCHECK_CONFIG["firm_search_url"]}/{crd_number}\' if entity_type.lower() == "firm" else \\\n                f\'{BROKERCHECK_CONFIG["entity_search_url"]}/{crd_number}\'\n'
        # Replace the params line to remove the query parameter
        lines[params_line_index] = '            params = dict(BROKERCHECK_CONFIG["default_params"])\n'
        # Replace the response line to use base_url instead of url
        lines[response_line_index] = '            response = self.session.get(base_url, params=params)\n'
        print("Fixed search_entity method")
    else:
        print("Could not find search_entity method URL, params, and response lines")
    
    # Add User-Agent header to the session initialization
    in_init = False
    session_line_index = None
    
    for i, line in enumerate(lines):
        if "def __init__" in line:
            in_init = True
        
        if in_init and "self.session = requests.Session()" in line:
            session_line_index = i
            break
    
    if session_line_index is not None:
        # Add User-Agent header after session initialization
        user_agent_lines = [
            '        # Add User-Agent header to avoid potential blocking\n',
            '        self.session.headers.update({\n',
            '            \'User-Agent\': \'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36\'\n',
            '        })\n'
        ]
        lines[session_line_index:session_line_index+1] = [lines[session_line_index]] + user_agent_lines
        print("Added User-Agent header to session initialization")
    else:
        print("Could not find session initialization line")
    
    # Add retry logic
    # First, add the retry_with_backoff decorator after rate_limit decorator
    in_rate_limit = False
    rate_limit_end_index = None
    
    for i, line in enumerate(lines):
        if "def rate_limit" in line:
            in_rate_limit = True
        
        if in_rate_limit and "return wrapper" in line and i+2 < len(lines) and "return wrapper" not in lines[i+1]:
            rate_limit_end_index = i+2
            break
    
    if rate_limit_end_index is not None:
        # Add retry_with_backoff decorator
        retry_decorator_lines = [
            '\n',
            'def retry_with_backoff(max_retries=3, backoff_factor=1.5):\n',
            '    """Retry decorator with exponential backoff."""\n',
            '    def decorator(func):\n',
            '        @wraps(func)\n',
            '        def wrapper(*args, **kwargs):\n',
            '            retries = 0\n',
            '            max_wait = 30  # Maximum wait time in seconds\n',
            '            while retries < max_retries:\n',
            '                try:\n',
            '                    return func(*args, **kwargs)\n',
            '                except (requests.exceptions.ConnectionError, ConnectionResetError) as e:\n',
            '                    retries += 1\n',
            '                    if retries >= max_retries:\n',
            '                        logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}: {e}")\n',
            '                        raise\n',
            '                    \n',
            '                    wait_time = min(backoff_factor * (2 ** (retries - 1)), max_wait)\n',
            '                    logger.warning(f"Connection error in {func.__name__}, retrying in {wait_time:.2f}s (attempt {retries}/{max_retries}): {e}")\n',
            '                    time.sleep(wait_time)\n',
            '            return func(*args, **kwargs)  # This line should never be reached\n',
            '        return wrapper\n',
            '    return decorator\n'
        ]
        lines[rate_limit_end_index:rate_limit_end_index] = retry_decorator_lines
        print("Added retry_with_backoff decorator")
    else:
        print("Could not find rate_limit decorator end")
    
    # Add retry decorator to methods
    methods = [
        ("@rate_limit\n    def search_firm(", "@rate_limit\n    @retry_with_backoff()\n    def search_firm("),
        ("@rate_limit\n    def search_firm_by_crd(", "@rate_limit\n    @retry_with_backoff()\n    def search_firm_by_crd("),
        ("@rate_limit\n    def get_firm_details(", "@rate_limit\n    @retry_with_backoff()\n    def get_firm_details("),
        ("@rate_limit\n    def search_entity(", "@rate_limit\n    @retry_with_backoff()\n    def search_entity("),
        ("@rate_limit\n    def search_entity_detailed_info(", "@rate_limit\n    @retry_with_backoff()\n    def search_entity_detailed_info(")
    ]
    
    for i, line in enumerate(lines):
        for old, new in methods:
            if old in line:
                lines[i] = line.replace(old, new)
                print(f"Added retry decorator to {old.strip()}")
    
    # Write the modified content back to the file
    with open(file_path, 'w') as f:
        f.writelines(lines)
    
    print(f"\nDone! The FINRA BrokerCheck agent has been updated to use the correct URL format.")
    print("The agent now also includes retry logic and User-Agent headers to handle connection errors.")

if __name__ == "__main__":
    fix_finra_agent()