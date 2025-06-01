#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_message() {
    echo -e "${GREEN}$1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3 and try again."
    exit 1
fi

# Get Python version
PYTHON_VERSION=$(python3 --version)
print_message "[INFO] Found $PYTHON_VERSION"

# Get the directory where this script is located
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Create virtual environment if it doesn't exist
if [ ! -d "$PROJECT_ROOT/venv" ]; then
    print_message "[INFO] Creating virtual environment..."
    python3 -m venv "$PROJECT_ROOT/venv"
    if [ $? -ne 0 ]; then
        print_error "Failed to create virtual environment"
        exit 1
    fi
fi

# Activate virtual environment
print_message "[INFO] Activating virtual environment..."
source "$PROJECT_ROOT/venv/bin/activate"

# Verify we're using the virtual environment's Python
if [[ "$VIRTUAL_ENV" == "" ]]; then
    print_error "Failed to activate virtual environment"
    exit 1
fi

# Upgrade pip
print_message "[INFO] Upgrading pip..."
python -m pip install --upgrade pip

# Install requirements
if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
    print_message "[INFO] Installing dependencies from requirements.txt..."
    pip install -r "$PROJECT_ROOT/requirements.txt"
    if [ $? -ne 0 ]; then
        print_error "Failed to install dependencies"
        exit 1
    fi
else
    print_error "requirements.txt not found"
    exit 1
fi

# Copy env_sample to .env if .env doesn't exist
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    if [ -f "$PROJECT_ROOT/env_sample" ]; then
        print_message "[INFO] Creating .env file from env_sample..."
        cp "$PROJECT_ROOT/env_sample" "$PROJECT_ROOT/.env"
        print_warning "Please update the credentials in .env file with your actual values"
    else
        print_error "env_sample file not found"
        exit 1
    fi
else
    print_warning "[INFO] .env file already exists"
fi

echo " "
echo " "

# Detect OS and provide appropriate PATH configuration instructions
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    print_message "For macOS users:"
    print_message "To make the 'ff' command available system-wide, add this line to your ~/.zshrc:"
    print_message "export PATH=\"$PROJECT_ROOT/bin:\$PATH\""
    print_message "Then run: source ~/.zshrc"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    print_message "For Linux users:"
    print_message "To make the 'ff' command available system-wide, add this line to your ~/.bashrc or ~/.zshrc:"
    print_message "export PATH=\"$PROJECT_ROOT/bin:\$PATH\""
    print_message "Then run: source ~/.bashrc (or source ~/.zshrc if using zsh)"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    print_message "For Windows users:"
    print_message "To make the 'ff' command available system-wide:"
    print_message "1. Open System Properties > Advanced > Environment Variables"
    print_message "2. Under 'User variables', find and select 'Path'"
    print_message "3. Click 'Edit' and add this path:"
    print_message "$PROJECT_ROOT/bin"
    print_message "4. Click 'OK' to save changes"
    print_message "Note: You may need to restart your terminal for changes to take effect"
fi

echo " "
print_message "INSTALLATION COMPLETED SUCCESSFULLY!"
echo " "
print_message "Next steps:"
print_message "1. Update the .env to add your credentials"
print_message "2. The virtual environment is now activated. To activate it in future sessions, run:"
print_message "   source venv/bin/activate"
print_message "3. Use './bin/ff' to run the tool"