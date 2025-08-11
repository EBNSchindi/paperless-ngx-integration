"""Domain models for Paperless NGX integration.

This package contains data models for processing reports, tag analysis,
and other domain entities.
"""

from .processing_report import (
    BatchProcessingResult,
    DocumentProcessingResult,
    ErrorSeverity,
    ProcessingError,
    ProcessingPhase,
    ProcessingStatistics,
    ProcessingStatus,
    QualityReport,
)
from .tag_models import (
    SimilarityMethod,
    Tag,
    TagAnalysisResult,
    TagCluster,
    TagMergeOperation,
    TagMergeRecommendation,
    TagMergeStrategy,
    TagSimilarity,
)

__all__ = [
    # Processing report models
    'ProcessingStatus',
    'ErrorSeverity',
    'ProcessingPhase',
    'ProcessingError',
    'DocumentProcessingResult',
    'BatchProcessingResult',
    'ProcessingStatistics',
    'QualityReport',
    # Tag models
    'TagMergeStrategy',
    'SimilarityMethod',
    'Tag',
    'TagSimilarity',
    'TagCluster',
    'TagMergeRecommendation',
    'TagAnalysisResult',
    'TagMergeOperation',
]