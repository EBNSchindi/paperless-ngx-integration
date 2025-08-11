# Generated Prompt: Interactive Menu System with Agent Chain Analysis
Generated: 2025-08-11
By: prompt-engineer
Status: DRAFT - Awaiting Review

## Project Context
- Documentation reviewed: CLAUDE.md, existing CLI structure (main.py), email_fetcher_service.py, Clean Architecture pattern
- Tech stack: Python, Paperless NGX API, LiteLLM (Ollama/OpenAI), IMAP email clients
- Relevant patterns: Service layer pattern, use case pattern, structured logging, state persistence
- Architecture: Clean Architecture with domain/application/infrastructure/presentation layers

## Available Agents Analysis
No specific agent definitions (*.md files) were found in the current directory. The implementation should proceed as a monolithic development task or be divided into phases as specified below.

## The Prompt

Implement a comprehensive interactive menu system for Paperless NGX document management with three core functionalities: Complete Quality Scan with CSV reporting, Quarterly Processing with intelligent tag unification, and Time-Range Email Document Download. The system must integrate seamlessly with the existing Clean Architecture in `src/paperless_ngx/` and extend the current CLI framework.

### Technical Requirements with Complexity Analysis

#### 1. COMPLETE QUALITY SCAN (Option 1)
**Complexity: HIGH | ~800 LOC | 5 new files**

Create comprehensive quality analysis system for all Paperless documents:

```python
# src/paperless_ngx/application/use_cases/quality_scan.py
class QualityScanner:
    """
    Document quality analysis with multi-dimensional validation.
    
    Validation Dimensions:
    1. OCR Quality: Text extraction success/failure detection
    2. Metadata Completeness: Required fields presence
    3. Data Consistency: Sender/recipient validation
    4. Content Analysis: Meaningful text detection
    """
    
    def __init__(self):
        self.paperless_api = PaperlessAPIService()
        self.quality_analyzer = QualityAnalyzerService()
        self.report_generator = CSVReportGenerator()
        
    def scan_documents_in_range(
        self,
        start_date: str = None,  # Format: "YYYY-MM"
        end_date: str = None,     # Format: "YYYY-MM" or None for today
        batch_size: int = 100
    ) -> QualityReport:
        """
        Perform comprehensive quality scan with date filtering.
        
        Quality Checks:
        - OCR text exists and length > 50 characters
        - Correspondent is not None and not Daniel/EBN
        - Document type is properly classified
        - Tags exist (minimum 3)
        - Title is meaningful (not default scanner name)
        - Custom fields populated (description)
        
        Returns QualityReport with:
        - document_id: int
        - title: str
        - created_date: datetime
        - ocr_status: Enum[SUCCESS, FAILED, EMPTY, INSUFFICIENT]
        - ocr_text_length: int
        - missing_fields: List[str]
        - validation_errors: List[str]
        - needs_reprocessing: bool
        - severity: Enum[CRITICAL, WARNING, INFO]
        - suggested_actions: List[str]
        """
        
    def export_findings_csv(
        self,
        report: QualityReport,
        output_dir: Path = Path("./reports/quality_scans")
    ) -> Path:
        """
        Generate timestamped CSV with categorized findings.
        
        CSV Structure:
        - Dokument_ID
        - Titel
        - Erstellungsdatum
        - OCR_Status
        - Textlänge
        - Fehlende_Felder
        - Validierungsfehler
        - Schweregrad
        - Empfohlene_Aktionen
        - Neu_Verarbeiten
        
        Filename: quality_scan_YYYY-MM-DD_HH-MM-SS.csv
        """
```

**Integration Points:**
- Paperless API for document retrieval
- LLM for content quality assessment
- Progress tracking with tqdm
- Structured logging for audit trail

#### 2. QUARTERLY PROCESSING (Option 2)
**Complexity: VERY HIGH | ~1200 LOC | 7 new files**

Intelligent quarterly document processing with advanced tag management:

