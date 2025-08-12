# Frequently Asked Questions (FAQ)

Common questions and answers about the Paperless NGX Integration System.

**Last Updated**: August 12, 2025

## Table of Contents
1. [General Questions](#general-questions)
2. [Installation & Setup](#installation--setup)
3. [Configuration](#configuration)
4. [Email Integration](#email-integration)
5. [Document Processing](#document-processing)
6. [LLM & AI](#llm--ai)
7. [Troubleshooting](#troubleshooting)
8. [Performance](#performance)
9. [Security & Privacy](#security--privacy)

## General Questions

### What is this system for?

The Paperless NGX Integration System automates document management by:
- Fetching email attachments automatically
- Extracting metadata using AI (sender, type, tags)
- Organizing documents in Paperless NGX
- Providing quality analysis and reports

### Who is this for?

Perfect for:
- Small businesses managing invoices and contracts
- Freelancers organizing client documents
- Individuals digitizing personal paperwork
- Anyone using Paperless NGX wanting automation

### What are the system requirements?

**Minimum**:
- Python 3.9+
- 4GB RAM
- 2GB disk space
- Windows 10+ or Linux (Ubuntu 20.04+)

**Recommended**:
- Python 3.11+
- 8GB RAM
- 5GB disk space
- SSD for better performance

### Is this free to use?

Yes! The software is open source (MIT License). However:
- OpenAI API has usage costs (~$0.002 per document)
- Ollama is completely free (runs locally)
- Paperless NGX is also free and open source

## Installation & Setup

### How long does setup take?

Typical setup time:
- Basic installation: 15-30 minutes
- Full configuration: 30-60 minutes
- First test run: 5-10 minutes

### Can I run this on Windows?

Yes! Full Windows support with:
- Automatic path handling
- UTF-8 encoding support
- Windows-specific setup guide
- PowerShell compatibility

See [Windows Setup Guide](../setup/WINDOWS_SETUP.md)

### Can I run this on a Raspberry Pi?

Yes, but with limitations:
- Use Ollama with small models (phi-2, tinyllama)
- Process documents in smaller batches
- Allow more time for processing
- Minimum 4GB RAM model recommended

### Do I need to know Python?

No! Basic usage requires no programming:
- Simple menu-driven interface
- Pre-configured commands
- Detailed documentation

Python knowledge helps for:
- Advanced customization
- Troubleshooting
- Contributing to development

### Can I use this without Paperless NGX?

Currently, Paperless NGX is required. The system is built specifically for Paperless NGX integration. Future versions may support other document management systems.

## Configuration

### Where do I get a Paperless API token?

1. Log into Paperless NGX admin
2. Go to User Settings
3. Click "Create Token"
4. Copy token to `.env` file

### How do I set up multiple email accounts?

Add numbered account entries in `.env`:

```env
# Account 1
EMAIL_ACCOUNT_1_NAME="Gmail Business"
EMAIL_ACCOUNT_1_SERVER=imap.gmail.com
EMAIL_ACCOUNT_1_USERNAME=business@gmail.com
EMAIL_ACCOUNT_1_PASSWORD=app-password-here

# Account 2
EMAIL_ACCOUNT_2_NAME="IONOS"
EMAIL_ACCOUNT_2_SERVER=imap.ionos.de
EMAIL_ACCOUNT_2_USERNAME=mail@domain.com
EMAIL_ACCOUNT_2_PASSWORD=password-here

# Account 3 (up to 10 supported)
EMAIL_ACCOUNT_3_NAME="Outlook"
# ... etc
```

### What's the difference between OpenAI and Ollama?

| Feature | OpenAI | Ollama |
|---------|--------|---------|
| **Cost** | ~$0.002/document | Free |
| **Speed** | Fast (1-2 sec) | Slower (3-10 sec) |
| **Quality** | Excellent | Good |
| **Privacy** | Cloud-based | Local/Private |
| **Internet** | Required | Not required |
| **Setup** | API key only | Install Ollama |

### How do I change the LLM provider order?

Edit `.env`:
```env
# Quality first (recommended)
LLM_PROVIDER_ORDER=openai,ollama

# Privacy first
LLM_PROVIDER_ORDER=ollama,openai

# Single provider only
LLM_PROVIDER_ORDER=ollama
```

## Email Integration

### Why are my Gmail attachments not downloading?

Common issues:
1. **2-Factor Authentication**: Use app-specific password, not regular password
2. **Less Secure Apps**: May need to enable (not recommended)
3. **Wrong folder**: Try "All Mail" instead of "INBOX"
4. **Attachment size**: Check if files are too large

### How do I get a Gmail app password?

1. Enable 2-factor authentication
2. Go to: https://myaccount.google.com/apppasswords
3. Select "Mail" and your device
4. Generate password
5. Use this in `.env` file

### Can I filter which emails to process?

Yes, several options:
```env
# By date range
EMAIL_SINCE_DAYS=30  # Last 30 days only

# By folder
EMAIL_ACCOUNT_1_FOLDER="Invoices"  # Specific folder

# By sender (in code)
FILTER_SENDERS="invoice@company.com,billing@service.com"
```

### What file types are supported?

Currently:
- ✅ PDF files (primary)
- ✅ Images (JPG, PNG) - OCR in Paperless
- ⚠️ Office docs - Convert to PDF first
- ❌ ZIP/RAR - Not supported

### How are duplicates handled?

The system:
1. Tracks processed emails by Message-ID
2. Skips already downloaded attachments
3. Checks file hash before processing
4. State saved in `~/.paperless_ngx/state/`

## Document Processing

### What metadata is extracted?

For each document:
- **Correspondent**: Who sent it (company/person)
- **Document Type**: Invoice, Contract, Letter, etc.
- **Tags**: 3-7 relevant keywords in German
- **Title**: Formatted filename
- **Description**: Brief summary (max 128 chars)
- **Date**: Document date (if found)

### Why are my documents in German?

The system is configured for German business documents by default. To change:

1. Update prompts in `src/paperless_ngx/infrastructure/llm/prompts.py`
2. Change tag language in configuration
3. Adjust document type classifications

### How does tag matching work?

Smart tag unification:
- **95% similar**: Automatically merged (e.g., "invoice" → "invoices")
- **85-94% similar**: Suggested for review
- **Below 85%**: Kept separate
- **Special cases**: "Telekom" ≠ "Telekommunikation" (60% similar)

### Can I customize document types?

Yes! Edit `config/document_types.yaml`:
```yaml
document_types:
  - name: "Rechnung"
    aliases: ["Invoice", "Bill", "Faktura"]
    keywords: ["total", "amount", "due date"]
  - name: "Vertrag"
    aliases: ["Contract", "Agreement"]
    keywords: ["terms", "parties", "signature"]
```

### How do I reprocess documents?

Several options:
```bash
# Single document
python run.py --process-document 1234

# Date range
python run.py --reprocess --from 2025-07-01 --to 2025-07-31

# Documents with errors
python run.py --reprocess --failed-only

# Force reprocessing (ignore cache)
python run.py --batch-process --force
```

## LLM & AI

### Which LLM model should I use?

**For quality** (OpenAI):
- gpt-3.5-turbo: Fast and cheap
- gpt-4: Best quality, more expensive

**For privacy** (Ollama):
- llama3.1:8b: Best overall (8GB RAM)
- mistral:7b: Good quality, faster
- phi-2: Very fast, lower quality
- gemma:2b: Minimal resources (4GB RAM)

### How much does OpenAI cost?

Typical costs:
- ~$0.002 per document (GPT-3.5-turbo)
- ~$0.02 per document (GPT-4)
- 1000 documents ≈ $2-20

Monitor costs:
```bash
python run.py --llm-costs
```

### Can I use both OpenAI and Ollama?

Yes! Configure fallback:
```env
LLM_PROVIDER_ORDER=openai,ollama
# Try OpenAI first, fall back to Ollama if it fails
```

### How do I install Ollama models?

```bash
# Install Ollama first
curl -fsSL https://ollama.ai/install.sh | sh  # Linux
# Or download from https://ollama.ai/download  # Windows

# Pull models
ollama pull llama3.1:8b    # Recommended
ollama pull mistral:7b     # Alternative
ollama pull phi-2           # Fast, lightweight

# List installed models
ollama list
```

### Why is Ollama slow?

Common reasons:
1. **No GPU**: CPU-only is 10x slower
2. **Large model**: Try smaller model (phi-2)
3. **Low RAM**: Need 8GB+ for good performance
4. **Background processes**: Close other apps

Speed up Ollama:
```bash
# Use GPU (NVIDIA)
CUDA_VISIBLE_DEVICES=0 ollama serve

# Limit context
OLLAMA_NUM_CTX=2048 ollama serve

# Use smaller model
OLLAMA_MODEL=phi-2
```

## Troubleshooting

### "Connection refused" error

Check services:
```bash
# Paperless NGX
curl http://localhost:8000/api/
# Should return JSON

# Ollama
curl http://localhost:11434/api/tags
# Should list models

# Email
python test_connections.py
```

### "UnicodeDecodeError" on Windows

Fix UTF-8 encoding:
```cmd
# Set environment variable
setx PYTHONUTF8 1

# Restart terminal and retry
```

### "Path too long" on Windows

Enable long paths:
```powershell
# Run as Administrator
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

### Documents not appearing in Paperless

Check:
1. API token is correct
2. Paperless is running
3. Document was uploaded successfully
4. Check Paperless logs
5. Verify permissions

### OCR text is empty

Solutions:
1. Reprocess in Paperless with higher DPI
2. Check if PDF has selectable text
3. Install better OCR languages in Paperless
4. Try different OCR engine (Tesseract settings)

## Performance

### How fast is processing?

Typical speeds:
- **Email fetch**: 10-20 documents/minute
- **LLM processing**: 
  - OpenAI: 30-60 documents/minute
  - Ollama (GPU): 10-20 documents/minute
  - Ollama (CPU): 2-5 documents/minute
- **Quality scan**: 100 documents/minute

### How can I speed up processing?

1. **Use faster LLM**:
   ```env
   OLLAMA_MODEL=phi-2  # Faster than llama
   ```

2. **Increase batch size**:
   ```env
   BATCH_CHUNK_SIZE=20  # Default is 10
   ```

3. **Parallel processing**:
   ```env
   PARALLEL_WORKERS=4  # Use multiple cores
   ```

4. **Skip unnecessary checks**:
   ```bash
   python run.py --batch-process --skip-validation
   ```

### Memory usage is high

Reduce memory:
```env
# Smaller batches
BATCH_CHUNK_SIZE=5

# Limit cache
CACHE_SIZE=100  # Documents in memory

# Stream processing
STREAM_MODE=true
```

### Can I process documents in parallel?

Yes, but carefully:
```bash
# Split by date range (safe)
python run.py --process --month 2025-07 &
python run.py --process --month 2025-08 &

# NOT recommended (conflicts):
# Multiple instances on same documents
```

## Security & Privacy

### Is my data safe?

**Local data**:
- Stored on your computer only
- No external transmission (except configured APIs)
- You control all data

**API data**:
- OpenAI: Sent to OpenAI servers (check their privacy policy)
- Ollama: Completely local, no external transmission
- Email: Standard IMAP security

### How are passwords stored?

Passwords in `.env` file:
- Local file only
- Should be protected (chmod 600 on Linux)
- Never committed to git (.gitignore)
- Consider using environment variables instead

### Can I use this offline?

Partially:
- ✅ Ollama works offline
- ❌ OpenAI requires internet
- ❌ Email fetch requires internet
- ✅ Local processing works offline
- ✅ Quality scans work offline

### GDPR compliance?

For GDPR compliance:
1. Use Ollama (local processing)
2. Self-host Paperless NGX
3. Don't use cloud LLMs for sensitive data
4. Implement data retention policies
5. Document your processing activities

### How do I delete processed data?

```bash
# Clear cache
rm -rf ~/.paperless_ngx/cache/

# Clear state
rm -rf ~/.paperless_ngx/state/

# Remove downloaded attachments
rm -rf data/attachments/

# Clean logs
rm -rf logs/
```

## Still Have Questions?

### Getting Help

1. **Check Documentation**: [Documentation Index](../INDEX.md)
2. **Review Examples**: [Workflow Guide](WORKFLOWS.md)
3. **Search Issues**: [GitHub Issues](https://github.com/yourusername/paperless-ngx-integration/issues)
4. **Ask Community**: [Discussions](https://github.com/yourusername/paperless-ngx-integration/discussions)

### Reporting Issues

When reporting issues, include:
- System info: `python diagnose.py`
- Error messages (full traceback)
- Configuration (sanitized)
- Steps to reproduce

### Feature Requests

We welcome suggestions! Please:
1. Check if already requested
2. Describe the use case
3. Explain expected behavior
4. Consider contributing code

---

**Navigation**: [Documentation Index](../INDEX.md) | [User Manual](../USER_MANUAL.md) | [Workflows](WORKFLOWS.md) | [Troubleshooting](../setup/TROUBLESHOOTING.md)