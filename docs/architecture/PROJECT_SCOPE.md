# PROJECT_SCOPE.md

## Project Overview
**Name**: Paperless NGX Integration System
**Type**: Document Management & Processing System
**Architecture**: Clean Architecture with Domain-Driven Design
**Status**: Active Development

## Core Functionality
Automated document processing system that:
- Fetches email attachments from multiple IMAP accounts
- Extracts metadata using LLM analysis (LiteLLM with Ollama/OpenAI)
- Manages documents in Paperless NGX instance
- Provides quality analysis and reporting

## Technical Stack

### Languages & Frameworks
- **Python 3.11+**: Core language
- **Pydantic v2**: Type-safe configuration and validation
- **LiteLLM**: Unified LLM interface with fallback support
- **RapidFuzz**: High-performance fuzzy string matching

### External Services
- **Paperless NGX**: Document management backend
- **Ollama**: Local LLM provider (primary)
- **OpenAI**: Cloud LLM provider (fallback)
- **IMAP Email Servers**: Gmail, IONOS, custom

### Architecture Layers
```
src/paperless_ngx/
├── domain/              # Business logic, no external dependencies
├── application/         # Use cases and service orchestration
├── infrastructure/      # External integrations
└── presentation/        # User interfaces (CLI)
```

## Key Components

### 1. Email Processing Pipeline
- **EmailFetcherService**: Multi-account IMAP integration
- **AttachmentProcessor**: Document extraction and organization
- State tracking to prevent duplicate processing
- Configurable batch processing

### 2. LLM Integration (LiteLLM)
- **Router-based architecture**: Automatic failover
- **Primary**: Ollama (local, llama3.1:8b)
- **Fallback**: OpenAI GPT-3.5-turbo
- Cost tracking and rate limiting
- Retry with exponential backoff

### 3. Document Management
- **PaperlessApiService**: High-level API operations
- Chunked retrieval for memory efficiency
- Date-based filtering (quarter/month)
- Batch operations with progress tracking

### 4. Tag Management System
- **TagModels**: Hierarchical tag structures
- **Similarity Analysis**: 85% threshold for matching
- **Clustering**: Automatic grouping of similar tags
- **Merge Recommendations**: Safe merge detection

### 5. Quality Assurance
- **OCRValidator**: OCR quality checks
- **MetadataValidator**: Metadata completeness
- **QualityAnalyzerService**: Comprehensive analysis
- **ReportGeneratorService**: PDF/HTML reports

## Business Rules

### Document Processing
- **Context**: Daniel Schindler / EBN GmbH is always RECIPIENT
- **Correspondent**: Always the sender (never Daniel/EBN)
- **Document Type**: German classification required
- **Tags**: 3-7 German keywords
- **Description**: Max 128 characters
- **Filename Format**: `YYYY-MM-DD_Sender_Type`

### Tag Management
- **High Similarity**: >= 85% match score
- **Medium Similarity**: 70-85% match score
- **Merge Strategy**: Most used, first created, or shortest name
- **Clustering**: Automatic with confidence scoring

## Configuration Management

### Environment Variables
- **Paperless NGX**: API URL, token
- **LLM Providers**: Ollama URL, OpenAI key
- **Email Accounts**: Multiple IMAP configurations
- **Processing Options**: Timeouts, retries, batch sizes

### Settings Architecture
- Type-safe with Pydantic v2
- SecretStr for sensitive data
- Validation at startup
- Environment-based (.env files)

## Processing Workflows

### 1. Email Attachment Fetch
```
IMAP Servers → EmailClient → AttachmentProcessor → Local Storage
```

### 2. Metadata Extraction
```
Document → LiteLLM → MetadataExtractor → Structured Data
```

### 3. Paperless Upload
```
Processed Document → API Client → Paperless NGX → Confirmation
```

### 4. Quality Analysis
```
Documents → Validators → Analyzer → Report Generator
```

## Error Handling

### Domain Exceptions
- `DocumentNotFoundError`
- `PaperlessAPIError`
- `ValidationError`
- `EmailConnectionError`

### Recovery Strategies
- Automatic retry with backoff
- Fallback to alternative providers
- State persistence for recovery
- Detailed error logging

## Performance Considerations

### Memory Management
- Chunked document retrieval
- Generator patterns for large datasets
- Streaming processing
- Cache management

### Scalability
- Batch processing support
- Parallel email account processing
- Rate limiting per provider
- Connection pooling

## Security Measures

### Credential Management
- SecretStr for all passwords/tokens
- Environment-based configuration
- No hardcoded credentials
- Sensitive data filtering in logs

### API Security
- Token-based authentication
- HTTPS enforcement
- Request validation
- Error message sanitization

## Monitoring & Logging

### Structured Logging
- JSON format support
- Log levels (DEBUG, INFO, WARNING, ERROR)
- Sensitive data masking
- Request/response tracking

### Metrics
- LLM usage and costs
- Processing statistics
- Error rates
- Performance metrics

## Testing Strategy

### Unit Tests
- Domain logic validation
- Service layer testing
- Utility function tests
- Mock external dependencies

### Integration Tests
- API client verification
- Email connection tests
- LLM provider health checks
- End-to-end workflows

## Development Guidelines

### Clean Architecture Principles
- Domain layer independence
- Dependency injection
- Interface segregation
- Single responsibility

### Code Organization
- Feature-based modules
- Clear separation of concerns
- Consistent naming conventions
- Type hints throughout

## Future Enhancements

### Planned Features
- Web UI with dashboard
- Real-time processing mode
- Advanced analytics
- Multi-language support

### Technical Improvements
- Database persistence layer
- Message queue integration
- Containerization (Docker)
- CI/CD pipeline

## Dependencies

### Core Libraries
```
litellm>=1.0.0
pydantic>=2.0.0
rapidfuzz>=3.0.0
rich>=13.0.0
httpx>=0.24.0
```

### Development Tools
```
pytest>=7.0.0
black>=23.0.0
mypy>=1.0.0
ruff>=0.1.0
```

## Maintenance Notes

### Regular Tasks
- Update LLM model versions
- Rotate API tokens
- Clean processed email state
- Archive old reports

### Monitoring Points
- API rate limits
- LLM costs
- Storage usage
- Error frequencies

## Contact & Support

### Development Team
- Architecture: Clean Architecture pattern
- LLM Integration: LiteLLM maintainers
- Document Management: Paperless NGX community

### Resources
- Project Repository: [GitHub URL]
- Documentation: /docs directory
- Issue Tracking: GitHub Issues
- Community: Paperless NGX forums