# Paperless NGX API Integration - API Reference

## Table of Contents
- [Core Services](#core-services)
- [Application Use Cases](#application-use-cases)
- [Domain Models](#domain-models)
- [Infrastructure Clients](#infrastructure-clients)
- [Validators](#validators)
- [Exception Handling](#exception-handling)
- [Utility Functions](#utility-functions)

## Core Services

### PaperlessApiService

**Location**: `src/paperless_ngx/application/services/paperless_api_service.py`

Main service for interacting with the Paperless NGX API.

```python
class PaperlessApiService:
    """Enhanced Paperless API service with streaming and validation."""
    
    def __init__(self, api_client: Optional[PaperlessApiClient] = None):
        """
        Initialize service.
        
        Args:
            api_client: Optional API client instance, creates default if None
        """
```

#### Methods

##### get_all_documents()
```python
def get_all_documents(
    self,
    page_size: int = 100,
    ordering: str = "-created"
) -> Generator[Dict[str, Any], None, None]:
    """
    Stream all documents with pagination.
    
    Args:
        page_size: Number of documents per page (default: 100)
        ordering: Sort order (default: "-created" for newest first)
        
    Yields:
        Document dictionaries
        
    Example:
        for doc in service.get_all_documents():
            print(f"Processing: {doc['title']}")
    """
```

##### get_documents_by_date_range()
```python
def get_documents_by_date_range(
    self,
    start_date: datetime,
    end_date: datetime,
    date_field: str = "created"
) -> Generator[Dict[str, Any], None, None]:
    """
    Get documents within date range.
    
    Args:
        start_date: Start of date range
        end_date: End of date range
        date_field: Field to filter on ("created", "added", "modified")
        
    Yields:
        Matching documents
    """
```

##### update_document_metadata()
```python
def update_document_metadata(
    self,
    document_id: int,
    metadata: Dict[str, Any],
    validate: bool = True
) -> Dict[str, Any]:
    """
    Update document with new metadata.
    
    Args:
        document_id: Document ID in Paperless
        metadata: Metadata dictionary with fields:
            - title: str
            - correspondent: int or str (name)
            - document_type: int or str (name)
            - tags: List[int] or List[str] (names)
            - custom_fields: List[Dict]
        validate: Whether to validate metadata before update
        
    Returns:
        Updated document data
        
    Raises:
        ValidationError: If metadata invalid
        PaperlessAPIError: If update fails
    """
```

##### get_or_create_correspondent()
```python
def get_or_create_correspondent(self, name: str) -> int:
    """
    Get existing or create new correspondent.
    
    Args:
        name: Correspondent name (case-insensitive match)
        
    Returns:
        Correspondent ID
        
    Example:
        correspondent_id = service.get_or_create_correspondent("Telekom")
    """
```

##### get_or_create_tag()
```python
def get_or_create_tag(self, name: str) -> int:
    """
    Get existing or create new tag.
    
    Args:
        name: Tag name (case-insensitive match)
        
    Returns:
        Tag ID
    """
```

### QualityAnalyzerService

**Location**: `src/paperless_ngx/application/services/quality_analyzer_service.py`

Service for analyzing document quality and detecting issues.

```python
class QualityAnalyzerService:
    """Service for analyzing document quality and detecting issues."""
    
    def analyze_document(
        self,
        document: Dict[str, Any]
    ) -> List[QualityIssue]:
        """
        Analyze single document for quality issues.
        
        Args:
            document: Document dictionary from Paperless API
            
        Returns:
            List of detected quality issues
            
        Example:
            issues = analyzer.analyze_document(doc)
            for issue in issues:
                print(f"{issue.severity}: {issue.description}")
        """
```

##### scan_all_documents()
```python
def scan_all_documents(
    self,
    progress_callback: Optional[Callable] = None
) -> QualityReport:
    """
    Scan all documents in Paperless for quality issues.
    
    Args:
        progress_callback: Optional callback for progress updates
        
    Returns:
        Comprehensive quality report
        
    Example:
        report = analyzer.scan_all_documents(
            progress_callback=lambda x: print(f"Progress: {x}%")
        )
    """
```

### EmailFetcherService

**Location**: `src/paperless_ngx/application/services/email_fetcher_service.py`

Service for fetching documents from email accounts.

```python
class EmailFetcherService:
    """Service for fetching attachments from multiple email accounts."""
    
    def fetch_all_accounts(
        self,
        since_date: Optional[datetime] = None,
        dry_run: bool = False
    ) -> Dict[str, List[EmailAttachment]]:
        """
        Fetch attachments from all configured accounts.
        
        Args:
            since_date: Only fetch emails after this date
            dry_run: If True, don't download, just list
            
        Returns:
            Dictionary mapping account names to attachments
        """
```

##### fetch_account()
```python
def fetch_account(
    self,
    account_name: str,
    since_date: Optional[datetime] = None,
    dry_run: bool = False
) -> List[EmailAttachment]:
    """
    Fetch attachments from specific account.
    
    Args:
        account_name: Name of email account ("Gmail Account 1", etc.)
        since_date: Only fetch emails after this date
        dry_run: If True, don't download, just list
        
    Returns:
        List of fetched attachments
    """
```

### ReportGeneratorService

**Location**: `src/paperless_ngx/application/services/report_generator_service.py`

Service for generating various reports.

```python
class ReportGeneratorService:
    """Service for generating processing reports."""
    
    def generate_quality_report(
        self,
        quality_data: QualityReport,
        output_format: str = "csv"
    ) -> Path:
        """
        Generate quality scan report.
        
        Args:
            quality_data: Quality report data
            output_format: "csv", "json", or "html"
            
        Returns:
            Path to generated report file
        """
```

## Application Use Cases

### MetadataExtractionUseCase

**Location**: `src/paperless_ngx/application/use_cases/metadata_extraction.py`

Main use case for extracting and enriching document metadata using LLMs.

```python
class MetadataExtractionUseCase:
    """Use case for extracting metadata from documents."""
    
    def extract_metadata(
        self,
        ocr_text: str,
        filename: Optional[str] = None,
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        Extract metadata from OCR text using LLM.
        
        Args:
            ocr_text: OCR text from document
            filename: Optional original filename for context
            validate: Whether to validate extracted metadata
            
        Returns:
            Metadata dictionary:
                - correspondent: str
                - document_type: str
                - tags: List[str]
                - title: str
                - description: str
                - date: str (ISO format)
                
        Example:
            metadata = use_case.extract_metadata(
                ocr_text="Invoice from Telekom...",
                filename="2025-01-15_scan.pdf"
            )
        """
```

### AttachmentProcessor

**Location**: `src/paperless_ngx/application/use_cases/attachment_processor.py`

Use case for processing email attachments.

```python
class AttachmentProcessor:
    """Process email attachments and upload to Paperless."""
    
    def process_attachment(
        self,
        attachment: EmailAttachment,
        extract_metadata: bool = True
    ) -> ProcessedAttachment:
        """
        Process single email attachment.
        
        Args:
            attachment: Email attachment object
            extract_metadata: Whether to extract metadata using LLM
            
        Returns:
            ProcessedAttachment with status and metadata
        """
```

## Domain Models

### Tag Models

**Location**: `src/paperless_ngx/domain/models/tag_models.py`

#### Tag
```python
@dataclass
class Tag:
    """Represents a tag in the system."""
    id: int
    name: str
    slug: str
    color: Optional[str] = None
    match: Optional[str] = None
    matching_algorithm: Optional[int] = None
    is_inbox_tag: bool = False
    document_count: int = 0
    
    def normalize(self) -> str:
        """Get normalized version of tag name."""
```

#### TagSimilarity
```python
@dataclass
class TagSimilarity:
    """Represents similarity between two tags."""
    tag1: Tag
    tag2: Tag
    similarity_score: float  # 0.0 to 1.0
    method: SimilarityMethod
    should_merge: bool
    recommended_name: str
```

#### TagAnalysisResult
```python
@dataclass
class TagAnalysisResult:
    """Complete tag analysis result."""
    total_tags: int
    duplicate_clusters: List[TagCluster]
    merge_recommendations: List[TagMergeRecommendation]
    analysis_timestamp: datetime
    estimated_reduction: int
```

### Processing Report Models

**Location**: `src/paperless_ngx/domain/models/processing_report.py`

#### DocumentProcessingResult
```python
@dataclass
class DocumentProcessingResult:
    """Result of processing a single document."""
    document_id: int
    title: str
    status: ProcessingStatus
    phase_completed: ProcessingPhase
    processing_time: float
    metadata_extracted: Optional[Dict[str, Any]] = None
    validation_passed: bool = False
    errors: List[ProcessingError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
```

#### BatchProcessingResult
```python
@dataclass
class BatchProcessingResult:
    """Result of processing multiple documents."""
    batch_id: str
    start_time: datetime
    end_time: Optional[datetime]
    total_documents: int
    processed_count: int
    success_count: int
    failure_count: int
    documents: List[DocumentProcessingResult]
```

#### QualityReport
```python
@dataclass
class QualityReport:
    """Comprehensive quality analysis report."""
    scan_date: datetime
    total_documents: int
    documents_with_issues: int
    critical_issues: List[QualityIssue]
    warnings: List[QualityIssue]
    info_issues: List[QualityIssue]
    ocr_statistics: Dict[str, int]
    metadata_statistics: Dict[str, int]
```

## Infrastructure Clients

### PaperlessApiClient

**Location**: `src/paperless_ngx/infrastructure/paperless/api_client.py`

Low-level client for Paperless NGX API.

```python
class PaperlessApiClient:
    """Low-level client for Paperless NGX REST API."""
    
    def __init__(
        self,
        base_url: str,
        api_token: str,
        timeout: int = 30
    ):
        """
        Initialize API client.
        
        Args:
            base_url: Paperless API base URL
            api_token: API authentication token
            timeout: Request timeout in seconds
        """
```

#### Core Methods
```python
def get_documents(
    self,
    page: int = 1,
    page_size: int = 100,
    **filters
) -> Dict[str, Any]:
    """Get paginated document list."""

def get_document(self, document_id: int) -> Dict[str, Any]:
    """Get single document by ID."""

def update_document(
    self,
    document_id: int,
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """Update document metadata."""

def create_correspondent(self, name: str) -> Dict[str, Any]:
    """Create new correspondent."""

def create_tag(self, name: str) -> Dict[str, Any]:
    """Create new tag."""
```

### LiteLLMClient

**Location**: `src/paperless_ngx/infrastructure/llm/litellm_client.py`

Client for LLM interactions with Ollama/OpenAI.

```python
class LiteLLMClient:
    """Unified client for multiple LLM providers."""
    
    def complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Get completion from LLM.
        
        Args:
            prompt: Input prompt
            model: Model to use (default: configured model)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum response tokens
            
        Returns:
            Model response text
            
        Example:
            response = client.complete(
                "Extract metadata from: Invoice #123...",
                temperature=0.3
            )
        """
```

### EmailClient

**Location**: `src/paperless_ngx/infrastructure/email/email_client.py`

IMAP client for email operations.

```python
class IMAPEmailClient:
    """IMAP client for fetching emails and attachments."""
    
    def connect(self) -> None:
        """Establish connection to email server."""
    
    def fetch_messages(
        self,
        folder: str = "INBOX",
        since_date: Optional[datetime] = None,
        unseen_only: bool = True
    ) -> List[EmailMessage]:
        """Fetch email messages."""
    
    def download_attachments(
        self,
        message: EmailMessage,
        output_dir: Path
    ) -> List[EmailAttachment]:
        """Download attachments from message."""
```

## Validators

### OCRValidator

**Location**: `src/paperless_ngx/domain/validators/ocr_validator.py`

```python
class OCRValidator:
    """Validator for OCR text quality."""
    
    def validate_ocr_text(
        self,
        text: str,
        min_length: int = 50
    ) -> ValidationResult:
        """
        Validate OCR text quality.
        
        Args:
            text: OCR text to validate
            min_length: Minimum acceptable length
            
        Returns:
            ValidationResult with status and issues
        """
```

### MetadataValidator

**Location**: `src/paperless_ngx/domain/validators/metadata_validator.py`

```python
class MetadataValidator:
    """Validator for document metadata."""
    
    def validate_metadata(
        self,
        metadata: Dict[str, Any],
        strict: bool = False
    ) -> ValidationResult:
        """
        Validate document metadata.
        
        Args:
            metadata: Metadata dictionary to validate
            strict: If True, apply strict business rules
            
        Returns:
            ValidationResult with status and corrections
        """
    
    def validate_correspondent(
        self,
        correspondent: str,
        ocr_text: str
    ) -> bool:
        """
        Validate correspondent against business rules.
        
        Args:
            correspondent: Proposed correspondent name
            ocr_text: Document OCR text for context
            
        Returns:
            True if valid, False if violates rules
        """
```

## Exception Handling

### Custom Exceptions

**Location**: `src/paperless_ngx/domain/exceptions/custom_exceptions.py`

#### Base Exception
```python
class BaseApplicationException(Exception):
    """Base exception for all application errors."""
    error_code: ErrorCode
    message: str
    details: Optional[Dict[str, Any]]
    retry_after: Optional[int]
```

#### API Exceptions
```python
class PaperlessAPIError(APIError):
    """Paperless API specific error."""

class PaperlessAuthenticationError(APIAuthenticationError):
    """Authentication failed with Paperless."""

class PaperlessConnectionError(APIConnectionError):
    """Cannot connect to Paperless API."""

class PaperlessRateLimitError(APIRateLimitError):
    """Rate limit exceeded."""
```

#### LLM Exceptions
```python
class LLMConnectionError(LLMError):
    """Cannot connect to LLM service."""

class LLMInvalidResponseError(LLMError):
    """LLM returned invalid/unparseable response."""

class LLMAllProvidersFailed(LLMError):
    """All LLM providers failed."""
```

#### Business Rule Exceptions
```python
class RecipientAsSenderError(BusinessRuleViolation):
    """Daniel/EBN incorrectly set as sender."""
```

### Exception Handler

```python
class ExceptionHandler:
    """Centralized exception handling."""
    
    @staticmethod
    def handle_api_error(
        error: Exception,
        retry_count: int = 0
    ) -> Optional[Any]:
        """
        Handle API errors with retry logic.
        
        Args:
            error: Exception to handle
            retry_count: Current retry attempt
            
        Returns:
            Recovery result or None
        """
```

## Utility Functions

### Filename Utilities

**Location**: `src/paperless_ngx/domain/utilities/filename_utils.py`

```python
def generate_filename(
    date: str,
    correspondent: str,
    document_type: str
) -> str:
    """
    Generate standardized filename.
    
    Args:
        date: Date in ISO format
        correspondent: Sender/correspondent name
        document_type: Type of document
        
    Returns:
        Formatted filename: "YYYY-MM-DD_Correspondent_Type.pdf"
        
    Example:
        filename = generate_filename(
            "2025-01-15",
            "Telekom",
            "Rechnung"
        )
        # Returns: "2025-01-15_Telekom_Rechnung.pdf"
    """

def sanitize_filename(filename: str) -> str:
    """Remove invalid characters from filename."""

def extract_date_from_filename(filename: str) -> Optional[str]:
    """Extract date from standardized filename."""
```

### Date Utilities

```python
def get_quarter_range(
    year: int,
    quarter: int
) -> Tuple[datetime, datetime]:
    """
    Get date range for quarter.
    
    Args:
        year: Year (e.g., 2025)
        quarter: Quarter number (1-4)
        
    Returns:
        Tuple of (start_date, end_date)
    """

def get_last_quarter() -> Tuple[int, int]:
    """Get last completed quarter as (year, quarter)."""
```

## Configuration

### Settings

**Location**: `src/paperless_ngx/infrastructure/config/settings.py`

```python
class Settings(BaseSettings):
    """Application settings from environment."""
    
    # Paperless API
    paperless_api_url: str
    paperless_api_token: str
    
    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_timeout: int = 120
    
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    
    # Processing
    min_ocr_text_length: int = 50
    tag_similarity_threshold: float = 0.85
    quarterly_processing_batch_size: int = 10
    
    class Config:
        env_file = ".env"
```

## Usage Examples

### Complete Document Processing Pipeline

```python
from paperless_ngx.application.services import PaperlessApiService
from paperless_ngx.application.use_cases import MetadataExtractionUseCase
from paperless_ngx.domain.validators import MetadataValidator

# Initialize services
api_service = PaperlessApiService()
metadata_extractor = MetadataExtractionUseCase()
validator = MetadataValidator()

# Process document
document = api_service.get_document(123)
ocr_text = document.get("content") or document.get("ocr", "")

# Extract metadata
metadata = metadata_extractor.extract_metadata(
    ocr_text=ocr_text,
    filename=document.get("original_filename")
)

# Validate
validation_result = validator.validate_metadata(metadata)
if not validation_result.is_valid:
    print(f"Validation issues: {validation_result.issues}")
    metadata = validation_result.corrected_metadata

# Update document
updated = api_service.update_document_metadata(
    document_id=123,
    metadata=metadata
)
```

### Batch Processing with Progress

```python
from paperless_ngx.application.services import PaperlessApiService
from tqdm import tqdm

service = PaperlessApiService()

# Get all documents
documents = list(service.get_all_documents())

# Process with progress bar
for doc in tqdm(documents, desc="Processing documents"):
    try:
        # Process document
        result = process_document(doc)
    except Exception as e:
        logger.error(f"Failed to process {doc['id']}: {e}")
        continue
```

### Tag Analysis and Merging

```python
from paperless_ngx.domain.models import TagAnalysisResult
from paperless_ngx.application.services import PaperlessApiService

service = PaperlessApiService()

# Analyze tags
analysis = service.analyze_tags(
    similarity_threshold=0.85,
    merge_strategy="conservative"
)

# Review recommendations
for recommendation in analysis.merge_recommendations:
    print(f"Merge: {recommendation.tags_to_merge} -> {recommendation.target_name}")
    if input("Approve? (y/n): ").lower() == 'y':
        service.merge_tags(recommendation)
```

---

*Last Updated: January 2025*
*Version: 1.0.0*