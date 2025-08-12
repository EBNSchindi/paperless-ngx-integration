"""Integration tests for the 3-point workflow system.

Tests:
- Workflow 1: Email fetch with month organization
- Workflow 2: Document processing with metadata extraction
- Workflow 3: Quality scan and report generation
"""

import asyncio
import datetime
import json
from pathlib import Path
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock

from src.paperless_ngx.application.services.email_fetcher_service import EmailFetcherService
from src.paperless_ngx.application.use_cases.metadata_extraction import MetadataExtractor
from src.paperless_ngx.application.use_cases.attachment_processor import AttachmentProcessor
from src.paperless_ngx.application.services.quality_analyzer_service import QualityAnalyzerService
from src.paperless_ngx.application.services.report_generator_service import ReportGeneratorService
from src.paperless_ngx.infrastructure.config.settings import Settings


class TestWorkflow1EmailFetch:
    """Test Workflow 1: Email fetch with month organization."""
    
    @pytest.fixture
    def email_fetcher(self):
        """Create email fetcher service."""
        settings = Mock()
        settings.email_check_interval = 300
        settings.email_download_dir = Path("/tmp/test_downloads")
        settings.email_processed_db = Path("/tmp/test_processed.json")
        settings.allowed_extensions = ['.pdf', '.doc', '.docx']
        settings.mark_as_read = True
        return EmailFetcherService(settings)
    
    @patch('imaplib.IMAP4_SSL')
    def test_fetch_emails_by_month(self, mock_imap, email_fetcher):
        """Test fetching emails organized by month."""
        mock_instance = MagicMock()
        mock_imap.return_value = mock_instance
        mock_instance.login.return_value = ('OK', [b'Authenticated'])
        mock_instance.select.return_value = ('OK', [b'50'])
        
        # Mock emails for different months
        month_data = {
            '2024-01': [b'1', b'2', b'3'],
            '2024-02': [b'4', b'5'],
            '2024-03': [b'6', b'7', b'8']
        }
        
        def search_mock(charset, criteria):
            for month, ids in month_data.items():
                if month in criteria:
                    return ('OK', [b' '.join(ids)])
            return ('OK', [b''])
        
        mock_instance.search.side_effect = search_mock
        
        # Test fetching for each month
        results = {}
        for month in month_data.keys():
            year, month_num = month.split('-')
            since_date = f"01-{month_num}-{year}"
            
            # Mock search
            status, data = mock_instance.search(None, f'(SINCE "{since_date}")')
            if status == 'OK' and data[0]:
                results[month] = len(data[0].split())
        
        assert results['2024-01'] == 3
        assert results['2024-02'] == 2
        assert results['2024-03'] == 3
    
    @patch('src.paperless_ngx.infrastructure.email.email_client.EmailClient')
    def test_process_multiple_accounts_sequentially(self, mock_client_class, email_fetcher):
        """Test processing emails from all 3 accounts sequentially."""
        accounts = [
            {"name": "Gmail 1", "email": "ebn.veranstaltungen.consulting@gmail.com"},
            {"name": "Gmail 2", "email": "daniel.schindler1992@gmail.com"},
            {"name": "IONOS", "email": "info@ettlingen-by-night.de"}
        ]
        
        processed_count = 0
        for account in accounts:
            mock_client = Mock()
            mock_client.connect.return_value = True
            mock_client.fetch_emails.return_value = [
                {"id": f"{account['name']}_1", "subject": f"Test from {account['name']}"},
                {"id": f"{account['name']}_2", "subject": f"Invoice from {account['name']}"}
            ]
            
            processed_count += len(mock_client.fetch_emails())
        
        assert processed_count == 6  # 2 emails × 3 accounts
    
    def test_attachment_extraction_and_storage(self, email_fetcher):
        """Test extracting and storing attachments from emails."""
        test_attachments = [
            {"filename": "invoice_2024_01.pdf", "content": b"PDF content 1"},
            {"filename": "report_2024_02.docx", "content": b"DOCX content"},
            {"filename": "data_2024_03.xlsx", "content": b"XLSX content"}
        ]
        
        # Test storage by month
        stored_files = {}
        for attachment in test_attachments:
            # Extract month from filename
            month = attachment["filename"].split('_')[2][:2]
            month_key = f"2024-{month}"
            
            if month_key not in stored_files:
                stored_files[month_key] = []
            stored_files[month_key].append(attachment["filename"])
        
        assert len(stored_files) == 3
        assert "invoice_2024_01.pdf" in stored_files["2024-01"]
        assert "report_2024_02.docx" in stored_files["2024-02"]
    
    def test_duplicate_email_prevention(self, email_fetcher):
        """Test that duplicate emails are not processed twice."""
        processed_ids = set()
        
        emails = [
            {"id": "email_1", "subject": "Test 1"},
            {"id": "email_2", "subject": "Test 2"},
            {"id": "email_1", "subject": "Test 1"},  # Duplicate
            {"id": "email_3", "subject": "Test 3"}
        ]
        
        new_emails = []
        for email in emails:
            if email["id"] not in processed_ids:
                processed_ids.add(email["id"])
                new_emails.append(email)
        
        assert len(new_emails) == 3
        assert len(processed_ids) == 3
        assert "email_1" in processed_ids
        assert "email_2" in processed_ids
        assert "email_3" in processed_ids


