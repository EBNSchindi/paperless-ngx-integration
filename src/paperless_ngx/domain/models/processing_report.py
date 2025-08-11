"""Domain models for processing reports and results.

This module defines data structures for tracking document processing
results, batch operations, and statistical analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ProcessingStatus(Enum):
    """Status of document processing."""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    PARTIAL = "partial"


class ErrorSeverity(Enum):
    """Severity levels for processing errors."""
    
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    WARNING = "warning"
    INFO = "info"


class ProcessingPhase(Enum):
    """Phases of document processing."""
    
    RETRIEVAL = "retrieval"
    OCR_EXTRACTION = "ocr_extraction"
    METADATA_EXTRACTION = "metadata_extraction"
    VALIDATION = "validation"
    ENRICHMENT = "enrichment"
    UPDATE = "update"
    VERIFICATION = "verification"


@dataclass
class ProcessingError:
    """Represents an error during processing.
    
    Attributes:
        phase: Processing phase where error occurred
        severity: Error severity level
        message: Error message
        details: Additional error details
        timestamp: When the error occurred
        document_id: Optional document ID if error is document-specific
        recoverable: Whether the error is recoverable
    """
    
    phase: ProcessingPhase
    severity: ErrorSeverity
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    document_id: Optional[int] = None
    recoverable: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'phase': self.phase.value,
            'severity': self.severity.value,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
            'document_id': self.document_id,
            'recoverable': self.recoverable
        }


@dataclass
class DocumentProcessingResult:
    """Result of processing a single document.
    
    Attributes:
        document_id: Document ID
        status: Processing status
        phases_completed: List of completed processing phases
        metadata_extracted: Extracted metadata
        metadata_updated: Updated metadata fields
        validation_results: Validation results
        errors: List of processing errors
        warnings: List of warnings
        processing_time: Time taken to process (seconds)
        timestamp: When processing completed
    """
    
    document_id: int
    status: ProcessingStatus
    phases_completed: List[ProcessingPhase] = field(default_factory=list)
    metadata_extracted: Optional[Dict[str, Any]] = None
    metadata_updated: Optional[Dict[str, Any]] = None
    validation_results: Optional[Dict[str, Any]] = None
    errors: List[ProcessingError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def is_successful(self) -> bool:
        """Check if processing was successful."""
        return self.status == ProcessingStatus.COMPLETED
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0
    
    @property
    def has_critical_errors(self) -> bool:
        """Check if there are critical errors."""
        return any(e.severity == ErrorSeverity.CRITICAL for e in self.errors)
    
    def add_error(
        self,
        phase: ProcessingPhase,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        **kwargs: Any
    ) -> None:
        """Add an error to the result.
        
        Args:
            phase: Processing phase
            message: Error message
            severity: Error severity
            **kwargs: Additional error properties
        """
        error = ProcessingError(
            phase=phase,
            severity=severity,
            message=message,
            document_id=self.document_id,
            **kwargs
        )
        self.errors.append(error)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'document_id': self.document_id,
            'status': self.status.value,
            'phases_completed': [p.value for p in self.phases_completed],
            'metadata_extracted': self.metadata_extracted,
            'metadata_updated': self.metadata_updated,
            'validation_results': self.validation_results,
            'errors': [e.to_dict() for e in self.errors],
            'warnings': self.warnings,
            'processing_time': self.processing_time,
            'timestamp': self.timestamp.isoformat(),
            'is_successful': self.is_successful,
            'has_critical_errors': self.has_critical_errors
        }


@dataclass
class BatchProcessingResult:
    """Result of processing multiple documents in a batch.
    
    Attributes:
        batch_id: Unique batch identifier
        total_documents: Total number of documents in batch
        results: Individual document results
        start_time: When batch processing started
        end_time: When batch processing ended
        configuration: Batch processing configuration
    """
    
    batch_id: str
    total_documents: int
    results: List[DocumentProcessingResult] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    configuration: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def processed_count(self) -> int:
        """Get count of processed documents."""
        return len(self.results)
    
    @property
    def successful_count(self) -> int:
        """Get count of successfully processed documents."""
        return sum(1 for r in self.results if r.is_successful)
    
    @property
    def failed_count(self) -> int:
        """Get count of failed documents."""
        return sum(1 for r in self.results if r.status == ProcessingStatus.FAILED)
    
    @property
    def skipped_count(self) -> int:
        """Get count of skipped documents."""
        return sum(1 for r in self.results if r.status == ProcessingStatus.SKIPPED)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.processed_count == 0:
            return 0.0
        return self.successful_count / self.processed_count
    
    @property
    def processing_time(self) -> Optional[float]:
        """Calculate total processing time in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def average_processing_time(self) -> float:
        """Calculate average processing time per document."""
        if self.processed_count == 0:
            return 0.0
        return sum(r.processing_time for r in self.results) / self.processed_count
    
    def add_result(self, result: DocumentProcessingResult) -> None:
        """Add a document processing result.
        
        Args:
            result: Document processing result
        """
        self.results.append(result)
    
    def get_errors_summary(self) -> Dict[str, Any]:
        """Get summary of all errors in the batch.
        
        Returns:
            Dictionary with error statistics
        """
        all_errors = []
        for result in self.results:
            all_errors.extend(result.errors)
        
        if not all_errors:
            return {
                'total_errors': 0,
                'by_severity': {},
                'by_phase': {},
                'critical_errors': []
            }
        
        # Group by severity
        by_severity = {}
        for severity in ErrorSeverity:
            count = sum(1 for e in all_errors if e.severity == severity)
            if count > 0:
                by_severity[severity.value] = count
        
        # Group by phase
        by_phase = {}
        for phase in ProcessingPhase:
            count = sum(1 for e in all_errors if e.phase == phase)
            if count > 0:
                by_phase[phase.value] = count
        
        # Get critical errors
        critical_errors = [
            e.to_dict() for e in all_errors
            if e.severity == ErrorSeverity.CRITICAL
        ]
        
        return {
            'total_errors': len(all_errors),
            'by_severity': by_severity,
            'by_phase': by_phase,
            'critical_errors': critical_errors[:10],  # Limit to first 10
            'recoverable_errors': sum(1 for e in all_errors if e.recoverable),
            'non_recoverable_errors': sum(1 for e in all_errors if not e.recoverable)
        }
    
    def complete(self) -> None:
        """Mark batch processing as complete."""
        self.end_time = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'batch_id': self.batch_id,
            'total_documents': self.total_documents,
            'processed_count': self.processed_count,
            'successful_count': self.successful_count,
            'failed_count': self.failed_count,
            'skipped_count': self.skipped_count,
            'success_rate': round(self.success_rate, 3),
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'processing_time': self.processing_time,
            'average_processing_time': round(self.average_processing_time, 2),
            'configuration': self.configuration,
            'errors_summary': self.get_errors_summary(),
            'results': [r.to_dict() for r in self.results[:100]]  # Limit for large batches
        }


