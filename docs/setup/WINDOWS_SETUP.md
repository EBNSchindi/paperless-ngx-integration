# Windows Setup Guide

Complete installation and configuration guide for Windows systems.

**Last Updated**: August 12, 2025

## Table of Contents
1. [System Requirements](#system-requirements)
2. [Prerequisites](#prerequisites)
3. [Python Installation](#python-installation)
4. [Project Setup](#project-setup)
5. [LLM Provider Setup](#llm-provider-setup)
6. [Configuration](#configuration)
7. [Testing Installation](#testing-installation)
8. [Windows-Specific Notes](#windows-specific-notes)
9. [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Requirements
- **OS**: Windows 10 (version 1909+) or Windows 11
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 2GB free space
- **Python**: 3.9+ (3.11+ recommended)
- **Network**: Internet connection for API access

### Recommended Setup
- **OS**: Windows 11 22H2 or later
- **RAM**: 8GB or more
- **Storage**: 5GB free space
- **CPU**: 4+ cores for Ollama
- **GPU**: Optional, improves Ollama performance

## Prerequisites

### 1. Enable Long Path Support (Recommended)

Windows has a 260-character path limit by default. Enable long paths:

**Option A: Via Group Policy (Windows Pro/Enterprise)**
1. Press `Win + R`, type `gpedit.msc`
2. Navigate to: Computer Configuration → Administrative Templates → System → Filesystem
3. Enable "Enable Win32 long paths"
4. Restart your computer

**Option B: Via Registry (All Windows versions)**
1. Press `Win + R`, type `regedit`
2. Navigate to: `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\FileSystem`
3. Set `LongPathsEnabled` to `1`
4. Restart your computer

**Option C: Via PowerShell (Administrator)**
```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

### 2. Set UTF-8 Encoding

Configure Windows to use UTF-8 by default:

**Method 1: Environment Variable**
```cmd
setx PYTHONUTF8 1
```

**Method 2: System Settings**
1. Open Settings → Time & Language → Language
2. Click "Administrative language settings"
3. Click "Change system locale"
4. Check "Beta: Use Unicode UTF-8 for worldwide language support"
5. Restart your computer

### 3. Install Git for Windows

Download and install from: https://git-scm.com/download/win

During installation:
- Choose "Git from the command line and also from 3rd-party software"
- Select "Checkout as-is, commit Unix-style line endings"
- Choose "Use Windows' default console window"

## Python Installation

### Option 1: Official Python (Recommended)

1. Download Python 3.11+ from https://www.python.org/downloads/
2. During installation:
   - ✅ Check "Add Python to PATH"
   - ✅ Check "Install for all users" (optional)
   - Choose "Customize installation"
   - ✅ Check "pip"
   - ✅ Check "py launcher"

3. Verify installation:
```cmd
python --version
pip --version
```

### Option 2: Microsoft Store

1. Open Microsoft Store
2. Search for "Python 3.11"
3. Click "Install"
4. Verify: `python3 --version`

### Option 3: Anaconda/Miniconda

1. Download from https://www.anaconda.com/products/individual
2. Install with default settings
3. Use Anaconda Prompt for commands

## Project Setup

### 1. Clone Repository

```cmd
# Using Command Prompt or PowerShell
cd %USERPROFILE%\Documents
git clone https://github.com/yourusername/paperless-ngx-integration.git
cd paperless-ngx-integration
```

### 2. Create Virtual Environment

```cmd
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# You should see (venv) in your prompt
```

### 3. Install Dependencies

```cmd
# Upgrade pip first
python -m pip install --upgrade pip

# Install project dependencies
pip install -r requirements.txt

# Install Windows-specific dependencies (if any)
pip install colorama  # Better console colors on Windows
```

### 4. Verify Installation

```cmd
# Check all packages installed
pip list

# Test imports
python -c "import litellm; print('LiteLLM OK')"
python -c "import pydantic; print('Pydantic OK')"
python -c "import rapidfuzz; print('RapidFuzz OK')"
```

## LLM Provider Setup

### Option 1: Ollama (Local, Recommended)

1. **Download Ollama for Windows**
   - Visit: https://ollama.ai/download/windows
   - Download and run OllamaSetup.exe
   - Follow installation wizard

2. **Start Ollama Service**
   ```cmd
   # Check if Ollama is running
   ollama list
   
   # Pull recommended model
   ollama pull llama3.1:8b
   
   # Test model
   ollama run llama3.1:8b "Hello, world!"
   ```

3. **Configure in .env**
   ```env
   OLLAMA_ENABLED=true
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama3.1:8b
   ```

### Option 2: OpenAI (Cloud)

1. **Get API Key**
   - Visit: https://platform.openai.com/api-keys
   - Create new secret key
   - Copy key (shown only once!)

2. **Configure in .env**
   ```env
   OPENAI_ENABLED=true
   OPENAI_API_KEY=sk-...your-key-here...
   OPENAI_MODEL=gpt-3.5-turbo
   ```

## Configuration

### 1. Create Environment File

```cmd
# Copy template
copy .env.example .env

# Edit with notepad
notepad .env
```

### 2. Essential Configuration

```env
# Paperless NGX
PAPERLESS_BASE_URL=http://your-paperless-server:8000/api
PAPERLESS_API_TOKEN=your-token-here

# LLM Provider Order (comma-separated)
LLM_PROVIDER_ORDER=openai,ollama

# Email Account (Gmail example)
EMAIL_ACCOUNT_1_NAME="Gmail Business"
EMAIL_ACCOUNT_1_SERVER=imap.gmail.com
EMAIL_ACCOUNT_1_PORT=993
EMAIL_ACCOUNT_1_USERNAME=your-email@gmail.com
EMAIL_ACCOUNT_1_PASSWORD=your-app-password

# Windows-specific paths (optional)
TEMP_DIR=%TEMP%\paperless_ngx
LOG_DIR=%APPDATA%\paperless_ngx\logs
```

### 3. Gmail App Password Setup

For Gmail accounts:
1. Enable 2-factor authentication
2. Visit: https://myaccount.google.com/apppasswords
3. Generate app-specific password
4. Use this password in .env

## Testing Installation

### 1. Test Connections

```cmd
# Test all connections
python test_connections.py

# Expected output:
# ✅ Paperless NGX: Connected
# ✅ Ollama: Connected
# ✅ OpenAI: Connected (if configured)
# ✅ Email: Connected
```

### 2. Run Quick Test

```cmd
# Test July 2025 workflows
python test_july_2025_simple.py

# Run interactive menu
python run.py
```

### 3. Test Simplified Menu

```cmd
# Run simplified 3-point workflow
python -m paperless_ngx.presentation.cli.simplified_menu
```

## Windows-Specific Notes

### Path Separators
The system automatically handles path separators. Use forward slashes in config files:
```env
# Good - works on all platforms
ATTACHMENT_DIR=data/attachments

# Avoid - Windows-specific
ATTACHMENT_DIR=data\attachments
```

### File Encoding
All file operations use UTF-8 encoding automatically. If you encounter encoding issues:
1. Ensure `PYTHONUTF8=1` is set
2. Save all text files as UTF-8
3. Use Notepad++ or VS Code for editing

### Temporary Files
Windows temp directory is used automatically:
- Default: `%TEMP%\paperless_ngx\`
- Override in .env if needed

### Hidden Directories
The system uses platform-appropriate hidden directories:
- Windows: `%APPDATA%\paperless_ngx\`
- Config: `%APPDATA%\paperless_ngx\config\`
- Logs: `%APPDATA%\paperless_ngx\logs\`

### Antivirus Considerations
Some antivirus software may flag Python scripts:
1. Add project directory to exclusions
2. Exclude Python.exe from real-time scanning
3. Whitelist Ollama if using local LLM

## Troubleshooting

### Common Issues

#### Python Not Found
```cmd
# Check if Python is in PATH
where python

# If not found, add to PATH:
setx PATH "%PATH%;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311"
```

#### Virtual Environment Not Activating
```cmd
# Try alternative activation methods:
venv\Scripts\activate.bat       # Command Prompt
venv\Scripts\Activate.ps1        # PowerShell
source venv/Scripts/activate     # Git Bash
```

#### Permission Denied Errors
1. Run Command Prompt as Administrator
2. Check file permissions
3. Disable real-time antivirus scanning temporarily

#### SSL Certificate Errors
```cmd
# Install certificates
pip install --upgrade certifi

# Or disable SSL verification (not recommended)
set PYTHONHTTPSVERIFY=0
```

#### Encoding Errors
```cmd
# Set UTF-8 encoding
set PYTHONUTF8=1
chcp 65001  # Change console to UTF-8
```

### PowerShell Execution Policy

If scripts won't run in PowerShell:
```powershell
# Check current policy
Get-ExecutionPolicy

# Allow script execution (admin required)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Network Issues

For corporate networks with proxies:
```cmd
# Set proxy for pip
set HTTP_PROXY=http://proxy.company.com:8080
set HTTPS_PROXY=http://proxy.company.com:8080

# Configure in .env for application
HTTP_PROXY=http://proxy.company.com:8080
```

## Next Steps

1. **Configure Paperless NGX**: Get API token from your Paperless instance
2. **Setup Email Accounts**: Configure IMAP credentials
3. **Choose LLM Provider**: Setup Ollama or OpenAI
4. **Run Test Workflow**: Process sample documents
5. **Read User Manual**: Learn about all features

## Support

### Getting Help
1. Check [Troubleshooting Guide](TROUBLESHOOTING.md)
2. Review [FAQ](../user-guide/FAQ.md)
3. Search [GitHub Issues](https://github.com/yourusername/paperless-ngx-integration/issues)
4. Ask in [Discussions](https://github.com/yourusername/paperless-ngx-integration/discussions)

### Reporting Issues
When reporting Windows-specific issues, include:
- Windows version (`winver`)
- Python version (`python --version`)
- Error messages with full traceback
- Environment configuration (sanitized)

---

**Navigation**: [Documentation Index](../INDEX.md) | [Linux Setup](LINUX_SETUP.md) | [Troubleshooting](TROUBLESHOOTING.md) | [Quick Start](QUICKSTART.md)