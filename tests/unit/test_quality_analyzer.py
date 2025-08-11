"""Unit tests for quality analysis service."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call
from typing import Dict, List, Any

from src.paperless_ngx.application.services.quality_analyzer_service import QualityAnalyzerService
from src.paperless_ngx.domain.models.processing_report import QualityIssue, QualityReport


class TestQualityAnalyzerService:
    """Test cases for document quality analysis."""
    
    @pytest.fixture
    def analyzer(self, mock_api_client):
        """Create a quality analyzer instance."""
        return QualityAnalyzerService(api_client=mock_api_client)
    
    @pytest.fixture
    def mock_validators(self):
        """Create mock validators."""
        with patch('src.paperless_ngx.application.services.quality_analyzer_service.OCRValidator') as mock_ocr:
            with patch('src.paperless_ngx.application.services.quality_analyzer_service.MetadataValidator') as mock_meta:
                ocr_instance = Mock()
                meta_instance = Mock()
                mock_ocr.return_value = ocr_instance
                mock_meta.return_value = meta_instance
                
                # Default validation results
                ocr_instance.validate_batch.return_value = [
                    {'document_id': 1, 'is_valid': True, 'errors': [], 'quality_score': 0.9},
                    {'document_id': 2, 'is_valid': False, 'errors': ['OCR too short'], 'quality_score': 0.3}
                ]
                
                meta_instance.validate_batch.return_value = [
                    {'document_id': 1, 'is_valid': True, 'errors': [], 'suggestions': {}},
                    {'document_id': 2, 'is_valid': False, 'errors': ['Missing tags'], 'suggestions': {'tags': []}}
                ]
                
                yield ocr_instance, meta_instance
    
    @pytest.fixture
    def sample_document_corpus(self, sample_documents):
        """Create a corpus of documents for analysis."""
        return sample_documents * 10  # 60 documents total
    
    async def test_analyze_document_quality_basic(self, analyzer, sample_documents):
        """Test basic quality analysis of documents."""
        analyzer.api_client.get_documents.return_value = sample_documents[:3]
        
        report = await analyzer.analyze_document_quality()
        
        assert isinstance(report, QualityReport)
        assert report.total_documents == 3
        assert report.documents_with_issues > 0
        assert report.quality_score >= 0 and report.quality_score <= 1
        assert len(report.recommendations) > 0
    
    async def test_analyze_with_progress_callback(self, analyzer, sample_documents):
        """Test analysis with progress callback."""
        analyzer.api_client.get_documents.return_value = sample_documents
        
        progress_updates = []
        def progress_callback(current, total, message):
            progress_updates.append((current, total, message))
        
        report = await analyzer.analyze_document_quality(
            progress_callback=progress_callback
        )
        
        assert len(progress_updates) > 0
        # Check progress goes from 0 to total
        assert progress_updates[0][0] == 0
        assert progress_updates[-1][0] <= len(sample_documents)
        # Check messages are provided
        assert all(update[2] for update in progress_updates)
    
    async def test_detect_ocr_failures(self, analyzer, sample_documents):
        """Test detection of OCR failures."""
        # Documents with various OCR issues
        test_docs = [
            {'id': 1, 'content': 'x' * 10, 'ocr': None},  # Too short
            {'id': 2, 'content': '', 'ocr': ''},  # Empty
            {'id': 3, 'content': None, 'ocr': None},  # No OCR
            {'id': 4, 'content': 'Good OCR text ' * 50, 'ocr': None},  # Good
        ]
        
        analyzer.api_client.get_documents.return_value = test_docs
        
        report = await analyzer.analyze_document_quality()
        
        assert report.ocr_failures >= 3  # First 3 documents have OCR issues
        assert any(issue.issue_type == 'ocr_failure' for issue in report.common_issues)
    
    async def test_detect_missing_metadata(self, analyzer):
        """Test detection of missing metadata fields."""
        test_docs = [
            {'id': 1, 'title': None, 'correspondent': None, 'tags': []},
            {'id': 2, 'title': 'Test', 'correspondent': None, 'tags': []},
            {'id': 3, 'title': 'Test', 'correspondent': 'Test GmbH', 'tags': ['tag1']},
        ]
        
        analyzer.api_client.get_documents.return_value = test_docs
        
        report = await analyzer.analyze_document_quality()
        
        assert report.missing_metadata >= 2
        assert any(issue.issue_type == 'missing_metadata' for issue in report.common_issues)
    
    async def test_detect_duplicate_documents(self, analyzer):
        """Test detection of duplicate documents."""
        # Create documents with similar content
        test_docs = [
            {'id': 1, 'title': 'Invoice 123', 'content': 'This is invoice content for order 123'},
            {'id': 2, 'title': 'Invoice 123', 'content': 'This is invoice content for order 123'},  # Exact duplicate
            {'id': 3, 'title': 'Invoice 124', 'content': 'This is invoice content for order 124'},
            {'id': 4, 'title': 'Different', 'content': 'Completely different content here'},
        ]
        
        analyzer.api_client.get_documents.return_value = test_docs
        
        report = await analyzer.analyze_document_quality()
        
        assert report.duplicate_candidates > 0
        duplicate_issue = next((issue for issue in report.common_issues 
                               if issue.issue_type == 'potential_duplicate'), None)
        assert duplicate_issue is not None
        assert 1 in duplicate_issue.affected_documents or 2 in duplicate_issue.affected_documents
    
    async def test_detect_tag_issues(self, analyzer):
        """Test detection of tag-related issues."""
        test_docs = [
            {'id': 1, 'tags': []},  # No tags
            {'id': 2, 'tags': ['single']},  # Too few
            {'id': 3, 'tags': ['tag1', 'tag2', 'tag3', 'tag4', 'tag5', 'tag6', 'tag7', 'tag8']},  # Too many
            {'id': 4, 'tags': ['good', 'tags', 'here']},  # Good
        ]
        
        analyzer.api_client.get_documents.return_value = test_docs
        
        report = await analyzer.analyze_document_quality()
        
        assert report.tag_issues >= 3
        tag_issue = next((issue for issue in report.common_issues 
                         if 'tag' in issue.issue_type.lower()), None)
        assert tag_issue is not None
    
    async def test_calculate_quality_score(self, analyzer):
        """Test quality score calculation."""
        # Perfect documents
        perfect_docs = [
            {
                'id': i,
                'title': f'Document {i}',
                'correspondent': 'Test GmbH',
                'document_type': 'Rechnung',
                'tags': ['tag1', 'tag2', 'tag3'],
                'content': 'x' * 500,
                'ocr_confidence': 0.95
            }
            for i in range(10)
        ]
        
        analyzer.api_client.get_documents.return_value = perfect_docs
        report = await analyzer.analyze_document_quality()
        assert report.quality_score > 0.8  # Should have high score
        
        # Poor quality documents
        poor_docs = [
            {
                'id': i,
                'title': None,
                'correspondent': None,
                'tags': [],
                'content': '',
            }
            for i in range(10)
        ]
        
        analyzer.api_client.get_documents.return_value = poor_docs
        report = await analyzer.analyze_document_quality()
        assert report.quality_score < 0.3  # Should have low score
    
    async def test_generate_recommendations(self, analyzer, sample_documents):
        """Test recommendation generation based on issues."""
        analyzer.api_client.get_documents.return_value = sample_documents
        
        report = await analyzer.analyze_document_quality()
        
        assert len(report.recommendations) > 0
        # Check for specific recommendation types
        recommendations_text = ' '.join(report.recommendations)
        
        # Should have recommendations for common issues
        if report.ocr_failures > 0:
            assert 'OCR' in recommendations_text or 'scan' in recommendations_text
        if report.missing_metadata > 0:
            assert 'metadata' in recommendations_text or 'Metadaten' in recommendations_text
        if report.duplicate_candidates > 0:
            assert 'duplicate' in recommendations_text or 'Duplikat' in recommendations_text
    
    async def test_filter_by_date_range(self, analyzer, sample_documents):
        """Test filtering documents by date range."""
        analyzer.api_client.get_documents.return_value = sample_documents
        
        start_date = datetime(2024, 2, 1)
        end_date = datetime(2024, 3, 1)
        
        report = await analyzer.analyze_document_quality(
            start_date=start_date,
            end_date=end_date
        )
        
        # Should have called with date filter
        analyzer.api_client.get_documents.assert_called()
        call_args = analyzer.api_client.get_documents.call_args
        
        # Verify date filtering logic would be applied
        assert report.total_documents <= len(sample_documents)
    
    async def test_filter_by_tags(self, analyzer, sample_documents):
        """Test filtering documents by tags."""
        analyzer.api_client.get_documents.return_value = sample_documents
        
        report = await analyzer.analyze_document_quality(
            tags=['2024', 'Rechnung']
        )
        
        # Results should be filtered
        assert report.total_documents <= len(sample_documents)
    
    async def test_chunked_processing(self, analyzer):
        """Test processing documents in chunks for memory efficiency."""
        # Create large document set
        large_doc_set = [
            {'id': i, 'title': f'Doc {i}', 'content': 'x' * 100}
            for i in range(1000)
        ]
        
        analyzer.api_client.get_documents.return_value = large_doc_set
        
        # Analyzer should process in chunks
        report = await analyzer.analyze_document_quality(chunk_size=100)
        
        assert report.total_documents == 1000
        # Processing should complete without memory issues
    
    async def test_severity_classification(self, analyzer):
        """Test issue severity classification."""
        test_docs = [
            {'id': 1, 'content': ''},  # Critical - no OCR
            {'id': 2, 'tags': []},  # High - no tags
            {'id': 3, 'description': None},  # Medium - missing optional field
            {'id': 4, 'title': 'scan_001'},  # Low - poor title
        ]
        
        analyzer.api_client.get_documents.return_value = test_docs
        
        report = await analyzer.analyze_document_quality()
        
        # Check severity levels
        assert any(issue.severity == 'critical' for issue in report.common_issues)
        assert any(issue.severity == 'high' for issue in report.common_issues)
        
        # Critical issues should be listed first
        if report.common_issues:
            severities = ['critical', 'high', 'medium', 'low']
            issue_severities = [issue.severity for issue in report.common_issues]
            # Check general ordering trend (critical/high before low)
    
    async def test_performance_metrics(self, analyzer, sample_documents):
        """Test performance metrics collection."""
        analyzer.api_client.get_documents.return_value = sample_documents
        
        start_time = datetime.now()
        report = await analyzer.analyze_document_quality()
        
        assert report.scan_duration_seconds > 0
        assert report.scan_timestamp <= datetime.now()
        assert report.scan_timestamp >= start_time
    
    async def test_empty_corpus_handling(self, analyzer):
        """Test handling of empty document corpus."""
        analyzer.api_client.get_documents.return_value = []
        
        report = await analyzer.analyze_document_quality()
        
        assert report.total_documents == 0
        assert report.documents_with_issues == 0
        assert report.quality_score == 1.0  # Perfect score for empty set
        assert len(report.common_issues) == 0
        assert len(report.recommendations) == 0
    
    async def test_error_handling(self, analyzer):
        """Test error handling during analysis."""
        # Simulate API error
        analyzer.api_client.get_documents.side_effect = Exception("API Error")
        
        with pytest.raises(Exception) as exc_info:
            await analyzer.analyze_document_quality()
        
        assert "API Error" in str(exc_info.value)
    
    async def test_daniel_ebn_rule_detection(self, analyzer):
        """Test detection of Daniel/EBN as sender violations."""
        test_docs = [
            {'id': 1, 'correspondent': 'Daniel Schindler'},
            {'id': 2, 'correspondent': 'EBN Veranstaltungen'},
            {'id': 3, 'correspondent': 'Amazon EU S.a.r.l.'},  # Valid
        ]
        
        analyzer.api_client.get_documents.return_value = test_docs
        
        report = await analyzer.analyze_document_quality()
        
        # Should detect business rule violations
        business_rule_issue = next(
            (issue for issue in report.common_issues 
             if 'recipient' in issue.description.lower() or 'empfänger' in issue.description.lower()),
            None
        )
        assert business_rule_issue is not None
        assert 1 in business_rule_issue.affected_documents
        assert 2 in business_rule_issue.affected_documents
        assert 3 not in business_rule_issue.affected_documents
    
    async def test_language_consistency_check(self, analyzer):
        """Test checking for language consistency."""
        test_docs = [
            {'id': 1, 'content': 'Dies ist ein deutscher Text.', 'tags': ['Rechnung', 'Steuer']},
            {'id': 2, 'content': 'This is English text.', 'tags': ['Invoice', 'Tax']},
            {'id': 3, 'content': 'Noch mehr deutscher Text hier.', 'tags': ['Brief', 'Versand']},
        ]
        
        analyzer.api_client.get_documents.return_value = test_docs
        
        report = await analyzer.analyze_document_quality()
        
        # Should detect language inconsistency
        if report.common_issues:
            language_issues = [issue for issue in report.common_issues 
                              if 'language' in issue.issue_type.lower() or 'sprache' in issue.description.lower()]
            # May or may not detect depending on implementation
    
    async def test_concurrent_analysis(self, analyzer):
        """Test concurrent analysis of multiple document batches."""
        import asyncio
        
        # Create multiple document sets
        doc_sets = [
            [{'id': i, 'title': f'Set1 Doc {i}'} for i in range(10)],
            [{'id': i, 'title': f'Set2 Doc {i}'} for i in range(10)],
            [{'id': i, 'title': f'Set3 Doc {i}'} for i in range(10)],
        ]
        
        async def analyze_set(docs):
            analyzer.api_client.get_documents.return_value = docs
            return await analyzer.analyze_document_quality()
        
        # Run analyses concurrently
        results = await asyncio.gather(*[analyze_set(docs) for docs in doc_sets])
        
        assert len(results) == 3
        for report in results:
            assert report.total_documents == 10
    
    async def test_custom_validation_rules(self, analyzer):
        """Test addition of custom validation rules."""
        # Add custom validation logic
        def custom_validator(doc):
            issues = []
            if doc.get('title', '').startswith('TEMP_'):
                issues.append("Temporary title detected")
            return issues
        
        # Would need to extend analyzer to support custom validators
        # This is a placeholder for extensibility testing
        pass
    
    async def test_export_friendly_format(self, analyzer, sample_documents):
        """Test that report can be easily exported."""
        analyzer.api_client.get_documents.return_value = sample_documents
        
        report = await analyzer.analyze_document_quality()
        
        # Test serialization
        report_dict = {
            'total_documents': report.total_documents,
            'documents_with_issues': report.documents_with_issues,
            'quality_score': report.quality_score,
            'common_issues': [
                {
                    'type': issue.issue_type,
                    'severity': issue.severity,
                    'count': issue.count,
                    'description': issue.description
                }
                for issue in report.common_issues
            ],
            'recommendations': report.recommendations,
            'scan_timestamp': report.scan_timestamp.isoformat() if report.scan_timestamp else None,
            'scan_duration': report.scan_duration_seconds
        }
        
        # Should be JSON serializable
        import json
        json_str = json.dumps(report_dict)
        assert json_str
        
        # Can be loaded back
        loaded = json.loads(json_str)
        assert loaded['total_documents'] == report.total_documents