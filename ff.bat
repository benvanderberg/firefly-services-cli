@echo off
REM Adobe Firefly Services CLI Launcher for Windows
REM This script can be placed anywhere and will find the project directory

setlocal

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM Look for the project root (where main.py is located)
set "PROJECT_ROOT=%SCRIPT_DIR%"
:find_project_root
if exist "%PROJECT_ROOT%\main.py" goto :found_project
if exist "%PROJECT_ROOT%\..\main.py" (
    set "PROJECT_ROOT=%PROJECT_ROOT%\.."
    goto :find_project
)
if exist "%PROJECT_ROOT%\..\..\main.py" (
    set "PROJECT_ROOT=%PROJECT_ROOT%\..\.."
    goto :find_project
)
if exist "%PROJECT_ROOT%\..\..\..\main.py" (
    set "PROJECT_ROOT=%PROJECT_ROOT%\..\..\.."
    goto :find_project
)

REM If we can't find main.py, assume we're in the project root
if not exist "%PROJECT_ROOT%\main.py" (
    echo Error: Could not find main.py in the project directory.
    echo Please ensure this script is in or near the project directory.
    pause
    exit /b 1
)

:found_project
REM Use the Python interpreter from the virtual environment
set "PYTHON_PATH=%PROJECT_ROOT%\venv\Scripts\python.exe"

REM Check if the Python interpreter exists
if not exist "%PYTHON_PATH%" (
    echo Error: Python interpreter not found in virtual environment
    echo Please ensure you have run the installation script first.
    echo.
    echo To install, navigate to the project directory and run: install.bat
    pause
    exit /b 1
)

REM Pass through all arguments to main.py
"%PYTHON_PATH%" "%PROJECT_ROOT%\main.py" %* 