```python
# src/paperless_ngx/application/use_cases/quarterly_processor.py
class QuarterlyProcessor:
    """
    Sophisticated quarterly processing with tag housekeeping.
    
    Features:
    - Automatic quarter calculation
    - Intelligent tag unification
    - Metadata re-enrichment
    - Batch processing with rollback
    """
    
    def __init__(self):
        self.tag_manager = TagManagementService()
        self.metadata_extractor = MetadataExtractionUseCase()
        self.paperless_api = PaperlessAPIService()
        self.transaction_manager = TransactionManager()
        
    def process_last_quarter(self) -> ProcessingReport:
        """
        Process documents from last completed quarter.
        
        Quarter Calculation:
        - Q1: Jan-Mar (process if current month >= April)
        - Q2: Apr-Jun (process if current month >= July)
        - Q3: Jul-Sep (process if current month >= October)
        - Q4: Oct-Dec (process if current month >= January next year)
        
        Processing Steps:
        1. Calculate quarter boundaries
        2. Fetch all documents in range
        3. Analyze existing tags across ALL documents
        4. Create tag unification map
        5. Re-extract metadata via LLM
        6. Apply unified tags
        7. Update documents in batches
        8. Generate processing report
        """

# src/paperless_ngx/application/services/tag_management_service.py
class TagManagementService:
    """
    Advanced tag unification and housekeeping.
    
    Unification Rules:
    1. Fuzzy matching with Levenshtein distance (threshold: 0.85)
    2. German language normalization:
       - Singular preferred ("Rechnung" not "Rechnungen")
       - Proper noun capitalization
       - Umlauts preserved (ä, ö, ü, ß)
    3. Semantic grouping:
       - Invoice variants → "Rechnung"
       - Contract variants → "Vertrag"
       - Correspondence → "Korrespondenz"
    """
    
    def analyze_tag_landscape(self) -> TagAnalysis:
        """
        Comprehensive tag analysis across entire document base.
        
        Returns:
        - total_unique_tags: int
        - duplicate_clusters: List[TagCluster]
        - suggested_merges: List[TagMerge]
        - orphaned_tags: List[str] (used < 3 times)
        - tag_frequency: Dict[str, int]
        """
        
    def create_unification_map(
        self,
        analysis: TagAnalysis,
        auto_merge_threshold: float = 0.90
    ) -> Dict[str, str]:
        """
        Generate tag unification mapping.
        
        Example:
        {
            "Rechnungen": "Rechnung",
            "Invoice": "Rechnung",
            "Stromrechnung": "Rechnung_Strom",
            "Versicherungsvertrag": "Vertrag_Versicherung"
        }
        """
        
    def apply_tag_unification(
        self,
        unification_map: Dict[str, str],
        dry_run: bool = False
    ) -> UnificationReport:
        """
        Apply tag unification with transaction support.
        
        Safety Features:
        - Dry run mode for preview
        - Automatic backup creation
        - Rollback on failure
        - Progress tracking
        """
```

**Advanced Features:**
- Machine learning-based tag clustering
- Multi-language tag normalization
- Hierarchical tag structures
- Tag usage analytics

#### 3. EMAIL DOCUMENT DOWNLOAD (Option 3)
**Complexity: MEDIUM | ~500 LOC | 3 new files**

Enhanced email fetching with time-range support:

```python
# src/paperless_ngx/application/use_cases/email_document_downloader.py
class EmailDocumentDownloader:
    """
    Time-range based email document retrieval.
    
    Supported Accounts:
    - GMAIL1: Primary Gmail account
    - GMAIL2: Secondary Gmail account
    - IONOS: Business email account
    """
    
    def download_by_period(
        self,
        start_month: str,  # "YYYY-MM"
        end_month: Optional[str] = None,  # None = today
        accounts: Optional[List[str]] = None,  # None = all
        filters: Optional[EmailFilters] = None
    ) -> DownloadReport:
        """
        Download documents from emails within period.
        
        Filters:
        - sender_whitelist: List[str]
        - sender_blacklist: List[str]
        - subject_patterns: List[str] (regex)
        - min_attachment_size: int (bytes)
        - max_attachment_size: int (bytes)
        - allowed_extensions: List[str]
        
        Processing:
        1. Connect to email accounts
        2. Search emails in date range
        3. Filter by criteria
        4. Download attachments
        5. Organize by date/sender
        6. Track in state database
        """
```

