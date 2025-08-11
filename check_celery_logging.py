#!/usr/bin/env python3
"""
Diagnostic script to check for common issues that might cause Celery logging errors.
This script checks:
1. Disk space
2. Log directory permissions
3. Log file permissions
4. Ability to write to log files
"""

import os
import sys
import shutil
import logging
import subprocess
from pathlib import Path

def check_disk_space():
    """Check disk space on all mounted filesystems."""
    print("\n=== DISK SPACE CHECK ===")
    try:
        # Use df command to get disk usage
        df_output = subprocess.check_output(['df', '-h']).decode('utf-8')
        print(df_output)
        
        # Check for filesystems with high usage (>90%)
        for line in df_output.splitlines()[1:]:  # Skip header
            parts = line.split()
            if len(parts) >= 5:
                usage = parts[4].rstrip('%')
                if usage.isdigit() and int(usage) > 90:
                    print(f"WARNING: High disk usage ({parts[4]}) on {parts[5] if len(parts) > 5 else parts[0]}")
    except Exception as e:
        print(f"Error checking disk space: {e}")

def check_log_directories():
    """Check log directory structure and permissions."""
    print("\n=== LOG DIRECTORY CHECK ===")
    
    # Get the current directory (where the script is run from)
    current_dir = os.getcwd()
    print(f"Current working directory: {current_dir}")
    
    # Check for logs directory
    log_dirs = [
        os.path.join(current_dir, "logs"),
        os.path.join(current_dir, "logs", "core"),
        os.path.join(current_dir, "logs", "services"),
        os.path.join(current_dir, "logs", "agents"),
        os.path.join(current_dir, "logs", "evaluation"),
        os.path.join(current_dir, "logs", "webhooks")
    ]
    
    for log_dir in log_dirs:
        if os.path.exists(log_dir):
            print(f"Directory exists: {log_dir}")
            # Check permissions
            stat_info = os.stat(log_dir)
            print(f"  Owner: {stat_info.st_uid}, Group: {stat_info.st_gid}")
            print(f"  Permissions: {oct(stat_info.st_mode)[-3:]}")
            
            # Check if writable
            if os.access(log_dir, os.W_OK):
                print(f"  Directory is writable")
            else:
                print(f"  WARNING: Directory is not writable")
                
            # List log files
            log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
            print(f"  Log files: {log_files}")
            
            # Check log file permissions
            for log_file in log_files:
                log_path = os.path.join(log_dir, log_file)
                try:
                    stat_info = os.stat(log_path)
                    print(f"  File: {log_file}")
                    print(f"    Owner: {stat_info.st_uid}, Group: {stat_info.st_gid}")
                    print(f"    Permissions: {oct(stat_info.st_mode)[-3:]}")
                    print(f"    Size: {stat_info.st_size} bytes")
                    
                    # Check if writable
                    if os.access(log_path, os.W_OK):
                        print(f"    File is writable")
                    else:
                        print(f"    WARNING: File is not writable")
                except Exception as e:
                    print(f"    Error checking file {log_file}: {e}")
        else:
            print(f"WARNING: Directory does not exist: {log_dir}")

def test_log_writing():
    """Test writing to log files."""
    print("\n=== LOG WRITING TEST ===")
    
    # Get the current directory
    current_dir = os.getcwd()
    
    # Define log directories to test
    log_dirs = [
        os.path.join(current_dir, "logs", "core"),
        os.path.join(current_dir, "logs", "services"),
        os.path.join(current_dir, "logs", "agents"),
        os.path.join(current_dir, "logs", "evaluation"),
        os.path.join(current_dir, "logs", "webhooks")
    ]
    
    for log_dir in log_dirs:
        if not os.path.exists(log_dir):
            print(f"Directory does not exist, skipping: {log_dir}")
            continue
            
        test_log_file = os.path.join(log_dir, "test_write.log")
        try:
            with open(test_log_file, 'w') as f:
                f.write("Test log entry\n")
            print(f"Successfully wrote to test file: {test_log_file}")
            
            # Clean up test file
            os.remove(test_log_file)
            print(f"Successfully removed test file: {test_log_file}")
        except Exception as e:
            print(f"ERROR writing to {test_log_file}: {e}")

def check_running_processes():
    """Check for running Celery processes."""
    print("\n=== CELERY PROCESS CHECK ===")
    try:
        # Use ps command to find Celery processes
        ps_output = subprocess.check_output(['ps', 'aux']).decode('utf-8')
        celery_processes = [line for line in ps_output.splitlines() if 'celery' in line]
        
        if celery_processes:
            print("Found Celery processes:")
            for process in celery_processes:
                print(process)
        else:
            print("No Celery processes found")
    except Exception as e:
        print(f"Error checking processes: {e}")

def check_file_descriptors():
    """Check open file descriptors for the current process."""
    print("\n=== FILE DESCRIPTOR CHECK ===")
    try:
        # Get current process ID
        pid = os.getpid()
        print(f"Current process ID: {pid}")
        
        # Check open file descriptors
        lsof_output = subprocess.check_output(['lsof', '-p', str(pid)]).decode('utf-8')
        print("Open file descriptors:")
        print(lsof_output)
    except Exception as e:
        print(f"Error checking file descriptors: {e}")

def main():
    """Run all checks."""
    print("=== CELERY LOGGING DIAGNOSTIC TOOL ===")
    print(f"Python version: {sys.version}")
    print(f"Current user: {os.getlogin() if hasattr(os, 'getlogin') else 'Unknown'}")
    
    check_disk_space()
    check_log_directories()
    test_log_writing()
    check_running_processes()
    
    try:
        check_file_descriptors()
    except Exception:
        print("Could not check file descriptors (lsof may not be installed)")
    
    print("\n=== DIAGNOSTIC COMPLETE ===")
    print("Run this script on the server experiencing Celery logging issues.")
    print("Look for WARNING or ERROR messages in the output.")

if __name__ == "__main__":
    main()