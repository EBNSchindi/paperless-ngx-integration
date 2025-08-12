# Test Scripts

This directory contains standalone test scripts for manual testing and validation.

## Quick Test Scripts

### Connection Tests
- `test_connections.py` - Comprehensive connection testing
- `test_connections_simple.py` - Simple connection validation
- `test_all_connections.py` - Test all configured connections

### Workflow Tests
- `test_july_2025_simple.py` - July 2025 workflow validation
- `test_july_2025_runner.py` - July 2025 workflow runner
- `test_end_to_end.py` - Complete end-to-end testing

### Manual Tests
- `test_manual_email_fetch.py` - Manual email fetching test
- `test_manual_paperless_processing.py` - Manual Paperless processing test
- `test_simple_integration.py` - Simple integration test

## Usage

These scripts can be run directly without pytest:

```bash
# Test connections
python tests/scripts/test_connections_simple.py

# Test July 2025 workflows
python tests/scripts/test_july_2025_simple.py

# Run all connection tests
python tests/scripts/test_all_connections.py
```

## Test Results

Test results are saved as JSON files in this directory:
- `test_results.json` - General test results
- `test_results_simple.json` - Simple test results
- `test_email_fetch_results.json` - Email fetch test results

## Note

For automated testing with pytest, use the tests in `tests/unit/` and `tests/integration/` directories.