### AGENT CHAIN
Use Architect-Cleaner, Researcher, Python-Generator, Test-Engineer from personal agents

### IMPLEMENTATION ARCHITECTURE

```
src/paperless_ngx/
├── application/
│   ├── services/
│   │   ├── paperless_api_service.py      # NEW: Core API interface
│   │   ├── tag_management_service.py     # NEW: Tag unification
│   │   ├── quality_analyzer_service.py   # NEW: Quality detection
│   │   └── report_generator_service.py   # NEW: CSV generation
│   └── use_cases/
│       ├── quality_scan.py               # NEW: Option 1 logic
│       ├── quarterly_processor.py        # NEW: Option 2 logic
│       └── email_document_downloader.py  # NEW: Option 3 logic
├── domain/
│   ├── models/
│   │   ├── quality_report.py            # NEW: Quality scan models
│   │   ├── tag_models.py                # NEW: Tag management models
│   │   └── processing_report.py         # NEW: Processing reports
│   └── validators/
│       ├── ocr_validator.py             # NEW: OCR validation rules
│       └── metadata_validator.py        # NEW: Metadata rules
├── infrastructure/
│   ├── paperless/
│   │   ├── api_client.py                # NEW: HTTP client
│   │   └── api_models.py                # NEW: API DTOs
│   └── persistence/
│       ├── transaction_manager.py       # NEW: Transaction support
│       └── backup_manager.py            # NEW: Backup handling
└── presentation/
    └── cli/
        ├── interactive_menu.py          # NEW: Menu system
        └── main.py                       # MODIFY: Add menu entry point
```

### INTERACTIVE MENU IMPLEMENTATION

