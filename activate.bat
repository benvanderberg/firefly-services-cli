@echo off
REM Windows virtual environment activation script
REM Run this from the project root directory

if not exist "venv\Scripts\activate.bat" (
    echo Error: Virtual environment not found.
    echo Please run install.bat first to create the virtual environment.
    pause
    exit /b 1
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

if defined VIRTUAL_ENV (
    echo Virtual environment activated successfully!
    echo You can now run: bin\ff.bat [command] [options]
    echo.
    echo To deactivate, run: deactivate
) else (
    echo Failed to activate virtual environment
    pause
    exit /b 1
) 