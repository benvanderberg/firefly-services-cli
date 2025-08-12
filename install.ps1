# PowerShell installation script for Adobe Firefly Services CLI
# Run this script as Administrator for best results

param(
    [switch]$AddToPath,
    [switch]$Force
)

# Colors for output
$Green = "`e[92m"
$Yellow = "`e[93m"
$Red = "`e[91m"
$Reset = "`e[0m"

# Function to print colored messages
function Write-ColorMessage {
    param([string]$Message, [string]$Color = $Green)
    Write-Host "$Color$Message$Reset"
}

function Write-Warning {
    param([string]$Message)
    Write-Host "$Yellow[WARNING]$Reset $Message"
}

function Write-Error {
    param([string]$Message)
    Write-Host "$Red[ERROR]$Reset $Message"
}

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")

if ($AddToPath -and -not $isAdmin) {
    Write-Error "Administrator privileges required to add to PATH. Run PowerShell as Administrator or use -Force to continue without PATH modification."
    if (-not $Force) {
        exit 1
    }
}

# Check if Python 3 is installed
$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonCmd = "python3"
} else {
    Write-Error "Python 3 is not installed. Please install Python 3 and try again."
    Write-Host "Download Python from: https://www.python.org/downloads/"
    Write-Host "Make sure to check 'Add Python to PATH' during installation."
    exit 1
}

# Get Python version
$pythonVersion = & $pythonCmd --version 2>&1
Write-ColorMessage "[INFO] Found $pythonVersion"

# Get the directory where this script is located
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Create virtual environment if it doesn't exist
if (-not (Test-Path "$projectRoot\venv")) {
    Write-ColorMessage "[INFO] Creating virtual environment..."
    & $pythonCmd -m venv "$projectRoot\venv"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create virtual environment"
        exit 1
    }
}

# Activate virtual environment
Write-ColorMessage "[INFO] Activating virtual environment..."
& "$projectRoot\venv\Scripts\Activate.ps1"

# Verify we're using the virtual environment's Python
if (-not $env:VIRTUAL_ENV) {
    Write-Error "Failed to activate virtual environment"
    exit 1
}

# Upgrade pip
Write-ColorMessage "[INFO] Upgrading pip..."
python -m pip install --upgrade pip

# Install requirements
if (Test-Path "$projectRoot\requirements.txt") {
    Write-ColorMessage "[INFO] Installing dependencies from requirements.txt..."
    pip install -r "$projectRoot\requirements.txt"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to install dependencies"
        exit 1
    }
} else {
    Write-Error "requirements.txt not found"
    exit 1
}

# Copy env_sample to .env if .env doesn't exist
if (-not (Test-Path "$projectRoot\.env")) {
    if (Test-Path "$projectRoot\env_sample") {
        Write-ColorMessage "[INFO] Creating .env file from env_sample..."
        Copy-Item "$projectRoot\env_sample" "$projectRoot\.env"
        Write-Warning "Please update the credentials in .env file with your actual values"
    } else {
        Write-Error "env_sample file not found"
        exit 1
    }
} else {
    Write-Warning "[INFO] .env file already exists"
}

Write-Host ""
Write-Host ""

# Add to PATH if requested
if ($AddToPath -and $isAdmin) {
    Write-ColorMessage "[INFO] Adding to system PATH..."
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $binPath = "$projectRoot\bin"
    
    if ($currentPath -notlike "*$binPath*") {
        $newPath = "$currentPath;$binPath"
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        Write-ColorMessage "[INFO] Added $binPath to user PATH"
        Write-Warning "You may need to restart your terminal for changes to take effect"
    } else {
        Write-ColorMessage "[INFO] $binPath is already in PATH"
    }
} elseif ($AddToPath -and -not $isAdmin) {
    Write-Warning "Cannot add to PATH without Administrator privileges"
    Write-Host "To add manually:"
    Write-Host "1. Press Win + R, type 'sysdm.cpl' and press Enter"
    Write-Host "2. Click 'Environment Variables'"
    Write-Host "3. Under 'User variables', find and select 'Path'"
    Write-Host "4. Click 'Edit' and add: $projectRoot\bin"
    Write-Host "5. Click 'OK' to save changes"
}

Write-Host ""
Write-ColorMessage "INSTALLATION COMPLETED SUCCESSFULLY!"
Write-Host ""
Write-ColorMessage "Next steps:"
Write-ColorMessage "1. Update the .env to add your credentials"
Write-ColorMessage "2. The virtual environment is now activated. To activate it in future sessions, run:"
Write-ColorMessage "   $projectRoot\venv\Scripts\Activate.ps1"
Write-ColorMessage "3. Use '$projectRoot\bin\ff.bat' to run the tool"

# Check if ImageMagick is installed
if (Get-Command magick -ErrorAction SilentlyContinue) {
    Write-Host ""
    Write-ColorMessage "ImageMagick is already installed."
} else {
    Write-Host ""
    Write-Warning "ImageMagick is not installed. Please install it manually:"
    Write-Host "Download from: https://imagemagick.org/script/download.php#windows"
    Write-Host "Make sure to check 'Add application directory to your system path' during installation."
}

Write-Host ""
if (-not $AddToPath) {
    Write-Host "To add the CLI to your PATH, run this script again with -AddToPath"
} 