```python
# src/paperless_ngx/presentation/cli/interactive_menu.py
import inquirer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

class InteractiveMenu:
    """
    Rich interactive menu with German interface.
    """
    
    def __init__(self):
        self.console = Console()
        self.quality_scanner = QualityScanner()
        self.quarterly_processor = QuarterlyProcessor()
        self.email_downloader = EmailDocumentDownloader()
        
    def display_main_menu(self):
        """
        Display main menu with ASCII art header.
        """
        self.console.print("""
╔══════════════════════════════════════════════════════════╗
║        PAPERLESS NGX - ERWEITERTE VERARBEITUNG          ║
║               Dokumentenverwaltungssystem                ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  [1] 📊 Kompletter Qualitäts-Scan                       ║
║      → Alle Dokumente auf Fehler prüfen                 ║
║      → OCR-Qualität analysieren                         ║
║      → CSV-Report generieren                            ║
║                                                          ║
║  [2] 📅 Quartalsweise Verarbeitung                      ║
║      → Letztes Quartal automatisch verarbeiten          ║
║      → Metadaten neu extrahieren                        ║
║      → Tags intelligent vereinheitlichen                ║
║                                                          ║
║  [3] 📧 Email-Dokumente herunterladen                   ║
║      → Zeitraum flexibel wählen                         ║
║      → Aus Gmail & IONOS Konten                         ║
║      → Mit intelligenter Filterung                      ║
║                                                          ║
║  [4] 🔧 Erweiterte Einstellungen                        ║
║  [5] 📈 Statistiken anzeigen                            ║
║  [0] 🚪 Beenden                                         ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
        """, style="bold cyan")
        
    def handle_quality_scan(self):
        """
        Interactive quality scan with date selection.
        """
        questions = [
            inquirer.Text(
                'start_date',
                message="Startdatum (YYYY-MM, leer für Anfang)",
                validate=lambda _, x: x == "" or self._validate_month(x)
            ),
            inquirer.Text(
                'end_date',
                message="Enddatum (YYYY-MM, leer für heute)",
                validate=lambda _, x: x == "" or self._validate_month(x)
            ),
            inquirer.Confirm(
                'export_csv',
                message="Ergebnisse als CSV exportieren?",
                default=True
            )
        ]
        
        answers = inquirer.prompt(questions)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            scan_task = progress.add_task(
                "[cyan]Scanne Dokumente...", 
                total=None
            )
            
            report = self.quality_scanner.scan_documents_in_range(
                start_date=answers['start_date'],
                end_date=answers['end_date']
            )
            
            if answers['export_csv']:
                csv_path = self.quality_scanner.export_findings_csv(report)
                self.console.print(
                    f"[green]✓ CSV exportiert nach: {csv_path}[/green]"
                )
        
        self._display_quality_report(report)
        
    def handle_quarterly_processing(self):
        """
        Quarterly processing with preview mode.
        """
        last_quarter = self.quarterly_processor.get_last_quarter_range()
        
        self.console.print(f"""
[yellow]Letztes abgeschlossenes Quartal:[/yellow]
Von: {last_quarter[0].strftime('%Y-%m-%d')}
Bis: {last_quarter[1].strftime('%Y-%m-%d')}
        """)
        
        questions = [
            inquirer.Confirm(
                'preview_tags',
                message="Tag-Vereinheitlichung vorher anzeigen?",
                default=True
            ),
            inquirer.Confirm(
                'backup',
                message="Backup vor Änderungen erstellen?",
                default=True
            )
        ]
        
        answers = inquirer.prompt(questions)
        
        if answers['preview_tags']:
            analysis = self.tag_manager.analyze_tag_landscape()
            self._display_tag_analysis(analysis)
            
            if not inquirer.confirm("Fortfahren mit Verarbeitung?"):
                return
        
        # Process with progress bar
        report = self.quarterly_processor.process_last_quarter()
        self._display_processing_report(report)
```

### ERROR HANDLING & RECOVERY

```python
class TransactionManager:
    """
    Transaction support with automatic rollback.
    """
    
    def __init__(self):
        self.backup_manager = BackupManager()
        self.rollback_points = []
        
    @contextmanager
    def transaction(self, operation_name: str):
        """
        Context manager for transactional operations.
        
        Usage:
        with transaction_manager.transaction("tag_unification"):
            # Perform operations
            # Automatic rollback on exception
        """
        backup_id = self.backup_manager.create_backup(operation_name)
        self.rollback_points.append(backup_id)
        
        try:
            yield
            self.rollback_points.pop()
        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            self.backup_manager.restore_backup(backup_id)
            self.rollback_points.pop()
            raise TransactionRollbackError(
                f"Operation '{operation_name}' rolled back: {e}"
            )
```

### RISK ASSESSMENT

#### High-Risk Areas:
1. **Tag Unification**: Potential data loss if merging incorrect tags
   - Mitigation: Preview mode, backup, manual confirmation
   
2. **Batch API Updates**: Could overwhelm Paperless instance
   - Mitigation: Rate limiting, batch size control, retry logic
   
3. **OCR Quality Detection**: False positives could mark good documents
   - Mitigation: Conservative thresholds, manual review option

4. **Email Download**: Duplicate downloads possible
   - Mitigation: UID tracking, state persistence, deduplication

#### Performance Considerations:
- **Large Document Sets**: Implement pagination (100 docs/batch)
- **API Rate Limits**: Add configurable delays between requests
- **Memory Usage**: Stream processing for CSV generation
- **Network Failures**: Exponential backoff with max retries

### TESTING STRATEGY

