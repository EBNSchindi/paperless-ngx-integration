"""Domain models for tag analysis and management.

This module defines data structures for tag similarity analysis,
clustering, and merge recommendations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class TagMergeStrategy(Enum):
    """Strategy for selecting primary tag when merging."""
    
    MOST_USED = "most_used"          # Select tag with most documents
    FIRST_CREATED = "first_created"   # Select oldest tag
    SHORTEST_NAME = "shortest_name"   # Select tag with shortest name
    LONGEST_NAME = "longest_name"     # Select tag with longest name
    MANUAL = "manual"                 # User selects manually


class SimilarityMethod(Enum):
    """Method for calculating tag similarity."""
    
    FUZZY_RATIO = "fuzzy_ratio"           # Basic fuzzy string matching
    TOKEN_SORT = "token_sort"             # Token sorting before comparison
    TOKEN_SET = "token_set"               # Token set comparison
    PARTIAL_RATIO = "partial_ratio"       # Partial string matching
    WEIGHTED_COMBINED = "weighted_combined" # Weighted combination of methods


@dataclass
class Tag:
    """Represents a single tag with metadata.
    
    Attributes:
        id: Tag ID
        name: Tag name
        color: Tag color (hex format)
        document_count: Number of documents with this tag
        created_at: When tag was created
        modified_at: When tag was last modified
        is_inbox_tag: Whether this is an inbox tag
        slug: URL-safe version of name
    """
    
    id: int
    name: str
    color: Optional[str] = None
    document_count: int = 0
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    is_inbox_tag: bool = False
    slug: Optional[str] = None
    
    @property
    def normalized_name(self) -> str:
        """Get normalized tag name for comparison."""
        return self.name.lower().strip()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'document_count': self.document_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'modified_at': self.modified_at.isoformat() if self.modified_at else None,
            'is_inbox_tag': self.is_inbox_tag,
            'slug': self.slug
        }


@dataclass
class TagSimilarity:
    """Represents similarity between two tags.
    
    Attributes:
        tag1: First tag
        tag2: Second tag
        similarity_score: Similarity score (0-100)
        method: Method used for similarity calculation
        details: Additional similarity details
    """
    
    tag1: Tag
    tag2: Tag
    similarity_score: float
    method: SimilarityMethod
    details: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_high_similarity(self) -> bool:
        """Check if similarity is high (>= 85%)."""
        return self.similarity_score >= 85.0
    
    @property
    def is_medium_similarity(self) -> bool:
        """Check if similarity is medium (70-85%)."""
        return 70.0 <= self.similarity_score < 85.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'tag1': self.tag1.to_dict(),
            'tag2': self.tag2.to_dict(),
            'similarity_score': round(self.similarity_score, 2),
            'method': self.method.value,
            'is_high_similarity': self.is_high_similarity,
            'details': self.details
        }


@dataclass
class TagCluster:
    """Represents a cluster of similar tags.
    
    Attributes:
        cluster_id: Unique cluster identifier
        tags: List of tags in the cluster
        similarities: Pairwise similarities within cluster
        representative_tag: Suggested primary tag
        merge_strategy: Strategy used to select representative
        confidence: Confidence in the clustering (0-1)
    """
    
    cluster_id: str
    tags: List[Tag] = field(default_factory=list)
    similarities: List[TagSimilarity] = field(default_factory=list)
    representative_tag: Optional[Tag] = None
    merge_strategy: TagMergeStrategy = TagMergeStrategy.MOST_USED
    confidence: float = 0.0
    
    @property
    def size(self) -> int:
        """Get cluster size."""
        return len(self.tags)
    
    @property
    def total_document_count(self) -> int:
        """Get total documents across all tags in cluster."""
        return sum(tag.document_count for tag in self.tags)
    
    @property
    def average_similarity(self) -> float:
        """Calculate average similarity within cluster."""
        if not self.similarities:
            return 0.0
        return sum(s.similarity_score for s in self.similarities) / len(self.similarities)
    
    def add_tag(self, tag: Tag) -> None:
        """Add a tag to the cluster.
        
        Args:
            tag: Tag to add
        """
        if tag not in self.tags:
            self.tags.append(tag)
    
    def add_similarity(self, similarity: TagSimilarity) -> None:
        """Add a similarity relationship.
        
        Args:
            similarity: Tag similarity to add
        """
        self.similarities.append(similarity)
    
    def select_representative(self, strategy: Optional[TagMergeStrategy] = None) -> Tag:
        """Select the representative tag based on strategy.
        
        Args:
            strategy: Merge strategy to use (uses cluster's strategy if None)
            
        Returns:
            Selected representative tag
        """
        if not self.tags:
            raise ValueError("Cannot select representative from empty cluster")
        
        strategy = strategy or self.merge_strategy
        
        if strategy == TagMergeStrategy.MOST_USED:
            self.representative_tag = max(self.tags, key=lambda t: t.document_count)
        elif strategy == TagMergeStrategy.FIRST_CREATED:
            tags_with_date = [t for t in self.tags if t.created_at]
            if tags_with_date:
                self.representative_tag = min(tags_with_date, key=lambda t: t.created_at)
            else:
                self.representative_tag = self.tags[0]
        elif strategy == TagMergeStrategy.SHORTEST_NAME:
            self.representative_tag = min(self.tags, key=lambda t: len(t.name))
        elif strategy == TagMergeStrategy.LONGEST_NAME:
            self.representative_tag = max(self.tags, key=lambda t: len(t.name))
        else:
            # Default to first tag for manual selection
            self.representative_tag = self.tags[0]
        
        return self.representative_tag
    
    def get_merge_candidates(self) -> List[Tag]:
        """Get tags that would be merged (all except representative).
        
        Returns:
            List of tags to be merged
        """
        if not self.representative_tag:
            self.select_representative()
        
        return [tag for tag in self.tags if tag != self.representative_tag]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'cluster_id': self.cluster_id,
            'size': self.size,
            'tags': [tag.to_dict() for tag in self.tags],
            'representative_tag': self.representative_tag.to_dict() if self.representative_tag else None,
            'merge_strategy': self.merge_strategy.value,
            'confidence': round(self.confidence, 3),
            'average_similarity': round(self.average_similarity, 2),
            'total_document_count': self.total_document_count,
            'merge_candidates': [t.to_dict() for t in self.get_merge_candidates()]
        }


@dataclass
class TagMergeRecommendation:
    """Recommendation for merging tags.
    
    Attributes:
        cluster: Tag cluster to merge
        reason: Reason for recommendation
        impact: Impact assessment of the merge
        estimated_documents_affected: Number of documents that would be updated
        confidence_score: Confidence in recommendation (0-1)
        warnings: List of potential warnings
    """
    
    cluster: TagCluster
    reason: str
    impact: Dict[str, Any] = field(default_factory=dict)
    estimated_documents_affected: int = 0
    confidence_score: float = 0.0
    warnings: List[str] = field(default_factory=list)
    
    @property
    def is_safe_merge(self) -> bool:
        """Check if merge is considered safe."""
        return self.confidence_score >= 0.8 and len(self.warnings) == 0
    
    @property
    def savings(self) -> Dict[str, int]:
        """Calculate savings from merge.
        
        Returns:
            Dictionary with tag and document savings
        """
        if not self.cluster:
            return {'tags_removed': 0, 'duplicate_associations_removed': 0}
        
        tags_removed = self.cluster.size - 1  # All except representative
        
        # Estimate duplicate associations (rough estimate)
        duplicate_estimate = int(self.estimated_documents_affected * 0.1)
        
        return {
            'tags_removed': tags_removed,
            'duplicate_associations_removed': duplicate_estimate
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'cluster': self.cluster.to_dict(),
            'reason': self.reason,
            'impact': self.impact,
            'estimated_documents_affected': self.estimated_documents_affected,
            'confidence_score': round(self.confidence_score, 3),
            'is_safe_merge': self.is_safe_merge,
            'warnings': self.warnings,
            'savings': self.savings
        }


@dataclass
class TagAnalysisResult:
    """Result of comprehensive tag analysis.
    
    Attributes:
        analysis_id: Unique analysis identifier
        timestamp: When analysis was performed
        total_tags: Total number of tags analyzed
        clusters_found: List of tag clusters found
        merge_recommendations: List of merge recommendations
        statistics: Analysis statistics
        quality_metrics: Tag quality metrics
    """
    
    analysis_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    total_tags: int = 0
    clusters_found: List[TagCluster] = field(default_factory=list)
    merge_recommendations: List[TagMergeRecommendation] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    quality_metrics: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def total_clusters(self) -> int:
        """Get total number of clusters."""
        return len(self.clusters_found)
    
    @property
    def tags_in_clusters(self) -> int:
        """Get total tags that are part of clusters."""
        return sum(cluster.size for cluster in self.clusters_found)
    
    @property
    def potential_tags_to_remove(self) -> int:
        """Calculate potential tags that could be removed."""
        return sum(cluster.size - 1 for cluster in self.clusters_found)
    
    @property
    def safe_recommendations(self) -> List[TagMergeRecommendation]:
        """Get only safe merge recommendations."""
        return [r for r in self.merge_recommendations if r.is_safe_merge]
    
    def add_cluster(self, cluster: TagCluster) -> None:
        """Add a cluster to the analysis.
        
        Args:
            cluster: Tag cluster to add
        """
        self.clusters_found.append(cluster)
    
    def add_recommendation(self, recommendation: TagMergeRecommendation) -> None:
        """Add a merge recommendation.
        
        Args:
            recommendation: Merge recommendation to add
        """
        self.merge_recommendations.append(recommendation)
    
    def calculate_statistics(self) -> None:
        """Calculate analysis statistics."""
        if not self.clusters_found:
            self.statistics = {
                'total_tags': self.total_tags,
                'clustered_tags': 0,
                'cluster_rate': 0.0,
                'average_cluster_size': 0.0,
                'largest_cluster_size': 0,
                'potential_reduction': 0.0
            }
            return
        
        cluster_sizes = [c.size for c in self.clusters_found]
        
        self.statistics = {
            'total_tags': self.total_tags,
            'total_clusters': self.total_clusters,
            'clustered_tags': self.tags_in_clusters,
            'cluster_rate': self.tags_in_clusters / self.total_tags if self.total_tags > 0 else 0.0,
            'average_cluster_size': sum(cluster_sizes) / len(cluster_sizes),
            'largest_cluster_size': max(cluster_sizes),
            'smallest_cluster_size': min(cluster_sizes),
            'potential_tags_to_remove': self.potential_tags_to_remove,
            'potential_reduction': self.potential_tags_to_remove / self.total_tags if self.total_tags > 0 else 0.0,
            'safe_merges': len(self.safe_recommendations),
            'total_recommendations': len(self.merge_recommendations)
        }
    
    def calculate_quality_metrics(self) -> None:
        """Calculate tag quality metrics."""
        if not self.clusters_found:
            self.quality_metrics = {
                'duplication_score': 0.0,
                'consistency_score': 1.0,
                'organization_score': 1.0
            }
            return
        
        # Duplication score (higher = more duplication)
        duplication_score = self.tags_in_clusters / self.total_tags if self.total_tags > 0 else 0.0
        
        # Consistency score (based on similarity within clusters)
        avg_similarities = [c.average_similarity for c in self.clusters_found if c.similarities]
        consistency_score = 1.0 - (sum(avg_similarities) / len(avg_similarities) / 100 if avg_similarities else 0.0)
        
        # Organization score (based on cluster sizes)
        # Smaller clusters = better organization
        avg_cluster_size = sum(c.size for c in self.clusters_found) / len(self.clusters_found)
        organization_score = max(0.0, 1.0 - (avg_cluster_size - 2) / 10)  # Normalize to 0-1
        
        self.quality_metrics = {
            'duplication_score': round(duplication_score, 3),
            'consistency_score': round(consistency_score, 3),
            'organization_score': round(organization_score, 3),
            'overall_quality': round((consistency_score + organization_score) / 2, 3)
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get analysis summary.
        
        Returns:
            Summary dictionary
        """
        self.calculate_statistics()
        self.calculate_quality_metrics()
        
        return {
            'analysis_id': self.analysis_id,
            'timestamp': self.timestamp.isoformat(),
            'total_tags': self.total_tags,
            'clusters_found': self.total_clusters,
            'merge_recommendations': len(self.merge_recommendations),
            'safe_merges': len(self.safe_recommendations),
            'potential_tag_reduction': f"{self.statistics.get('potential_reduction', 0) * 100:.1f}%",
            'quality_score': self.quality_metrics.get('overall_quality', 0),
            'top_clusters': [
                {
                    'tags': [t.name for t in c.tags],
                    'size': c.size,
                    'representative': c.representative_tag.name if c.representative_tag else None
                }
                for c in sorted(self.clusters_found, key=lambda x: x.size, reverse=True)[:5]
            ]
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        self.calculate_statistics()
        self.calculate_quality_metrics()
        
        return {
            'analysis_id': self.analysis_id,
            'timestamp': self.timestamp.isoformat(),
            'total_tags': self.total_tags,
            'statistics': self.statistics,
            'quality_metrics': self.quality_metrics,
            'clusters': [c.to_dict() for c in self.clusters_found[:50]],  # Limit for large results
            'recommendations': [r.to_dict() for r in self.merge_recommendations[:20]],  # Limit
            'summary': self.get_summary()
        }


@dataclass
class TagMergeOperation:
    """Represents a tag merge operation.
    
    Attributes:
        operation_id: Unique operation identifier
        cluster: Tag cluster being merged
        documents_updated: List of document IDs updated
        started_at: When operation started
        completed_at: When operation completed
        status: Operation status
        errors: Any errors encountered
    """
    
    operation_id: str
    cluster: TagCluster
    documents_updated: List[int] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    status: str = "pending"
    errors: List[str] = field(default_factory=list)
    
    @property
    def is_complete(self) -> bool:
        """Check if operation is complete."""
        return self.status == "completed"
    
    @property
    def is_successful(self) -> bool:
        """Check if operation was successful."""
        return self.is_complete and len(self.errors) == 0
    
    @property
    def duration(self) -> Optional[float]:
        """Get operation duration in seconds."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def complete(self, status: str = "completed") -> None:
        """Mark operation as complete.
        
        Args:
            status: Final status
        """
        self.completed_at = datetime.now()
        self.status = status
    
    def add_error(self, error: str) -> None:
        """Add an error to the operation.
        
        Args:
            error: Error message
        """
        self.errors.append(error)
        self.status = "failed"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'operation_id': self.operation_id,
            'cluster': self.cluster.to_dict(),
            'documents_updated_count': len(self.documents_updated),
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration': self.duration,
            'status': self.status,
            'is_successful': self.is_successful,
            'errors': self.errors
        }