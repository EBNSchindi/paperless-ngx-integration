"""Pytest configuration and shared fixtures for test suite."""

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.paperless_ngx.domain.models.processing_report import (
    DocumentProcessingReport,
    ProcessingStatus,
    QualityIssue,
    QualityReport,
)
from src.paperless_ngx.domain.models.tag_models import (
    Tag,
    TagCluster,
    TagMergeRecommendation,
    TagSimilarity,
)
from src.paperless_ngx.infrastructure.config.settings import Settings


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings for testing."""
    settings = Mock(spec=Settings)
    settings.paperless_api_url = "http://test.example.com/api"
    settings.paperless_api_token = "test-token-123"
    settings.llm_provider = "ollama"
    settings.ollama_base_url = "http://localhost:11434"
    settings.ollama_model = "llama3.1:8b"
    settings.openai_api_key = "test-openai-key"
    settings.openai_model = "gpt-3.5-turbo"
    settings.max_retries = 3
    settings.timeout = 30
    settings.batch_size = 100
    settings.log_level = "INFO"
    settings.log_file = "test.log"
    return settings


@pytest.fixture
def mock_api_client():
    """Create a mock PaperlessApiClient."""
    client = MagicMock()
    client.base_url = "http://test.example.com/api"
    client.session = MagicMock()
    
    # Default responses
    client.get_documents.return_value = []
    client.get_correspondents.return_value = []
    client.get_tags.return_value = []
    client.get_document_types.return_value = []
    client.update_document.return_value = {"id": 1, "title": "Updated"}
    client.create_tag.return_value = {"id": 1, "name": "New Tag"}
    client.create_correspondent.return_value = {"id": 1, "name": "New Correspondent"}
    client.create_document_type.return_value = {"id": 1, "name": "Rechnung"}
    
    return client


@pytest.fixture
def sample_documents() -> List[Dict[str, Any]]:
    """Create sample document data for testing."""
    return [
        {
            "id": 1,
            "title": "Rechnung Amazon 2024",
            "correspondent": "Amazon EU S.a.r.l.",
            "correspondent_name": "Amazon EU S.a.r.l.",
            "document_type": "Rechnung",
            "document_type_name": "Rechnung",
            "tags": ["Online-Shopping", "Elektronik", "2024"],
            "description": "Bestellung von Elektronikartikeln",
            "created": "2024-03-15T10:30:00Z",
            "modified": "2024-03-15T10:35:00Z",
            "added": "2024-03-15T10:32:00Z",
            "original_filename": "2024-03-15_Amazon_Rechnung.pdf",
            "content": "Dies ist eine Rechnung von Amazon EU S.a.r.l. für Ihre Bestellung vom 14. März 2024. Bestellnummer: 123-4567890. Artikel: USB-Kabel, Maus, Tastatur. Gesamtbetrag: 89,99 EUR. Lieferadresse: Daniel Schindler, Alexiusstr. 6, 76275 Ettlingen. Vielen Dank für Ihren Einkauf.",
            "ocr": None,
            "ocr_confidence": 0.95
        },
        {
            "id": 2,
            "title": "Vertrag Mobilfunk",
            "correspondent": "Telekom Deutschland GmbH",
            "correspondent_name": "Telekom Deutschland GmbH",
            "document_type": "Vertrag",
            "document_type_name": "Vertrag",
            "tags": ["Mobilfunk", "Telekommunikation", "Vertrag", "2024"],
            "description": "Mobilfunkvertrag mit 24 Monaten Laufzeit",
            "created": "2024-02-01T14:00:00Z",
            "modified": "2024-02-01T14:10:00Z",
            "added": "2024-02-01T14:05:00Z",
            "original_filename": "2024-02-01_Telekom_Vertrag.pdf",
            "content": "Mobilfunkvertrag zwischen Telekom Deutschland GmbH und Daniel Schindler. Vertragsbeginn: 01.02.2024. Laufzeit: 24 Monate. Tarif: MagentaMobil L. Monatliche Grundgebühr: 59,95 EUR. Inklusivleistungen: Unbegrenzt Datenvolumen, Telefonie und SMS in alle deutschen Netze.",
            "ocr": None,
            "ocr_confidence": 0.92
        },
        {
            "id": 3,
            "title": "scan_001",  # Bad title
            "correspondent": "Daniel Schindler",  # Invalid - Daniel is always recipient
            "correspondent_name": "Daniel Schindler",
            "document_type": "Unknown",  # Invalid type
            "tags": ["a"],  # Too few tags
            "description": "x" * 200,  # Too long description
            "created": "2024-01-15T09:00:00Z",
            "modified": "2024-01-14T09:00:00Z",  # Modified before created
            "added": "2024-01-15T09:05:00Z",
            "original_filename": "scan_001.pdf",
            "content": "Short",  # OCR too short
            "ocr": None,
            "ocr_confidence": 0.3  # Low confidence
        },
        {
            "id": 4,
            "title": "Meeting Notes",  # English title
            "correspondent": None,  # Missing correspondent
            "correspondent_name": None,
            "document_type": None,  # Missing document type
            "tags": [],  # No tags
            "description": None,
            "created": "not-a-date",  # Invalid date format
            "modified": "2024-01-10T10:00:00Z",
            "added": "2024-01-10T10:05:00Z",
            "original_filename": "notes.txt",
            "content": "This is an English document with meeting notes from yesterday's discussion about the project timeline and deliverables.",
            "ocr": None,
            "ocr_confidence": None
        },
        {
            "id": 5,
            "title": "Lieferschein DHL",
            "correspondent": "DHL Paket GmbH",
            "correspondent_name": "DHL Paket GmbH",
            "document_type": "Lieferschein",
            "document_type_name": "Lieferschein",
            "tags": ["Versand", "Logistik", "DHL", "Paket", "2024", "Express"],  # Good tags
            "description": "Express-Lieferung Sendungsnummer 12345",
            "created": "2024-03-20T08:00:00Z",
            "modified": "2024-03-20T08:05:00Z",
            "added": "2024-03-20T08:02:00Z",
            "original_filename": "2024-03-20_DHL_Lieferschein.pdf",
            "content": "",  # Empty OCR
            "ocr": "",
            "ocr_confidence": 0.0
        },
        {
            "id": 6,
            "title": "12345",  # Numeric title
            "correspondent": "EBN Veranstaltungen",  # Invalid - EBN is always recipient
            "correspondent_name": "EBN Veranstaltungen",
            "document_type": "Brief",
            "document_type_name": "Brief",
            "tags": ["tag1", "tag1", "TAG1"],  # Duplicate tags
            "description": "Test",
            "created": "2024-03-25T12:00:00Z",
            "modified": "2024-03-25T12:10:00Z",
            "added": "2024-03-25T12:05:00Z",
            "original_filename": "document.pdf",
            "content": "@@@@@@@@@@" * 100,  # OCR with excessive special characters
            "ocr": None,
            "ocr_confidence": 0.5
        }
    ]


@pytest.fixture
def sample_quality_report() -> QualityReport:
    """Create a sample quality report for testing."""
    return QualityReport(
        total_documents=100,
        documents_with_issues=25,
        ocr_failures=5,
        missing_metadata=10,
        duplicate_candidates=3,
        tag_issues=8,
        common_issues=[
            QualityIssue(
                issue_type="ocr_too_short",
                severity="high",
                count=5,
                affected_documents=[3, 5, 7, 9, 11],
                description="OCR text shorter than 50 characters",
                recommendation="Re-scan documents or perform manual OCR"
            ),
            QualityIssue(
                issue_type="missing_tags",
                severity="medium",
                count=10,
                affected_documents=list(range(20, 30)),
                description="Documents have fewer than 3 tags",
                recommendation="Add relevant tags for better organization"
            )
        ],
        recommendations=[
            "Re-process 5 documents with failed OCR",
            "Add missing metadata to 10 documents",
            "Review 3 potential duplicate documents",
            "Standardize tag naming conventions"
        ],
        quality_score=0.75,
        scan_timestamp=datetime.now(),
        scan_duration_seconds=45.3
    )


@pytest.fixture
def temp_output_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_tags() -> List[Tag]:
    """Create sample tag data for testing."""
    return [
        Tag(id=1, name="Rechnung", slug="rechnung", document_count=50),
        Tag(id=2, name="Rechnungen", slug="rechnungen", document_count=5),  # Similar to Rechnung
        Tag(id=3, name="Invoice", slug="invoice", document_count=3),  # English version
        Tag(id=4, name="Vertrag", slug="vertrag", document_count=30),
        Tag(id=5, name="Verträge", slug="vertraege", document_count=2),  # Plural
        Tag(id=6, name="2024", slug="2024", document_count=100),
        Tag(id=7, name="2023", slug="2023", document_count=80),
        Tag(id=8, name="Amazon", slug="amazon", document_count=15),
        Tag(id=9, name="amazon", slug="amazon-2", document_count=2),  # Duplicate with different case
        Tag(id=10, name="Brief", slug="brief", document_count=20),
        Tag(id=11, name="Briefe", slug="briefe", document_count=1),  # Plural
        Tag(id=12, name="Steuern", slug="steuern", document_count=25),
        Tag(id=13, name="Steuer", slug="steuer", document_count=3),  # Singular
        Tag(id=14, name="unused-tag", slug="unused-tag", document_count=0),  # Unused
        Tag(id=15, name="test", slug="test", document_count=1),
    ]


@pytest.fixture
def sample_tag_clusters() -> List[TagCluster]:
    """Create sample tag clusters for testing."""
    return [
        TagCluster(
            primary_tag=Tag(id=1, name="Rechnung", slug="rechnung", document_count=50),
            similar_tags=[
                Tag(id=2, name="Rechnungen", slug="rechnungen", document_count=5),
                Tag(id=3, name="Invoice", slug="invoice", document_count=3)
            ],
            total_documents=58,
            similarity_threshold=0.8
        ),
        TagCluster(
            primary_tag=Tag(id=4, name="Vertrag", slug="vertrag", document_count=30),
            similar_tags=[
                Tag(id=5, name="Verträge", slug="vertraege", document_count=2)
            ],
            total_documents=32,
            similarity_threshold=0.8
        )
    ]


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client for testing."""
    client = MagicMock()
    
    # Default metadata extraction response
    client.extract_metadata.return_value = {
        "title": "Rechnung Amazon März 2024",
        "correspondent": "Amazon EU S.a.r.l.",
        "document_type": "Rechnung",
        "tags": ["Online-Shopping", "Elektronik", "2024", "Amazon", "März"],
        "description": "Rechnung für Elektronikbestellung",
        "created": "2024-03-15"
    }
    
    # Default validation response
    client.validate_metadata.return_value = {
        "is_valid": True,
        "errors": [],
        "corrections": {}
    }
    
    return client


