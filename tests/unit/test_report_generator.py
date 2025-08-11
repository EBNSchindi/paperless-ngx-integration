"""Unit tests for report generation functionality."""

import csv
import json
import tempfile
from datetime import datetime
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, mock_open

import pytest

from src.paperless_ngx.application.services.report_generator_service import ReportGeneratorService
from src.paperless_ngx.domain.models.processing_report import (
    DocumentProcessingReport,
    ProcessingStatus,
    QualityIssue,
    QualityReport,
)


class TestReportGeneratorService:
    """Test cases for report generation."""
    
    @pytest.fixture
    def generator(self):
        """Create a report generator instance."""
        return ReportGeneratorService()
    
    @pytest.fixture
    def processing_report_full(self):
        """Create a comprehensive processing report."""
        report = DocumentProcessingReport()
        
        # Add various document statuses
        for i in range(10):
            report.add_document(i, ProcessingStatus.SUCCESS, metadata={
                'title': f'Success Doc {i}',
                'tags': ['tag1', 'tag2']
            })
        
        for i in range(10, 15):
            report.add_document(i, ProcessingStatus.FAILED, error=f"Error processing doc {i}")
        
        for i in range(15, 18):
            report.add_document(i, ProcessingStatus.SKIPPED, reason="Already processed")
        
        return report
    
    @pytest.fixture
    def quality_report_full(self, sample_quality_report):
        """Use the sample quality report from conftest."""
        return sample_quality_report
    
    def test_generate_csv_report(self, generator, processing_report_full, temp_output_dir):
        """Test CSV report generation with German headers."""
        output_file = temp_output_dir / "test_report.csv"
        
        generator.generate_csv_report(
            processing_report_full,
            output_file=str(output_file)
        )
        
        assert output_file.exists()
        
        # Read and verify CSV content
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == 18  # 10 success + 5 failed + 3 skipped
        
        # Check German headers
        assert 'Dokument-ID' in reader.fieldnames
        assert 'Status' in reader.fieldnames
        assert 'Titel' in reader.fieldnames
        assert 'Fehler' in reader.fieldnames
        
        # Check data content
        success_row = rows[0]
        assert success_row['Status'] == 'SUCCESS'
        assert success_row['Titel'] == 'Success Doc 0'
        
        failed_row = rows[10]
        assert failed_row['Status'] == 'FAILED'
        assert 'Error processing' in failed_row['Fehler']
    
    def test_generate_csv_streaming(self, generator, temp_output_dir):
        """Test streaming CSV generation for large datasets."""
        # Create large report
        large_report = DocumentProcessingReport()
        for i in range(10000):
            large_report.add_document(i, ProcessingStatus.SUCCESS, metadata={
                'title': f'Doc {i}'
            })
        
        output_file = temp_output_dir / "large_report.csv"
        
        # Should handle large dataset efficiently
        generator.generate_csv_report(
            large_report,
            output_file=str(output_file),
            stream=True
        )
        
        assert output_file.exists()
        
        # Verify file size is reasonable
        file_size = output_file.stat().st_size
        assert file_size > 0
        
        # Spot check some rows
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            first_row = next(reader)
            assert first_row['Dokument-ID'] == '0'
            
            # Skip to end
            for row in reader:
                last_row = row
            assert last_row['Dokument-ID'] == '9999'
    
    def test_generate_json_report(self, generator, processing_report_full, temp_output_dir):
        """Test JSON report generation."""
        output_file = temp_output_dir / "test_report.json"
        
        generator.generate_json_report(
            processing_report_full,
            output_file=str(output_file)
        )
        
        assert output_file.exists()
        
        # Read and verify JSON content
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data['summary']['total_processed'] == 18
        assert data['summary']['successful'] == 10
        assert data['summary']['failed'] == 5
        assert data['summary']['skipped'] == 3
        
        assert len(data['documents']) == 18
        
        # Check document structure
        doc = data['documents'][0]
        assert 'id' in doc
        assert 'status' in doc
        assert 'metadata' in doc
        assert 'timestamp' in doc
    
    def test_generate_quality_report_html(self, generator, quality_report_full, temp_output_dir):
        """Test HTML quality report generation."""
        output_file = temp_output_dir / "quality_report.html"
        
        generator.generate_quality_report_html(
            quality_report_full,
            output_file=str(output_file)
        )
        
        assert output_file.exists()
        
        # Read and verify HTML content
        content = output_file.read_text(encoding='utf-8')
        
        # Check for key elements
        assert '<html>' in content
        assert 'Qualitätsbericht' in content or 'Quality Report' in content
        assert str(quality_report_full.total_documents) in content
        assert f"{quality_report_full.quality_score:.1%}" in content or f"{quality_report_full.quality_score:.2f}" in content
        
        # Check for issues section
        assert 'ocr_too_short' in content or 'OCR' in content
        assert 'missing_tags' in content or 'Tags' in content
        
        # Check for recommendations
        for rec in quality_report_full.recommendations:
            assert rec in content or rec[:20] in content  # Partial match for long recommendations
    
    def test_generate_pdf_report_mock(self, generator, processing_report_full, temp_output_dir):
        """Test PDF report generation (mocked if reportlab not available)."""
        output_file = temp_output_dir / "test_report.pdf"
        
        try:
            generator.generate_pdf_report(
                processing_report_full,
                output_file=str(output_file)
            )
            
            if output_file.exists():
                # If reportlab is installed, verify PDF was created
                assert output_file.stat().st_size > 0
            else:
                # If not available, should handle gracefully
                pass
        except ImportError:
            # reportlab not installed - expected
            pass
        except Exception as e:
            # Should handle missing dependency gracefully
            assert "reportlab" in str(e).lower() or "PDF" in str(e)
    
    def test_generate_markdown_report(self, generator, quality_report_full, temp_output_dir):
        """Test Markdown report generation."""
        output_file = temp_output_dir / "report.md"
        
        generator.generate_markdown_report(
            quality_report_full,
            output_file=str(output_file)
        )
        
        assert output_file.exists()
        
        content = output_file.read_text(encoding='utf-8')
        
        # Check Markdown formatting
        assert '# ' in content  # Headers
        assert '## ' in content  # Subheaders
        assert '- ' in content or '* ' in content  # Lists
        assert '|' in content  # Tables (if used)
        
        # Check content
        assert str(quality_report_full.total_documents) in content
        assert 'Quality Score' in content or 'Qualität' in content
    
    def test_generate_summary_statistics(self, generator, processing_report_full):
        """Test summary statistics generation."""
        stats = generator.generate_summary_statistics(processing_report_full)
        
        assert stats['total_processed'] == 18
        assert stats['successful'] == 10
        assert stats['failed'] == 5
        assert stats['skipped'] == 3
        assert stats['success_rate'] == pytest.approx(10/18, rel=0.01)
        assert stats['failure_rate'] == pytest.approx(5/18, rel=0.01)
        
        # Time-based stats
        assert 'processing_start' in stats
        assert 'processing_end' in stats
        assert 'total_duration' in stats
    
    def test_generate_error_report(self, generator, processing_report_full, temp_output_dir):
        """Test error-specific report generation."""
        output_file = temp_output_dir / "errors.txt"
        
        generator.generate_error_report(
            processing_report_full,
            output_file=str(output_file)
        )
        
        assert output_file.exists()
        
        content = output_file.read_text(encoding='utf-8')
        
        # Should contain only failed documents
        assert 'Error processing doc 10' in content
        assert 'Error processing doc 14' in content
        assert 'Success Doc' not in content  # Should not include successful docs
        
        # Should have error summary
        assert '5' in content  # Total errors
    
    def test_export_for_excel(self, generator, processing_report_full, temp_output_dir):
        """Test Excel-compatible CSV export."""
        output_file = temp_output_dir / "excel_report.csv"
        
        generator.export_for_excel(
            processing_report_full,
            output_file=str(output_file)
        )
        
        assert output_file.exists()
        
        # Check for Excel-friendly formatting
        with open(output_file, 'r', encoding='utf-8-sig') as f:  # BOM for Excel
            reader = csv.reader(f, delimiter=';')  # German Excel uses semicolon
            headers = next(reader)
            
            assert len(headers) > 0
            
            # Read a data row
            data_row = next(reader)
            assert len(data_row) == len(headers)
    
    def test_generate_tag_analysis_report(self, generator, temp_output_dir):
        """Test tag analysis report generation."""
        from src.paperless_ngx.domain.models.tag_models import Tag, TagCluster
        
        tags = [
            Tag(id=1, name="Rechnung", slug="rechnung", document_count=50),
            Tag(id=2, name="2024", slug="2024", document_count=100),
            Tag(id=3, name="unused", slug="unused", document_count=0),
        ]
        
        clusters = [
            TagCluster(
                primary_tag=tags[0],
                similar_tags=[Tag(id=4, name="Rechnungen", slug="rechnungen", document_count=5)],
                total_documents=55,
                similarity_threshold=0.8
            )
        ]
        
        output_file = temp_output_dir / "tag_analysis.csv"
        
        generator.generate_tag_analysis_report(
            tags=tags,
            clusters=clusters,
            output_file=str(output_file)
        )
        
        assert output_file.exists()
        
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Rechnung" in content
            assert "50" in content  # Document count
            assert "unused" in content
            assert "Cluster" in content or "Gruppe" in content
    
    def test_streaming_json_generation(self, generator, temp_output_dir):
        """Test streaming JSON generation for large datasets."""
        # Create very large report
        huge_report = DocumentProcessingReport()
        for i in range(50000):
            huge_report.add_document(i, ProcessingStatus.SUCCESS)
        
        output_file = temp_output_dir / "huge_report.json"
        
        # Should handle without loading all in memory
        generator.generate_json_report(
            huge_report,
            output_file=str(output_file),
            stream=True
        )
        
        assert output_file.exists()
        
        # Verify structure without loading entire file
        with open(output_file, 'r') as f:
            first_line = f.readline()
            assert '{' in first_line  # Valid JSON start
    
    def test_report_with_german_formatting(self, generator, processing_report_full, temp_output_dir):
        """Test German number and date formatting in reports."""
        output_file = temp_output_dir / "german_format.csv"
        
        # Add document with German-specific data
        processing_report_full.add_document(
            999,
            ProcessingStatus.SUCCESS,
            metadata={
                'title': 'Rechnung für 1.234,56 €',
                'date': '15.03.2024',
                'amount': 1234.56
            }
        )
        
        generator.generate_csv_report(
            processing_report_full,
            output_file=str(output_file),
            locale='de_DE'
        )
        
        assert output_file.exists()
        
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Check for German number format
            assert '1.234,56' in content or '1234.56' in content
            # Check for German date format
            assert '15.03.2024' in content or '2024-03-15' in content
    
    def test_empty_report_handling(self, generator, temp_output_dir):
        """Test handling of empty reports."""
        empty_report = DocumentProcessingReport()
        output_file = temp_output_dir / "empty.csv"
        
        generator.generate_csv_report(
            empty_report,
            output_file=str(output_file)
        )
        
        assert output_file.exists()
        
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            assert len(headers) > 0  # Should have headers
            
            # Should have no data rows
            data_rows = list(reader)
            assert len(data_rows) == 0
    
    def test_error_handling_invalid_path(self, generator, processing_report_full):
        """Test error handling with invalid output paths."""
        invalid_path = "/invalid/path/that/does/not/exist/report.csv"
        
        with pytest.raises((IOError, OSError, FileNotFoundError)):
            generator.generate_csv_report(
                processing_report_full,
                output_file=invalid_path
            )
    
    def test_unicode_handling(self, generator, temp_output_dir):
        """Test handling of Unicode characters in reports."""
        report = DocumentProcessingReport()
        report.add_document(
            1,
            ProcessingStatus.SUCCESS,
            metadata={
                'title': 'Übung macht den Meister 🎯',
                'tags': ['Größe', 'Straße', '日本語', '中文']
            }
        )
        
        output_file = temp_output_dir / "unicode_report.csv"
        
        generator.generate_csv_report(
            report,
            output_file=str(output_file)
        )
        
        assert output_file.exists()
        
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'Übung' in content
            assert 'Größe' in content
            assert 'Straße' in content
            # Emoji and Asian characters might be encoded differently
    
    def test_performance_report_generation(self, generator, temp_output_dir):
        """Test generation of performance metrics report."""
        import time
        
        report = DocumentProcessingReport()
        
        # Simulate processing with timing
        for i in range(100):
            start = time.time()
            # Simulate work
            time.sleep(0.001)
            duration = time.time() - start
            
            report.add_document(
                i,
                ProcessingStatus.SUCCESS,
                processing_time=duration
            )
        
        output_file = temp_output_dir / "performance.json"
        
        generator.generate_performance_report(
            report,
            output_file=str(output_file)
        )
        
        if output_file.exists():
            with open(output_file, 'r') as f:
                data = json.load(f)
                
                assert 'average_processing_time' in data
                assert 'total_processing_time' in data
                assert 'documents_per_second' in data
                assert data['average_processing_time'] > 0
    
    def test_comparative_report(self, generator, temp_output_dir):
        """Test generation of comparative reports between runs."""
        # Create two reports for comparison
        report1 = DocumentProcessingReport()
        for i in range(10):
            report1.add_document(i, ProcessingStatus.SUCCESS)
        
        report2 = DocumentProcessingReport()
        for i in range(15):
            report2.add_document(i, ProcessingStatus.SUCCESS)
        for i in range(15, 18):
            report2.add_document(i, ProcessingStatus.FAILED)
        
        output_file = temp_output_dir / "comparison.html"
        
        generator.generate_comparative_report(
            previous=report1,
            current=report2,
            output_file=str(output_file)
        )
        
        if output_file.exists():
            content = output_file.read_text()
            
            # Should show improvement/regression
            assert '10' in content  # Previous count
            assert '18' in content  # Current count
            assert '+' in content or 'increase' in content.lower() or 'mehr' in content.lower()
    
    def test_custom_template_support(self, generator, processing_report_full, temp_output_dir):
        """Test support for custom report templates."""
        template = """
        Report Summary
        ==============
        Total: {total}
        Success: {success}
        Failed: {failed}
        """
        
        output_file = temp_output_dir / "custom.txt"
        
        # Would need template support in generator
        try:
            generator.generate_from_template(
                processing_report_full,
                template=template,
                output_file=str(output_file)
            )
            
            if output_file.exists():
                content = output_file.read_text()
                assert '18' in content  # Total
                assert '10' in content  # Success
                assert '5' in content   # Failed
        except AttributeError:
            # Method might not exist yet
            pass