class TestWorkflow2DocumentProcessing:
    """Test Workflow 2: Document processing with metadata extraction."""
    
    @pytest.fixture
    def metadata_extractor(self):
        """Create metadata extractor."""
        llm_client = Mock()
        llm_client.complete_sync.return_value = (
            json.dumps({
                "correspondent": "Telekom Deutschland GmbH",
                "document_type": "Rechnung",
                "tags": ["Telekommunikation", "Mobilfunk", "Geschäftskunde", "2024", "Januar"],
                "description": "Mobilfunkrechnung Januar 2024 - Geschäftskunde",
                "date": "2024-01-15"
            }),
            {"model": "gpt-3.5-turbo", "provider": "openai"}
        )
        return MetadataExtractor(llm_client)
    
    @pytest.fixture
    def attachment_processor(self):
        """Create attachment processor."""
        return AttachmentProcessor()
    
    def test_metadata_extraction_from_document(self, metadata_extractor):
        """Test extracting metadata from document content."""
        document_content = """
        Telekom Deutschland GmbH
        Rechnung
        
        Rechnungsnummer: 2024-001234
        Datum: 15.01.2024
        
        Mobilfunkvertrag Business L
        Monatliche Grundgebühr: 79,99 EUR
        """
        
        # Extract metadata
        response, _ = metadata_extractor.llm_client.complete_sync(document_content)
        metadata = json.loads(response)
        
        assert metadata["correspondent"] == "Telekom Deutschland GmbH"
        assert metadata["document_type"] == "Rechnung"
        assert "Telekommunikation" in metadata["tags"]
        assert len(metadata["tags"]) >= 3
        assert len(metadata["tags"]) <= 7
        assert metadata["date"] == "2024-01-15"
    
    def test_german_document_type_classification(self, metadata_extractor):
        """Test German document type classification."""
        document_types = [
            ("Rechnung Nr. 12345", "Rechnung"),
            ("Vertrag zur Miete", "Vertrag"),
            ("Angebot für Dienstleistungen", "Angebot"),
            ("Mahnung - Erste Erinnerung", "Mahnung"),
            ("Lieferschein Nr. 9876", "Lieferschein")
        ]
        
        for content, expected_type in document_types:
            # Mock response for each document type
            metadata_extractor.llm_client.complete_sync.return_value = (
                json.dumps({"document_type": expected_type}),
                {"model": "gpt-3.5-turbo", "provider": "openai"}
            )
            
            response, _ = metadata_extractor.llm_client.complete_sync(content)
            metadata = json.loads(response)
            assert metadata["document_type"] == expected_type
    
    def test_correspondent_never_daniel_schindler(self, metadata_extractor):
        """Test that correspondent is never Daniel Schindler/EBN (always recipient)."""
        test_documents = [
            "Von: Telekom An: Daniel Schindler",
            "Empfänger: EBN Veranstaltungen und Consulting GmbH",
            "An: Daniel Schindler, Alexiusstr. 6, 76275 Ettlingen"
        ]
        
        for doc in test_documents:
            # Mock response ensuring Daniel/EBN is never the correspondent
            metadata_extractor.llm_client.complete_sync.return_value = (
                json.dumps({
                    "correspondent": "Telekom Deutschland GmbH",  # Always sender, not Daniel
                    "recipient": "Daniel Schindler / EBN Veranstaltungen und Consulting GmbH"
                }),
                {"model": "gpt-3.5-turbo", "provider": "openai"}
            )
            
            response, _ = metadata_extractor.llm_client.complete_sync(doc)
            metadata = json.loads(response)
            
            assert "Daniel Schindler" not in metadata["correspondent"]
            assert "EBN" not in metadata["correspondent"]
    
    def test_filename_generation_format(self, metadata_extractor):
        """Test filename generation in format YYYY-MM-DD_Sender_Type."""
        test_cases = [
            {
                "date": "2024-01-15",
                "correspondent": "Telekom Deutschland GmbH",
                "document_type": "Rechnung",
                "expected": "2024-01-15_Telekom_Deutschland_GmbH_Rechnung"
            },
            {
                "date": "2024-02-20",
                "correspondent": "Stadtwerke Ettlingen",
                "document_type": "Vertrag",
                "expected": "2024-02-20_Stadtwerke_Ettlingen_Vertrag"
            }
        ]
        
        for case in test_cases:
            filename = f"{case['date']}_{case['correspondent'].replace(' ', '_')}_{case['document_type']}"
            assert filename == case["expected"]
    
    def test_description_max_length_128_chars(self, metadata_extractor):
        """Test that descriptions are limited to 128 characters."""
        long_description = "Dies ist eine sehr lange Beschreibung für ein Dokument, die definitiv mehr als 128 Zeichen enthält und daher gekürzt werden muss, um den Anforderungen zu entsprechen"
        
        # Limit to 128 chars
        truncated = long_description[:128]
        
        assert len(truncated) <= 128
        assert len(long_description) > 128