@pytest.fixture
def mock_email_client():
    """Create a mock email client for testing."""
    client = MagicMock()
    client.connect.return_value = None
    client.disconnect.return_value = None
    client.fetch_unread.return_value = []
    client.mark_as_read.return_value = None
    client.download_attachment.return_value = b"PDF content here"
    return client


@pytest.fixture
def processing_report() -> DocumentProcessingReport:
    """Create a sample processing report."""
    report = DocumentProcessingReport()
    
    # Add some processed documents
    report.add_document(1, ProcessingStatus.SUCCESS, metadata={
        "title": "Test Document 1",
        "tags": ["test", "success"]
    })
    report.add_document(2, ProcessingStatus.FAILED, error="OCR extraction failed")
    report.add_document(3, ProcessingStatus.SKIPPED, reason="Already processed")
    report.add_document(4, ProcessingStatus.SUCCESS, metadata={
        "title": "Test Document 4",
        "tags": ["test", "batch"]
    })
    
    return report


@pytest.fixture
def mock_rapidfuzz():
    """Mock rapidfuzz for testing without the actual library."""
    with patch("src.paperless_ngx.domain.validators.metadata_validator.process") as mock_process:
        with patch("src.paperless_ngx.domain.validators.metadata_validator.fuzz") as mock_fuzz:
            mock_process.extract.return_value = [
                ("Rechnung", 95, 0),
                ("Quittung", 70, 1),
                ("Vertrag", 60, 2)
            ]
            mock_fuzz.ratio.return_value = 85
            yield mock_process, mock_fuzz


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset any singleton instances between tests."""
    # Add any singleton resets here if needed
    yield


@pytest.fixture
def german_text_sample() -> str:
    """Sample German text for language detection testing."""
    return """
    Dies ist ein Beispieltext auf Deutsch. Der Text enthält verschiedene 
    deutsche Wörter und Sätze, die zur Spracherkennung verwendet werden können.
    Mit diesem Text können wir überprüfen, ob die Spracherkennung korrekt 
    funktioniert und deutsche Texte richtig identifiziert werden.
    """


@pytest.fixture
def english_text_sample() -> str:
    """Sample English text for language detection testing."""
    return """
    This is a sample text in English. The text contains various English 
    words and sentences that can be used for language detection. With this 
    text we can verify that the language detection works correctly and 
    properly identifies English texts.
    """


@pytest.fixture
def ocr_error_text_sample() -> str:
    """Sample text with common OCR errors."""
    return """
    Th1s t3xt c0nta1ns numer0us 0CR err0rs !!!!!!! 
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    12345678901234567890
    &&&&&&&&&&&&&&&&&&&&
    iiiiiiiiiiiiiiiiiii
    """


@pytest.fixture
def mock_paperless_api_responses():
    """Mock responses from Paperless API."""
    return {
        "documents": {
            "count": 3,
            "next": None,
            "previous": None,
            "results": [
                {
                    "id": 1,
                    "title": "Test Document",
                    "correspondent": 1,
                    "document_type": 1,
                    "tags": [1, 2, 3]
                }
            ]
        },
        "correspondents": {
            "count": 2,
            "results": [
                {"id": 1, "name": "Amazon EU S.a.r.l."},
                {"id": 2, "name": "DHL Paket GmbH"}
            ]
        },
        "tags": {
            "count": 5,
            "results": [
                {"id": 1, "name": "Rechnung"},
                {"id": 2, "name": "2024"},
                {"id": 3, "name": "Online-Shopping"},
                {"id": 4, "name": "Versand"},
                {"id": 5, "name": "Brief"}
            ]
        },
        "document_types": {
            "count": 3,
            "results": [
                {"id": 1, "name": "Rechnung"},
                {"id": 2, "name": "Vertrag"},
                {"id": 3, "name": "Lieferschein"}
            ]
        }
    }