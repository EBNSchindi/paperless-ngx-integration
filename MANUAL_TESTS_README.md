# Manual Integration Tests for Paperless NGX System

This document describes the manual integration tests created for the Paperless NGX API system. These tests allow comprehensive verification of email fetching, document processing, and metadata extraction functionality.

## Test Files Overview

### 1. `test_manual_email_fetch.py`
Tests email retrieval from all configured email accounts (GMAIL1, GMAIL2, IONOS).

**Features:**
- Test connections to all email accounts
- Fetch attachments from specific or all accounts
- Display download folder structure
- Track processing state
- Reset account states
- List available folders

**Usage:**
```bash
# Interactive mode (recommended)
python test_manual_email_fetch.py --interactive

# Fetch from all accounts (last 7 days)
python test_manual_email_fetch.py

# Dry run (no downloads)
python test_manual_email_fetch.py --dry-run

# Specific account only
python test_manual_email_fetch.py --account GMAIL1 --days 30

# Fetch from last 14 days
python test_manual_email_fetch.py --days 14
```

### 2. `test_manual_paperless_processing.py`
Tests metadata extraction and update functionality with Paperless NGX.

**Features:**
- Test Paperless API connection
- Process random or recent documents
- Extract metadata using LLM
- Update document metadata
- Search functionality testing
- Tag analysis and management

**Usage:**
```bash
# Interactive mode (recommended)
python test_manual_paperless_processing.py --interactive

# Process 5 random documents
python test_manual_paperless_processing.py --count 5 --random

# Process recent documents (last 7 days)
python test_manual_paperless_processing.py --recent 7

# Auto-update documents after extraction
python test_manual_paperless_processing.py --count 3 --auto-update

# Process specific number of documents
python test_manual_paperless_processing.py --count 10
```

### 3. `test_end_to_end.py`
Tests the complete workflow from email fetching to document update.

**Features:**
- Complete pipeline testing
- Performance metrics
- Stage-by-stage verification
- Error tracking and reporting
- Success rate calculation

**Usage:**
```bash
# Run complete workflow
python test_end_to_end.py

# Dry run mode (no changes)
python test_end_to_end.py --dry-run

# Auto mode (no user prompts)
python test_end_to_end.py --auto

# Process emails from last 14 days
python test_end_to_end.py --days 14

# Skip setup verification
python test_end_to_end.py --skip-setup-check
```

## Interactive Menu Options

### Email Fetch Test Menu
1. **Test all connections** - Verify connectivity to all email accounts
2. **Fetch from specific account** - Choose and fetch from one account
3. **Fetch from all accounts** - Batch fetch from all configured accounts
4. **Display folder structure** - Show downloaded attachments organization
5. **Reset account state** - Clear processing history for fresh start
6. **Show account statistics** - Display processing metrics
7. **List folders for account** - Show available IMAP folders
8. **Save results and exit** - Save test results to JSON
9. **Exit without saving** - Exit immediately

### Paperless Processing Test Menu
1. **Test connection and show statistics** - Verify API and show document stats
2. **Process random documents** - Select and process random documents
3. **Process recent documents** - Process recently added documents
4. **Process specific document by ID** - Enter document ID to process
5. **Test search functionality** - Run various search queries
6. **Show tag statistics** - Display most used tags
7. **Find similar tags** - Identify potentially duplicate tags
8. **Test metadata extraction only** - Extract without updating
9. **Save results and exit** - Save test results to JSON
0. **Exit without saving** - Exit immediately

## Test Results

All tests save their results to JSON files:
- `test_email_fetch_results.json` - Email fetching test results
- `test_paperless_processing_results.json` - Document processing results
- `test_end_to_end_results.json` - Complete workflow results

Results include:
- Timestamps
- Success/failure counts
- Error messages
- Performance metrics
- Detailed logs of operations

## Prerequisites

1. **Environment Setup:**
   - Virtual environment activated: `source venv/bin/activate`
   - All dependencies installed
   - Environment variables configured (see `.env` file)

2. **Email Configuration:**
   - GMAIL1_EMAIL and GMAIL1_APP_PASSWORD
   - GMAIL2_EMAIL and GMAIL2_APP_PASSWORD
   - IONOS_EMAIL and IONOS_PASSWORD

3. **Paperless Configuration:**
   - PAPERLESS_URL (default: http://192.168.178.76:8010/api)
   - PAPERLESS_TOKEN

4. **LLM Configuration:**
   - Ollama running locally or
   - OpenAI API key configured

## Testing Workflow

### Quick Test (5 minutes)
1. Run connection tests:
   ```bash
   python test_manual_email_fetch.py --interactive
   # Select option 1 (Test all connections)
   ```

2. Test document processing:
   ```bash
   python test_manual_paperless_processing.py --count 1 --random
   ```

### Comprehensive Test (15-30 minutes)
1. Full email fetch test:
   ```bash
   python test_manual_email_fetch.py --interactive
   # Test all menu options
   ```

2. Full document processing:
   ```bash
   python test_manual_paperless_processing.py --interactive
   # Test multiple scenarios
   ```

3. End-to-end workflow:
   ```bash
   python test_end_to_end.py --days 7
   ```

### Troubleshooting Test
If experiencing issues:
1. Test in dry-run mode first:
   ```bash
   python test_end_to_end.py --dry-run
   ```

2. Check individual components:
   ```bash
   # Test email only
   python test_manual_email_fetch.py --dry-run --days 1
   
   # Test Paperless only
   python test_manual_paperless_processing.py --count 1
   ```

## Common Issues and Solutions

### Email Connection Failures
- Verify app passwords are correct
- Check IMAP is enabled in email accounts
- Ensure no 2FA conflicts
- Try resetting account state

### Paperless API Errors
- Verify API URL is accessible
- Check API token is valid
- Ensure Paperless service is running
- Verify network connectivity

### LLM Processing Issues
- Check Ollama is running (`ollama serve`)
- Verify OpenAI API key if using fallback
- Ensure sufficient system memory
- Check model is downloaded (`ollama pull llama3.1:8b`)

### Attachment Processing
- Verify download directory permissions
- Check disk space availability
- Ensure file type is supported
- Verify attachment size limits

## Performance Expectations

- **Email Fetching:** 1-5 seconds per account connection
- **Attachment Download:** Depends on size and count
- **Metadata Extraction:** 5-30 seconds per document (LLM dependent)
- **Document Update:** < 1 second per document
- **Full Workflow:** 2-10 minutes for typical batch

## Best Practices

1. **Start with dry-run mode** to verify configuration
2. **Use interactive mode** for detailed testing
3. **Test incrementally** - start with 1-2 documents
4. **Monitor logs** in `logs/` directory
5. **Save test results** for comparison
6. **Reset states** when switching test scenarios

## Support

For issues or questions:
1. Check log files in `logs/` directory
2. Review error messages in test results JSON
3. Verify all environment variables are set
4. Ensure all services are running (Paperless, Ollama)
5. Test network connectivity to services