@dataclass
class ProcessingStatistics:
    """Overall processing statistics.
    
    Attributes:
        total_batches: Total number of batches processed
        total_documents: Total documents processed
        total_successful: Total successful documents
        total_failed: Total failed documents
        total_errors: Total number of errors
        average_success_rate: Average success rate across batches
        total_processing_time: Total time spent processing
        common_errors: Most common error messages
        performance_metrics: Performance-related metrics
    """
    
    total_batches: int = 0
    total_documents: int = 0
    total_successful: int = 0
    total_failed: int = 0
    total_errors: int = 0
    average_success_rate: float = 0.0
    total_processing_time: float = 0.0
    common_errors: List[Dict[str, Any]] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    
    @classmethod
    def from_batch_results(
        cls,
        batch_results: List[BatchProcessingResult]
    ) -> 'ProcessingStatistics':
        """Create statistics from batch results.
        
        Args:
            batch_results: List of batch processing results
            
        Returns:
            ProcessingStatistics instance
        """
        if not batch_results:
            return cls()
        
        stats = cls(
            total_batches=len(batch_results),
            total_documents=sum(b.total_documents for b in batch_results),
            total_successful=sum(b.successful_count for b in batch_results),
            total_failed=sum(b.failed_count for b in batch_results)
        )
        
        # Calculate total errors
        for batch in batch_results:
            for result in batch.results:
                stats.total_errors += len(result.errors)
        
        # Calculate average success rate
        success_rates = [b.success_rate for b in batch_results if b.processed_count > 0]
        stats.average_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0.0
        
        # Calculate total processing time
        processing_times = [b.processing_time for b in batch_results if b.processing_time]
        stats.total_processing_time = sum(processing_times)
        
        # Find common errors
        error_counts: Dict[str, int] = {}
        for batch in batch_results:
            for result in batch.results:
                for error in result.errors:
                    key = f"{error.phase.value}:{error.message[:50]}"
                    error_counts[key] = error_counts.get(key, 0) + 1
        
        # Get top 10 common errors
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        stats.common_errors = [
            {'error': err, 'count': count}
            for err, count in sorted_errors[:10]
        ]
        
        # Calculate performance metrics
        if batch_results:
            all_processing_times = []
            for batch in batch_results:
                all_processing_times.extend([r.processing_time for r in batch.results])
            
            if all_processing_times:
                stats.performance_metrics = {
                    'avg_document_time': sum(all_processing_times) / len(all_processing_times),
                    'min_document_time': min(all_processing_times),
                    'max_document_time': max(all_processing_times),
                    'documents_per_minute': 60 / (sum(all_processing_times) / len(all_processing_times))
                    if all_processing_times else 0
                }
        
        return stats
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'total_batches': self.total_batches,
            'total_documents': self.total_documents,
            'total_successful': self.total_successful,
            'total_failed': self.total_failed,
            'total_errors': self.total_errors,
            'average_success_rate': round(self.average_success_rate, 3),
            'total_processing_time': round(self.total_processing_time, 2),
            'total_processing_hours': round(self.total_processing_time / 3600, 2),
            'common_errors': self.common_errors,
            'performance_metrics': {
                k: round(v, 2) for k, v in self.performance_metrics.items()
            }
        }


