@echo off
REM Cloud Foundry Service Tester - Setup Script for Windows
REM This script sets up a Python virtual environment and installs all dependencies

echo Cloud Foundry Service Tester - Setup Script
echo ==========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher and try again.
    exit /b 1
)

REM Check Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Found Python %PYTHON_VERSION%

REM Set virtual environment directory
set VENV_DIR=venv

REM Check if virtual environment already exists
if exist "%VENV_DIR%" (
    echo Virtual environment already exists at %VENV_DIR%
    set /p RECREATE="Do you want to recreate it? (y/N): "
    if /i not "%RECREATE%"=="y" (
        echo Using existing virtual environment...
        call %VENV_DIR%\Scripts\activate.bat
        echo Virtual environment activated
        
        REM Upgrade pip
        echo Upgrading pip...
        python -m pip install --upgrade pip --quiet
        
        REM Install requirements
        if exist "requirements.txt" (
            echo Installing requirements...
            pip install -r requirements.txt
            echo Requirements installed
        ) else (
            echo Error: requirements.txt not found
            exit /b 1
        )
        
        echo.
        echo Setup complete!
        echo.
        echo To activate the virtual environment in the future, run:
        echo   %VENV_DIR%\Scripts\activate.bat
        echo.
        echo To run the application:
        echo   python app.py
        exit /b 0
    ) else (
        echo Removing existing virtual environment...
        rmdir /s /q "%VENV_DIR%"
    )
)

REM Create virtual environment
echo Creating Python virtual environment...
python -m venv "%VENV_DIR%"

if not exist "%VENV_DIR%" (
    echo Error: Failed to create virtual environment
    exit /b 1
)

echo Virtual environment created

REM Activate virtual environment
echo Activating virtual environment...
call %VENV_DIR%\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip --quiet
echo pip upgraded

REM Install requirements
if exist "requirements.txt" (
    echo Installing requirements from requirements.txt...
    pip install -r requirements.txt
    echo Requirements installed
) else (
    echo Error: requirements.txt not found
    exit /b 1
)

echo.
echo ==========================================
echo Setup complete!
echo ==========================================
echo.
echo Virtual environment is now active.
echo.
echo To activate the virtual environment in a new terminal, run:
echo   %VENV_DIR%\Scripts\activate.bat
echo.
echo To deactivate the virtual environment, run:
echo   deactivate
echo.
echo To run the application:
echo   python app.py
echo.

pause
