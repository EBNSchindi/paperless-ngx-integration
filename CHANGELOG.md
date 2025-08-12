# Changelog

All notable changes to the Paperless NGX Integration System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Cross-platform compatibility layer for Windows and Linux
- Platform-specific setup guides for Windows and Linux
- Comprehensive troubleshooting documentation
- Documentation index for easy navigation

### Changed
- Updated file operations to use UTF-8 encoding explicitly
- Migrated all path operations to use pathlib
- Enhanced error handling for platform-specific issues

### Fixed
- Windows path separator issues
- UTF-8 encoding problems on Windows
- Temporary file handling across platforms

## [1.0.0] - 2025-08-12

### Added
- **Core Features**
  - Complete Paperless NGX API integration
  - Multi-account email attachment fetching
  - AI-powered metadata extraction using LiteLLM
  - Smart tag management with 95% similarity threshold
  - Quality analysis and CSV report generation
  - Simplified 3-point workflow interface

- **Architecture**
  - Clean Architecture implementation
  - Domain-driven design patterns
  - Platform abstraction layer
  - Comprehensive error handling
  - State management for duplicate prevention

- **LLM Integration**
  - Configurable provider order (OpenAI, Ollama, Anthropic, Gemini)
  - Automatic fallback between providers
  - Cost tracking and rate limiting
  - Retry logic with exponential backoff

- **Documentation**
  - Complete user manual
  - API reference documentation
  - Installation guides
  - Architecture documentation
  - Testing documentation

- **Testing**
  - 100% test coverage for July 2025 workflows
  - Integration test suite (62 test cases)
  - Unit tests for core components
  - Cross-platform test compatibility

### Changed
- Improved email processing with batch support
- Enhanced error isolation in batch processing
- Updated tag matching algorithm to prevent false unifications
- Optimized memory usage with streaming architecture

### Fixed
- ID mapping issues with Paperless NGX API
- Langfuse optional import errors
- Email state tracking inconsistencies
- OCR validation edge cases

## [0.9.0] - 2025-07-01 (Beta)

### Added
- Initial implementation of email fetcher service
- Basic Paperless NGX API client
- LiteLLM integration with Ollama support
- Command-line interface with 8-option menu
- Configuration management with Pydantic

### Changed
- Refactored to Clean Architecture
- Improved error handling
- Added logging system

### Fixed
- Memory leaks in document processing
- Connection timeout issues
- Configuration validation errors

## [0.5.0] - 2025-06-01 (Alpha)

### Added
- Prototype document processing pipeline
- Basic metadata extraction
- Simple tag management
- Initial Paperless NGX integration

### Known Issues
- Limited error recovery
- No batch processing support
- Single email account only
- No quality analysis features

---

## Version History Summary

### Major Versions
- **1.0.0** (2025-08-12): First stable release with full feature set
- **0.9.0** (2025-07-01): Beta release with core functionality
- **0.5.0** (2025-06-01): Alpha prototype

### Compatibility Notes
- **Python**: Requires 3.9+, recommended 3.11+
- **Paperless NGX**: Compatible with v1.17.0+
- **Platforms**: Windows 10+, Linux (Ubuntu 20.04+), WSL2
- **Breaking Changes**: None since 1.0.0

### Migration Guide

#### From 0.9.x to 1.0.0
1. Update configuration file format (see .env.example)
2. Migrate from old email state files
3. Update LLM provider configuration
4. Review new simplified workflow options

#### From 0.5.x to 1.0.0
1. Complete reinstallation recommended
2. New configuration format required
3. Database schema changes
4. API endpoints updated

## Roadmap

### Version 1.1.0 (Q3 2025)
- [ ] macOS native support
- [ ] Web UI with FastAPI
- [ ] Real-time document processing
- [ ] Advanced analytics dashboard

### Version 1.2.0 (Q4 2025)
- [ ] Plugin system for custom processors
- [ ] Database persistence layer
- [ ] Message queue integration
- [ ] Multi-language support

### Version 2.0.0 (2026)
- [ ] Microservices architecture
- [ ] Kubernetes deployment
- [ ] Enterprise features
- [ ] SaaS offering

## Support

For questions about changes:
- Review [Documentation Index](docs/INDEX.md)
- Check [Migration Guides](#migration-guide)
- Search [GitHub Issues](https://github.com/yourusername/paperless-ngx-integration/issues)
- Ask in [Discussions](https://github.com/yourusername/paperless-ngx-integration/discussions)

---

[Unreleased]: https://github.com/yourusername/paperless-ngx-integration/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/yourusername/paperless-ngx-integration/compare/v0.9.0...v1.0.0
[0.9.0]: https://github.com/yourusername/paperless-ngx-integration/compare/v0.5.0...v0.9.0
[0.5.0]: https://github.com/yourusername/paperless-ngx-integration/releases/tag/v0.5.0