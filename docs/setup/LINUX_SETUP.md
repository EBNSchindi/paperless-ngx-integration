# Linux Setup Guide

Complete installation and configuration guide for Linux systems (Ubuntu, Debian, Fedora, Arch).

**Last Updated**: August 12, 2025

## Table of Contents
1. [System Requirements](#system-requirements)
2. [Prerequisites](#prerequisites)
3. [Python Installation](#python-installation)
4. [Project Setup](#project-setup)
5. [LLM Provider Setup](#llm-provider-setup)
6. [Configuration](#configuration)
7. [Testing Installation](#testing-installation)
8. [Distribution-Specific Notes](#distribution-specific-notes)
9. [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Requirements
- **OS**: Ubuntu 20.04+, Debian 11+, Fedora 35+, or Arch Linux
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 2GB free space
- **Python**: 3.9+ (3.11+ recommended)
- **Network**: Internet connection for API access

### Recommended Setup
- **OS**: Ubuntu 22.04 LTS or latest stable release
- **RAM**: 8GB or more
- **Storage**: 5GB free space
- **CPU**: 4+ cores for Ollama
- **GPU**: Optional, NVIDIA GPU improves Ollama performance

## Prerequisites

### 1. Update System Packages

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential curl git
```

**Fedora:**
```bash
sudo dnf update -y
sudo dnf install -y gcc make curl git
```

**Arch Linux:**
```bash
sudo pacman -Syu
sudo pacman -S base-devel git curl
```

### 2. Install System Dependencies

**Ubuntu/Debian:**
```bash
# Development tools
sudo apt install -y python3-dev python3-pip python3-venv

# Optional: For better terminal experience
sudo apt install -y tmux htop ncdu

# For SSL/TLS support
sudo apt install -y ca-certificates
```

**Fedora:**
```bash
sudo dnf install -y python3-devel python3-pip
sudo dnf install -y tmux htop ncdu
```

**Arch Linux:**
```bash
sudo pacman -S python python-pip
sudo pacman -S tmux htop ncdu
```

## Python Installation

### Option 1: System Python (Quick Start)

Most Linux distributions include Python 3.9+:

```bash
# Check Python version
python3 --version

# If Python 3.9+ is installed, you're ready!
# Install pip if missing
sudo apt install python3-pip  # Ubuntu/Debian
sudo dnf install python3-pip  # Fedora
sudo pacman -S python-pip     # Arch
```

### Option 2: Python 3.11 (Recommended)

**Ubuntu 22.04+:**
```bash
# Python 3.11 is available in default repos
sudo apt install -y python3.11 python3.11-venv python3.11-dev
```

**Ubuntu 20.04 (via PPA):**
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev
```

**Fedora:**
```bash
sudo dnf install -y python3.11 python3.11-devel
```

**Arch Linux:**
```bash
# Arch typically has the latest Python
sudo pacman -S python
```

### Option 3: pyenv (Version Management)

Install multiple Python versions:

```bash
# Install pyenv
curl https://pyenv.run | bash

# Add to shell config (~/.bashrc or ~/.zshrc)
echo 'export PATH="$HOME/.pyenv/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc

# Reload shell
source ~/.bashrc

# Install Python 3.11
pyenv install 3.11.8
pyenv global 3.11.8
```

## Project Setup

### 1. Clone Repository

```bash
# Navigate to desired directory
cd ~/Documents  # or wherever you prefer

# Clone the repository
git clone https://github.com/yourusername/paperless-ngx-integration.git
cd paperless-ngx-integration
```

### 2. Create Virtual Environment

```bash
# Using Python 3.11 specifically
python3.11 -m venv venv

# Or use system Python
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# You should see (venv) in your prompt
```

### 3. Install Dependencies

```bash
# Upgrade pip first
pip install --upgrade pip

# Install project dependencies
pip install -r requirements.txt

# For development (optional)
pip install -r requirements-dev.txt
```

### 4. Verify Installation

```bash
# Check all packages installed
pip list | grep -E "litellm|pydantic|rapidfuzz"

# Test imports
python -c "import litellm; print('✓ LiteLLM')"
python -c "import pydantic; print('✓ Pydantic')"
python -c "import rapidfuzz; print('✓ RapidFuzz')"
```

## LLM Provider Setup

### Option 1: Ollama (Local, Recommended)

1. **Install Ollama**

```bash
# Official installation script
curl -fsSL https://ollama.ai/install.sh | sh

# Verify installation
ollama --version
```

2. **Start Ollama Service**

```bash
# Start Ollama (runs in background)
ollama serve &

# Or use systemd (if available)
sudo systemctl start ollama
sudo systemctl enable ollama  # Start on boot

# Pull recommended model
ollama pull llama3.1:8b

# Test model
ollama run llama3.1:8b "Hello from Linux!"
```

3. **Configure GPU Support (Optional)**

For NVIDIA GPUs:
```bash
# Install NVIDIA drivers
sudo apt install nvidia-driver-535  # Ubuntu
sudo dnf install nvidia-driver      # Fedora

# Verify GPU detected
nvidia-smi

# Ollama will automatically use GPU if available
```

### Option 2: OpenAI (Cloud)

1. **Get API Key**
   - Visit: https://platform.openai.com/api-keys
   - Create new secret key
   - Store securely

2. **Configure securely**
```bash
# Don't put API keys in shell history!
read -s OPENAI_KEY
# Paste your key and press Enter

# Add to .env file
echo "OPENAI_API_KEY=$OPENAI_KEY" >> .env
```

## Configuration

### 1. Create Environment File

```bash
# Copy template
cp .env.example .env

# Edit with your preferred editor
nano .env        # or
vim .env         # or
code .env        # VS Code
```

### 2. Essential Configuration

```bash
# Edit .env file
cat > .env << 'EOF'
# Paperless NGX
PAPERLESS_BASE_URL=http://localhost:8000/api
PAPERLESS_API_TOKEN=your-token-here

# LLM Provider Order
LLM_PROVIDER_ORDER=ollama,openai

# Ollama (local)
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# OpenAI (optional fallback)
OPENAI_ENABLED=false
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-3.5-turbo

# Email Account
EMAIL_ACCOUNT_1_NAME="Gmail Business"
EMAIL_ACCOUNT_1_SERVER=imap.gmail.com
EMAIL_ACCOUNT_1_PORT=993
EMAIL_ACCOUNT_1_USERNAME=your-email@gmail.com
EMAIL_ACCOUNT_1_PASSWORD=your-app-password

# Linux-specific paths
TEMP_DIR=/tmp/paperless_ngx
LOG_DIR=~/.paperless_ngx/logs
ATTACHMENT_DIR=~/Documents/paperless_attachments
EOF
```

### 3. Secure Permissions

```bash
# Protect .env file
chmod 600 .env

# Create necessary directories
mkdir -p ~/.paperless_ngx/logs
mkdir -p ~/Documents/paperless_attachments
```

## Testing Installation

### 1. Test Connections

```bash
# Run connection tests
python test_connections.py

# Expected output:
# ✅ Paperless NGX: Connected
# ✅ Ollama: Connected (v0.1.34)
# ✅ Email: Connected (3 accounts)
```

### 2. Run Test Suite

```bash
# Quick workflow test
python test_july_2025_simple.py

# Full test suite (requires pytest)
pytest tests/ -v

# With coverage
pytest --cov=src/paperless_ngx --cov-report=term-missing
```

### 3. Test Interactive Menu

```bash
# Main menu
python run.py

# Simplified 3-point workflow
python -m paperless_ngx.presentation.cli.simplified_menu
```

## Distribution-Specific Notes

### Ubuntu/Debian

- **AppArmor**: May restrict file access. Check with `aa-status`
- **Snap Packages**: Avoid snap Python, use apt version
- **UFW Firewall**: Allow Ollama port if needed: `sudo ufw allow 11434`

### Fedora/RHEL

- **SELinux**: May block operations. Check with `getenforce`
- **Firewall**: Open ports with `firewall-cmd --add-port=11434/tcp`
- **Python**: Multiple versions available via `alternatives`

### Arch Linux

- **AUR Packages**: Can install Ollama from AUR
- **Rolling Release**: Keep system updated regularly
- **Python**: Usually latest version available

### WSL2 (Windows Subsystem for Linux)

Special considerations for WSL2:
```bash
# Use Windows paths
ATTACHMENT_DIR=/mnt/c/Users/YourName/Documents/attachments

# Ollama in Windows, accessed from WSL
OLLAMA_BASE_URL=http://host.docker.internal:11434

# Better performance with WSL2 backend
wsl --set-version Ubuntu 2
```

## System Service Setup (Optional)

### Create systemd Service

```bash
# Create service file
sudo tee /etc/systemd/system/paperless-fetcher.service << EOF
[Unit]
Description=Paperless NGX Email Fetcher
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/Documents/paperless-ngx-integration
Environment="PATH=$HOME/Documents/paperless-ngx-integration/venv/bin"
ExecStart=$HOME/Documents/paperless-ngx-integration/venv/bin/python run.py --run-email-fetcher
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable paperless-fetcher
sudo systemctl start paperless-fetcher

# Check status
sudo systemctl status paperless-fetcher
```

## Troubleshooting

### Common Issues

#### Python Version Conflicts
```bash
# Use specific Python version
python3.11 -m venv venv

# Or use update-alternatives
sudo update-alternatives --config python3
```

#### Permission Denied
```bash
# Fix ownership
sudo chown -R $USER:$USER ~/Documents/paperless-ngx-integration

# Fix permissions
chmod -R u+rwX ~/Documents/paperless-ngx-integration
```

#### Missing Dependencies
```bash
# Ubuntu/Debian
sudo apt install -y python3-dev libffi-dev libssl-dev

# Fedora
sudo dnf install -y python3-devel openssl-devel

# Arch
sudo pacman -S python openssl
```

#### Ollama Connection Issues
```bash
# Check if Ollama is running
ps aux | grep ollama

# Check port
netstat -tlnp | grep 11434

# Restart Ollama
pkill ollama
ollama serve &
```

#### SSL Certificate Errors
```bash
# Update certificates
sudo apt update && sudo apt install ca-certificates
sudo update-ca-certificates

# For Python
pip install --upgrade certifi
```

### Performance Optimization

#### CPU Governor
```bash
# Check current governor
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Set to performance mode
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

#### Memory Management
```bash
# Check memory usage
free -h

# Clear cache if needed
sudo sync && sudo sysctl -w vm.drop_caches=3
```

#### Process Priority
```bash
# Run with higher priority
nice -n -10 python run.py
```

## Cron Job Setup

Schedule automatic processing:

```bash
# Edit crontab
crontab -e

# Add scheduled tasks
# Fetch emails every hour
0 * * * * cd ~/Documents/paperless-ngx-integration && ./venv/bin/python run.py --fetch-email-attachments

# Weekly quality scan (Sunday 2 AM)
0 2 * * 0 cd ~/Documents/paperless-ngx-integration && ./venv/bin/python -m paperless_ngx.presentation.cli.simplified_menu --workflow 3

# Monthly processing (1st of month, 3 AM)
0 3 1 * * cd ~/Documents/paperless-ngx-integration && ./venv/bin/python -m paperless_ngx.presentation.cli.simplified_menu --workflow 2
```

## Security Best Practices

1. **File Permissions**
```bash
chmod 600 .env                    # Protect credentials
chmod 700 ~/.paperless_ngx        # Protect config directory
```

2. **Use Secret Management**
```bash
# Use pass or similar
pass insert paperless/api_token
PAPERLESS_API_TOKEN=$(pass paperless/api_token) python run.py
```

3. **Audit Logs**
```bash
# Monitor access
tail -f ~/.paperless_ngx/logs/access.log
```

## Next Steps

1. **Configure Paperless NGX**: Get API token from admin interface
2. **Setup Email Accounts**: Configure IMAP credentials
3. **Choose LLM Provider**: Install Ollama or configure OpenAI
4. **Run Test Workflow**: Process sample documents
5. **Read User Manual**: Explore all features

## Support

### Getting Help
1. Check [Troubleshooting Guide](TROUBLESHOOTING.md)
2. Review [FAQ](../user-guide/FAQ.md)
3. Search [GitHub Issues](https://github.com/yourusername/paperless-ngx-integration/issues)
4. Linux community forums

### Reporting Issues
When reporting Linux-specific issues, include:
- Distribution and version (`lsb_release -a`)
- Python version (`python3 --version`)
- Kernel version (`uname -r`)
- Error messages with full traceback
- Relevant log files

---

**Navigation**: [Documentation Index](../INDEX.md) | [Windows Setup](WINDOWS_SETUP.md) | [Troubleshooting](TROUBLESHOOTING.md) | [Quick Start](QUICKSTART.md)