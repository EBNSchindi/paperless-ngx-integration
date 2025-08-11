# Paperless NGX - API Data Processing System

A powerful integration system for Paperless NGX that automates document processing using AI-powered metadata extraction, intelligent tag management, and comprehensive quality analysis.

## Features

### Core Capabilities

- **AI-Powered Metadata Extraction**: Automatic extraction of sender, document type, tags, and descriptions using Ollama (local) or OpenAI (fallback)
- **Intelligent Tag Management**: Fuzzy matching and automatic unification of similar tags
- **Comprehensive Quality Analysis**: Detect OCR failures, missing metadata, and validation issues
- **Email Integration**: Automatic document retrieval from Gmail and IONOS accounts
- **Batch Processing**: Efficient processing of large document sets with progress tracking
- **German Language Support**: Full support for German document processing and metadata

### Key Components

- **8-Option Interactive Menu**: User-friendly CLI for all operations
- **Clean Architecture**: Modular, maintainable codebase following DDD principles
- **Robust Error Handling**: Graceful fallbacks and detailed error reporting
- **91% Test Coverage**: Comprehensive test suite ensuring reliability

## Quick Start

### Prerequisites

- Python 3.9+
- Paperless NGX instance (v1.17.0+)
- Ollama (for local LLM) or OpenAI API key
- 8GB RAM recommended

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/paperless-ngx-api-processing.git
cd "Paperless NGX - API-Datenverarbeitung"
```

2. **Set up Python environment**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/macOS
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your settings
```

5. **Install Ollama and model**
```bash
# Install Ollama from https://ollama.ai
ollama pull llama3.1:8b
```

6. **Run the application**
```bash
python run.py
```

## Usage

### Interactive Menu

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

### Command Line Interface

```bash
# Fetch email attachments
python run.py --fetch-email-attachments --since-days 7

# Test connections
python run.py --test-email-connections

# Run with verbose logging
python run.py --verbose

# Dry run (preview without changes)
python run.py --fetch-email-attachments --dry-run
```

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

## Configuration

### Essential Settings (.env)

```env
# Paperless NGX
PAPERLESS_API_URL=http://192.168.178.76:8010/api
PAPERLESS_API_TOKEN=your-token-here

# Ollama (Local LLM)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# OpenAI (Fallback)
OPENAI_API_KEY=sk-your-key-here

# Email Accounts
GMAIL1_EMAIL=your.email@gmail.com
GMAIL1_PASSWORD=app-specific-password
```

## Documentation

- **[User Manual](docs/USER_MANUAL.md)**: Complete user guide with workflows and troubleshooting
- **[Installation Guide](docs/INSTALLATION_GUIDE.md)**: Detailed setup instructions
- **[API Reference](docs/API_REFERENCE.md)**: Technical API documentation
- **[CLAUDE.md](CLAUDE.md)**: Project context for AI assistants

## Business Rules

The system enforces important business rules for German document processing:

1. **Recipient Rule**: Daniel Schindler / EBN GmbH is always the recipient, never the sender
2. **Language**: All metadata in German (tags, descriptions, document types)
3. **Filename Format**: `YYYY-MM-DD_Sender_DocumentType.pdf`
4. **Tag Management**: Singular forms preferred, 3-7 tags per document

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=paperless_ngx --cov-report=html

# Run specific test category
pytest tests/unit/
pytest tests/integration/

# Test connections only
python test_connections.py
```

Current test coverage: **91%**

## Performance

- **Document Processing**: ~2-3 seconds per document with LLM
- **Quality Scan**: ~100 documents per 2-3 minutes
- **Tag Analysis**: ~1000 tags in under 10 seconds
- **Memory Efficient**: Streaming architecture for large datasets

## Contributing

### Development Setup

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Install dev dependencies (`pip install -r requirements-dev.txt`)
4. Make your changes
5. Run tests (`pytest`)
6. Format code (`black src/ tests/`)
7. Commit changes (`git commit -m 'Add amazing feature'`)
8. Push to branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

### Code Style

- Follow PEP 8
- Use type hints
- Add docstrings (Google style)
- Write tests for new features
- Update documentation

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "Connection refused to Paperless" | Check Paperless URL and network |
| "Ollama not responding" | Run `ollama serve` in terminal |
| "Gmail authentication failed" | Use app-specific password, not regular password |
| "OCR text empty" | Reprocess document in Paperless |

For detailed troubleshooting, see the [User Manual](docs/USER_MANUAL.md#fehlerbehebung).

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

## Roadmap

### Planned Features

- [ ] Web UI using FastAPI/Streamlit
- [ ] Scheduled processing with cron
- [ ] Multi-language support (English, French)
- [ ] Advanced OCR correction algorithms
- [ ] Document similarity detection
- [ ] Automated backup system
- [ ] Plugin architecture for custom processors

### Version History

- **v1.0.0** (January 2025): Initial release with 8-option menu system
- **v0.9.0**: Beta with core functionality
- **v0.5.0**: Alpha with basic API integration

---

**Project Status**: Active Development

**Last Updated**: January 2025

**Maintainer**: Your Organization

**Contact**: paperless-support@your-domain.com