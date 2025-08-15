# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Personal Agents Available

This project includes personal agents in `.claude/agents/`:
- **researcher**: Research and requirements analysis
- **architect-cleaner**: Architecture validation and cleanup
- **python-generator**: Modern Python 3.10+ code generation
- **test-engineer**: Comprehensive test suite creation
- **code-reviewer**: Code review for Python projects
- **doc-writer**: Documentation generation and maintenance
- **security-engineer**: Security analysis and vulnerability detection
- **prompt-engineer**: Technical prompt optimization
- **claude-status**: Dashboard and metrics tracking

See `.claude/agents/README.md` for agent usage guidelines.

## Project Overview

**Paperless NGX Integration** - Document management automation system for processing email attachments, extracting metadata via LLM, and managing documents in Paperless NGX.

- **Architecture**: Clean Architecture with Domain-Driven Design
- **Python**: 3.11+ (3.9+ minimum)
- **Key Dependencies**: litellm, pydantic v2, imapclient, rapidfuzz

## Commands

### Installation and Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env  # Then add your credentials

# Run main application (interactive menu)
python run.py
```

### Core Workflows
```bash
# Interactive 3-point menu
python -m paperless_ngx.presentation.cli.simplified_menu

# Direct workflow execution
python -m paperless_ngx.presentation.cli.simplified_menu --workflow 1  # Email fetch
python -m paperless_ngx.presentation.cli.simplified_menu --workflow 2  # Process & enrich
python -m paperless_ngx.presentation.cli.simplified_menu --workflow 3  # Quality scan

# Workflow 1: Email-Dokumente abrufen
# - Zeitraum wählen (YYYY-MM Format oder Quick-Options)
# - Email-Anhänge herunterladen und nach Monat organisieren
# - Automatische PDF-Erkennung

# Workflow 2: Dokumente verarbeiten & Metadaten anreichern  
# - OCR-Text aus Paperless extrahieren
# - LLM-Analyse für Metadaten (konfigurierbar: OpenAI/Ollama)
# - Intelligentes Tag-Matching (95% Threshold)
# - Verhindert falsche Vereinheitlichungen (Telekommunikation ≠ Telekom)

# Workflow 3: Quality Scan & Report
# - Zeitraum-basierte Qualitätsprüfung
# - Identifiziert fehlende Metadaten und Tag-Probleme
# - Generiert CSV-Report mit Handlungsempfehlungen
```

### Email Processing Commands
```bash
# Fetch email attachments from all accounts
python run.py --fetch-email-attachments

# Fetch from specific account
python run.py --fetch-email-attachments --email-account "Gmail Account 1"

# Dry run to preview actions
python run.py --fetch-email-attachments --dry-run

# Fetch emails from last 7 days
python run.py --fetch-email-attachments --since-days 7

# Test email connections
python run.py --test-email-connections

# Run continuous email fetcher
python run.py --run-email-fetcher --fetch-interval 300

# List email folders for debugging
python run.py --list-email-folders "Account Name"

# Check email processing statistics
python run.py --email-stats
```

### Testing Commands
```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src/paperless_ngx --cov-report=html

# Run specific test categories
pytest tests/unit/
pytest tests/integration/

# Run specific test files
pytest tests/unit/domain/test_validators.py -v
pytest tests/integration/test_email_connections.py -v

# Test without pytest
python test_connections.py
python test_july_2025_simple.py
```

### Development Commands
```bash
# Format code with black
black src/ tests/

# Run linter
flake8 src/ tests/

# Type checking
mypy src/

# Enable verbose logging
python run.py --verbose [command]

# Enable debug logging
python run.py --debug [command]

# Output results as JSON
python run.py --output json [command]
```

## Architecture

The codebase follows Clean Architecture with these layers:

### Project Structure
```
src/paperless_ngx/
├── domain/              # Business logic and entities
│   ├── exceptions/      # Custom domain exceptions
│   ├── models/          # Domain models (tag_models, processing_report)
│   ├── utilities/       # Domain utilities (filename_utils, date handling)
│   ├── validators/      # OCR and metadata validation
│   └── value_objects/   # date_range, tag_similarity
├── application/         # Use cases and orchestration
│   ├── services/        # EmailFetcherService, SmartTagMatcher, etc.
│   └── use_cases/       # AttachmentProcessor, MetadataExtraction
├── infrastructure/      # External integrations
│   ├── config/          # settings.py - Pydantic v2 configuration
│   ├── email/           # email_client.py, email_config.py
│   ├── llm/             # litellm_client.py - Multi-provider support
│   ├── logging/         # Structured logging setup
│   ├── paperless/       # api_client.py - Paperless NGX integration
│   └── platform/        # OS-specific adapters (Windows, POSIX)
└── presentation/        # User interfaces
    └── cli/             # main.py, simplified_menu.py
