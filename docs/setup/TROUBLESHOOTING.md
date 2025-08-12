# Platform-Specific Troubleshooting Guide

Comprehensive troubleshooting for Windows and Linux platforms.

**Last Updated**: August 12, 2025

## Table of Contents
1. [Quick Diagnosis](#quick-diagnosis)
2. [Cross-Platform Issues](#cross-platform-issues)
3. [Windows-Specific Issues](#windows-specific-issues)
4. [Linux-Specific Issues](#linux-specific-issues)
5. [Connection Problems](#connection-problems)
6. [Performance Issues](#performance-issues)
7. [Error Messages](#error-messages)
8. [Recovery Procedures](#recovery-procedures)

## Quick Diagnosis

### Diagnostic Script

Run this to identify common issues:

```bash
# Save as diagnose.py
python3 << 'EOF'
import sys
import platform
import os
import subprocess

print("=== System Diagnosis ===")
print(f"Platform: {platform.system()} {platform.release()}")
print(f"Python: {sys.version}")
print(f"Working Dir: {os.getcwd()}")

# Check UTF-8 support
print(f"UTF-8 Mode: {sys.flags.utf8_mode}")
print(f"Default Encoding: {sys.getdefaultencoding()}")
print(f"Filesystem Encoding: {sys.getfilesystemencoding()}")

# Check environment
env_vars = ['PYTHONUTF8', 'PAPERLESS_BASE_URL', 'OLLAMA_BASE_URL']
for var in env_vars:
    value = os.environ.get(var, "NOT SET")
    if 'TOKEN' in var or 'KEY' in var:
        value = "***" if value != "NOT SET" else value
    print(f"{var}: {value}")

# Check imports
packages = ['litellm', 'pydantic', 'rapidfuzz', 'httpx']
for pkg in packages:
    try:
        __import__(pkg)
        print(f"✓ {pkg} installed")
    except ImportError:
        print(f"✗ {pkg} missing")

# Platform-specific checks
if platform.system() == "Windows":
    # Check long path support
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                           r"SYSTEM\CurrentControlSet\Control\FileSystem")
        value, _ = winreg.QueryValueEx(key, "LongPathsEnabled")
        print(f"Long Paths: {'Enabled' if value else 'Disabled'}")
    except:
        print("Long Paths: Unknown")
EOF
```

## Cross-Platform Issues

### Issue: Path Separator Problems

**Symptoms:**
- File not found errors
- Incorrect path construction
- Backslash/forward slash confusion

**Solution:**
```python
# Always use pathlib
from pathlib import Path

# Good - works everywhere
config_path = Path.home() / ".paperless_ngx" / "config.yaml"

# Bad - platform-specific
config_path = os.path.join(os.environ['HOME'], '.paperless_ngx/config.yaml')
```

**Fix in config:**
```env
# Use forward slashes in .env (works on all platforms)
ATTACHMENT_DIR=data/attachments
LOG_DIR=logs/application
```

### Issue: Encoding Errors

**Symptoms:**
- UnicodeDecodeError
- Characters display incorrectly
- File reading/writing fails

**Windows Fix:**
```cmd
# Set environment variable
setx PYTHONUTF8 1

# Or in PowerShell
[Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User")
```

**Linux Fix:**
```bash
# Set in shell profile
echo 'export PYTHONUTF8=1' >> ~/.bashrc
echo 'export LC_ALL=en_US.UTF-8' >> ~/.bashrc
source ~/.bashrc
```

**Code Fix:**
```python
# Always specify encoding
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()
```

### Issue: Line Ending Conflicts

**Symptoms:**
- Git shows all files as modified
- Scripts fail with ^M characters
- Config files not parsed correctly

**Solution:**
```bash
# Configure Git globally
git config --global core.autocrlf input  # Linux/Mac
git config --global core.autocrlf true   # Windows

# Fix existing files
# Linux/Mac
find . -type f -name "*.py" -exec dos2unix {} \;

# Windows (Git Bash)
find . -type f -name "*.py" -exec unix2dos {} \;
```

### Issue: Virtual Environment Not Portable

**Symptoms:**
- venv doesn't work after copying between systems
- Module import errors after system change
- Different Python versions cause issues

**Solution:**
```bash
# Never copy venv between systems!
# Instead, use requirements.txt

# On source system
pip freeze > requirements.txt

# On target system
python -m venv venv_new
source venv_new/bin/activate  # Linux
venv_new\Scripts\activate      # Windows
pip install -r requirements.txt
```

## Windows-Specific Issues

### Issue: PowerShell Execution Policy

**Symptoms:**
- "cannot be loaded because running scripts is disabled"
- venv activation fails in PowerShell

**Solution:**
```powershell
# Check current policy
Get-ExecutionPolicy

# Fix for current user
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Or bypass for single session
powershell.exe -ExecutionPolicy Bypass -File script.ps1
```

### Issue: Long Path Limitations

**Symptoms:**
- "path too long" errors
- Cannot create deeply nested directories
- Installation fails with path errors

**Solution:**
```powershell
# Enable long paths (requires admin)
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
    -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force

# Restart required!
```

**Alternative workaround:**
```python
# Use \\?\ prefix for long paths
import os
long_path = r"\\?\C:\very\long\path\to\file"
if os.path.exists(long_path):
    print("File exists")
```

### Issue: Windows Defender Blocking

**Symptoms:**
- Scripts deleted automatically
- "Virus detected" warnings
- Slow performance during scanning

**Solution:**
1. Add exclusions in Windows Security:
   - Settings → Windows Security → Virus & threat protection
   - Manage settings → Add exclusions
   - Add folder: Your project directory

2. Command line exclusion:
```powershell
Add-MpPreference -ExclusionPath "C:\path\to\project"
Add-MpPreference -ExclusionProcess "python.exe"
```

### Issue: SSL Certificate Verification Failed

**Symptoms:**
- SSL: CERTIFICATE_VERIFY_FAILED
- Unable to connect to APIs

**Solution:**
```cmd
# Update certificates
pip install --upgrade certifi

# Set certificate bundle
set SSL_CERT_FILE=C:\path\to\cacert.pem
set REQUESTS_CA_BUNDLE=C:\path\to\cacert.pem

# Or disable (NOT RECOMMENDED)
set PYTHONHTTPSVERIFY=0
```

### Issue: Ollama Not Starting on Windows

**Symptoms:**
- "connection refused" to localhost:11434
- Ollama command not found

**Solution:**
```cmd
# Check if Ollama service is running
sc query ollama

# Start Ollama service
sc start ollama

# Or run manually
"C:\Program Files\Ollama\ollama.exe" serve

# Add to PATH if needed
setx PATH "%PATH%;C:\Program Files\Ollama"
```

## Linux-Specific Issues

### Issue: Permission Denied

**Symptoms:**
- Cannot write to directories
- Cannot execute scripts
- pip install fails

**Solution:**
```bash
# Fix ownership
sudo chown -R $USER:$USER ~/project-directory

# Fix permissions
chmod 755 ~/project-directory
chmod 644 .env  # Secure credentials

# For pip issues (avoid sudo pip!)
pip install --user package-name
# Or use virtual environment
```

### Issue: Missing System Libraries

**Symptoms:**
- "error: Microsoft Visual C++ 14.0 is required" (WSL)
- "No module named '_ctypes'"
- Build errors during pip install

**Ubuntu/Debian Solution:**
```bash
sudo apt update
sudo apt install -y \
    build-essential \
    python3-dev \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev
```

**Fedora Solution:**
```bash
sudo dnf install -y \
    gcc \
    python3-devel \
    libffi-devel \
    openssl-devel \
    libxml2-devel \
    libxslt-devel \
    zlib-devel
```

### Issue: Ollama GPU Not Detected

**Symptoms:**
- Ollama using CPU only
- Slow inference
- nvidia-smi not showing ollama

**Solution:**
```bash
# Check NVIDIA drivers
nvidia-smi

# Install/update drivers
sudo apt install nvidia-driver-535  # Ubuntu

# Check CUDA
nvcc --version

# Restart Ollama
systemctl restart ollama

# Verify GPU usage
ollama run llama3.1:8b --verbose
```

### Issue: Port Already in Use

**Symptoms:**
- "Address already in use"
- Cannot start Ollama
- API connection fails

**Solution:**
```bash
# Find process using port
sudo lsof -i :11434
# or
sudo netstat -tlnp | grep 11434

# Kill process
kill -9 <PID>

# Or change port in config
OLLAMA_HOST=0.0.0.0:11435 ollama serve
```

## Connection Problems

### Paperless NGX Connection Issues

**Diagnosis:**
```python
# Test connection manually
import httpx

url = "http://your-paperless:8000/api/"
token = "your-token"

response = httpx.get(
    url,
    headers={"Authorization": f"Token {token}"},
    timeout=10
)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:200]}")
```

**Common Fixes:**
1. Check URL format (include /api/)
2. Verify token is correct
3. Check network/firewall
4. Ensure Paperless is running
5. Try http:// instead of https://

### Email IMAP Connection Issues

**Gmail Specific:**
1. Enable 2-factor authentication
2. Generate app-specific password
3. Use imap.gmail.com:993
4. Enable "Less secure app access" (if needed)

**General IMAP:**
```python
# Test IMAP connection
import imaplib

mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
try:
    mail.login('user@gmail.com', 'app-password')
    print("✓ Login successful")
    mail.select('INBOX')
    typ, data = mail.search(None, 'ALL')
    print(f"✓ Found {len(data[0].split())} emails")
except Exception as e:
    print(f"✗ Error: {e}")
finally:
    mail.logout()
```

### LLM Provider Connection Issues

**Ollama:**
```bash
# Test Ollama
curl http://localhost:11434/api/tags

# If fails, check:
ps aux | grep ollama
systemctl status ollama
ollama serve  # Run manually
```

**OpenAI:**
```python
# Test OpenAI
import openai
openai.api_key = "sk-..."

try:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "test"}],
        max_tokens=5
    )
    print("✓ OpenAI connected")
except Exception as e:
    print(f"✗ Error: {e}")
```

## Performance Issues

### Slow Document Processing

**Diagnosis:**
```bash
# Profile the code
python -m cProfile -o profile.stats run.py
python -m pstats profile.stats
```

**Solutions:**
1. **Reduce batch size:**
   ```env
   BATCH_CHUNK_SIZE=5  # Instead of 10
   ```

2. **Use faster LLM model:**
   ```env
   OLLAMA_MODEL=llama3.1:7b  # Instead of 8b
   # Or use Gemma, Phi-2 for speed
   ```

3. **Increase timeouts:**
   ```env
   LLM_TIMEOUT=60  # Seconds
   HTTP_TIMEOUT=30
   ```

### High Memory Usage

**Monitor:**
```bash
# Linux
htop
free -h

# Windows
tasklist /FI "IMAGENAME eq python.exe"
```

**Solutions:**
1. Process documents in smaller batches
2. Clear cache periodically
3. Use generator patterns
4. Limit concurrent operations

### Ollama Performance

**Optimize Ollama:**
```bash
# Limit memory usage
OLLAMA_MAX_LOADED_MODELS=1 ollama serve

# Use GPU
CUDA_VISIBLE_DEVICES=0 ollama serve

# Adjust number of threads
OLLAMA_NUM_THREADS=4 ollama serve
```

## Error Messages

### Common Error Patterns

| Error | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError: No module named 'X'` | Package not installed | `pip install X` |
| `PermissionError: [Errno 13]` | No write permission | Check file/directory permissions |
| `FileNotFoundError: [Errno 2]` | Path doesn't exist | Verify path, create directories |
| `UnicodeDecodeError` | Encoding mismatch | Use `encoding='utf-8'` |
| `ConnectionRefusedError` | Service not running | Start the service |
| `TimeoutError` | Slow response | Increase timeout values |
| `JSONDecodeError` | Invalid JSON | Check API response format |
| `ImportError: cannot import name` | Version mismatch | Check package versions |

### Detailed Error Analysis

For any error:
1. **Capture full traceback:**
   ```python
   import traceback
   try:
       # Your code
   except Exception as e:
       print(traceback.format_exc())
   ```

2. **Enable debug logging:**
   ```bash
   python run.py --debug 2>&1 | tee debug.log
   ```

3. **Check system resources:**
   ```bash
   df -h     # Disk space
   free -m   # Memory
   uptime    # Load average
   ```

## Recovery Procedures

### Complete Reset

If nothing else works:

```bash
# 1. Backup configuration
cp .env .env.backup
cp -r ~/.paperless_ngx ~/.paperless_ngx.backup

# 2. Clean everything
deactivate  # Exit venv
rm -rf venv
rm -rf __pycache__
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# 3. Reinstall
python3 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install --upgrade pip
pip install -r requirements.txt

# 4. Restore configuration
cp .env.backup .env

# 5. Test
python test_connections.py
```

### Database/Cache Reset

```bash
# Clear application cache
rm -rf ~/.paperless_ngx/cache/*
rm -rf /tmp/paperless_ngx/*

# Reset state files
rm ~/.paperless_ngx/state/*.json

# Rebuild cache
python -c "from src.paperless_ngx.infrastructure.paperless.api_client import PaperlessApiClient; client = PaperlessApiClient(); client.clear_cache()"
```

### Emergency Rollback

```bash
# If recent changes broke the system
git status  # Check changes
git stash   # Save current changes
git checkout main  # Return to stable
git pull    # Get latest stable

# Test if working
python test_connections.py

# If OK, carefully reapply changes
git stash pop
```

## Getting Help

### Information to Provide

When asking for help, include:

1. **System Info:**
   ```bash
   python diagnose.py > system_info.txt
   ```

2. **Error Details:**
   - Full error message and traceback
   - What you were trying to do
   - What you expected to happen

3. **Configuration (sanitized):**
   ```bash
   grep -v "TOKEN\|KEY\|PASSWORD" .env > config_sanitized.txt
   ```

4. **Recent Changes:**
   - What changed recently?
   - New packages installed?
   - System updates?

### Support Channels

1. **GitHub Issues**: For bugs and feature requests
2. **Discussions**: For questions and help
3. **Documentation**: Check all guides first
4. **Community Forums**: Paperless NGX community

---

**Navigation**: [Documentation Index](../INDEX.md) | [Windows Setup](WINDOWS_SETUP.md) | [Linux Setup](LINUX_SETUP.md) | [Quick Start](QUICKSTART.md)