#!/bin/bash

# Cloud Foundry Service Tester - Setup Script
# This script sets up a Python virtual environment and installs all dependencies

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Cloud Foundry Service Tester - Setup Script${NC}"
echo "=========================================="
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    echo "Please install Python 3.8 or higher and try again."
    exit 1
fi

# Check Python version (3.8+ required)
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo -e "${RED}Error: Python 3.8 or higher is required (found $PYTHON_VERSION)${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION found"

# Determine virtual environment directory
VENV_DIR="venv"

# Check if virtual environment already exists
if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Virtual environment already exists at $VENV_DIR${NC}"
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing virtual environment..."
        rm -rf "$VENV_DIR"
    else
        echo "Using existing virtual environment..."
        source "$VENV_DIR/bin/activate"
        echo -e "${GREEN}✓${NC} Virtual environment activated"
        
        # Upgrade pip
        echo "Upgrading pip..."
        pip install --upgrade pip --quiet
        
        # Install requirements
        if [ -f "requirements.txt" ]; then
            echo "Installing requirements..."
            pip install -r requirements.txt
            echo -e "${GREEN}✓${NC} Requirements installed"
        else
            echo -e "${RED}Error: requirements.txt not found${NC}"
            exit 1
        fi
        
        echo ""
        echo -e "${GREEN}Setup complete!${NC}"
        echo ""
        echo "To activate the virtual environment in the future, run:"
        echo "  source $VENV_DIR/bin/activate"
        echo ""
        echo "To run the application:"
        echo "  python app.py"
        exit 0
    fi
fi

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv "$VENV_DIR"

if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}Error: Failed to create virtual environment${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Virtual environment created"

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip --quiet
echo -e "${GREEN}✓${NC} pip upgraded"

# Install requirements
if [ -f "requirements.txt" ]; then
    echo "Installing requirements from requirements.txt..."
    pip install -r requirements.txt
    echo -e "${GREEN}✓${NC} Requirements installed"
else
    echo -e "${RED}Error: requirements.txt not found${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}=========================================="
echo -e "Setup complete!${NC}"
echo "=========================================="
echo ""
echo "Virtual environment is now active."
echo ""
echo "To activate the virtual environment in a new terminal, run:"
echo "  source $VENV_DIR/bin/activate"
echo ""
echo "To deactivate the virtual environment, run:"
echo "  deactivate"
echo ""
echo "To run the application:"
echo "  python app.py"
echo ""
echo "To run with gunicorn (production):"
echo "  gunicorn --bind 0.0.0.0:8080 app:app"
echo ""
