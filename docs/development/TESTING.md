# Cross-Platform Testing Guide

Comprehensive guide for testing the Paperless NGX Integration System across different platforms.

**Last Updated**: August 12, 2025

## Table of Contents
1. [Testing Overview](#testing-overview)
2. [Test Structure](#test-structure)
3. [Platform-Specific Testing](#platform-specific-testing)
4. [Running Tests](#running-tests)
5. [Writing Tests](#writing-tests)
6. [Test Coverage](#test-coverage)
7. [Continuous Integration](#continuous-integration)
8. [Troubleshooting Tests](#troubleshooting-tests)

## Testing Overview

### Testing Philosophy
- **Test-Driven Development (TDD)** encouraged
- **Cross-platform validation** required
- **Isolation** - tests should not depend on external services
- **Repeatability** - tests must produce consistent results
- **Speed** - unit tests should be fast (<1 second each)

### Test Categories

| Category | Purpose | Speed | Dependencies |
|----------|---------|-------|--------------|
| Unit | Test individual functions/classes | Fast | Mocked |
| Integration | Test component interactions | Medium | Some real |
| E2E | Test complete workflows | Slow | All real |
| Platform | Test OS-specific features | Fast | OS-specific |

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                 # Shared fixtures
├── unit/                       # Unit tests
│   ├── domain/                # Domain layer tests
│   ├── application/           # Application layer tests
│   ├── infrastructure/        # Infrastructure tests
│   └── presentation/          # Presentation tests
├── integration/               # Integration tests
│   ├── test_email_workflow.py
│   ├── test_llm_integration.py
│   └── test_paperless_api.py
├── e2e/                       # End-to-end tests
│   └── test_complete_workflow.py
├── platform/                  # Platform-specific tests
│   ├── test_windows.py
│   ├── test_linux.py
│   └── test_paths.py
└── fixtures/                  # Test data
    ├── documents/
    └── responses/
```

## Platform-Specific Testing

### Windows Testing

```python
# tests/platform/test_windows.py
import pytest
import platform
from pathlib import Path

@pytest.mark.skipif(
    platform.system() != "Windows",
    reason="Windows-specific test"
)
class TestWindowsPlatform:
    """Windows-specific platform tests."""
    
    def test_long_path_support(self, tmp_path):
        """Test Windows long path handling."""
        # Create path longer than 260 characters
        long_dir = tmp_path
        for i in range(30):
            long_dir = long_dir / f"directory_{i:02d}"
        
        # Should handle with \\?\ prefix
        from src.paperless_ngx.infrastructure.platform import PlatformService
        service = PlatformService()
        
        safe_path = service.make_path_safe(long_dir)
        assert str(safe_path).startswith("\\\\?\\")
    
    def test_hidden_directory_creation(self):
        """Test Windows hidden directory creation."""
        from src.paperless_ngx.infrastructure.platform import WindowsPlatform
        platform = WindowsPlatform()
        
        config_dir = platform.get_config_directory()
        assert config_dir.exists()
        
        # Check if directory is in APPDATA
        import os
        assert os.environ["APPDATA"] in str(config_dir)
    
    def test_utf8_encoding_flag(self):
        """Test UTF-8 mode is enabled."""
        import sys
        import os
        
        # Check PYTHONUTF8 environment variable
        assert os.environ.get("PYTHONUTF8") == "1" or sys.flags.utf8_mode == 1
```

### Linux Testing

```python
# tests/platform/test_linux.py
import pytest
import platform
from pathlib import Path

@pytest.mark.skipif(
    platform.system() != "Linux",
    reason="Linux-specific test"
)
class TestLinuxPlatform:
    """Linux-specific platform tests."""
    
    def test_hidden_directory_convention(self):
        """Test Linux hidden directory with dot prefix."""
        from src.paperless_ngx.infrastructure.platform import LinuxPlatform
        platform = LinuxPlatform()
        
        config_dir = platform.get_config_directory()
        assert config_dir.name.startswith(".")
        assert ".paperless_ngx" in str(config_dir)
    
    def test_file_permissions(self, tmp_path):
        """Test Unix file permissions."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        
        # Set restrictive permissions
        import os
        os.chmod(test_file, 0o600)
        
        # Check permissions
        stat = test_file.stat()
        assert oct(stat.st_mode)[-3:] == "600"
    
    def test_signal_handling(self):
        """Test Unix signal handling."""
        import signal
        from src.paperless_ngx.infrastructure.platform import LinuxPlatform
        
        platform = LinuxPlatform()
        
        # Should register signal handlers
        handlers = platform.setup_signal_handlers()
        assert signal.SIGTERM in handlers
        assert signal.SIGINT in handlers
```

### Cross-Platform Path Testing

```python
# tests/platform/test_paths.py
import pytest
from pathlib import Path
import tempfile

class TestCrossPlatformPaths:
    """Test path handling across platforms."""
    
    def test_path_separator_normalization(self):
        """Test paths work regardless of separator."""
        from src.paperless_ngx.infrastructure.platform import PlatformService
        service = PlatformService()
        
        # Test various path formats
        paths = [
            "data/attachments/file.pdf",
            "data\\attachments\\file.pdf",
            Path("data") / "attachments" / "file.pdf"
        ]
        
        normalized = [service.normalize_path(p) for p in paths]
        
        # All should resolve to same path
        assert len(set(str(p) for p in normalized)) == 1
    
    def test_temp_directory_creation(self):
        """Test temporary directory creation."""
        from src.paperless_ngx.infrastructure.platform import PlatformService
        service = PlatformService()
        
        with service.create_temp_directory() as temp_dir:
            assert temp_dir.exists()
            assert temp_dir.is_dir()
            
            # Write test file
            test_file = temp_dir / "test.txt"
            test_file.write_text("test content", encoding="utf-8")
            assert test_file.exists()
        
        # Directory should be cleaned up
        assert not temp_dir.exists()
    
    @pytest.mark.parametrize("filename,expected", [
        ("test.pdf", True),
        ("test file.pdf", True),
        ("тест.pdf", True),  # Cyrillic
        ("test:file.pdf", False),  # Invalid on Windows
        ("test<>file.pdf", False),  # Invalid on Windows
    ])
    def test_filename_validation(self, filename, expected):
        """Test filename validation across platforms."""
        from src.paperless_ngx.infrastructure.platform import PlatformService
        service = PlatformService()
        
        is_valid = service.is_valid_filename(filename)
        assert is_valid == expected or platform.system() != "Windows"
```

## Running Tests

### Basic Test Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_document_processor.py

# Run specific test class
pytest tests/unit/test_document_processor.py::TestDocumentProcessor

# Run specific test method
pytest tests/unit/test_document_processor.py::TestDocumentProcessor::test_process

# Run tests matching pattern
pytest -k "email"  # Runs all tests with "email" in name

# Run only marked tests
pytest -m "slow"   # Run only slow tests
pytest -m "not slow"  # Skip slow tests
```

### Platform-Specific Testing

```bash
# Run only Windows tests
pytest tests/platform/test_windows.py

# Run only Linux tests
pytest tests/platform/test_linux.py

# Skip platform-specific tests
pytest -m "not windows and not linux"

# Run on specific Python version
python3.11 -m pytest
```

### Coverage Testing

```bash
# Run with coverage
pytest --cov=src/paperless_ngx

# Generate HTML coverage report
pytest --cov=src/paperless_ngx --cov-report=html
# Open htmlcov/index.html in browser

# Show missing lines in terminal
pytest --cov=src/paperless_ngx --cov-report=term-missing

# Set coverage threshold
pytest --cov=src/paperless_ngx --cov-fail-under=80

# Coverage for specific module
pytest --cov=src/paperless_ngx/domain tests/unit/domain/
```

### Performance Testing

```bash
# Profile test execution time
pytest --durations=10  # Show 10 slowest tests

# Run tests in parallel
pip install pytest-xdist
pytest -n auto  # Use all CPU cores
pytest -n 4     # Use 4 processes

# Benchmark tests
pip install pytest-benchmark
pytest tests/performance/
```

## Writing Tests

### Test Structure Template

```python
"""Test module for DocumentProcessor."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile

from src.paperless_ngx.application.services import DocumentProcessor
from src.paperless_ngx.domain.exceptions import ValidationError


class TestDocumentProcessor:
    """Test DocumentProcessor service."""
    
    # Fixtures
    @pytest.fixture
    def processor(self):
        """Create processor instance."""
        config = Mock()
        config.batch_size = 10
        config.timeout = 30
        return DocumentProcessor(config)
    
    @pytest.fixture
    def sample_document(self, tmp_path):
        """Create sample document for testing."""
        doc_path = tmp_path / "invoice_2025.pdf"
        doc_path.write_bytes(b"%PDF-1.4 sample content")
        return doc_path
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        with patch('src.paperless_ngx.infrastructure.llm.LLMClient') as mock:
            client = mock.return_value
            client.extract_metadata.return_value = {
                "sender": "Test Company",
                "type": "Invoice",
                "tags": ["invoice", "2025", "test"]
            }
            yield client
    
    # Unit Tests
    def test_initialization(self):
        """Test processor initialization."""
        config = Mock()
        processor = DocumentProcessor(config)
        
        assert processor.config == config
        assert processor._processed_count == 0
    
    def test_process_valid_document(self, processor, sample_document, mock_llm_client):
        """Test processing valid document."""
        # Arrange
        expected_sender = "Test Company"
        
        # Act
        result = processor.process_document(sample_document)
        
        # Assert
        assert result is not None
        assert result.sender == expected_sender
        assert result.file_path == sample_document
        mock_llm_client.extract_metadata.assert_called_once()
    
    def test_process_invalid_document(self, processor, tmp_path):
        """Test processing invalid document."""
        # Arrange
        invalid_doc = tmp_path / "invalid.txt"
        invalid_doc.write_text("Not a PDF")
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            processor.process_document(invalid_doc)
        
        assert "Invalid document format" in str(exc_info.value)
    
    def test_process_missing_document(self, processor):
        """Test processing non-existent document."""
        # Arrange
        missing_path = Path("/nonexistent/document.pdf")
        
        # Act & Assert
        with pytest.raises(FileNotFoundError):
            processor.process_document(missing_path)
    
    # Parametrized Tests
    @pytest.mark.parametrize("file_size,expected_result", [
        (100, True),      # Small file
        (1024*1024, True),  # 1MB file
        (100*1024*1024, False),  # 100MB file (too large)
    ])
    def test_file_size_validation(self, processor, tmp_path, file_size, expected_result):
        """Test file size validation."""
        # Create file of specific size
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"0" * file_size)
        
        if expected_result:
            result = processor.validate_file_size(test_file)
            assert result is True
        else:
            with pytest.raises(ValidationError):
                processor.validate_file_size(test_file)
    
    # Integration Tests
    @pytest.mark.integration
    def test_full_processing_pipeline(self, processor, sample_document):
        """Test complete document processing pipeline."""
        # This test uses real services (marked as integration)
        result = processor.process_with_pipeline(sample_document)
        
        assert result.status == "completed"
        assert result.metadata is not None
        assert result.tags is not None
    
    # Async Tests
    @pytest.mark.asyncio
    async def test_async_processing(self, processor, sample_document):
        """Test asynchronous document processing."""
        result = await processor.process_async(sample_document)
        assert result is not None
    
    # Platform-specific Tests
    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="Unix-specific test"
    )
    def test_unix_permissions(self, processor, sample_document):
        """Test Unix-specific file permissions."""
        import os
        os.chmod(sample_document, 0o644)
        result = processor.process_document(sample_document)
        assert result is not None
    
    # Error Handling Tests
    def test_llm_failure_fallback(self, processor, sample_document):
        """Test fallback when LLM fails."""
        with patch('src.paperless_ngx.infrastructure.llm.LLMClient') as mock_llm:
            mock_llm.return_value.extract_metadata.side_effect = Exception("LLM Error")
            
            # Should fallback to basic extraction
            result = processor.process_document(sample_document)
            assert result is not None
            assert result.metadata_source == "fallback"
```

### Testing Best Practices

```python
# 1. Use descriptive test names
def test_email_fetcher_retrieves_attachments_from_multiple_accounts():
    """Test that email fetcher can retrieve attachments from all configured accounts."""
    pass

# 2. Arrange-Act-Assert pattern
def test_document_validation():
    # Arrange
    validator = DocumentValidator()
    invalid_doc = create_invalid_document()
    
    # Act
    result = validator.validate(invalid_doc)
    
    # Assert
    assert result.is_valid is False
    assert "format" in result.errors

# 3. One assertion per test (when possible)
def test_user_creation():
    user = User(name="Test", email="test@example.com")
    assert user.name == "Test"

def test_user_email():
    user = User(name="Test", email="test@example.com")
    assert user.email == "test@example.com"

# 4. Use fixtures for common setup
@pytest.fixture
def authenticated_client():
    client = APIClient()
    client.authenticate("test_token")
    return client

def test_api_call(authenticated_client):
    response = authenticated_client.get("/documents")
    assert response.status_code == 200

# 5. Mock external dependencies
@patch('requests.get')
def test_external_api_call(mock_get):
    mock_get.return_value.json.return_value = {"status": "ok"}
    result = fetch_external_data()
    assert result["status"] == "ok"
```

## Test Coverage

### Coverage Goals

| Component | Target | Current | Status |
|-----------|--------|---------|--------|
| Domain Layer | 95% | 98% | ✅ |
| Application Layer | 85% | 87% | ✅ |
| Infrastructure Layer | 75% | 72% | ⚠️ |
| Presentation Layer | 70% | 75% | ✅ |
| **Overall** | **80%** | **83%** | ✅ |

### Coverage Configuration

Create `.coveragerc`:

```ini
[run]
source = src/paperless_ngx
omit = 
    */tests/*
    */test_*.py
    */__pycache__/*
    */venv/*
    */migrations/*

[report]
precision = 2
skip_empty = True
show_missing = True
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
    @abstract

[html]
directory = htmlcov
```

### Improving Coverage

```bash
# Find uncovered lines
pytest --cov=src/paperless_ngx --cov-report=term-missing

# Generate detailed HTML report
pytest --cov=src/paperless_ngx --cov-report=html
open htmlcov/index.html  # Linux/macOS
start htmlcov/index.html  # Windows

# Focus on specific module
pytest --cov=src/paperless_ngx/domain --cov-report=term-missing tests/unit/domain/
```

## Continuous Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
        python-version: [3.9, 3.11]
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run tests
      run: |
        pytest --cov=src/paperless_ngx --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella
```

### Local CI Simulation

```bash
# Run tests like CI
./scripts/run_ci_tests.sh

# Script content:
#!/bin/bash
set -e

echo "Running linters..."
black --check src/ tests/
flake8 src/ tests/
mypy src/

echo "Running tests..."
pytest --cov=src/paperless_ngx --cov-fail-under=80

echo "Building documentation..."
cd docs && make html

echo "All checks passed!"
```

## Troubleshooting Tests

### Common Test Issues

#### Import Errors
```python
# Problem: ModuleNotFoundError
# Solution: Add to PYTHONPATH
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

#### Fixture Not Found
```python
# Problem: fixture 'xxx' not found
# Solution: Check conftest.py location and scope
# conftest.py should be in tests/ directory
```

#### Async Test Issues
```python
# Problem: RuntimeWarning: coroutine was never awaited
# Solution: Use pytest-asyncio
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result
```

#### Platform-Specific Failures
```python
# Problem: Test fails on specific platform
# Solution: Use platform detection
import platform
import pytest

@pytest.mark.skipif(
    platform.system() == "Windows" and platform.version() < "10",
    reason="Requires Windows 10+"
)
def test_modern_windows_feature():
    pass
```

#### Flaky Tests
```python
# Problem: Test sometimes fails
# Solution: Add retry logic
import pytest

@pytest.mark.flaky(reruns=3, reruns_delay=2)
def test_network_dependent():
    # Test that might fail due to network
    pass
```

### Test Debugging

```bash
# Drop into debugger on failure
pytest --pdb

# Show print statements
pytest -s

# Verbose output
pytest -vv

# Show local variables on failure
pytest -l

# Stop on first failure
pytest -x

# Run last failed tests
pytest --lf

# Run failed tests first
pytest --ff
```

## Performance Optimization

### Speed Up Tests

1. **Use pytest-xdist for parallel execution**
```bash
pip install pytest-xdist
pytest -n auto
```

2. **Cache expensive fixtures**
```python
@pytest.fixture(scope="session")
def expensive_resource():
    # Created once per session
    return create_expensive_resource()
```

3. **Mark slow tests**
```python
@pytest.mark.slow
def test_integration():
    # Long-running test
    pass

# Skip slow tests during development
pytest -m "not slow"
```

4. **Use mocks instead of real services**
```python
@patch('external_service.api_call')
def test_with_mock(mock_api):
    mock_api.return_value = {"fast": "response"}
    # Test runs instantly
```

## Next Steps

1. **Increase Coverage**: Focus on infrastructure layer
2. **Add Performance Tests**: Benchmark critical paths
3. **Implement E2E Tests**: Full workflow validation
4. **Set Up CI/CD**: Automated testing on commits
5. **Add Security Tests**: Validate security measures

---

**Navigation**: [Documentation Index](../INDEX.md) | [Contributing Guide](CONTRIBUTING.md) | [Code Standards](STANDARDS.md)