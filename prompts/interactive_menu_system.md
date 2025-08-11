# Generated Prompt: Interactive Menu System for Paperless NGX
Generated: 2025-08-11
By: prompt-engineer
Status: DRAFT - Awaiting Review

## Project Context
- Documentation reviewed: CLAUDE.md, existing CLI structure, email_fetcher_service.py, metadata_extraction.py
- Tech stack: Python, Paperless NGX API, LiteLLM (Ollama/OpenAI), Clean Architecture
- Relevant patterns: Existing service layer, use case pattern, structured logging

## The Prompt

Implement an interactive menu system for the Paperless NGX integration with three core functionalities: Complete Quality Scan, Quarterly Processing, and Email Document Download. The implementation should extend the existing Clean Architecture structure in `src/paperless_ngx/` and integrate with the current CLI framework in `src/paperless_ngx/presentation/cli/main.py`.

### Technical Requirements

#### 1. Architecture Integration
- Extend the existing CLI module at `src/paperless_ngx/presentation/cli/main.py`
- Create new use cases in `src/paperless_ngx/application/use_cases/`:
  - `quality_scan.py` - Document quality analysis
  - `quarterly_processor.py` - Quarterly document processing
  - `document_downloader.py` - Email document download management
- Add new services in `src/paperless_ngx/application/services/`:
  - `paperless_api_service.py` - Core Paperless API interaction
  - `tag_management_service.py` - Tag unification and housekeeping
  - `quality_analyzer_service.py` - OCR quality detection

#### 2. Menu Option 1 - Complete Quality Scan

Create `src/paperless_ngx/application/use_cases/quality_scan.py`:

```python
class QualityScanner:
    def scan_all_documents(self) -> pd.DataFrame:
        """
        Scan all documents in Paperless for quality issues.
        
        Returns DataFrame with columns:
        - document_id: int
        - title: str
        - ocr_status: str (success/failed/empty)
        - missing_fields: List[str]
        - ocr_text_length: int
        - has_correspondent: bool
        - has_document_type: bool
        - has_tags: bool
        - needs_reprocessing: bool
        - error_details: str
        """
        
    def export_findings_to_csv(self, findings: pd.DataFrame, output_path: Path):
        """Export quality scan findings to CSV with timestamp."""
```

Key implementation points:
- Connect to Paperless API using base URL: `http://192.168.178.76:8010/api`
- Iterate through ALL documents (handle pagination)
- Check OCR quality:
  - OCR text empty or < 50 characters → "ocr_failed"
  - Missing correspondent → flag for reprocessing
  - Missing document_type → flag for reprocessing
  - No tags → flag for reprocessing
- Generate CSV with timestamp: `quality_scan_YYYY-MM-DD_HH-MM-SS.csv`

#### 3. Menu Option 2 - Quarterly Processing

Create `src/paperless_ngx/application/use_cases/quarterly_processor.py`:

```python
class QuarterlyProcessor:
    def __init__(self):
        self.tag_manager = TagManagementService()
        self.metadata_extractor = MetadataExtractionUseCase()
        
    def get_last_quarter_range(self) -> Tuple[datetime, datetime]:
        """Calculate date range for last completed quarter."""
        
    def process_quarterly_documents(self, start_date: datetime, end_date: datetime):
        """
        Process documents from specified quarter.
        - Fetch documents in date range
        - Re-extract metadata using LLM
        - Unify tags across document base
        - Update documents in Paperless
        """
        
    def unify_tags(self):
        """
        Tag housekeeping:
        1. Get all existing tags from Paperless
        2. Find similar tags (fuzzy matching)
        3. Merge duplicates (e.g., "Rechnung", "Rechnungen" → "Rechnung")
        4. Apply consistent naming conventions
        """
```

Tag Management Strategy:
- Before creating new tags, ALWAYS check existing tags
- Use fuzzy matching (Levenshtein distance) to find similar tags
- Implement tag normalization rules:
  - Singular form preferred over plural
  - Consistent capitalization (Title Case for German nouns)
  - Remove special characters except hyphens
- Maintain tag mapping dictionary for consistency

#### 4. Menu Option 3 - Email Document Download

Extend existing `EmailFetcherService` with new parameters:

```python
class EnhancedEmailFetcher(EmailFetcherService):
    def fetch_documents_by_period(
        self,
        start_month: str,  # Format: "YYYY-MM"
        end_month: Optional[str] = None,  # Default: current date
        account_filter: Optional[List[str]] = None  # Filter specific accounts
    ):
        """
        Download documents from emails within specified period.
        Supports GMAIL1, GMAIL2, IONOS accounts.
        """
```

#### 5. Interactive Menu Implementation

Extend `src/paperless_ngx/presentation/cli/main.py`:

```python
def interactive_menu():
    """
    Display interactive menu for Paperless NGX operations.
    
    ╔════════════════════════════════════════════════════╗
    ║     Paperless NGX - Erweiterte Verarbeitung       ║
    ╠════════════════════════════════════════════════════╣
    ║  1. Kompletter Qualitäts-Scan                     ║
    ║     → Alle Dokumente prüfen                       ║
    ║     → Fehlerhafte OCR erkennen                    ║
    ║     → CSV-Report erstellen                        ║
    ║                                                    ║
    ║  2. Quartalsweise Verarbeitung                    ║
    ║     → Letztes Quartal verarbeiten                 ║
    ║     → Metadaten neu extrahieren                   ║
    ║     → Tags vereinheitlichen                       ║
    ║                                                    ║
    ║  3. Email-Dokumente herunterladen                 ║
    ║     → Zeitraum wählen (YYYY-MM)                   ║
    ║     → Aus konfigurierten Email-Konten             ║
    ║                                                    ║
    ║  0. Beenden                                        ║
    ╚════════════════════════════════════════════════════╝
    
    Auswahl: _
    """
```

