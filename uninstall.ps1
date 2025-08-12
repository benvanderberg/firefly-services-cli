# PowerShell uninstallation script for Adobe Firefly Services CLI
# Run this script as Administrator for best results

param(
    [switch]$RemoveFromPath,
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

if ($RemoveFromPath -and -not $isAdmin) {
    Write-Error "Administrator privileges required to remove from PATH. Run PowerShell as Administrator or use -Force to continue without PATH modification."
    if (-not $Force) {
        exit 1
    }
}

# Get the directory where this script is located
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-ColorMessage "Adobe Firefly Services CLI Uninstaller"
Write-Host ""

# Check if virtual environment exists
if (Test-Path "$projectRoot\venv") {
    Write-ColorMessage "[INFO] Found virtual environment"
    
    # Deactivate if currently active
    if ($env:VIRTUAL_ENV -eq "$projectRoot\venv") {
        Write-ColorMessage "[INFO] Deactivating virtual environment..."
        deactivate
    }
    
    # Remove virtual environment
    Write-ColorMessage "[INFO] Removing virtual environment..."
    Remove-Item -Path "$projectRoot\venv" -Recurse -Force
    Write-ColorMessage "[INFO] Virtual environment removed"
} else {
    Write-Warning "Virtual environment not found"
}

# Remove from PATH if requested
if ($RemoveFromPath -and $isAdmin) {
    Write-ColorMessage "[INFO] Removing from system PATH..."
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $binPath = "$projectRoot\bin"
    
    if ($currentPath -like "*$binPath*") {
        $newPath = $currentPath -replace [regex]::Escape($binPath), ""
        $newPath = $newPath -replace ";;", ";"  # Clean up double semicolons
        $newPath = $newPath.Trim(";")  # Remove leading/trailing semicolons
        
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        Write-ColorMessage "[INFO] Removed $binPath from user PATH"
    } else {
        Write-ColorMessage "[INFO] $binPath was not found in PATH"
    }
} elseif ($RemoveFromPath -and -not $isAdmin) {
    Write-Warning "Cannot remove from PATH without Administrator privileges"
    Write-Host "To remove manually:"
    Write-Host "1. Press Win + R, type 'sysdm.cpl' and press Enter"
    Write-Host "2. Click 'Environment Variables'"
    Write-Host "3. Under 'User variables', find and select 'Path'"
    Write-Host "4. Click 'Edit' and remove: $projectRoot\bin"
    Write-Host "5. Click 'OK' to save changes"
}

# Check if installed as a Python package
try {
    $packageInfo = pip show firefly-services-cli 2>$null
    if ($packageInfo) {
        Write-ColorMessage "[INFO] Found Python package installation"
        $uninstall = Read-Host "Do you want to uninstall the Python package? (y/N)"
        if ($uninstall -eq "y" -or $uninstall -eq "Y") {
            Write-ColorMessage "[INFO] Uninstalling Python package..."
            pip uninstall firefly-services-cli -y
            Write-ColorMessage "[INFO] Python package uninstalled"
        }
    }
} catch {
    Write-ColorMessage "[INFO] No Python package installation found"
}

# Clean up generated files
$filesToRemove = @(
    ".env",
    "*.log",
    "outputs\*",
    "logs\*"
)

foreach ($pattern in $filesToRemove) {
    $files = Get-ChildItem -Path $projectRoot -Filter $pattern -Recurse -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        if (Test-Path $file.FullName) {
            Remove-Item $file.FullName -Force
            Write-ColorMessage "[INFO] Removed: $($file.Name)"
        }
    }
}

Write-Host ""
Write-ColorMessage "UNINSTALLATION COMPLETED!"
Write-Host ""
Write-Warning "Note: The project directory and source code remain intact."
Write-Host "To completely remove the CLI, delete the entire project directory:"
Write-Host "  $projectRoot"
Write-Host ""

$removeDir = Read-Host "Do you want to remove the entire project directory? (y/N)"
if ($removeDir -eq "y" -or $removeDir -eq "Y") {
    Write-ColorMessage "[INFO] Removing project directory..."
    Remove-Item -Path $projectRoot -Recurse -Force
    Write-ColorMessage "[INFO] Project directory removed"
    Write-ColorMessage "Uninstallation complete!"
} else {
    Write-ColorMessage "Project directory preserved. You can delete it manually if needed."
} 