# Workflow Guide

Complete guide to the simplified 3-point workflow and advanced workflows for document processing.

**Last Updated**: August 12, 2025

## Table of Contents
1. [Quick Start](#quick-start)
2. [Simplified 3-Point Workflow](#simplified-3-point-workflow)
3. [Advanced Workflows](#advanced-workflows)
4. [Automation](#automation)
5. [Best Practices](#best-practices)
6. [Troubleshooting](#troubleshooting)

## Quick Start

### First Time Setup
1. Install and configure the system ([Setup Guide](../setup/))
2. Configure at least one email account
3. Set up LLM provider (OpenAI or Ollama)
4. Test connections: `python test_connections.py`

### Daily Usage
```bash
# Run the simplified menu
python -m paperless_ngx.presentation.cli.simplified_menu

# Or use direct commands
python -m paperless_ngx.presentation.cli.simplified_menu --workflow 1  # Fetch emails
python -m paperless_ngx.presentation.cli.simplified_menu --workflow 2  # Process docs
python -m paperless_ngx.presentation.cli.simplified_menu --workflow 3  # Quality check
```

## Simplified 3-Point Workflow

The simplified workflow provides three essential operations for document management:

### Workflow 1: Email-Dokumente abrufen (Fetch Email Documents)

**Purpose**: Download attachments from configured email accounts

```
╔══════════════════════════════════════════════════╗
║        📧 Email-Dokumente abrufen                ║
╠══════════════════════════════════════════════════╣
║  Zeitraum wählen:                               ║
║                                                  ║
║  1. Letztes Quartal (Apr-Jun 2025)             ║
║  2. Letzter Monat (Jul 2025)                   ║
║  3. Aktueller Monat (Aug 2025)                 ║
║  4. Aktuelles Quartal (Jul-Sep 2025)           ║
║  5. Benutzerdefiniert (YYYY-MM)                ║
╚══════════════════════════════════════════════════╝
```

**Process Flow**:
1. Select time period
2. System connects to all configured email accounts
3. Downloads PDF attachments
4. Organizes by month (YYYY-MM folders)
5. Skips duplicates automatically

**Example Output**:
```
📧 Fetching from 3 email accounts...
✓ Gmail Business: 12 attachments found
✓ IONOS Professional: 8 attachments found
✓ Outlook Archive: 5 attachments found

📁 Downloaded to:
  - 2025-07/: 15 files
  - 2025-08/: 10 files

✅ Total: 25 documents fetched successfully
```

### Workflow 2: Dokumente verarbeiten & anreichern (Process & Enrich)

**Purpose**: Extract metadata and enrich documents with AI

```
╔══════════════════════════════════════════════════╗
║     🔄 Dokumente verarbeiten & anreichern        ║
╠══════════════════════════════════════════════════╣
║  Verarbeitungsmodus:                            ║
║                                                  ║
║  1. Neue Dokumente (nicht verarbeitet)          ║
║  2. Alle Dokumente im Zeitraum                  ║
║  3. Dokumente ohne Metadaten                    ║
║  4. Dokumente mit OCR-Fehlern                   ║
╚══════════════════════════════════════════════════╝
```

**Process Flow**:
1. Select documents to process
2. Extract OCR text from Paperless
3. Send to LLM for analysis
4. Extract metadata:
   - Correspondent (sender)
   - Document type
   - Tags (3-7 German keywords)
   - Description (max 128 chars)
5. Apply smart tag matching (95% threshold)
6. Update in Paperless NGX

**Metadata Extraction Example**:
```json
{
  "correspondent": "Deutsche Telekom AG",
  "document_type": "Rechnung",
  "tags": ["telekommunikation", "festnetz", "2025-07", "rechnung"],
  "description": "Telekom Festnetz-Rechnung Juli 2025, Kundennr. 123456789",
  "title": "2025-07-15_Deutsche-Telekom_Rechnung"
}
```

### Workflow 3: Quality Scan & Report

**Purpose**: Analyze document quality and generate reports

```
╔══════════════════════════════════════════════════╗
║         ✅ Quality Scan & Report                 ║
╠══════════════════════════════════════════════════╣
║  Analyse-Optionen:                              ║
║                                                  ║
║  1. Vollständiger Scan (alle Kriterien)        ║
║  2. Metadaten-Vollständigkeit                   ║
║  3. OCR-Qualität                                ║
║  4. Tag-Konsistenz                              ║
║  5. Duplikate-Prüfung                           ║
╚══════════════════════════════════════════════════╝
```

**Quality Metrics**:
- **OCR Quality**: Text extraction success rate
- **Metadata Completeness**: Required fields populated
- **Tag Consistency**: Similar tags unified
- **Duplicate Detection**: Same content identification

**Report Output** (CSV):
```csv
Document_ID,Title,Issue_Type,Severity,Recommendation
1234,Invoice_2025-07.pdf,Missing_Tags,High,Add industry and date tags
1235,Contract_Draft.pdf,OCR_Failed,Critical,Reprocess with higher DPI
1236,Receipt_Store.pdf,No_Correspondent,Medium,Set correspondent to "Store Name"
```

## Advanced Workflows

### Full 8-Option Menu

For power users, the full menu provides additional options:

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
╚════════════════════════════════════════════════════╝
```

### Quarterly Processing

Process documents by quarter for better organization:

```python
# Process Q2 2025 (April-June)
python run.py --process-quarter Q2-2025

# Workflow:
# 1. Fetch all Q2 emails
# 2. Process with LLM
# 3. Generate quarterly report
# 4. Archive processed emails
```

### Tag Analysis & Cleanup

Identify and merge similar tags:

```python
# Analyze tags
python run.py --analyze-tags

# Output:
# Similar tag groups found:
# - "rechnung", "rechnungen", "invoice" (85% similar)
# - "telekom", "telekommunikation" (60% similar - NOT merged)
# 
# Recommended merges:
# - Merge "rechnungen" → "rechnung" (42 documents)
# - Keep "telekom" and "telekommunikation" separate
```

### Batch Processing

Process multiple documents efficiently:

```python
# Process specific folder
python run.py --batch-process --folder "2025-07"

# Features:
# - Processes in chunks of 10
# - Individual error isolation
# - Progress tracking
# - Detailed log output
```

## Automation

### Scheduled Processing (Cron)

```bash
# Edit crontab
crontab -e

# Daily email fetch at 8 AM
0 8 * * * cd /path/to/project && ./venv/bin/python -m paperless_ngx.presentation.cli.simplified_menu --workflow 1

# Weekly processing on Sunday 2 AM
0 2 * * 0 cd /path/to/project && ./venv/bin/python -m paperless_ngx.presentation.cli.simplified_menu --workflow 2

# Monthly quality report on 1st at 3 AM
0 3 1 * * cd /path/to/project && ./venv/bin/python -m paperless_ngx.presentation.cli.simplified_menu --workflow 3
```

### Windows Task Scheduler

```xml
<!-- Save as paperless-daily.xml -->
<Task xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2025-01-01T08:00:00</StartBoundary>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Actions>
    <Exec>
      <Command>C:\path\to\python.exe</Command>
      <Arguments>-m paperless_ngx.presentation.cli.simplified_menu --workflow 1</Arguments>
      <WorkingDirectory>C:\path\to\project</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
```

### Continuous Processing

Run email fetcher continuously:

```bash
# Fetch every 5 minutes
python run.py --run-email-fetcher --fetch-interval 300

# Features:
# - Automatic retry on failure
# - State tracking (no duplicates)
# - Graceful shutdown (Ctrl+C)
# - Memory efficient
```

## Best Practices

### 1. Regular Processing Schedule

**Recommended Schedule**:
- **Daily**: Fetch email attachments (Workflow 1)
- **Weekly**: Process and enrich documents (Workflow 2)
- **Monthly**: Quality scan and cleanup (Workflow 3)

### 2. Document Organization

```
paperless_attachments/
├── 2025-01/          # January documents
│   ├── processed/    # Already processed
│   └── pending/      # Awaiting processing
├── 2025-02/          # February documents
└── reports/          # Quality reports
    ├── 2025-Q1.csv
    └── 2025-Q2.csv
```

### 3. LLM Provider Strategy

**Cost-Optimized**:
```env
LLM_PROVIDER_ORDER=ollama,openai
# Use local Ollama first, OpenAI as fallback
```

**Quality-Optimized**:
```env
LLM_PROVIDER_ORDER=openai,ollama
# Use OpenAI for best results, Ollama as backup
```

### 4. Error Recovery

When processing fails:
1. Check error log: `logs/error.log`
2. Identify failed documents
3. Fix issue (usually OCR or encoding)
4. Reprocess specific documents:
   ```bash
   python run.py --process-document <document_id>
   ```

### 5. Performance Optimization

**Large Batches** (1000+ documents):
```env
# Adjust batch size
BATCH_CHUNK_SIZE=5  # Smaller chunks

# Increase timeouts
LLM_TIMEOUT=60
HTTP_TIMEOUT=30

# Use faster model
OLLAMA_MODEL=phi-2  # Faster than llama
```

## Troubleshooting

### Common Workflow Issues

#### Workflow 1: Email Fetch Issues

**Problem**: No attachments found
```bash
# Check email configuration
python run.py --test-email-connections

# List folders to verify
python run.py --list-email-folders "Account Name"

# Try different folder
EMAIL_ACCOUNT_1_FOLDER="All Mail"  # Instead of INBOX
```

**Problem**: Duplicates downloaded
```bash
# Clear state file
rm ~/.paperless_ngx/state/email_state.json

# Or reset specific account
python -c "from src.paperless_ngx.application.services import EmailFetcherService; service = EmailFetcherService(); service.reset_state('Gmail Account')"
```

#### Workflow 2: Processing Issues

**Problem**: LLM timeout
```python
# Increase timeout in .env
LLM_TIMEOUT=120  # 2 minutes

# Or use simpler prompts
LLM_SIMPLE_MODE=true
```

**Problem**: Wrong metadata extracted
```bash
# Check OCR quality first
python run.py --check-ocr <document_id>

# If OCR is bad, reprocess in Paperless
# Then retry metadata extraction
```

#### Workflow 3: Quality Report Issues

**Problem**: Report too large
```bash
# Process in smaller chunks
python -m paperless_ngx.presentation.cli.simplified_menu --workflow 3 --month 2025-07

# Or filter by severity
python run.py --quality-scan --min-severity high
```

### Performance Monitoring

```bash
# Check processing statistics
python run.py --stats

# Output:
# Documents processed: 1,234
# Average time: 2.3s per document
# Success rate: 98.5%
# LLM costs: $12.34
```

### Debug Mode

For detailed troubleshooting:
```bash
# Maximum verbosity
python run.py --debug --verbose

# Log to file
python run.py --debug 2>&1 | tee debug.log

# Dry run (no changes)
python run.py --dry-run --workflow 1
```

## Workflow Examples

### Example 1: Monthly Invoice Processing

```bash
# 1. Fetch this month's emails
python -m paperless_ngx.presentation.cli.simplified_menu --workflow 1 --period "2025-08"

# 2. Process only invoices
python run.py --batch-process --filter-type "Rechnung"

# 3. Generate invoice report
python run.py --report --type invoices --month "2025-08"
```

### Example 2: Quarterly Cleanup

```bash
# 1. Full quality scan for Q2
python -m paperless_ngx.presentation.cli.simplified_menu --workflow 3 --quarter "Q2-2025"

# 2. Fix missing metadata
python run.py --fix-metadata --from-report "reports/Q2-2025-quality.csv"

# 3. Merge similar tags
python run.py --merge-tags --threshold 85
```

### Example 3: New Account Setup

```bash
# 1. Test new email account
python run.py --test-email-connections

# 2. Fetch last 30 days
python run.py --fetch-email-attachments --since-days 30

# 3. Process all with verbose output
python run.py --batch-process --verbose

# 4. Verify quality
python -m paperless_ngx.presentation.cli.simplified_menu --workflow 3
```

## Next Steps

1. **Set Up Automation**: Configure scheduled tasks
2. **Customize Settings**: Adjust thresholds and preferences
3. **Monitor Quality**: Regular quality scans
4. **Optimize Performance**: Tune batch sizes and timeouts
5. **Explore Advanced Features**: Try the full 8-option menu

---

**Navigation**: [Documentation Index](../INDEX.md) | [User Manual](../USER_MANUAL.md) | [FAQ](FAQ.md) | [Commands](COMMANDS.md)