@echo off
setlocal

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "PROJECT_ROOT=%SCRIPT_DIR%\.."

REM Use the Python interpreter from the virtual environment
set "PYTHON_PATH=%PROJECT_ROOT%\venv\Scripts\python.exe"

REM Check if the Python interpreter exists
if not exist "%PYTHON_PATH%" (
    echo Error: Python interpreter not found in virtual environment
    echo Please ensure you have activated the virtual environment and installed dependencies
    echo.
    echo To install, run: install.bat
    pause
    exit /b 1
)

REM Pass through all arguments to main.py
"%PYTHON_PATH%" "%PROJECT_ROOT%\main.py" %* 