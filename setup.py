#!/usr/bin/env python3
"""
Cloud Foundry Service Tester - Cross-platform Setup Script
This script sets up a Python virtual environment and installs all dependencies
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# Colors for output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
NC = '\033[0m'  # No Color

def print_error(message):
    """Print error message"""
    print(f"{RED}{message}{NC}", file=sys.stderr)

def print_success(message):
    """Print success message"""
    print(f"{GREEN}✓{NC} {message}")

def print_warning(message):
    """Print warning message"""
    print(f"{YELLOW}{message}{NC}")

def check_python_version():
    """Check if Python version is 3.8 or higher"""
    if sys.version_info < (3, 8):
        print_error(f"Python 3.8 or higher is required (found {sys.version})")
        sys.exit(1)
    print_success(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} found")

def run_command(cmd, check=True):
    """Run a command and return the result"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=check,
            capture_output=True,
            text=True
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr

def main():
    """Main setup function"""
    print(f"{GREEN}Cloud Foundry Service Tester - Setup Script{NC}")
    print("=" * 50)
    print()
    
    # Check Python version
    check_python_version()
    
    # Determine virtual environment directory
    venv_dir = Path("venv")
    
    # Check if virtual environment already exists
    if venv_dir.exists():
        print_warning(f"Virtual environment already exists at {venv_dir}")
        response = input("Do you want to recreate it? (y/N): ").strip().lower()
        if response == 'y':
            print("Removing existing virtual environment...")
            shutil.rmtree(venv_dir)
        else:
            print("Using existing virtual environment...")
            # Note: We can't activate venv in the same process, so we'll just upgrade and install
            if sys.platform == "win32":
                pip_cmd = str(venv_dir / "Scripts" / "python.exe") + " -m pip"
            else:
                pip_cmd = str(venv_dir / "bin" / "python3") + " -m pip"
            
            print("Upgrading pip...")
            success, _, _ = run_command(f"{pip_cmd} install --upgrade pip --quiet", check=False)
            
            if Path("requirements.txt").exists():
                print("Installing requirements...")
                success, _, _ = run_command(f"{pip_cmd} install -r requirements.txt", check=False)
                if success:
                    print_success("Requirements installed")
                else:
                    print_error("Failed to install requirements")
                    sys.exit(1)
            else:
                print_error("requirements.txt not found")
                sys.exit(1)
            
            print()
            print(f"{GREEN}Setup complete!{NC}")
            print()
            if sys.platform == "win32":
                print("To activate the virtual environment, run:")
                print(f"  {venv_dir}\\Scripts\\activate.bat")
            else:
                print("To activate the virtual environment, run:")
                print(f"  source {venv_dir}/bin/activate")
            print()
            print("To run the application:")
            print("  python app.py")
            return
    else:
        # Create virtual environment
        print("Creating Python virtual environment...")
        success, _, error = run_command(f"{sys.executable} -m venv {venv_dir}", check=False)
        
        if not success or not venv_dir.exists():
            print_error(f"Failed to create virtual environment: {error}")
            sys.exit(1)
        
        print_success("Virtual environment created")
    
    # Determine pip command based on platform
    if sys.platform == "win32":
        pip_cmd = str(venv_dir / "Scripts" / "python.exe") + " -m pip"
    else:
        pip_cmd = str(venv_dir / "bin" / "python3") + " -m pip"
    
    # Upgrade pip
    print("Upgrading pip...")
    success, _, _ = run_command(f"{pip_cmd} install --upgrade pip --quiet", check=False)
    if success:
        print_success("pip upgraded")
    else:
        print_warning("Failed to upgrade pip (continuing anyway)")
    
    # Install requirements
    requirements_file = Path("requirements.txt")
    if requirements_file.exists():
        print("Installing requirements from requirements.txt...")
        success, _, error = run_command(f"{pip_cmd} install -r requirements.txt", check=False)
        if success:
            print_success("Requirements installed")
        else:
            print_error(f"Failed to install requirements: {error}")
            sys.exit(1)
    else:
        print_error("requirements.txt not found")
        sys.exit(1)
    
    print()
    print(f"{GREEN}" + "=" * 50)
    print("Setup complete!")
    print("=" * 50 + f"{NC}")
    print()
    print("Virtual environment created and activated.")
    print()
    
    if sys.platform == "win32":
        print("To activate the virtual environment in a new terminal, run:")
        print(f"  {venv_dir}\\Scripts\\activate.bat")
    else:
        print("To activate the virtual environment in a new terminal, run:")
        print(f"  source {venv_dir}/bin/activate")
    
    print()
    print("To deactivate the virtual environment, run:")
    print("  deactivate")
    print()
    print("To run the application:")
    print("  python app.py")
    print()
    print("To run with gunicorn (production):")
    print("  gunicorn --bind 0.0.0.0:8080 app:app")
    print()

if __name__ == "__main__":
    main()

