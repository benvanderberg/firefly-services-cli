# Windows Installation Guide

This guide provides detailed instructions for installing the Adobe Firefly Services CLI on Windows systems.

## Prerequisites

### 1. Python 3.8 or Higher
- Download Python from: https://www.python.org/downloads/
- **Important**: During installation, make sure to check "Add Python to PATH"
- Verify installation by opening Command Prompt and running:
  ```cmd
  python --version
  ```

### 2. ImageMagick (Optional but Recommended)
- Download from: https://imagemagick.org/script/download.php#windows
- **Important**: During installation, check "Add application directory to your system path"
- Verify installation by running:
  ```cmd
  magick --version
  ```

## Installation Methods

### Method 1: Batch File Installation (Easiest)

1. **Download the project**
   - Clone or download the project to your desired location
   - Open Command Prompt in the project directory

2. **Run the installation script**
   ```cmd
   install.bat
   ```

3. **Follow the prompts**
   - The script will automatically:
     - Check Python installation
     - Create a virtual environment
     - Install dependencies
     - Set up your environment file

4. **Add to PATH (Optional)**
   - The script will provide instructions for adding the CLI to your system PATH
   - Follow the GUI instructions or use the provided commands

### Method 2: PowerShell Installation (Advanced)

1. **Open PowerShell as Administrator**
   - Press `Win + X` and select "Windows PowerShell (Admin)"

2. **Set execution policy (if needed)**
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

3. **Navigate to project directory**
   ```powershell
   cd "path\to\your\project"
   ```

4. **Run installation with automatic PATH setup**
   ```powershell
   .\install.ps1 -AddToPath
   ```

### Method 3: Python Package Installation

1. **Open Command Prompt in project directory**

2. **Install in development mode**
   ```cmd
   pip install -e .
   ```

3. **The `ff` command will be available system-wide**

## Usage

### After Installation

1. **Activate the virtual environment**
   ```cmd
   activate.bat
   ```

2. **Run the CLI**
   ```cmd
   ff [command] [options]
   ```

### Alternative Usage Methods

1. **Using the batch file directly**
   ```cmd
   bin\ff.bat [command] [options]
   ```

2. **Using the full Python path**
   ```cmd
   venv\Scripts\python.exe main.py [command] [options]
   ```

## Configuration

### 1. Set up your credentials
- Edit the `.env` file in the project root
- Add your Adobe Firefly Services credentials:
  ```
  FIREFLY_SERVICES_CLIENT_ID=your_client_id
  FIREFLY_SERVICES_CLIENT_SECRET=your_client_secret
  FIREFLY_SERVICES_SCOPE=openid,AdobeID,session,additional_info,read_organizations,firefly_api,ff_apis
  ```

### 2. Configure Azure Storage (if needed)
- Add your Azure Storage credentials to `.env`:
  ```
  AZURE_STORAGE_ACCOUNT=your_storage_account
  AZURE_STORAGE_CONTAINER=your_container_name
  AZURE_STORAGE_SAS_TOKEN=your_sas_token
  ```

## Troubleshooting

### Common Issues

1. **"Python is not recognized"**
   - Reinstall Python and check "Add Python to PATH"
   - Or manually add Python to your system PATH

2. **"Virtual environment not found"**
   - Run `install.bat` first to create the virtual environment

3. **"Permission denied"**
   - Run Command Prompt or PowerShell as Administrator
   - Or use the `-Force` parameter with PowerShell installation

4. **"ImageMagick not found"**
   - Install ImageMagick and check "Add to PATH" during installation
   - Or add ImageMagick manually to your system PATH

5. **PowerShell execution policy error**
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

### PATH Issues

If the `ff` command is not recognized:

1. **Check if it's in PATH**
   ```cmd
   echo %PATH%
   ```

2. **Add manually to PATH**
   - Press `Win + R`, type `sysdm.cpl`, press Enter
   - Click "Environment Variables"
   - Under "User variables", find "Path" and click "Edit"
   - Add the full path to the `bin` directory
   - Click "OK" to save

3. **Or use setx command (as Administrator)**
   ```cmd
   setx PATH "%PATH%;C:\path\to\your\project\bin"
   ```

## Uninstallation

To remove the CLI:

1. **Delete the project directory**
2. **Remove from PATH** (if added)
   - Follow the PATH setup instructions in reverse
3. **If installed as a package**
   ```cmd
   pip uninstall firefly-services-cli
   ```

## Support

If you encounter issues:

1. Check the main README.md for general troubleshooting
2. Ensure all prerequisites are installed correctly
3. Try running the installation scripts as Administrator
4. Check that your Python installation is working correctly

## Examples

### Basic Usage
```cmd
# Generate an image
ff image -p "a beautiful sunset" -o sunset.jpg

# Convert text to speech
ff tts -t "Hello, world!" -o hello.mp3

# Transcribe audio
ff transcribe -i audio.mp3 -o transcript.txt
```

### With Virtual Environment
```cmd
# Activate environment
activate.bat

# Run commands
ff image -p "a cat" -o cat.jpg

# Deactivate when done
deactivate
``` 