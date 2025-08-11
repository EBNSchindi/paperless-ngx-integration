"""Comprehensive integration tests for quality scan workflow.

Tests the complete quality scan process including progress tracking,
CSV report generation, and error handling.
"""

import pytest
import csv
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, call
import tempfile
import threading
import time

from src.paperless_ngx.application.services.quality_analyzer_service import QualityAnalyzerService
from src.paperless_ngx.application.services.report_generator_service import ReportGeneratorService
from src.paperless_ngx.domain.models.processing_report import (
    QualityReport, QualityIssue, DocumentProcessingReport, ProcessingStatus
)
from src.paperless_ngx.domain.validators.ocr_validator import OCRValidator
from src.paperless_ngx.domain.validators.metadata_validator import MetadataValidator


class TestQualityScanWorkflow:
    """Test suite for complete quality scan workflow."""
    
    @pytest.fixture
    def quality_analyzer(self, mock_api_client):
        """Create quality analyzer service."""
        return QualityAnalyzerService(
            api_client=mock_api_client,
            ocr_validator=OCRValidator(),
            metadata_validator=MetadataValidator()
        )
    
    @pytest.fixture
    def report_generator(self, temp_output_dir):
        """Create report generator service."""
        return ReportGeneratorService(output_dir=temp_output_dir)
    
    @pytest.fixture
    def mock_progress_callback(self):
        """Create mock progress callback."""
        callback = Mock()
        callback.return_value = None
        return callback
    
    # ============= Complete Workflow Tests =============
    
    def test_complete_quality_scan_workflow(
        self, quality_analyzer, report_generator, sample_documents, 
        mock_progress_callback, temp_output_dir
    ):
        """Test complete quality scan from start to finish."""
        # Setup
        quality_analyzer.api_client.get_documents.return_value = sample_documents
        
        # Execute quality scan
        quality_report = quality_analyzer.analyze_documents(
            progress_callback=mock_progress_callback
        )
        
        # Verify scan results
        assert isinstance(quality_report, QualityReport)
        assert quality_report.total_documents == len(sample_documents)
        assert quality_report.documents_with_issues > 0
        
        # Verify progress callbacks
        assert mock_progress_callback.called
        expected_calls = len(sample_documents)
        assert mock_progress_callback.call_count >= expected_calls
        
        # Generate report
        report_path = report_generator.generate_csv_report(quality_report)
        
        # Verify report exists and is valid
        assert report_path.exists()
        assert report_path.suffix == '.csv'
        
        # Verify report contents
        with open(report_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) > 0
            
            # Check required columns
            required_columns = ['document_id', 'issue_type', 'severity', 'description']
            for column in required_columns:
                assert column in reader.fieldnames
    
    def test_quality_scan_with_filters(self, quality_analyzer, sample_documents):
        """Test quality scan with document filters."""
        # Filter for specific date range
        start_date = datetime(2024, 3, 1)
        end_date = datetime(2024, 3, 31)
        
        filtered_docs = [
            doc for doc in sample_documents 
            if doc.get('created', '').startswith('2024-03')
        ]
        
        quality_analyzer.api_client.get_documents.return_value = filtered_docs
        
        quality_report = quality_analyzer.analyze_documents(
            start_date=start_date,
            end_date=end_date
        )
        
        assert quality_report.total_documents == len(filtered_docs)
        
        # Verify date filter was applied to API call
        call_args = quality_analyzer.api_client.get_documents.call_args
        assert 'created__date__gte' in call_args[1]
        assert 'created__date__lte' in call_args[1]
    
    def test_quality_scan_batch_processing(self, quality_analyzer, mock_progress_callback):
        """Test quality scan with large batch of documents."""
        # Create large batch of documents
        large_batch = []
        for i in range(500):
            large_batch.append({
                'id': i,
                'title': f'Document {i}',
                'content': f'Content for document {i}' * 10,
                'correspondent': f'Sender {i % 10}',
                'document_type': 'Rechnung' if i % 2 == 0 else 'Vertrag',
                'tags': [f'tag{j}' for j in range(3, 6)],
                'created': f'2024-{(i % 12) + 1:02d}-15T10:00:00Z'
            })
        
        quality_analyzer.api_client.get_documents.return_value = large_batch
        
        # Execute scan
        start_time = time.time()
        quality_report = quality_analyzer.analyze_documents(
            batch_size=50,
            progress_callback=mock_progress_callback
        )
        execution_time = time.time() - start_time
        
        # Verify results
        assert quality_report.total_documents == 500
        assert quality_report.scan_duration_seconds > 0
        
        # Verify batching
        assert mock_progress_callback.call_count >= 10  # 500 / 50 = 10 batches
        
        # Performance check (should complete reasonably fast)
        assert execution_time < 30  # 30 seconds max for 500 documents
    
    # ============= Progress Tracking Tests =============
    
    def test_progress_callback_updates(self, quality_analyzer, sample_documents):
        """Test progress callback receives correct updates."""
        progress_updates = []
        
        def track_progress(current, total, message):
            progress_updates.append({
                'current': current,
                'total': total,
                'message': message,
                'percentage': (current / total * 100) if total > 0 else 0
            })
        
        quality_analyzer.api_client.get_documents.return_value = sample_documents
        
        quality_report = quality_analyzer.analyze_documents(
            progress_callback=track_progress
        )
        
        # Verify progress updates
        assert len(progress_updates) > 0
        
        # Check first update
        assert progress_updates[0]['current'] > 0
        assert progress_updates[0]['total'] == len(sample_documents)
        
        # Check last update
        last_update = progress_updates[-1]
        assert last_update['current'] == last_update['total']
        assert last_update['percentage'] == 100
    
    def test_progress_callback_error_handling(self, quality_analyzer):
        """Test progress callback handles errors gracefully."""
        def failing_callback(current, total, message):
            raise Exception("Callback failed")
        
        quality_analyzer.api_client.get_documents.return_value = [
            {'id': 1, 'content': 'Test document'}
        ]
        
        # Should not raise exception even if callback fails
        quality_report = quality_analyzer.analyze_documents(
            progress_callback=failing_callback
        )
        
        assert quality_report.total_documents == 1
    
    def test_concurrent_progress_tracking(self, quality_analyzer, sample_documents):
        """Test progress tracking with concurrent operations."""
        progress_lock = threading.Lock()
        progress_data = {'updates': []}
        
        def thread_safe_callback(current, total, message):
            with progress_lock:
                progress_data['updates'].append({
                    'thread': threading.current_thread().name,
                    'current': current,
                    'total': total
                })
        
        quality_analyzer.api_client.get_documents.return_value = sample_documents
        
        # Run multiple scans concurrently
        threads = []
        for i in range(3):
            thread = threading.Thread(
                target=lambda: quality_analyzer.analyze_documents(
                    progress_callback=thread_safe_callback
                ),
                name=f'Scanner-{i}'
            )
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify thread-safe progress updates
        assert len(progress_data['updates']) > 0
        
        # Check updates from different threads
        thread_names = set(update['thread'] for update in progress_data['updates'])
        assert len(thread_names) == 3
    
    # ============= CSV Report Generation Tests =============
    
    def test_csv_report_generation(self, report_generator, sample_quality_report):
        """Test CSV report generation from quality report."""
        report_path = report_generator.generate_csv_report(sample_quality_report)
        
        assert report_path.exists()
        
        # Read and verify CSV contents
        with open(report_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            # Should have rows for each issue
            assert len(rows) > 0
            
            # Verify data integrity
            for row in rows:
                assert row['document_id']
                assert row['issue_type']
                assert row['severity'] in ['high', 'medium', 'low']
                assert row['description']
    
    def test_csv_report_with_german_characters(self, report_generator):
        """Test CSV report handles German characters correctly."""
        quality_report = QualityReport(
            total_documents=1,
            documents_with_issues=1,
            common_issues=[
                QualityIssue(
                    issue_type="missing_metadata",
                    severity="high",
                    count=1,
                    affected_documents=[1],
                    description="Dokument fehlt Metadaten für Überweisung",
                    recommendation="Bitte fügen Sie Empfänger hinzu"
                )
            ],
            quality_score=0.5,
            scan_timestamp=datetime.now()
        )
        
        report_path = report_generator.generate_csv_report(quality_report)
        
        # Read with UTF-8 encoding
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'Überweisung' in content
            assert 'Empfänger' in content
            assert 'fügen' in content
    
    def test_csv_report_large_dataset(self, report_generator):
        """Test CSV report generation with large dataset."""
        # Create large quality report
        issues = []
        for i in range(1000):
            issues.append(
                QualityIssue(
                    issue_type=f"issue_type_{i % 10}",
                    severity=['high', 'medium', 'low'][i % 3],
                    count=1,
                    affected_documents=[i],
                    description=f"Issue description for document {i}",
                    recommendation=f"Recommendation {i}"
                )
            )
        
        quality_report = QualityReport(
            total_documents=1000,
            documents_with_issues=1000,
            common_issues=issues,
            quality_score=0.3,
            scan_timestamp=datetime.now()
        )
        
        start_time = time.time()
        report_path = report_generator.generate_csv_report(quality_report)
        generation_time = time.time() - start_time
        
        # Should generate quickly even for large reports
        assert generation_time < 5  # 5 seconds max
        
        # Verify file size is reasonable
        file_size = report_path.stat().st_size
        assert file_size > 0
        assert file_size < 10 * 1024 * 1024  # Less than 10MB
    
    def test_csv_report_custom_delimiter(self, report_generator, sample_quality_report):
        """Test CSV report with custom delimiter."""
        report_path = report_generator.generate_csv_report(
            sample_quality_report,
            delimiter=';'
        )
        
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert ';' in content
            
            # Parse with custom delimiter
            f.seek(0)
            reader = csv.DictReader(f, delimiter=';')
            rows = list(reader)
            assert len(rows) > 0
    
    # ============= Error Handling and Recovery Tests =============
    
    def test_quality_scan_with_api_errors(self, quality_analyzer):
        """Test quality scan handles API errors gracefully."""
        # Simulate API error
        quality_analyzer.api_client.get_documents.side_effect = Exception("API Error")
        
        with pytest.raises(Exception) as exc_info:
            quality_analyzer.analyze_documents()
        
        assert "API Error" in str(exc_info.value)
    
    def test_quality_scan_partial_failures(self, quality_analyzer):
        """Test quality scan continues despite partial failures."""
        documents = [
            {'id': 1, 'content': 'Valid document'},
            {'id': 2, 'content': None},  # Will cause validation error
            {'id': 3, 'content': 'Another valid document'}
        ]
        
        quality_analyzer.api_client.get_documents.return_value = documents
        
        quality_report = quality_analyzer.analyze_documents()
        
        # Should process all documents despite errors
        assert quality_report.total_documents == 3
        # Document 2 should have issues
        assert quality_report.documents_with_issues >= 1
    
    def test_report_generation_disk_space_error(self, report_generator, sample_quality_report):
        """Test report generation handles disk space errors."""
        with patch('builtins.open', side_effect=IOError("No space left on device")):
            with pytest.raises(IOError) as exc_info:
                report_generator.generate_csv_report(sample_quality_report)
            
            assert "No space left on device" in str(exc_info.value)
    
    def test_quality_scan_memory_efficient(self, quality_analyzer):
        """Test quality scan is memory efficient for large datasets."""
        # Create generator for streaming documents
        def document_generator():
            for i in range(10000):
                yield {
                    'id': i,
                    'content': f'Document {i} content',
                    'title': f'Document {i}'
                }
        
        quality_analyzer.api_client.get_documents.return_value = list(document_generator())
        
        # Should handle large dataset without memory issues
        quality_report = quality_analyzer.analyze_documents(
            stream=True,
            batch_size=100
        )
        
        assert quality_report.total_documents == 10000
    
    # ============= Performance and Optimization Tests =============
    
    def test_quality_scan_performance_metrics(self, quality_analyzer, sample_documents):
        """Test quality scan collects performance metrics."""
        quality_analyzer.api_client.get_documents.return_value = sample_documents
        
        quality_report = quality_analyzer.analyze_documents()
        
        # Should include performance metrics
        assert quality_report.scan_duration_seconds > 0
        assert quality_report.scan_timestamp is not None
        
        # Calculate documents per second
        docs_per_second = (
            quality_report.total_documents / quality_report.scan_duration_seconds
            if quality_report.scan_duration_seconds > 0 else 0
        )
        
        # Should process at reasonable speed
        assert docs_per_second > 10  # At least 10 docs/second
    
    def test_quality_scan_caching(self, quality_analyzer, sample_documents):
        """Test quality scan uses caching for repeated analyses."""
        quality_analyzer.api_client.get_documents.return_value = sample_documents
        
        # First scan
        report1 = quality_analyzer.analyze_documents()
        
        # Second scan (should use cached results where possible)
        with patch.object(quality_analyzer, '_use_cache', True):
            report2 = quality_analyzer.analyze_documents()
        
        # Results should be consistent
        assert report1.total_documents == report2.total_documents
        assert report1.documents_with_issues == report2.documents_with_issues
    
    def test_parallel_quality_analysis(self, quality_analyzer, sample_documents):
        """Test parallel processing of quality analysis."""
        quality_analyzer.api_client.get_documents.return_value = sample_documents
        
        with patch('concurrent.futures.ThreadPoolExecutor') as mock_executor:
            mock_executor.return_value.__enter__.return_value.map = lambda func, items: map(func, items)
            
            quality_report = quality_analyzer.analyze_documents(
                parallel=True,
                max_workers=4
            )
            
            assert quality_report.total_documents == len(sample_documents)
            # Verify thread pool was used
            mock_executor.assert_called_with(max_workers=4)
    
    # ============= Integration with Other Components =============
    
    def test_quality_scan_with_llm_enrichment(
        self, quality_analyzer, mock_llm_client, sample_documents
    ):
        """Test quality scan with LLM-based enrichment."""
        quality_analyzer.api_client.get_documents.return_value = sample_documents
        quality_analyzer.llm_client = mock_llm_client
        
        # Mock LLM suggestions
        mock_llm_client.suggest_improvements.return_value = {
            'title': 'Improved Title',
            'tags': ['better', 'tags', 'here']
        }
        
        quality_report = quality_analyzer.analyze_documents(
            enrich_with_llm=True
        )
        
        # Should call LLM for documents with issues
        assert mock_llm_client.suggest_improvements.called
    
    def test_quality_scan_triggers_reprocessing(
        self, quality_analyzer, sample_documents
    ):
        """Test quality scan can trigger document reprocessing."""
        quality_analyzer.api_client.get_documents.return_value = sample_documents
        
        # Documents that need reprocessing
        reprocess_queue = []
        
        def reprocess_callback(doc_id, issues):
            if len(issues) > 2:  # Reprocess if more than 2 issues
                reprocess_queue.append(doc_id)
        
        quality_report = quality_analyzer.analyze_documents(
            reprocess_callback=reprocess_callback
        )
        
        # Should identify documents for reprocessing
        assert len(reprocess_queue) > 0
    
    # ============= Summary and Statistics Tests =============
    
    def test_quality_summary_statistics(self, quality_analyzer, sample_documents):
        """Test quality scan generates comprehensive statistics."""
        quality_analyzer.api_client.get_documents.return_value = sample_documents
        
        quality_report = quality_analyzer.analyze_documents()
        
        # Should include various statistics
        assert hasattr(quality_report, 'ocr_failures')
        assert hasattr(quality_report, 'missing_metadata')
        assert hasattr(quality_report, 'duplicate_candidates')
        assert hasattr(quality_report, 'tag_issues')
        
        # Quality score should be between 0 and 1
        assert 0 <= quality_report.quality_score <= 1
        
        # Should have recommendations
        assert len(quality_report.recommendations) > 0
    
    def test_quality_trends_over_time(self, quality_analyzer):
        """Test tracking quality trends over multiple scans."""
        scan_results = []
        
        # Simulate multiple scans over time
        for month in range(1, 4):
            documents = [
                {
                    'id': i,
                    'content': f'Document {i}' * 20,
                    'created': f'2024-{month:02d}-15T10:00:00Z',
                    'tags': ['tag1', 'tag2', 'tag3'] if i % 2 == 0 else ['tag1']
                }
                for i in range(1, 11)
            ]
            
            quality_analyzer.api_client.get_documents.return_value = documents
            report = quality_analyzer.analyze_documents()
            scan_results.append(report)
        
        # Analyze trends
        quality_scores = [r.quality_score for r in scan_results]
        
        # Should track quality over time
        assert len(quality_scores) == 3
        
        # Calculate trend (improvement or degradation)
        if len(quality_scores) > 1:
            trend = quality_scores[-1] - quality_scores[0]
            # Trend can be positive (improvement) or negative (degradation)
            assert isinstance(trend, float)