#### 6. Paperless API Service Implementation

Create `src/paperless_ngx/application/services/paperless_api_service.py`:

```python
class PaperlessAPIService:
    def __init__(self):
        self.base_url = settings.paperless_base_url
        self.api_token = settings.paperless_api_token
        self.session = self._create_session()
        
    def get_all_documents(self, page_size: int = 100) -> Generator[Dict, None, None]:
        """Paginated document retrieval."""
        
    def get_document_ocr(self, document_id: int) -> str:
        """Get OCR text for document."""
        
    def update_document_metadata(self, document_id: int, metadata: Dict):
        """Update document with new metadata."""
        
    def get_or_create_correspondent(self, name: str) -> int:
        """Get or create correspondent, return ID."""
        
    def get_or_create_tag(self, name: str) -> int:
        """Get or create tag, return ID."""
        
    def get_all_tags(self) -> List[Dict]:
        """Get all existing tags from Paperless."""
```

#### 7. Data Models

Create `src/paperless_ngx/domain/models/quality_report.py`:

```python
@dataclass
class QualityIssue:
    document_id: int
    title: str
    issue_type: str  # "ocr_failed", "missing_metadata", "invalid_correspondent"
    severity: str  # "critical", "warning", "info"
    details: str
    needs_reprocessing: bool
    
@dataclass
class QualityReport:
    scan_date: datetime
    total_documents: int
    documents_with_issues: int
    critical_issues: List[QualityIssue]
    warnings: List[QualityIssue]
    
    def to_csv(self, output_path: Path):
        """Export report to CSV format."""
```

#### 8. Configuration Updates

Add to `src/paperless_ngx/infrastructure/config/settings.py`:

```python
# Paperless API Configuration
paperless_base_url: str = "http://192.168.178.76:8010/api"
paperless_api_token: str  # Load from .env

# Quality Scan Settings
min_ocr_text_length: int = 50
quality_scan_output_dir: Path = Path("./reports/quality_scans")

# Quarterly Processing Settings
quarterly_processing_batch_size: int = 10
tag_similarity_threshold: float = 0.85  # For fuzzy matching

# Email Download Settings
email_download_start_default: str  # Default start month YYYY-MM
```

#### 9. Error Handling

Implement comprehensive error handling:
- Network failures → Retry with exponential backoff
- Invalid OCR → Mark for manual review
- LLM failures → Fallback to basic extraction
- API rate limits → Implement throttling

#### 10. Testing Requirements

Create test files:
- `tests/test_quality_scanner.py`
- `tests/test_quarterly_processor.py`
- `tests/test_tag_manager.py`

#### 11. Progress Tracking

Implement progress bars for long-running operations:
```python
from tqdm import tqdm

for document in tqdm(documents, desc="Scanning documents"):
    # Process document
```

#### 12. Logging Strategy

Use structured logging throughout:
```python
logger.info(
    "Quality scan completed",
    total_documents=total,
    issues_found=len(issues),
    critical_count=critical_count,
    output_file=output_path
)
```

### Implementation Order

1. **Phase 1**: Create Paperless API service layer
2. **Phase 2**: Implement Quality Scanner (Option 1)
3. **Phase 3**: Implement Tag Management and Quarterly Processor (Option 2)
4. **Phase 4**: Enhance Email Fetcher (Option 3)
5. **Phase 5**: Create Interactive Menu UI
6. **Phase 6**: Testing and Documentation

### Success Criteria

- [ ] All three menu options functional
- [ ] CSV reports generated with proper formatting
- [ ] Tag unification reduces duplicate tags by >50%
- [ ] OCR quality detection accuracy >95%
- [ ] Email document download supports date ranges
- [ ] Progress indicators for all long operations
- [ ] Comprehensive error handling and recovery
- [ ] German language interface and metadata

## Suggested Agent Chain
Since no specific agents are available in this codebase, this should be implemented as a single development task or broken into the phases listed above.

## Execution Command
```bash
"Implement an interactive menu system for Paperless NGX with three core functionalities: Complete Quality Scan (detecting OCR failures and missing metadata, exporting to CSV), Quarterly Processing (with tag unification and metadata re-extraction), and Email Document Download (with date range selection). Extend the existing Clean Architecture in src/paperless_ngx/ by creating new use cases (quality_scan.py, quarterly_processor.py), services (paperless_api_service.py, tag_management_service.py), and enhancing the CLI module. Use the existing Paperless API at http://192.168.178.76:8010/api with token authentication. Implement comprehensive error handling, progress tracking with tqdm, and German language interface. Generate timestamped CSV reports for quality scans in reports/quality_scans/. Ensure tag housekeeping uses fuzzy matching to unify similar tags before creating new ones."
```

## Pre-Execution Checklist
- [ ] Context verified against project documentation
- [ ] Requirements complete
- [ ] Agent chain logical (N/A - no agents available)
- [ ] Resources available (Paperless API, LLM services)
- [ ] Clean Architecture patterns understood
- [ ] German language requirements considered
- [ ] Error handling strategy defined
- [ ] CSV output format specified