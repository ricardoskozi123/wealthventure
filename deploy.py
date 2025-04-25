#!/usr/bin/env python3
"""
Enhanced deployment script for OMCRM
This script packages the application for deployment while respecting .gitignore settings
Usage: python deploy.py user@server_ip [--password PASSWORD]
"""

import os
import sys
import time
import subprocess
import tempfile
import shutil

def read_gitignore():
    """Read .gitignore file and parse patterns"""
    patterns = []
    if os.path.exists('.gitignore'):
        with open('.gitignore', 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith('#'):
                    # Handle negation patterns (files to include)
                    if line.startswith('!'):
                        continue  # We'll handle these separately
                    # Replace directory indicator with proper exclude pattern
                    if line.endswith('/'):
                        line = line[:-1]
                    patterns.append(line)
    return patterns

def main():
    if len(sys.argv) < 2:
        print("Usage: python deploy.py user@server_ip [--password PASSWORD]")
        sys.exit(1)
    
    server = sys.argv[1]
    
    # Check if password is provided
    password = None
    if len(sys.argv) > 3 and sys.argv[2] == '--password':
        password = sys.argv[3]
    
    # Create deployment package
    print("Creating deployment package...")
    
    # Get exclusions from .gitignore
    gitignore_patterns = read_gitignore()
    
    # Additional excludes not in .gitignore
    additional_excludes = [
        '.git',
        '.github',
        'deploy.py',
        'omcrm_deploy.tar.gz'
    ]
    
    # Combine all excludes
    excludes = list(set(gitignore_patterns + additional_excludes))
    
    # Create exclude args for tar
    exclude_args = ' '.join([f'--exclude="{x}"' for x in excludes])
    
    # Create tarball
    tar_cmd = f'tar -czf omcrm_deploy.tar.gz {exclude_args} .'
    print(f"Running: {tar_cmd}")
    
    # Execute tar command
    result = os.system(tar_cmd)
    if result != 0:
        print("Error creating tarball. Check your .gitignore file for invalid patterns.")
        sys.exit(1)
    
    print(f"Deployment package created: omcrm_deploy.tar.gz ({os.path.getsize('omcrm_deploy.tar.gz') / (1024*1024):.2f} MB)")
    
    # Transfer to server
    if input("\nTransfer to server? (y/n): ").lower() == 'y':
        print(f"Transferring to {server}...")
        
        # Determine whether to use sshpass with password
        transfer_cmd = f"scp omcrm_deploy.tar.gz {server}:~/"
        
        if password:
            # Use sshpass if available
            if subprocess.run(['which', 'sshpass'], capture_output=True).returncode == 0:
                transfer_cmd = f"sshpass -p '{password}' {transfer_cmd}"
            else:
                print("Warning: sshpass not installed. You'll need to enter the password manually.")
        
        # Execute transfer command
        print(f"Running: {transfer_cmd}")
        result = os.system(transfer_cmd)
        
        if result == 0:
            print("Transfer complete!")
            
            # Instructions for server-side deployment
            print("\nServer-side deployment steps:")
            print(f"1. SSH into your server: ssh {server}")
            print("2. Extract the package: mkdir -p /var/www/omcrm && tar -xzf ~/omcrm_deploy.tar.gz -C /var/www/omcrm")
            print("3. Follow the steps in deployment_steps.md to complete the setup")
            
            # Remote deployment option
            if input("\nWould you like to run the initial setup commands on the server? (y/n): ").lower() == 'y':
                print("Setting up application on the server...")
                
                # Basic setup commands
                setup_commands = [
                    "mkdir -p /var/www/omcrm",
                    "tar -xzf ~/omcrm_deploy.tar.gz -C /var/www/omcrm",
                    "cd /var/www/omcrm",
                    "python3 -m venv venv",
                    "source venv/bin/activate",
                    "pip install -r requirements.txt",
                    "echo 'Setup completed. You can now follow the remaining steps in deployment_steps.md'"
                ]
                
                # Join commands with && to ensure they run in sequence
                remote_cmd = f"ssh {server} \"{' && '.join(setup_commands)}\""
                
                if password:
                    # Use sshpass if available
                    if subprocess.run(['which', 'sshpass'], capture_output=True).returncode == 0:
                        remote_cmd = f"sshpass -p '{password}' {remote_cmd}"
                
                print(f"Running remote setup...")
                os.system(remote_cmd)
        else:
            print("Error transferring package. Check your server connection details.")
    
    print("Deployment preparation complete")

if __name__ == "__main__":
    main() 