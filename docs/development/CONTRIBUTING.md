# Contributing Guide

Thank you for considering contributing to the Paperless NGX Integration System! This guide will help you get started with contributing to the project.

**Last Updated**: August 12, 2025

## Table of Contents
1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Making Changes](#making-changes)
5. [Testing](#testing)
6. [Submitting Changes](#submitting-changes)
7. [Code Standards](#code-standards)
8. [Documentation](#documentation)
9. [Review Process](#review-process)

## Code of Conduct

### Our Pledge
We are committed to providing a welcoming and inclusive environment for all contributors.

### Expected Behavior
- Be respectful and considerate
- Welcome newcomers and help them get started
- Focus on constructive criticism
- Accept feedback gracefully

### Unacceptable Behavior
- Harassment or discrimination
- Personal attacks
- Trolling or inflammatory comments
- Publishing private information

## Getting Started

### Prerequisites
- Python 3.9+ (3.11+ recommended)
- Git
- GitHub account
- Basic understanding of Clean Architecture

### First Time Contributors
Look for issues labeled:
- `good first issue` - Simple tasks for newcomers
- `help wanted` - Tasks where we need assistance
- `documentation` - Documentation improvements

### Understanding the Project
1. Read [PROJECT_SCOPE.md](../architecture/PROJECT_SCOPE.md)
2. Review [Architecture Documentation](../architecture/)
3. Explore the codebase structure
4. Run the test suite

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/paperless-ngx-integration.git
cd paperless-ngx-integration

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/paperless-ngx-integration.git
```

### 2. Create Development Environment

```bash
# Create virtual environment
python -m venv venv-dev

# Activate it
source venv-dev/bin/activate  # Linux/macOS
venv-dev\Scripts\activate      # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. Install Development Tools

```bash
# Code formatting
pip install black isort

# Linting
pip install flake8 pylint mypy

# Testing
pip install pytest pytest-cov pytest-asyncio

# Documentation
pip install sphinx sphinx-rtd-theme
```

### 4. Configure Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Set up hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

### 5. Set Up Test Environment

```bash
# Copy test configuration
cp .env.example .env.test

# Edit with test credentials
# Use test Paperless instance if available
```

## Making Changes

### 1. Create Feature Branch

```bash
# Update main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 2. Follow Architecture

Our project uses Clean Architecture:

```
src/paperless_ngx/
├── domain/         # No external dependencies!
├── application/    # Use cases, depends on domain
├── infrastructure/ # External services
└── presentation/   # User interfaces
```

**Rules:**
- Domain layer must not import from other layers
- Application layer can only import from domain
- Infrastructure can import from domain and application
- Presentation can import from all layers

### 3. Write Clean Code

```python
# Good example
from pathlib import Path
from typing import Optional, List
from src.paperless_ngx.domain.models import Document

class DocumentProcessor:
    """Process documents with metadata extraction.
    
    This class handles the document processing pipeline,
    including validation, metadata extraction, and storage.
    """
    
    def __init__(self, config: ProcessorConfig) -> None:
        """Initialize processor with configuration.
        
        Args:
            config: Processor configuration object
        """
        self.config = config
        self._validator = DocumentValidator()
    
    def process_document(
        self,
        file_path: Path,
        extract_metadata: bool = True
    ) -> Optional[Document]:
        """Process a single document.
        
        Args:
            file_path: Path to document file
            extract_metadata: Whether to extract metadata
            
        Returns:
            Processed Document object or None if failed
            
        Raises:
            ValidationError: If document validation fails
            ProcessingError: If processing fails
        """
        # Implementation here
        pass
```

### 4. Handle Cross-Platform Code

```python
# Always use pathlib for paths
from pathlib import Path

# Good - works everywhere
config_path = Path.home() / ".paperless_ngx" / "config.yaml"

# Bad - platform-specific
import os
config_path = os.path.join(os.environ['HOME'], '.paperless_ngx/config.yaml')

# Always specify encoding
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()
```

## Testing

### Test Requirements
- All new features must have tests
- Bug fixes should include regression tests
- Maintain or improve code coverage (target: 80%+)

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_document_processor.py

# Run with coverage
pytest --cov=src/paperless_ngx --cov-report=html

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run with verbose output
pytest -v

# Run specific test
pytest tests/unit/test_document_processor.py::TestDocumentProcessor::test_process_document
```

### Writing Tests

```python
# tests/unit/test_document_processor.py
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from src.paperless_ngx.application.services import DocumentProcessor

class TestDocumentProcessor:
    """Test DocumentProcessor service."""
    
    @pytest.fixture
    def processor(self):
        """Create processor instance for testing."""
        config = Mock()
        return DocumentProcessor(config)
    
    @pytest.fixture
    def sample_document(self, tmp_path):
        """Create sample document for testing."""
        doc_path = tmp_path / "test.pdf"
        doc_path.write_bytes(b"PDF content")
        return doc_path
    
    def test_process_document_success(self, processor, sample_document):
        """Test successful document processing."""
        # Arrange
        expected_metadata = {"title": "Test Document"}
        
        # Act
        result = processor.process_document(sample_document)
        
        # Assert
        assert result is not None
        assert result.file_path == sample_document
        
    def test_process_document_invalid_file(self, processor, tmp_path):
        """Test processing with invalid file."""
        # Arrange
        invalid_path = tmp_path / "nonexistent.pdf"
        
        # Act & Assert
        with pytest.raises(FileNotFoundError):
            processor.process_document(invalid_path)
    
    @patch('src.paperless_ngx.infrastructure.llm.client.LLMClient')
    def test_metadata_extraction(self, mock_llm, processor, sample_document):
        """Test metadata extraction using LLM."""
        # Arrange
        mock_llm.return_value.extract_metadata.return_value = {
            "sender": "Test Company",
            "type": "Invoice"
        }
        
        # Act
        result = processor.process_document(
            sample_document,
            extract_metadata=True
        )
        
        # Assert
        assert result.metadata["sender"] == "Test Company"
        mock_llm.return_value.extract_metadata.assert_called_once()
```

### Test Coverage Standards
- New code: Minimum 80% coverage
- Critical paths: 100% coverage required
- Domain layer: 95%+ coverage
- Infrastructure: Mock external services

## Submitting Changes

### 1. Commit Guidelines

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
# Format: <type>(<scope>): <subject>

# Features
git commit -m "feat(email): add support for OAuth2 authentication"

# Bug fixes
git commit -m "fix(processor): handle UTF-8 encoding on Windows"

# Documentation
git commit -m "docs(api): update API reference for new endpoints"

# Performance
git commit -m "perf(llm): optimize batch processing for large documents"

# Refactoring
git commit -m "refactor(domain): simplify document validation logic"

# Tests
git commit -m "test(integration): add tests for email fetcher service"

# Chores
git commit -m "chore(deps): update litellm to v1.2.0"
```

### 2. Push Changes

```bash
# Push to your fork
git push origin feature/your-feature-name
```

### 3. Create Pull Request

1. Go to GitHub and create PR from your fork
2. Use the PR template
3. Fill in all sections:
   - Description of changes
   - Related issues
   - Testing performed
   - Checklist items

### PR Template

```markdown
## Description
Brief description of changes

## Related Issues
Fixes #123
Relates to #456

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] No new warnings
```

## Code Standards

### Python Style Guide

We follow PEP 8 with these additions:

```python
# Line length
# Maximum 88 characters (Black default)

# Imports
# Standard library
import os
import sys
from pathlib import Path

# Third-party
import pytest
from pydantic import BaseModel

# Local
from src.paperless_ngx.domain import Document
from src.paperless_ngx.application import DocumentProcessor

# Type hints required
def process_file(file_path: Path) -> Optional[Document]:
    pass

# Docstrings (Google style)
def complex_function(
    param1: str,
    param2: int = 10
) -> Dict[str, Any]:
    """Brief description.
    
    Longer description if needed.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When param1 is empty
        TypeError: When param2 is not an integer
        
    Example:
        >>> result = complex_function("test", 20)
        >>> print(result["status"])
        'success'
    """
    pass
```

### Error Handling

```python
# Good - specific exception handling
try:
    document = process_document(file_path)
except FileNotFoundError as e:
    logger.error(f"File not found: {file_path}")
    raise DocumentNotFoundError(str(e)) from e
except PermissionError as e:
    logger.error(f"Permission denied: {file_path}")
    raise ProcessingError(f"Cannot access file: {e}") from e

# Bad - catch-all exception
try:
    document = process_document(file_path)
except Exception as e:
    print(f"Error: {e}")
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Use appropriate log levels
logger.debug("Detailed information for debugging")
logger.info("General information")
logger.warning("Warning - something unexpected")
logger.error("Error - operation failed")
logger.critical("Critical - system might crash")

# Include context
logger.info(
    "Processing document",
    extra={
        "document_id": doc_id,
        "user": user_id,
        "action": "process"
    }
)
```

## Documentation

### Code Documentation

Every public function/class needs:
1. Docstring with description
2. Type hints for all parameters
3. Examples for complex functions

### User Documentation

When adding features:
1. Update User Manual
2. Add to appropriate guide
3. Update API Reference if needed

### Commit Documentation

Good commit messages:
- First line: 50 chars max
- Blank line
- Body: 72 chars per line
- Explain what and why

## Review Process

### What We Look For

1. **Functionality**
   - Does it work as intended?
   - Are edge cases handled?
   - Is it tested?

2. **Code Quality**
   - Clean, readable code
   - Follows architecture
   - Proper error handling

3. **Performance**
   - No unnecessary operations
   - Efficient algorithms
   - Memory considerations

4. **Security**
   - No hardcoded secrets
   - Input validation
   - Safe file operations

5. **Documentation**
   - Code is documented
   - User docs updated
   - Examples provided

### Review Timeline

- Initial review: 2-3 days
- Follow-up reviews: 1-2 days
- Small fixes: Same day

### After Merge

Once your PR is merged:
1. Delete your feature branch
2. Update your main branch
3. Celebrate your contribution!

## Getting Help

### Resources
- [Documentation Index](../INDEX.md)
- [Architecture Guide](../architecture/PROJECT_SCOPE.md)
- [Testing Guide](TESTING.md)
- [API Reference](../API_REFERENCE.md)

### Communication
- GitHub Issues: Bug reports and features
- Discussions: Questions and ideas
- Email: [maintainer@example.com]

## Recognition

Contributors are recognized in:
- [CONTRIBUTORS.md](../../CONTRIBUTORS.md)
- Release notes
- Project documentation

Thank you for contributing!

---

**Navigation**: [Documentation Index](../INDEX.md) | [Testing Guide](TESTING.md) | [Code Standards](STANDARDS.md)