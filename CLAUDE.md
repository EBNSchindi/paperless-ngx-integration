# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Paperless NGX integration system that automatically processes email attachments, extracts document metadata using LLMs (LiteLLM with Ollama/OpenAI), and manages documents in a Paperless NGX instance. The system follows Clean Architecture principles with clear separation of concerns.

## Commands

### Installation and Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env  # Then add your credentials

# Run main application
python run.py
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
```

## Architecture

The codebase follows Clean Architecture with these layers:

### Project Structure
```
src/paperless_ngx/
├── domain/              # Business logic and entities
│   ├── exceptions/      # Custom domain exceptions
│   └── utilities/       # Domain utilities (filename generation, date handling)
├── application/         # Use cases and orchestration
│   ├── services/        # Application services (EmailFetcherService)
│   └── use_cases/       # Business use cases (AttachmentProcessor, MetadataExtraction)
├── infrastructure/      # External integrations
│   ├── config/          # Settings management with Pydantic
│   ├── email/           # IMAP email client and configuration
│   ├── llm/             # LiteLLM integration with fallback and retry
│   └── logging/         # Structured logging setup
└── presentation/        # User interfaces
    └── cli/             # Command-line interface
```

### Core Components

1. **LiteLLM Integration** (`infrastructure/llm/litellm_client.py`)
   - Unified interface for multiple LLM providers
   - Primary: Ollama (local, default model: llama3.1:8b)
   - Fallback: OpenAI GPT-3.5-turbo
   - Features: Automatic retry with exponential backoff, cost tracking, rate limiting
   - Router-based automatic failover between providers

2. **Email Processing** (`application/services/email_fetcher_service.py`)
   - IMAP integration with multiple account support
   - Attachment extraction with filtering
   - State tracking to avoid reprocessing
   - Continuous fetching mode with configurable intervals

3. **Configuration** (`infrastructure/config/settings.py`)
   - Type-safe settings using Pydantic v2
   - Environment-based configuration (.env files)
   - Secret management with SecretStr
   - Comprehensive validation at startup

4. **Document Processing**
   - **Business Context**: Daniel Schindler / EBN Veranstaltungen und Consulting GmbH is always the RECIPIENT
   - **Metadata Rules**:
     - Correspondent = Sender (never Daniel/EBN)
     - Document type = German classification
     - Tags = 3-7 German keywords
     - Description = Max 128 chars
     - Filename: `YYYY-MM-DD_Sender_Type`

## Configuration

Key environment variables (.env file):
```bash
# Paperless NGX
PAPERLESS_BASE_URL=https://paperless.local/api
PAPERLESS_API_TOKEN=your_token_here

# LLM Configuration
OLLAMA_ENABLED=true
OLLAMA_MODEL=llama3.1:8b
OLLAMA_BASE_URL=http://localhost:11434
OPENAI_API_KEY=sk-...  # Optional fallback

# Email Accounts (multiple supported)
EMAIL_ACCOUNT_1_NAME="Gmail Account 1"
EMAIL_ACCOUNT_1_SERVER=imap.gmail.com
EMAIL_ACCOUNT_1_USERNAME=user@gmail.com
EMAIL_ACCOUNT_1_PASSWORD=app_specific_password
```

## Development

### Testing
```bash
# Test email connections
python run.py --test-email-connections

# List email folders for debugging
python run.py --list-email-folders "Account Name"

# Check email processing statistics
python run.py --email-stats
```

### Debugging
```bash
# Enable verbose logging
python run.py --verbose [command]

# Enable debug logging
python run.py --debug [command]

# Output results as JSON
python run.py --output json [command]
```

## Important Implementation Details

- **Clean Architecture**: Strict dependency rules - domain layer has no external dependencies
- **LiteLLM Router**: Automatically handles failover from Ollama to OpenAI
- **Cost Tracking**: Monitors LLM usage costs with configurable alerts
- **Rate Limiting**: Built-in rate limiter prevents API overload
- **Error Handling**: Comprehensive exception hierarchy with domain-specific exceptions
- **State Management**: Email processing state tracked to prevent duplicates
- **Validation**: Pydantic models ensure type safety throughout the application