```python
# tests/test_quality_scanner.py
class TestQualityScanner:
    """Comprehensive quality scanner tests."""
    
    def test_ocr_detection(self):
        """Test OCR failure detection accuracy."""
        
    def test_date_range_filtering(self):
        """Test document filtering by date range."""
        
    def test_csv_generation(self):
        """Test CSV report generation."""
        
    @pytest.mark.integration
    def test_paperless_api_integration(self):
        """Test real API integration."""

# tests/test_tag_management.py
class TestTagManagement:
    """Tag unification and management tests."""
    
    def test_fuzzy_matching(self):
        """Test Levenshtein distance calculation."""
        
    def test_german_normalization(self):
        """Test German language normalization rules."""
        
    def test_unification_rollback(self):
        """Test transaction rollback on failure."""
```

### DEPLOYMENT CONSIDERATIONS

1. **Virtual Environment Setup**:
```bash
# Activate existing venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install new dependencies
pip install inquirer rich tqdm pandas python-Levenshtein
```

2. **Configuration Updates**:
```python
# .env additions
PAPERLESS_API_TIMEOUT=120
QUALITY_SCAN_BATCH_SIZE=100
TAG_MERGE_THRESHOLD=0.85
EMAIL_DOWNLOAD_MAX_SIZE=25MB
```

3. **Directory Structure Creation**:
```bash
mkdir -p reports/quality_scans
mkdir -p reports/quarterly_processing
mkdir -p backups/tag_unifications
```

## Suggested Manual Execution Steps

1. **Initial Setup**:
   - Review and approve this technical specification
   - Create necessary directory structure
   - Install required dependencies

2. **Phase 1 - Core API Layer** (2-3 hours):
   - Implement PaperlessAPIService
   - Add authentication and pagination
   - Create error handling

3. **Phase 2 - Quality Scanner** (3-4 hours):
   - Implement quality detection logic
   - Create CSV report generator
   - Add progress tracking

4. **Phase 3 - Tag Management** (4-5 hours):
   - Implement fuzzy matching
   - Create unification logic
   - Add transaction support

5. **Phase 4 - Quarterly Processor** (3-4 hours):
   - Implement quarter calculation
   - Integrate tag management
   - Add batch processing

6. **Phase 5 - Email Downloader** (2-3 hours):
   - Extend existing email service
   - Add date range support
   - Implement filters

7. **Phase 6 - Interactive Menu** (2-3 hours):
   - Create menu interface
   - Add user interactions
   - Implement progress displays

8. **Phase 7 - Testing** (3-4 hours):
   - Write unit tests
   - Create integration tests
   - Perform manual testing

## Execution Command
```bash
"Implement a comprehensive interactive menu system for Paperless NGX with three core functionalities: 1) Complete Quality Scan that detects OCR failures, missing metadata, and generates timestamped CSV reports with findings categorized by severity; 2) Quarterly Processing with intelligent tag unification using fuzzy matching (Levenshtein distance), German language normalization, and metadata re-extraction via LLM; 3) Time-range based Email Document Download from GMAIL1, GMAIL2, and IONOS accounts. The system must extend the existing Clean Architecture in src/paperless_ngx/, integrate with Paperless API at http://192.168.178.76:8010/api, implement transaction support with automatic rollback, use tqdm for progress tracking, create an interactive German-language menu using inquirer and rich libraries, handle batch processing with configurable limits, persist state for recovery, and generate comprehensive reports. Include robust error handling with exponential backoff, rate limiting for API calls, and preview modes for destructive operations."
```

## Pre-Execution Checklist
- [ ] Project structure analyzed and understood
- [ ] Clean Architecture patterns identified
- [ ] Paperless API endpoints documented
- [ ] Email configuration verified
- [ ] German language requirements considered
- [ ] Risk mitigation strategies defined
- [ ] Testing approach established
- [ ] Rollback procedures documented
- [ ] Progress tracking implemented
- [ ] CSV export formats specified
- [ ] Date range handling tested
- [ ] Tag unification rules defined
- [ ] Transaction support designed
- [ ] Error recovery mechanisms in place