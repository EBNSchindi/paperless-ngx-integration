# Paperless NGX Integration System

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Clean Architecture](https://img.shields.io/badge/architecture-clean-green.svg)](docs/architecture/PROJECT_SCOPE.md)
[![Test Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)](tests/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](docs/setup/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A comprehensive document management automation system that integrates with Paperless NGX to provide AI-powered metadata extraction, intelligent tag management, and automated quality assurance.

## 🎯 Key Features

### 🤖 AI-Powered Processing
- **Multi-Provider LLM Support**: Configurable provider order (OpenAI, Ollama, Anthropic, Gemini)
- **Intelligent Metadata Extraction**: Automatic extraction of sender, document type, tags, and descriptions
- **Smart Tag Management**: 95% similarity threshold prevents false unifications
- **German Language Optimization**: Full support for German document processing

### 📧 Email Integration
- **Multi-Account Support**: Gmail, IONOS, and custom IMAP servers
- **Batch Processing**: Efficient handling of large document sets
- **Month-Based Organization**: Intuitive document organization by date
- **Duplicate Prevention**: State tracking to avoid reprocessing

### 📊 Quality Assurance
- **OCR Validation**: Detect and report OCR failures
- **Metadata Completeness Checks**: Ensure all required fields are populated
- **Quality Scoring**: Comprehensive document quality metrics
- **CSV Report Generation**: Actionable insights and recommendations

### 🏗️ Architecture
- **Clean Architecture**: Domain-driven design with clear separation of concerns
- **Robust Error Handling**: Individual error isolation in batch processing
- **Comprehensive Testing**: 100% test coverage for critical workflows
- **Security First**: SecretStr handling, credential masking in logs

## 🚀 Quick Start

### Prerequisites

- **Python**: 3.11+ recommended (3.9+ minimum)
- **OS**: Windows 10+, Ubuntu 20.04+, macOS 11+ (or equivalent)
- **Paperless NGX**: Instance v1.17.0+ with API access
- **LLM Provider** (choose one or more):
  - OpenAI API key (recommended for quality)
  - Ollama local installation (recommended for privacy)
  - Anthropic/Gemini API key (coming soon)
- **Memory**: 8GB RAM recommended (4GB minimum)
- **Storage**: 2-5GB free space

### Installation

#### Quick Install (All Platforms)

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/paperless-ngx-integration.git
cd paperless-ngx-integration

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# Linux/macOS:
source venv/bin/activate
# Windows Command Prompt:
venv\Scripts\activate
# Windows PowerShell:
venv\Scripts\Activate.ps1

# 4. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 5. Configure environment
cp .env.example .env  # Linux/macOS
copy .env.example .env  # Windows
# Edit .env with your credentials

# 6. (Optional) Install Ollama for local LLM
# Linux: curl -fsSL https://ollama.ai/install.sh | sh
# Windows: Download from https://ollama.ai/download/windows
ollama pull llama3.1:8b

# 7. Test connections
python test_connections.py

# 8. Run the application
python run.py
```

#### Platform-Specific Guides

For detailed platform-specific instructions:
- **[Windows Setup Guide](docs/setup/WINDOWS_SETUP.md)** - Includes PowerShell setup, long path support, encoding configuration
- **[Linux Setup Guide](docs/setup/LINUX_SETUP.md)** - Covers Ubuntu, Debian, Fedora, Arch, and WSL2
- **[macOS Setup Guide](docs/setup/MACOS_SETUP.md)** - Coming soon
- **[Troubleshooting Guide](docs/setup/TROUBLESHOOTING.md)** - Platform-specific issues and solutions

## 📖 Usage

### Simplified 3-Point Workflow (Recommended)

```bash
# Interactive simplified menu
python -m paperless_ngx.presentation.cli.simplified_menu

# Direct workflow execution
python -m paperless_ngx.presentation.cli.simplified_menu --workflow 1  # Email fetch
python -m paperless_ngx.presentation.cli.simplified_menu --workflow 2  # Process & enrich
python -m paperless_ngx.presentation.cli.simplified_menu --workflow 3  # Quality scan
```

**Workflow Overview:**
1. **📧 Email-Dokumente abrufen**: Fetch attachments from configured email accounts
2. **🔄 Dokumente verarbeiten**: Extract metadata and enrich with AI
3. **✅ Quality Scan**: Generate comprehensive quality reports

### Full Interactive Menu

```bash
python run.py
```

```
╔════════════════════════════════════════════════════╗
║     Paperless NGX - Erweiterte Verarbeitung       ║
╠════════════════════════════════════════════════════╣
║  1. Email-Anhänge abrufen                         ║
║  2. Kompletter Qualitäts-Scan                     ║
║  3. Quartalsweise Verarbeitung                    ║
║  4. Stapelverarbeitung von Dokumenten             ║
║  5. Einzeldokument verarbeiten                    ║
║  6. Tag-Analyse und Bereinigung                   ║
║  7. Berichte generieren                           ║
║  8. Verbindungen testen                           ║
║                                                    ║
║  0. Beenden                                        ║
╚════════════════════════════════════════════════════╝
```

### Command Line Options

```bash
# Fetch email attachments
python run.py --fetch-email-attachments --since-days 7

# Test all connections
python run.py --test-email-connections

# Run with verbose logging
python run.py --verbose

# Dry run (preview without changes)
python run.py --fetch-email-attachments --dry-run

# Output as JSON
python run.py --output json [command]
```

## Cross-Platform Compatibility

This project is designed to work seamlessly across different operating systems:

### Supported Platforms
- ✅ **Windows 10/11** - Full support with automatic path handling
- ✅ **Linux** - Ubuntu, Debian, Fedora, Arch Linux tested
- ✅ **WSL2** - Windows Subsystem for Linux fully supported
- 🔄 **macOS** - Community testing in progress

### Platform Features
- **Automatic Path Handling**: Uses pathlib for cross-platform paths
- **UTF-8 Encoding**: Consistent encoding across all platforms
- **Platform Detection**: Automatically adapts to your OS
- **Unified Configuration**: Same .env file works everywhere

## Project Structure

```
Paperless NGX - API-Datenverarbeitung/
├── src/paperless_ngx/          # Main application code
│   ├── application/            # Use cases and services
│   │   ├── services/          # Business services
│   │   └── use_cases/         # Application use cases
│   ├── domain/                # Domain models and logic
│   │   ├── exceptions/        # Custom exceptions
│   │   ├── models/           # Domain models
│   │   ├── utilities/        # Domain utilities
│   │   └── validators/       # Business validators
│   ├── infrastructure/       # External integrations
│   │   ├── config/          # Configuration
│   │   ├── email/           # Email client
│   │   ├── llm/             # LLM integration
│   │   ├── logging/         # Logging setup
│   │   └── paperless/       # Paperless API client
│   └── presentation/         # User interface
│       └── cli/             # Command-line interface
├── tests/                    # Test suite
│   ├── unit/                # Unit tests
│   └── integration/         # Integration tests
├── docs/                    # Documentation
│   ├── USER_MANUAL.md      # User guide
│   ├── INSTALLATION_GUIDE.md # Setup instructions
│   └── API_REFERENCE.md    # API documentation
├── requirements.txt         # Python dependencies
├── .env.example            # Environment template
└── run.py                  # Main entry point
```

## ⚙️ Configuration

### LLM Provider Configuration (NEW)

The system now supports configurable LLM provider order. Define your preferred providers in `.env`:

```env
# Define provider order (comma-separated)
LLM_PROVIDER_ORDER=openai,ollama,anthropic

# Provider configurations
OPENAI_ENABLED=true
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-3.5-turbo

OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

### Essential Settings

```env
# Paperless NGX
PAPERLESS_BASE_URL=http://your-paperless:8000/api
PAPERLESS_API_TOKEN=your-token-here

# Email Account Example
EMAIL_ACCOUNT_1_NAME="Gmail Business"
EMAIL_ACCOUNT_1_SERVER=imap.gmail.com
EMAIL_ACCOUNT_1_USERNAME=business@gmail.com
EMAIL_ACCOUNT_1_PASSWORD=app-specific-password

# Processing Settings
TAG_SIMILARITY_THRESHOLD=0.95
BATCH_CHUNK_SIZE=10
QUALITY_REPORT_FORMAT=csv
```

See [.env.example](.env.example) for complete configuration options.

## 📚 Documentation

### Quick Navigation
- **[📑 Documentation Index](docs/INDEX.md)** - Complete documentation directory
- **[🚀 Quick Start Guide](docs/setup/QUICKSTART.md)** - Get running in 5 minutes
- **[❓ FAQ](docs/user-guide/FAQ.md)** - Common questions answered

### User Documentation
- **[User Manual](docs/USER_MANUAL.md)** - Complete user guide with workflows
- **[Installation Guide](docs/INSTALLATION_GUIDE.md)** - Detailed setup instructions
- **[Platform Setup Guides](docs/setup/)** - OS-specific installation
- **[Configuration Guide](.env.example)** - All configuration options explained

### Technical Documentation
- **[Architecture Overview](docs/architecture/PROJECT_SCOPE.md)** - System design and components
- **[API Reference](docs/API_REFERENCE.md)** - Technical API documentation
- **[Platform Abstraction](docs/architecture/PLATFORM_ABSTRACTION.md)** - Cross-platform design
- **[CLAUDE.md](CLAUDE.md)** - AI assistant context and guidelines

### Development
- **[Contributing Guide](docs/development/CONTRIBUTING.md)** - How to contribute
- **[Agent Log](AGENT_LOG.md)** - Development history and decisions
- **[Test Documentation](tests/README.md)** - Testing strategy and coverage
- **[Changelog](CHANGELOG.md)** - Version history and updates

## Business Rules

The system enforces important business rules for German document processing:

1. **Recipient Rule**: Daniel Schindler / EBN GmbH is always the recipient, never the sender
2. **Language**: All metadata in German (tags, descriptions, document types)
3. **Filename Format**: `YYYY-MM-DD_Sender_DocumentType.pdf`
4. **Tag Management**: Singular forms preferred, 3-7 tags per document

## 🧪 Testing

### Test Coverage Status
- **July 2025 Workflows**: 100% (18/18 tests passing)
- **Integration Tests**: 62 test cases across 6 files
- **Unit Tests**: Comprehensive coverage of core components

### Running Tests

```bash
# Quick connection test (no pytest required)
python test_connections.py

# Test July 2025 workflows
python test_july_2025_simple.py

# Run all tests (requires pytest)
pytest

# Run with coverage report
pytest --cov=src/paperless_ngx --cov-report=html

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
```

### Key Test Validations
- ✅ LLM provider priority and fallback
- ✅ 95% tag matching threshold
- ✅ Telekommunikation ≠ Telekom prevention
- ✅ Batch processing error isolation
- ✅ Email account configurations
- ✅ Quality report generation

## Performance

- **Document Processing**: ~2-3 seconds per document with LLM
- **Quality Scan**: ~100 documents per 2-3 minutes
- **Tag Analysis**: ~1000 tags in under 10 seconds
- **Memory Efficient**: Streaming architecture for large datasets

## 🤝 Contributing

### Development Setup

```bash
# 1. Fork and clone
git clone https://github.com/yourusername/paperless-ngx-integration.git
cd paperless-ngx-integration

# 2. Create feature branch
git checkout -b feature/amazing-feature

# 3. Install dev dependencies
pip install -r requirements-dev.txt

# 4. Make changes and test
pytest
black src/ tests/
mypy src/

# 5. Commit and push
git commit -m 'Add amazing feature'
git push origin feature/amazing-feature
```

### Code Standards
- **Architecture**: Follow Clean Architecture principles
- **Style**: PEP 8 with Black formatting
- **Types**: Full type hints required
- **Docs**: Google-style docstrings
- **Tests**: Minimum 80% coverage for new code
- **Security**: No credentials in code

## Troubleshooting

### Common Issues

| Issue | Platform | Solution |
|-------|----------|----------|
| "Connection refused to Paperless" | All | Check Paperless URL and network |
| "Ollama not responding" | All | Run `ollama serve` (Linux) or check service (Windows) |
| "Gmail authentication failed" | All | Use app-specific password, not regular password |
| "OCR text empty" | All | Reprocess document in Paperless |
| "Path too long" error | Windows | Enable long path support (see [Windows Setup](docs/setup/WINDOWS_SETUP.md)) |
| "Permission denied" | Linux | Check file ownership and permissions |
| "UnicodeDecodeError" | Windows | Set `PYTHONUTF8=1` environment variable |
| "Module not found" | All | Ensure virtual environment is activated |

For detailed troubleshooting, see the [Platform Troubleshooting Guide](docs/setup/TROUBLESHOOTING.md) or [User Manual](docs/USER_MANUAL.md#fehlerbehebung).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Paperless NGX**: Document management system
- **Ollama**: Local LLM runtime
- **LiteLLM**: Unified LLM interface
- **Rich**: Beautiful terminal formatting
- **RapidFuzz**: Fast string matching

## Support

For issues, questions, or suggestions:
1. Check the [documentation](docs/)
2. Review [existing issues](https://github.com/yourusername/paperless-ngx-api-processing/issues)
3. Create a new issue with detailed information

## 🗺️ Roadmap

### Version 2.0 (Q2 2025)
- [ ] Web UI with FastAPI/Streamlit
- [ ] Real-time document processing
- [ ] Advanced analytics dashboard
- [ ] Plugin system for custom processors

### Version 1.5 (Q1 2025)
- [x] Configurable LLM provider order
- [x] Simplified 3-point workflow
- [ ] Scheduled processing (cron)
- [ ] Database persistence layer

### Version 1.0 (Current)
- ✅ Full CLI with 8-option menu
- ✅ Multi-account email support
- ✅ AI-powered metadata extraction
- ✅ Smart tag management (95% threshold)
- ✅ Quality analysis and reporting
- ✅ 100% test coverage for workflows

## 🛡️ Security

### Reporting Security Issues
Please report security vulnerabilities to [security@example.com](mailto:security@example.com)

### Security Features
- SecretStr for all sensitive data
- Credential masking in logs
- Environment-based configuration
- No hardcoded secrets

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **[Paperless NGX](https://github.com/paperless-ngx/paperless-ngx)**: Document management system
- **[LiteLLM](https://github.com/BerriAI/litellm)**: Unified LLM interface
- **[Ollama](https://ollama.ai)**: Local LLM runtime
- **[Rich](https://github.com/Textualize/rich)**: Beautiful terminal formatting
- **[RapidFuzz](https://github.com/maxbachmann/RapidFuzz)**: Fast string matching

---

<div align="center">

**Project Status**: 🟢 Active Development

**Version**: 1.0.0 | **Updated**: August 2025

[Report Bug](https://github.com/yourusername/paperless-ngx-integration/issues) • 
[Request Feature](https://github.com/yourusername/paperless-ngx-integration/issues) • 
[Documentation](docs/)

</div>