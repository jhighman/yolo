#!/usr/bin/env python3
"""
Script to add retry logic to the SEC and FINRA agent code.
This will make the API requests more resilient to connection errors.
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

def add_retry_logic_to_sec_agent():
    """Add retry logic to the SEC agent code."""
    file_path = "agents/sec_firm_iapd_agent.py"
    
    # Create backup
    backup_file(file_path)
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Add retry decorator
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
    
    # Insert retry decorator after rate_limit decorator
    pattern = r"def rate_limit\(func\):.*?return wrapper\n"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        insert_pos = match.end()
        content = content[:insert_pos] + retry_decorator + content[insert_pos:]
    
    # Add retry decorator to search_firm method
    pattern = r"@rate_limit\n    def search_firm\("
    content = content.replace(pattern, "@rate_limit\n    @retry_with_backoff()\n    def search_firm(")
    
    # Add retry decorator to search_firm_by_crd method
    pattern = r"@rate_limit\n    def search_firm_by_crd\("
    content = content.replace(pattern, "@rate_limit\n    @retry_with_backoff()\n    def search_firm_by_crd(")
    
    # Add retry decorator to get_firm_details method
    pattern = r"@rate_limit\n    def get_firm_details\("
    content = content.replace(pattern, "@rate_limit\n    @retry_with_backoff()\n    def get_firm_details(")
    
    # Write modified content back to file
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"Added retry logic to {file_path}")

def add_retry_logic_to_finra_agent():
    """Add retry logic to the FINRA agent code."""
    file_path = "agents/finra_firm_broker_check_agent.py"
    
    # Create backup
    backup_file(file_path)
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Add retry decorator
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
    
    # Insert retry decorator after rate_limit decorator
    pattern = r"def rate_limit\(func\):.*?return wrapper\n"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        insert_pos = match.end()
        content = content[:insert_pos] + retry_decorator + content[insert_pos:]
    
    # Add retry decorator to search_firm method
    pattern = r"@rate_limit\n    def search_firm\("
    content = content.replace(pattern, "@rate_limit\n    @retry_with_backoff()\n    def search_firm(")
    
    # Add retry decorator to search_firm_by_crd method
    pattern = r"@rate_limit\n    def search_firm_by_crd\("
    content = content.replace(pattern, "@rate_limit\n    @retry_with_backoff()\n    def search_firm_by_crd(")
    
    # Add retry decorator to get_firm_details method
    pattern = r"@rate_limit\n    def get_firm_details\("
    content = content.replace(pattern, "@rate_limit\n    @retry_with_backoff()\n    def get_firm_details(")
    
    # Add retry decorator to search_entity method
    pattern = r"@rate_limit\n    def search_entity\("
    content = content.replace(pattern, "@rate_limit\n    @retry_with_backoff()\n    def search_entity(")
    
    # Add retry decorator to search_entity_detailed_info method
    pattern = r"@rate_limit\n    def search_entity_detailed_info\("
    content = content.replace(pattern, "@rate_limit\n    @retry_with_backoff()\n    def search_entity_detailed_info(")
    
    # Write modified content back to file
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"Added retry logic to {file_path}")

def add_user_agent_headers():
    """Add User-Agent headers to the requests to avoid potential blocking."""
    # SEC agent
    sec_file_path = "agents/sec_firm_iapd_agent.py"
    
    with open(sec_file_path, 'r') as f:
        sec_content = f.read()
    
    # Add User-Agent header to SEC agent
    pattern = r"self\.session = requests\.Session\(\)"
    replacement = """self.session = requests.Session()
        # Add User-Agent header to avoid potential blocking
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })"""
    sec_content = sec_content.replace(pattern, replacement)
    
    with open(sec_file_path, 'w') as f:
        f.write(sec_content)
    
    print(f"Added User-Agent header to {sec_file_path}")
    
    # FINRA agent
    finra_file_path = "agents/finra_firm_broker_check_agent.py"
    
    with open(finra_file_path, 'r') as f:
        finra_content = f.read()
    
    # Add User-Agent header to FINRA agent
    finra_content = finra_content.replace(pattern, replacement)
    
    with open(finra_file_path, 'w') as f:
        f.write(finra_content)
    
    print(f"Added User-Agent header to {finra_file_path}")

def main():
    """Main function."""
    print("Adding retry logic and User-Agent headers to SEC and FINRA agents...")
    
    # Check if agent files exist
    sec_file_path = "agents/sec_firm_iapd_agent.py"
    finra_file_path = "agents/finra_firm_broker_check_agent.py"
    
    if not os.path.exists(sec_file_path):
        print(f"Error: {sec_file_path} not found")
        return
    
    if not os.path.exists(finra_file_path):
        print(f"Error: {finra_file_path} not found")
        return
    
    # Add retry logic
    add_retry_logic_to_sec_agent()
    add_retry_logic_to_finra_agent()
    
    # Add User-Agent headers
    add_user_agent_headers()
    
    print("\nDone! The agent code now has retry logic and User-Agent headers.")
    print("This should help handle connection errors in production.")
    print("\nIf you still experience issues, you can run the test_api_connections.py script to diagnose further.")

if __name__ == "__main__":
    main()