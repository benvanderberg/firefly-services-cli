@echo off
setlocal enabledelayedexpansion

REM Colors for output (Windows 10+ supports ANSI colors)
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "NC=[0m"

REM Function to print colored messages
:print_message
echo %GREEN%%~1%NC%
goto :eof

:print_warning
echo %YELLOW%[WARNING]%NC% %~1
goto :eof

:print_error
echo %RED%[ERROR]%NC% %~1
goto :eof

REM Check if Python 3 is installed
python --version >nul 2>&1
if errorlevel 1 (
    python3 --version >nul 2>&1
    if errorlevel 1 (
        call :print_error "Python 3 is not installed. Please install Python 3 and try again."
        echo.
        echo Download Python from: https://www.python.org/downloads/
        echo Make sure to check "Add Python to PATH" during installation.
        pause
        exit /b 1
    ) else (
        set "PYTHON_CMD=python3"
    )
) else (
    set "PYTHON_CMD=python"
)

REM Get Python version
for /f "tokens=*" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set PYTHON_VERSION=%%i
call :print_message "[INFO] Found %PYTHON_VERSION%"

REM Get the directory where this script is located
set "PROJECT_ROOT=%~dp0"
set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

REM Create virtual environment if it doesn't exist
if not exist "%PROJECT_ROOT%\venv" (
    call :print_message "[INFO] Creating virtual environment..."
    %PYTHON_CMD% -m venv "%PROJECT_ROOT%\venv"
    if errorlevel 1 (
        call :print_error "Failed to create virtual environment"
        pause
        exit /b 1
    )
)

REM Activate virtual environment
call :print_message "[INFO] Activating virtual environment..."
call "%PROJECT_ROOT%\venv\Scripts\activate.bat"

REM Verify we're using the virtual environment's Python
if not defined VIRTUAL_ENV (
    call :print_error "Failed to activate virtual environment"
    pause
    exit /b 1
)

REM Upgrade pip
call :print_message "[INFO] Upgrading pip..."
python -m pip install --upgrade pip

REM Install requirements
if exist "%PROJECT_ROOT%\requirements.txt" (
    call :print_message "[INFO] Installing dependencies from requirements.txt..."
    pip install -r "%PROJECT_ROOT%\requirements.txt"
    if errorlevel 1 (
        call :print_error "Failed to install dependencies"
        pause
        exit /b 1
    )
) else (
    call :print_error "requirements.txt not found"
    pause
    exit /b 1
)

REM Copy env_sample to .env if .env doesn't exist
if not exist "%PROJECT_ROOT%\.env" (
    if exist "%PROJECT_ROOT%\env_sample" (
        call :print_message "[INFO] Creating .env file from env_sample..."
        copy "%PROJECT_ROOT%\env_sample" "%PROJECT_ROOT%\.env" >nul
        call :print_warning "Please update the credentials in .env file with your actual values"
    ) else (
        call :print_error "env_sample file not found"
        pause
        exit /b 1
    )
) else (
    call :print_warning "[INFO] .env file already exists"
)

echo.
echo.

REM Windows-specific PATH configuration instructions
call :print_message "For Windows users:"
call :print_message "To make the 'ff' command available system-wide:"
echo.
echo Method 1 - Using System Properties:
echo 1. Press Win + R, type "sysdm.cpl" and press Enter
echo 2. Click "Environment Variables"
echo 3. Under "User variables", find and select "Path"
echo 4. Click "Edit" and add this path:
echo    %PROJECT_ROOT%\bin
echo 5. Click "OK" to save changes
echo.
echo Method 2 - Using PowerShell (Run as Administrator):
echo [Environment]::SetEnvironmentVariable("Path", $env:Path + ";%PROJECT_ROOT%\bin", "User")
echo.
echo Method 3 - Using Command Prompt (Run as Administrator):
echo setx PATH "%%PATH%%;%PROJECT_ROOT%\bin"
echo.
call :print_warning "Note: You may need to restart your terminal for changes to take effect"

echo.
call :print_message "INSTALLATION COMPLETED SUCCESSFULLY!"
echo.
call :print_message "Next steps:"
call :print_message "1. Update the .env to add your credentials"
call :print_message "2. The virtual environment is now activated. To activate it in future sessions, run:"
call :print_message "   %PROJECT_ROOT%\venv\Scripts\activate.bat"
call :print_message "3. Use '%PROJECT_ROOT%\bin\ff.bat' to run the tool"

REM Check if ImageMagick is installed
magick --version >nul 2>&1
if errorlevel 1 (
    echo.
    call :print_warning "ImageMagick is not installed. Please install it manually:"
    echo Download from: https://imagemagick.org/script/download.php#windows
    echo Make sure to check "Add application directory to your system path" during installation.
) else (
    echo.
    call :print_message "ImageMagick is already installed."
)

echo.
pause 