# Test Documentation

## 🧪 Test Coverage Overview

### Current Status
- **Workflow Coverage**: 100% (18/18 tests passing)
- **Integration Tests**: 62 test cases
- **Unit Tests**: Comprehensive domain logic coverage
- **Last Updated**: August 12, 2025

## 📊 Test Structure

```
tests/
├── unit/                      # Domain logic tests
│   ├── test_metadata_validator.py
│   ├── test_ocr_validator.py
│   ├── test_quality_analyzer.py
│   ├── test_report_generator.py
│   ├── test_smart_tag_matcher.py
│   └── test_tag_models.py
│
├── integration/               # External service tests
│   ├── test_connections.py   # Service connectivity
│   ├── test_email_accounts.py # Email IMAP tests
│   ├── test_july_2025_workflows.py # Workflow validation
│   ├── test_llm_priority.py  # LLM provider order
│   ├── test_paperless_api.py # API integration
│   ├── test_quality_scan.py  # Quality analysis
│   └── test_workflows.py     # End-to-end workflows
│
└── conftest.py               # Shared fixtures

Root-level test scripts (no pytest required):
├── test_connections.py       # Quick connection test
├── test_july_2025_simple.py  # July 2025 validation
└── test_all_connections.py   # Comprehensive check
```

## 🚀 Running Tests

### Quick Tests (No pytest Required)

```bash
# Test all connections
python test_connections.py

# Test July 2025 workflows
python test_july_2025_simple.py

# Test with detailed output
python test_all_connections.py --verbose
```

### Full Test Suite (Requires pytest)

```bash
# Install test dependencies
pip install pytest pytest-cov pytest-asyncio

# Run all tests
pytest

# Run with coverage report
pytest --cov=src/paperless_ngx --cov-report=html

# Run specific test categories
pytest tests/unit/
pytest tests/integration/

# Run specific test file
pytest tests/integration/test_july_2025_workflows.py -v

# Run tests matching pattern
pytest -k "test_llm" -v
```

## ✅ Key Test Validations

### July 2025 Workflow Tests
Successfully validates all requirements for July 2025 processing:

| Test | Status | Description |
|------|--------|-------------|
| Date Range | ✅ | July 2025 (2025-07-01 to 2025-07-31) |
| Email Accounts | ✅ | All 3 accounts configured |
| LLM Priority | ✅ | OpenAI → Ollama fallback |
| Tag Threshold | ✅ | 95% similarity enforced |
| False Positives | ✅ | Telekommunikation ≠ Telekom |
| Error Isolation | ✅ | Batch continues on failure |
| Quality Reports | ✅ | CSV generation working |

### Connection Tests
Validates all external service connections:

| Service | Test Coverage | Status |
|---------|--------------|--------|
| Paperless NGX | API connectivity, auth | ✅ |
| Gmail Account 1 | IMAP, app password | ✅ |
| Gmail Account 2 | IMAP, app password | ✅ |
| IONOS Account | IMAP, standard auth | ✅ |
| OpenAI | API key, model access | ✅ |
| Ollama | Local service, model | ✅ |

### Smart Tag Matcher Tests
Comprehensive validation of tag matching logic:

| Scenario | Threshold | Result |
|----------|-----------|--------|
| Identical tags | 100% | Match ✅ |
| Telekom vs Telekommunikation | 60% | No match ✅ |
| Singular vs Plural (German) | 90%+ | Match ✅ |
| Umlauts handling | 95%+ | Match ✅ |
| Compound words | Variable | Correct ✅ |

## 🧩 Test Fixtures

### Common Fixtures (conftest.py)

```python
@pytest.fixture
def mock_paperless_client():
    """Mocked Paperless API client"""
    
@pytest.fixture
def mock_llm_client():
    """Mocked LLM client with provider order"""
    
@pytest.fixture
def sample_documents():
    """Test document dataset"""
    
@pytest.fixture
def july_2025_date_range():
    """Date range for July 2025 tests"""
```

## 📝 Writing New Tests

### Test Structure Template

```python
import pytest
from unittest.mock import Mock, patch

class TestFeatureName:
    """Test suite for FeatureName"""
    
    @pytest.fixture
    def setup(self):
        """Setup test dependencies"""
        return {...}
    
    def test_happy_path(self, setup):
        """Test normal operation"""
        # Arrange
        service = setup['service']
        
        # Act
        result = service.process()
        
        # Assert
        assert result.success
        assert result.data == expected
    
    def test_error_handling(self, setup):
        """Test error scenarios"""
        with pytest.raises(ExpectedError):
            service.process_invalid()
    
    @pytest.mark.parametrize("input,expected", [
        ("case1", "result1"),
        ("case2", "result2"),
    ])
    def test_multiple_scenarios(self, input, expected):
        """Test with multiple inputs"""
        assert process(input) == expected
```

### Test Categories

1. **Unit Tests**: Test individual functions/classes in isolation
2. **Integration Tests**: Test interaction with external services
3. **End-to-End Tests**: Test complete workflows
4. **Performance Tests**: Test speed and memory usage

## 🔍 Test Coverage Reports

### Generate Coverage Report

```bash
# HTML report
pytest --cov=src/paperless_ngx --cov-report=html
# Open htmlcov/index.html in browser

# Terminal report
pytest --cov=src/paperless_ngx --cov-report=term-missing

# XML report (for CI/CD)
pytest --cov=src/paperless_ngx --cov-report=xml
```

### Coverage Goals
- **Domain Layer**: 95% minimum
- **Application Layer**: 90% minimum
- **Infrastructure Layer**: 80% minimum
- **Critical Workflows**: 100% required

## 🐛 Debugging Tests

### Verbose Output
```bash
pytest -vvv tests/integration/test_connections.py
```

### Debug with pdb
```bash
pytest --pdb tests/unit/test_smart_tag_matcher.py
```

### Show print statements
```bash
pytest -s tests/integration/test_workflows.py
```

### Run specific test
```bash
pytest tests/unit/test_tag_models.py::TestTagModel::test_similarity_calculation
```

## 🚦 Continuous Integration

### GitHub Actions Configuration

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov
      - run: pytest --cov=src/paperless_ngx --cov-report=xml
      - uses: codecov/codecov-action@v2
```

## 📊 Test Results Archive

### July 2025 Test Results
```json
{
  "date": "2025-08-12",
  "total_tests": 18,
  "passed": 18,
  "failed": 0,
  "duration": "0.8s",
  "workflows": {
    "email_fetch": "6/6 passed",
    "document_processing": "6/6 passed",
    "quality_scan": "6/6 passed"
  }
}
```

## 🔧 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Import errors | Ensure `PYTHONPATH` includes src directory |
| Mock failures | Check fixture scope and reset mocks |
| Async test failures | Use `pytest-asyncio` and `@pytest.mark.asyncio` |
| Connection timeouts | Increase timeout values in test config |

### Test Environment Variables

```bash
# Set for testing
export TEST_MODE=true
export MOCK_EXTERNAL_SERVICES=true
export LOG_LEVEL=DEBUG
```

## 📚 Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Python Testing Best Practices](https://realpython.com/pytest-python-testing/)
- [Test-Driven Development](https://testdriven.io/)
- [Mocking in Python](https://docs.python.org/3/library/unittest.mock.html)

---

<div align="center">

**[← Back to Docs](README.md)** | **[Main README →](../README.md)** | **[Contributing →](../README.md#-contributing)**

</div>