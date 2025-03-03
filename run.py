#!/usr/bin/env python3
"""
Revision Timetable Runner Script
-------------------------------
Simple script to verify dependencies and start the application
"""

import sys
import subprocess
import os

def verify_dependencies():
    """Verify all required packages are installed"""
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if not os.path.exists(requirements_path):
        print("Error: requirements.txt not found!")
        sys.exit(1)

    # Read requirements file
    with open(requirements_path) as f:
        requirements = [line.strip().split('==')[0] for line in f if line.strip() and not line.startswith('#')]

    # Try to check installed packages 
    try:
        # First install setuptools if it's missing
        try:
            import pkg_resources
        except ImportError:
            print("Installing setuptools package...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'setuptools'])
            import pkg_resources
        
        # Check installed packages
        installed = {pkg.key for pkg in pkg_resources.working_set}
        missing = [pkg for pkg in requirements if pkg.lower() not in installed]
    except:
        # Fallback method - just try to import each package
        print("Using fallback method to check packages...")
        missing = []
        for pkg in requirements:
            try:
                __import__(pkg.split('>')[0].split('=')[0].lower())
            except ImportError:
                missing.append(pkg)

    if missing:
        print(f"Missing required packages: {', '.join(missing)}")
        print("Installing...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', requirements_path])
            print("All required packages installed successfully!")
        except subprocess.CalledProcessError:
            print("Error: Failed to install required packages!")
            sys.exit(1)
    
    return True

if __name__ == "__main__":
    # First verify dependencies
    if verify_dependencies():
        try:
            from app import app
            app.run(debug=True)
        except ImportError:
            print("Error: Could not import the application. Make sure app.py exists.")
            sys.exit(1)