@dataclass
class QualityReport:
    """Quality analysis report for documents.
    
    Attributes:
        report_id: Unique report identifier
        generated_at: When report was generated
        document_count: Number of documents analyzed
        quality_issues: List of quality issues found
        ocr_statistics: OCR quality statistics
        metadata_statistics: Metadata quality statistics
        recommendations: List of recommendations
    """
    
    report_id: str
    generated_at: datetime = field(default_factory=datetime.now)
    document_count: int = 0
    quality_issues: List[Dict[str, Any]] = field(default_factory=list)
    ocr_statistics: Dict[str, Any] = field(default_factory=dict)
    metadata_statistics: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    
    def add_issue(
        self,
        document_id: int,
        issue_type: str,
        severity: ErrorSeverity,
        description: str,
        **kwargs: Any
    ) -> None:
        """Add a quality issue.
        
        Args:
            document_id: Document ID
            issue_type: Type of issue
            severity: Issue severity
            description: Issue description
            **kwargs: Additional issue properties
        """
        issue = {
            'document_id': document_id,
            'issue_type': issue_type,
            'severity': severity.value,
            'description': description,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        self.quality_issues.append(issue)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get quality report summary.
        
        Returns:
            Summary dictionary
        """
        if not self.quality_issues:
            return {
                'total_issues': 0,
                'affected_documents': 0,
                'critical_issues': 0,
                'high_issues': 0,
                'medium_issues': 0,
                'low_issues': 0
            }
        
        # Count by severity
        severity_counts = {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0
        }
        
        for issue in self.quality_issues:
            severity = issue.get('severity', 'medium')
            if severity in severity_counts:
                severity_counts[severity] += 1
        
        # Count affected documents
        affected_docs = len(set(issue['document_id'] for issue in self.quality_issues))
        
        return {
            'total_issues': len(self.quality_issues),
            'affected_documents': affected_docs,
            'critical_issues': severity_counts['critical'],
            'high_issues': severity_counts['high'],
            'medium_issues': severity_counts['medium'],
            'low_issues': severity_counts['low'],
            'by_type': self._count_by_type(),
            'top_affected_documents': self._get_top_affected_documents()
        }
    
    def _count_by_type(self) -> Dict[str, int]:
        """Count issues by type."""
        type_counts = {}
        for issue in self.quality_issues:
            issue_type = issue.get('issue_type', 'unknown')
            type_counts[issue_type] = type_counts.get(issue_type, 0) + 1
        return dict(sorted(type_counts.items(), key=lambda x: x[1], reverse=True))
    
    def _get_top_affected_documents(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get documents with most issues."""
        doc_counts = {}
        for issue in self.quality_issues:
            doc_id = issue['document_id']
            doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1
        
        sorted_docs = sorted(doc_counts.items(), key=lambda x: x[1], reverse=True)
        return [
            {'document_id': doc_id, 'issue_count': count}
            for doc_id, count in sorted_docs[:limit]
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'report_id': self.report_id,
            'generated_at': self.generated_at.isoformat(),
            'document_count': self.document_count,
            'summary': self.get_summary(),
            'ocr_statistics': self.ocr_statistics,
            'metadata_statistics': self.metadata_statistics,
            'recommendations': self.recommendations,
            'issues': self.quality_issues[:100]  # Limit for large reports
        }