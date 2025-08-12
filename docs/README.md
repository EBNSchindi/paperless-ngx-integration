# Paperless NGX Integration - Documentation

Welcome to the comprehensive documentation for the Paperless NGX Integration System.

## 📚 Documentation Index

### Getting Started
- **[Installation Guide](INSTALLATION_GUIDE.md)** - Step-by-step setup instructions for all platforms
- **[Configuration Guide](../.env.example)** - Complete environment variable reference
- **[Quick Start Tutorial](../README.md#-quick-start)** - Get up and running in 5 minutes

### User Documentation
- **[User Manual](USER_MANUAL.md)** - Complete guide to all features and workflows
- **[Simplified Workflow Guide](USER_MANUAL.md#simplified-3-point-workflow)** - Quick 3-step process
- **[Troubleshooting Guide](USER_MANUAL.md#fehlerbehebung)** - Common issues and solutions

### Technical Documentation
- **[Architecture Overview](architecture/PROJECT_SCOPE.md)** - System design and components
- **[API Reference](API_REFERENCE.md)** - Complete API documentation
- **[Testing Guide](../tests/README.md)** - Testing strategy and running tests

### Development Documentation
- **[Contributing Guide](../README.md#-contributing)** - How to contribute to the project
- **[Development Setup](INSTALLATION_GUIDE.md#development-setup)** - Setting up a dev environment
- **[Agent Log](../AGENT_LOG.md)** - Development history and decisions

## 🎯 Quick Navigation

### By User Role

#### 👤 End Users
1. Start with the [Installation Guide](INSTALLATION_GUIDE.md)
2. Configure using [.env.example](../.env.example)
3. Follow the [User Manual](USER_MANUAL.md)
4. Check [Troubleshooting](USER_MANUAL.md#fehlerbehebung) if needed

#### 👨‍💻 Developers
1. Review [Architecture Overview](architecture/PROJECT_SCOPE.md)
2. Set up [Development Environment](INSTALLATION_GUIDE.md#development-setup)
3. Read [API Reference](API_REFERENCE.md)
4. Check [Testing Guide](../tests/README.md)

#### 🤖 AI Assistants
1. Read [CLAUDE.md](../CLAUDE.md) for context
2. Review [Architecture](architecture/PROJECT_SCOPE.md)
3. Check [Agent Log](../AGENT_LOG.md) for history

### By Task

#### 📦 Initial Setup
- [System Requirements](INSTALLATION_GUIDE.md#system-requirements)
- [Installation Steps](INSTALLATION_GUIDE.md#installation-steps)
- [Configuration](../.env.example)
- [Connection Testing](USER_MANUAL.md#8-verbindungen-testen)

#### 📧 Email Processing
- [Email Account Setup](../.env.example#L43-L72)
- [Fetching Attachments](USER_MANUAL.md#1-email-anhänge-abrufen)
- [Batch Processing](USER_MANUAL.md#4-stapelverarbeitung-von-dokumenten)

#### 🤖 AI Configuration
- [LLM Provider Setup](../.env.example#L5-L42)
- [Provider Order Configuration](../.env.example#L7)
- [Metadata Extraction](USER_MANUAL.md#workflow-2-dokumente-verarbeiten--metadaten-anreichern)

#### 📊 Quality Management
- [Quality Scan](USER_MANUAL.md#2-kompletter-qualitäts-scan)
- [Tag Analysis](USER_MANUAL.md#6-tag-analyse-und-bereinigung)
- [Report Generation](USER_MANUAL.md#7-berichte-generieren)

## 🔧 Key Features Documentation

### Simplified 3-Point Workflow
The system offers a streamlined workflow for document processing:

1. **Email Fetch** - Retrieve documents from configured email accounts
2. **Process & Enrich** - Extract metadata using AI
3. **Quality Scan** - Generate comprehensive reports

[Learn more →](USER_MANUAL.md#simplified-3-point-workflow)

### Smart Tag Management
Intelligent tag matching with 95% similarity threshold prevents false unifications:
- Prevents "Telekommunikation" ≠ "Telekom" errors
- Supports German language nuances
- Hierarchical tag structures

[Learn more →](API_REFERENCE.md#smart-tag-matcher)

### Configurable LLM Providers
Define your preferred AI provider order:
```env
LLM_PROVIDER_ORDER=openai,ollama,anthropic
```

[Learn more →](../.env.example#L7)

## 📊 System Overview

### Architecture
```
Clean Architecture with Domain-Driven Design
├── Domain Layer (Business Logic)
├── Application Layer (Use Cases)
├── Infrastructure Layer (External Services)
└── Presentation Layer (User Interface)
```

[Full Architecture →](architecture/PROJECT_SCOPE.md)

### Technology Stack
- **Language**: Python 3.11+
- **Framework**: Clean Architecture
- **AI**: LiteLLM (OpenAI, Ollama, Anthropic)
- **Document Management**: Paperless NGX
- **Testing**: pytest with 100% workflow coverage

## 🚀 Version Information

### Current Version: 1.0.0
- ✅ Full CLI with 8-option menu
- ✅ Simplified 3-point workflow
- ✅ Configurable LLM providers
- ✅ Smart tag management (95% threshold)
- ✅ 100% test coverage for workflows

### Coming in v1.5
- Scheduled processing (cron)
- Database persistence
- Enhanced reporting

[See Roadmap →](../README.md#️-roadmap)

## 📞 Support

### Getting Help
1. Check the [User Manual](USER_MANUAL.md)
2. Review [Troubleshooting Guide](USER_MANUAL.md#fehlerbehebung)
3. Search [existing issues](https://github.com/yourusername/paperless-ngx-integration/issues)
4. Create a [new issue](https://github.com/yourusername/paperless-ngx-integration/issues/new)

### Contributing
We welcome contributions! See our [Contributing Guide](../README.md#-contributing) to get started.

## 📄 License

This project is licensed under the MIT License. See [LICENSE](../LICENSE) for details.

---

<div align="center">

**[← Back to Main README](../README.md)** | **[User Manual →](USER_MANUAL.md)** | **[API Reference →](API_REFERENCE.md)**

</div>