```

## Configuration

### LLM Provider Configuration

**⚠️ IMPORTANT: Use only real OpenAI model names! GPT-5 models do not exist.**

```bash
# Define provider order (comma-separated)
LLM_PROVIDER_ORDER=openai,ollama,anthropic

# OpenAI Configuration
OPENAI_ENABLED=true
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini        # ✅ RECOMMENDED (best value)
# OPENAI_MODEL=gpt-3.5-turbo    # ✅ Budget option
# OPENAI_MODEL=gpt-4-turbo      # ✅ Highest quality
# OPENAI_MODEL=gpt-4o           # ✅ Latest model

# ⚠️ NEVER USE THESE (non-existent models):
# OPENAI_MODEL=gpt-5-nano       # ❌ DOES NOT EXIST
# OPENAI_MODEL=gpt-5-mini       # ❌ DOES NOT EXIST
# OPENAI_MODEL=gpt-4o5-mini     # ❌ TYPO (should be gpt-4o-mini)

# Ollama Configuration (local LLM)
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

#### Model Configuration Tips
- **Model Switching**: Simply change `OPENAI_MODEL` in `.env` - no code changes needed
- **JSON Format**: Automatically enabled for compatible models (gpt-4*, gpt-3.5-turbo*)
- **Fallback Chain**: Configure via `LLM_PROVIDER_ORDER` for automatic failover
- **Cost Optimization**: Use `gpt-4o-mini` for best price/performance ratio
- See `docs/development/MODEL_SWITCHING_GUIDE.md` for detailed configuration

### Essential Settings
```bash
# Paperless NGX
PAPERLESS_BASE_URL=http://your-paperless:8000/api
PAPERLESS_API_TOKEN=your_token_here

# Email Accounts (multiple supported)
EMAIL_ACCOUNT_1_NAME="Gmail Business"
EMAIL_ACCOUNT_1_SERVER=imap.gmail.com
EMAIL_ACCOUNT_1_USERNAME=user@gmail.com
EMAIL_ACCOUNT_1_PASSWORD=app_specific_password

# Smart Tag Management
TAG_SIMILARITY_THRESHOLD=0.95  # Prevents false unifications
```

## Key Implementation Details

### Architecture Principles
- **Clean Architecture**: Domain layer has no external dependencies
- **Domain Models**: Pydantic v2 for type safety and validation
- **Platform Abstraction**: `infrastructure/platform/` handles OS-specific operations

### Critical Implementation Notes

**LLM Integration** (`infrastructure/llm/litellm_client.py`)
- Provider order via `LLM_PROVIDER_ORDER` env variable
- Automatic failover with exponential backoff
- Cost tracking per provider

**Tag Matching** (`application/services/smart_tag_matcher.py`)
- 95% similarity threshold (`TAG_SIMILARITY_THRESHOLD`)
- Uses rapidfuzz for fuzzy matching
- Prevents false unifications (e.g., "Telekommunikation" ≠ "Telekom")

**Email Processing** (`application/services/email_fetcher_service.py`)
- Multiple IMAP accounts via `EMAIL_ACCOUNT_*` env variables
- State tracking in `.email_state.json`
- Attachment filtering by extensions

**Document Metadata Rules**
- Correspondent = Sender (never Daniel Schindler/EBN)
- Tags = 3-7 German keywords
- Filename format: `YYYY-MM-DD_Sender_Type`

**API Client** (`infrastructure/paperless/api_client.py`)
- Async/await pattern for all API calls
- Automatic retry with exponential backoff
- `format=json` parameter for all GET requests

**Platform Support** (`infrastructure/platform/`)
- Windows: Long path support, UTF-8 mode
- Linux/macOS: Signal handling, permissions
- WSL2: Hybrid path handling