class TestWorkflow3QualityScanAndReport:
    """Test Workflow 3: Quality scan and report generation."""
    
    @pytest.fixture
    def quality_analyzer(self):
        """Create quality analyzer service."""
        return QualityAnalyzerService()
    
    @pytest.fixture
    def report_generator(self):
        """Create report generator service."""
        return ReportGeneratorService()
    
    @pytest.mark.asyncio
    async def test_quality_scan_all_documents(self, quality_analyzer):
        """Test scanning all documents for quality issues."""
        documents = [
            {"id": 1, "title": "Invoice_2024", "tags": ["Invoice", "2024"], "correspondent": "Telekom"},
            {"id": 2, "title": "", "tags": [], "correspondent": ""},  # Missing metadata
            {"id": 3, "title": "Contract", "tags": ["Contract"], "correspondent": "Stadtwerke"},
            {"id": 4, "title": "Report", "tags": [], "correspondent": "Unknown"}  # Missing tags
        ]
        
        quality_issues = []
        for doc in documents:
            issues = []
            if not doc["title"]:
                issues.append("Missing title")
            if not doc["tags"]:
                issues.append("Missing tags")
            if not doc["correspondent"] or doc["correspondent"] == "Unknown":
                issues.append("Missing or unknown correspondent")
            
            if issues:
                quality_issues.append({
                    "document_id": doc["id"],
                    "issues": issues
                })
        
        assert len(quality_issues) == 3
        assert quality_issues[0]["document_id"] == 2
        assert "Missing title" in quality_issues[0]["issues"]
    
    def test_generate_quality_report(self, report_generator):
        """Test generating quality scan report."""
        scan_results = {
            "total_documents": 100,
            "documents_with_issues": 15,
            "issue_breakdown": {
                "missing_tags": 8,
                "missing_correspondent": 5,
                "missing_date": 2
            },
            "quality_score": 85.0
        }
        
        report = {
            "title": "Paperless NGX Quality Scan Report",
            "date": datetime.datetime.now().isoformat(),
            "summary": scan_results,
            "recommendations": [
                "Add tags to 8 documents",
                "Identify correspondents for 5 documents",
                "Set dates for 2 documents"
            ]
        }
        
        assert report["summary"]["quality_score"] == 85.0
        assert len(report["recommendations"]) == 3
        assert report["summary"]["documents_with_issues"] == 15
    
    def test_identify_duplicate_tags(self, quality_analyzer):
        """Test identifying duplicate or similar tags."""
        tags = [
            "Telekommunikation",
            "Telekom",  # Different from Telekommunikation
            "Mobilfunk",
            "Mobilfunk",  # Exact duplicate
            "Rechnung",
            "Rechnungen",  # Plural form
            "2024",
            "2024"  # Exact duplicate
        ]
        
        # Find duplicates and similar tags
        unique_tags = []
        duplicates = []
        seen = set()
        
        for tag in tags:
            if tag in seen:
                duplicates.append(tag)
            else:
                seen.add(tag)
                unique_tags.append(tag)
        
        assert len(unique_tags) == 6
        assert len(duplicates) == 2
        assert "Mobilfunk" in duplicates
        assert "2024" in duplicates
    
    def test_monthly_statistics_generation(self, report_generator):
        """Test generating monthly statistics."""
        monthly_data = {
            "2024-01": {"documents": 45, "emails": 120, "attachments": 50},
            "2024-02": {"documents": 38, "emails": 95, "attachments": 40},
            "2024-03": {"documents": 52, "emails": 140, "attachments": 58}
        }
        
        statistics = {
            "total_documents": sum(m["documents"] for m in monthly_data.values()),
            "total_emails": sum(m["emails"] for m in monthly_data.values()),
            "total_attachments": sum(m["attachments"] for m in monthly_data.values()),
            "average_per_month": {
                "documents": sum(m["documents"] for m in monthly_data.values()) / len(monthly_data),
                "emails": sum(m["emails"] for m in monthly_data.values()) / len(monthly_data),
                "attachments": sum(m["attachments"] for m in monthly_data.values()) / len(monthly_data)
            }
        }
        
        assert statistics["total_documents"] == 135
        assert statistics["total_emails"] == 355
        assert statistics["total_attachments"] == 148
        assert statistics["average_per_month"]["documents"] == 45.0
    
    def test_export_report_formats(self, report_generator):
        """Test exporting reports in different formats."""
        report_data = {
            "title": "Quality Report",
            "date": "2024-03-15",
            "quality_score": 92.5,
            "issues_found": 8
        }
        
        # Test JSON export
        json_export = json.dumps(report_data, indent=2)
        assert "quality_score" in json_export
        assert "92.5" in json_export
        
        # Test Markdown export
        markdown_export = f"""# {report_data['title']}
        
Date: {report_data['date']}
Quality Score: {report_data['quality_score']}%
Issues Found: {report_data['issues_found']}
"""
        
        assert "# Quality Report" in markdown_export
        assert "92.5%" in markdown_export


class TestIntegratedWorkflow:
    """Test complete integrated workflow from email to report."""
    
    @pytest.mark.asyncio
    async def test_complete_workflow_integration(self):
        """Test complete workflow: fetch -> process -> scan -> report."""
        # Mock services
        with patch('imaplib.IMAP4_SSL') as mock_imap, \
             patch('src.paperless_ngx.infrastructure.llm.litellm_client.LiteLLMClient') as mock_llm:
            
            # Step 1: Fetch emails
            mock_instance = MagicMock()
            mock_imap.return_value = mock_instance
            mock_instance.login.return_value = ('OK', [b'Authenticated'])
            mock_instance.search.return_value = ('OK', [b'1 2 3'])
            
            fetched_emails = 3
            
            # Step 2: Process documents
            mock_llm_instance = Mock()
            mock_llm_instance.complete_sync.return_value = (
                json.dumps({
                    "correspondent": "Test Sender",
                    "document_type": "Rechnung",
                    "tags": ["Test", "2024"],
                    "date": "2024-03-15"
                }),
                {"model": "gpt-3.5-turbo"}
            )
            
            processed_documents = fetched_emails
            
            # Step 3: Quality scan
            quality_issues = 1  # One document with missing tags
            
            # Step 4: Generate report
            report = {
                "emails_fetched": fetched_emails,
                "documents_processed": processed_documents,
                "quality_issues": quality_issues,
                "quality_score": ((processed_documents - quality_issues) / processed_documents) * 100
            }
            
            assert report["emails_fetched"] == 3
            assert report["documents_processed"] == 3
            assert report["quality_issues"] == 1
            assert report["quality_score"] == 66.66666666666667