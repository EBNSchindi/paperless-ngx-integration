"""Service for analyzing document quality and metadata completeness.

This module provides comprehensive quality checks for documents including
OCR quality detection, metadata validation, and duplicate detection.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional, Set, Tuple

from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


class QualityIssue:
    """Represents a quality issue found in a document."""
    
    SEVERITY_LOW = 'low'
    SEVERITY_MEDIUM = 'medium'
    SEVERITY_HIGH = 'high'
    SEVERITY_CRITICAL = 'critical'
    
    def __init__(
        self,
        document_id: int,
        issue_type: str,
        severity: str,
        description: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize a quality issue.
        
        Args:
            document_id: Document ID
            issue_type: Type of issue (e.g., 'ocr_missing', 'metadata_incomplete')
            severity: Issue severity level
            description: Human-readable description
            details: Additional issue details
        """
        self.document_id = document_id
        self.issue_type = issue_type
        self.severity = severity
        self.description = description
        self.details = details or {}
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'document_id': self.document_id,
            'issue_type': self.issue_type,
            'severity': self.severity,
            'description': self.description,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }


class QualityAnalyzerService:
    """Service for analyzing document quality and detecting issues.
    
    This service provides:
    - OCR quality detection with configurable thresholds
    - Metadata completeness validation
    - Duplicate detection using fuzzy matching
    - Batch quality scanning with streaming results
    """
    
    # Issue type constants
    ISSUE_OCR_MISSING = 'ocr_missing'
    ISSUE_OCR_FAILED = 'ocr_failed'
    ISSUE_OCR_LOW_QUALITY = 'ocr_low_quality'
    ISSUE_METADATA_INCOMPLETE = 'metadata_incomplete'
    ISSUE_MISSING_CORRESPONDENT = 'missing_correspondent'
    ISSUE_MISSING_DOCUMENT_TYPE = 'missing_document_type'
    ISSUE_MISSING_TAGS = 'missing_tags'
    ISSUE_INVALID_DATE = 'invalid_date'
    ISSUE_POTENTIAL_DUPLICATE = 'potential_duplicate'
    ISSUE_FILENAME_MISMATCH = 'filename_mismatch'
    ISSUE_DESCRIPTION_TOO_LONG = 'description_too_long'
    
    def __init__(
        self,
        min_ocr_length: int = 50,
        min_tags_required: int = 3,
        max_description_length: int = 128,
        duplicate_similarity_threshold: float = 90.0
    ):
        """Initialize the quality analyzer service.
        
        Args:
            min_ocr_length: Minimum OCR text length to be considered valid
            min_tags_required: Minimum number of tags required
            max_description_length: Maximum allowed description length
            duplicate_similarity_threshold: Similarity threshold for duplicate detection (0-100)
        """
        self.min_ocr_length = min_ocr_length
        self.min_tags_required = min_tags_required
        self.max_description_length = max_description_length
        self.duplicate_similarity_threshold = duplicate_similarity_threshold
        
        logger.info(f"Initialized QualityAnalyzerService with OCR threshold: {min_ocr_length} chars")
    
    def analyze_document(self, document: Dict[str, Any]) -> List[QualityIssue]:
        """Analyze a single document for quality issues.
        
        Args:
            document: Document dictionary from Paperless API
            
        Returns:
            List of quality issues found
        """
        issues = []
        doc_id = document['id']
        
        # Check OCR quality
        ocr_issues = self._check_ocr_quality(document)
        issues.extend(ocr_issues)
        
        # Check metadata completeness
        metadata_issues = self._check_metadata_completeness(document)
        issues.extend(metadata_issues)
        
        # Check filename format
        filename_issues = self._check_filename_format(document)
        issues.extend(filename_issues)
        
        # Check description length
        description_issues = self._check_description(document)
        issues.extend(description_issues)
        
        if issues:
            logger.debug(f"Document {doc_id} has {len(issues)} quality issues")
        
        return issues
    
    def _check_ocr_quality(self, document: Dict[str, Any]) -> List[QualityIssue]:
        """Check OCR text quality.
        
        Args:
            document: Document dictionary
            
        Returns:
            List of OCR-related issues
        """
        issues = []
        doc_id = document['id']
        
        # Get OCR text from either 'content' or 'ocr' field
        ocr_text = document.get('content') or document.get('ocr') or ''
        
        if not ocr_text:
            issues.append(QualityIssue(
                document_id=doc_id,
                issue_type=self.ISSUE_OCR_MISSING,
                severity=QualityIssue.SEVERITY_CRITICAL,
                description="Dokument hat keinen OCR-Text",
                details={'has_ocr_field': 'ocr' in document or 'content' in document}
            ))
            return issues
        
        # Check OCR text length
        text_length = len(ocr_text.strip())
        if text_length < self.min_ocr_length:
            issues.append(QualityIssue(
                document_id=doc_id,
                issue_type=self.ISSUE_OCR_FAILED,
                severity=QualityIssue.SEVERITY_HIGH,
                description=f"OCR-Text zu kurz ({text_length} Zeichen)",
                details={'text_length': text_length, 'threshold': self.min_ocr_length}
            ))
            return issues
        
        # Check for OCR quality indicators
        quality_checks = self._assess_ocr_text_quality(ocr_text)
        
        if quality_checks['gibberish_ratio'] > 0.3:
            issues.append(QualityIssue(
                document_id=doc_id,
                issue_type=self.ISSUE_OCR_LOW_QUALITY,
                severity=QualityIssue.SEVERITY_MEDIUM,
                description="OCR-Text enthält möglicherweise Erkennungsfehler",
                details=quality_checks
            ))
        
        return issues
    
    def _assess_ocr_text_quality(self, text: str) -> Dict[str, Any]:
        """Assess the quality of OCR text.
        
        Args:
            text: OCR text to analyze
            
        Returns:
            Dictionary with quality metrics
        """
        # Clean text for analysis
        clean_text = text.strip().lower()
        words = clean_text.split()
        
        metrics = {
            'total_chars': len(text),
            'total_words': len(words),
            'avg_word_length': sum(len(w) for w in words) / len(words) if words else 0,
            'gibberish_ratio': 0,
            'special_char_ratio': 0,
            'uppercase_ratio': 0,
            'numeric_ratio': 0
        }
        
        if not text:
            return metrics
        
        # Count character types
        special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace())
        uppercase_chars = sum(1 for c in text if c.isupper())
        numeric_chars = sum(1 for c in text if c.isdigit())
        
        metrics['special_char_ratio'] = special_chars / len(text)
        metrics['uppercase_ratio'] = uppercase_chars / len(text)
        metrics['numeric_ratio'] = numeric_chars / len(text)
        
        # Detect gibberish (words with unusual character patterns)
        gibberish_pattern = re.compile(r'[^aeiouäöü]{5,}|[aeiouäöü]{4,}', re.IGNORECASE)
        gibberish_words = sum(1 for word in words if gibberish_pattern.search(word))
        metrics['gibberish_ratio'] = gibberish_words / len(words) if words else 0
        
        return metrics
    
    def _check_metadata_completeness(self, document: Dict[str, Any]) -> List[QualityIssue]:
        """Check if document metadata is complete.
        
        Args:
            document: Document dictionary
            
        Returns:
            List of metadata-related issues
        """
        issues = []
        doc_id = document['id']
        
        # Check correspondent
        if not document.get('correspondent'):
            issues.append(QualityIssue(
                document_id=doc_id,
                issue_type=self.ISSUE_MISSING_CORRESPONDENT,
                severity=QualityIssue.SEVERITY_HIGH,
                description="Korrespondent fehlt",
                details={'field': 'correspondent'}
            ))
        
        # Check document type
        if not document.get('document_type'):
            issues.append(QualityIssue(
                document_id=doc_id,
                issue_type=self.ISSUE_MISSING_DOCUMENT_TYPE,
                severity=QualityIssue.SEVERITY_MEDIUM,
                description="Dokumenttyp fehlt",
                details={'field': 'document_type'}
            ))
        
        # Check tags
        tags = document.get('tags', [])
        if len(tags) < self.min_tags_required:
            issues.append(QualityIssue(
                document_id=doc_id,
                issue_type=self.ISSUE_MISSING_TAGS,
                severity=QualityIssue.SEVERITY_LOW,
                description=f"Zu wenige Tags ({len(tags)}/{self.min_tags_required})",
                details={'current_tags': len(tags), 'required_tags': self.min_tags_required}
            ))
        
        # Check date fields
        if not document.get('created'):
            issues.append(QualityIssue(
                document_id=doc_id,
                issue_type=self.ISSUE_INVALID_DATE,
                severity=QualityIssue.SEVERITY_MEDIUM,
                description="Erstellungsdatum fehlt",
                details={'field': 'created'}
            ))
        
        # Calculate overall metadata completeness
        required_fields = ['correspondent', 'document_type', 'tags', 'created', 'title']
        missing_fields = [f for f in required_fields if not document.get(f)]
        
        if len(missing_fields) > 2:
            issues.append(QualityIssue(
                document_id=doc_id,
                issue_type=self.ISSUE_METADATA_INCOMPLETE,
                severity=QualityIssue.SEVERITY_MEDIUM,
                description=f"Metadaten unvollständig ({len(missing_fields)} Felder fehlen)",
                details={'missing_fields': missing_fields}
            ))
        
        return issues
    
    def _check_filename_format(self, document: Dict[str, Any]) -> List[QualityIssue]:
        """Check if filename follows expected format.
        
        Expected format: YYYY-MM-DD_Sender_Type
        
        Args:
            document: Document dictionary
            
        Returns:
            List of filename-related issues
        """
        issues = []
        doc_id = document['id']
        
        title = document.get('title', '')
        if not title:
            return issues
        
        # Check for date pattern at the beginning
        date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}_')
        if not date_pattern.match(title):
            issues.append(QualityIssue(
                document_id=doc_id,
                issue_type=self.ISSUE_FILENAME_MISMATCH,
                severity=QualityIssue.SEVERITY_LOW,
                description="Dateiname folgt nicht dem Standard-Format (YYYY-MM-DD_Sender_Typ)",
                details={'current_title': title, 'expected_format': 'YYYY-MM-DD_Sender_Typ'}
            ))
        
        return issues
    
    def _check_description(self, document: Dict[str, Any]) -> List[QualityIssue]:
        """Check description field constraints.
        
        Args:
            document: Document dictionary
            
        Returns:
            List of description-related issues
        """
        issues = []
        doc_id = document['id']
        
        # Check custom fields for description (assuming field ID 1)
        custom_fields = document.get('custom_fields', [])
        description_field = next((f for f in custom_fields if f.get('field') == 1), None)
        
        if description_field:
            description = description_field.get('value', '')
            if len(description) > self.max_description_length:
                issues.append(QualityIssue(
                    document_id=doc_id,
                    issue_type=self.ISSUE_DESCRIPTION_TOO_LONG,
                    severity=QualityIssue.SEVERITY_LOW,
                    description=f"Beschreibung zu lang ({len(description)}/{self.max_description_length} Zeichen)",
                    details={
                        'current_length': len(description),
                        'max_length': self.max_description_length,
                        'description_preview': description[:50] + '...'
                    }
                ))
        
        return issues
    
    def find_potential_duplicates(
        self,
        documents: List[Dict[str, Any]],
        compare_fields: List[str] = None
    ) -> List[Tuple[Dict[str, Any], Dict[str, Any], float]]:
        """Find potential duplicate documents using fuzzy matching.
        
        Args:
            documents: List of document dictionaries
            compare_fields: Fields to compare (default: title, correspondent, created)
            
        Returns:
            List of tuples (doc1, doc2, similarity_score)
        """
        if compare_fields is None:
            compare_fields = ['title', 'correspondent_name', 'created']
        
        duplicates = []
        processed_pairs = set()
        
        for i, doc1 in enumerate(documents):
            for doc2 in documents[i + 1:]:
                # Skip if already processed
                pair_key = tuple(sorted([doc1['id'], doc2['id']]))
                if pair_key in processed_pairs:
                    continue
                
                # Calculate similarity
                similarity = self._calculate_document_similarity(doc1, doc2, compare_fields)
                
                if similarity >= self.duplicate_similarity_threshold:
                    duplicates.append((doc1, doc2, similarity))
                    processed_pairs.add(pair_key)
                    
                    logger.info(
                        f"Potential duplicates found: "
                        f"Doc {doc1['id']} and Doc {doc2['id']} "
                        f"(similarity: {similarity:.1f}%)"
                    )
        
        return duplicates
    
    def _calculate_document_similarity(
        self,
        doc1: Dict[str, Any],
        doc2: Dict[str, Any],
        compare_fields: List[str]
    ) -> float:
        """Calculate similarity between two documents.
        
        Args:
            doc1: First document
            doc2: Second document
            compare_fields: Fields to compare
            
        Returns:
            Similarity score (0-100)
        """
        field_scores = []
        
        for field in compare_fields:
            val1 = str(doc1.get(field, '')).lower()
            val2 = str(doc2.get(field, '')).lower()
            
            if val1 and val2:
                # Use fuzzy string matching
                score = fuzz.ratio(val1, val2)
                field_scores.append(score)
            elif not val1 and not val2:
                # Both empty, consider as match
                field_scores.append(100)
            else:
                # One empty, one not
                field_scores.append(0)
        
        # Return average similarity
        return sum(field_scores) / len(field_scores) if field_scores else 0
    
    def scan_document_batch(
        self,
        documents: Generator[List[Dict[str, Any]], None, None],
        check_duplicates: bool = True
    ) -> Generator[QualityIssue, None, Dict[str, Any]]:
        """Scan document batches for quality issues using streaming.
        
        Args:
            documents: Generator yielding document batches
            check_duplicates: Whether to check for duplicates
            
        Yields:
            Individual quality issues as they are found
            
        Returns:
            Summary statistics after generator is exhausted
        """
        stats = {
            'total_documents': 0,
            'total_issues': 0,
            'issues_by_type': Counter(),
            'issues_by_severity': Counter(),
            'documents_with_issues': set()
        }
        
        all_documents = []  # For duplicate checking
        
        for batch in documents:
            for document in batch:
                stats['total_documents'] += 1
                
                # Analyze individual document
                issues = self.analyze_document(document)
                
                for issue in issues:
                    stats['total_issues'] += 1
                    stats['issues_by_type'][issue.issue_type] += 1
                    stats['issues_by_severity'][issue.severity] += 1
                    stats['documents_with_issues'].add(issue.document_id)
                    
                    yield issue
                
                # Store for duplicate checking
                if check_duplicates:
                    all_documents.append(document)
        
        # Check for duplicates after all documents are processed
        if check_duplicates and all_documents:
            logger.info(f"Checking {len(all_documents)} documents for duplicates...")
            duplicates = self.find_potential_duplicates(all_documents)
            
            for doc1, doc2, similarity in duplicates:
                issue = QualityIssue(
                    document_id=doc1['id'],
                    issue_type=self.ISSUE_POTENTIAL_DUPLICATE,
                    severity=QualityIssue.SEVERITY_MEDIUM,
                    description=f"Mögliches Duplikat von Dokument {doc2['id']} ({similarity:.1f}% Ähnlichkeit)",
                    details={
                        'duplicate_id': doc2['id'],
                        'similarity': similarity,
                        'doc1_title': doc1.get('title'),
                        'doc2_title': doc2.get('title')
                    }
                )
                stats['total_issues'] += 1
                stats['issues_by_type'][issue.issue_type] += 1
                stats['issues_by_severity'][issue.severity] += 1
                stats['documents_with_issues'].add(issue.document_id)
                
                yield issue
        
        # Convert set to count for final stats
        stats['documents_with_issues'] = len(stats['documents_with_issues'])
        stats['issues_by_type'] = dict(stats['issues_by_type'])
        stats['issues_by_severity'] = dict(stats['issues_by_severity'])
        
        logger.info(
            f"Quality scan complete: {stats['total_documents']} documents, "
            f"{stats['total_issues']} issues found in {stats['documents_with_issues']} documents"
        )
        
        return stats
    
    def generate_quality_report(
        self,
        issues: List[QualityIssue]
    ) -> Dict[str, Any]:
        """Generate a quality report from a list of issues.
        
        Args:
            issues: List of quality issues
            
        Returns:
            Report dictionary with statistics and recommendations
        """
        report = {
            'summary': {
                'total_issues': len(issues),
                'affected_documents': len(set(i.document_id for i in issues)),
                'critical_issues': sum(1 for i in issues if i.severity == QualityIssue.SEVERITY_CRITICAL),
                'high_issues': sum(1 for i in issues if i.severity == QualityIssue.SEVERITY_HIGH),
                'medium_issues': sum(1 for i in issues if i.severity == QualityIssue.SEVERITY_MEDIUM),
                'low_issues': sum(1 for i in issues if i.severity == QualityIssue.SEVERITY_LOW)
            },
            'by_type': {},
            'recommendations': [],
            'top_affected_documents': []
        }
        
        # Count issues by type
        issue_counts = Counter(i.issue_type for i in issues)
        report['by_type'] = dict(issue_counts.most_common())
        
        # Find most affected documents
        doc_issue_counts = Counter(i.document_id for i in issues)
        report['top_affected_documents'] = [
            {'document_id': doc_id, 'issue_count': count}
            for doc_id, count in doc_issue_counts.most_common(10)
        ]
        
        # Generate recommendations
        if issue_counts.get(self.ISSUE_OCR_MISSING, 0) > 0:
            report['recommendations'].append(
                "Führen Sie OCR für Dokumente ohne Text durch"
            )
        
        if issue_counts.get(self.ISSUE_OCR_FAILED, 0) > 0:
            report['recommendations'].append(
                "Überprüfen Sie Dokumente mit fehlgeschlagener OCR-Erkennung"
            )
        
        if issue_counts.get(self.ISSUE_MISSING_CORRESPONDENT, 0) > 5:
            report['recommendations'].append(
                "Viele Dokumente haben keinen Korrespondenten - verwenden Sie die automatische Zuordnung"
            )
        
        if issue_counts.get(self.ISSUE_POTENTIAL_DUPLICATE, 0) > 0:
            report['recommendations'].append(
                f"{issue_counts[self.ISSUE_POTENTIAL_DUPLICATE]} mögliche Duplikate gefunden - überprüfen und bereinigen"
            )
        
        if issue_counts.get(self.ISSUE_MISSING_TAGS, 0) > 10:
            report['recommendations'].append(
                "Verbessern Sie die Tag-Zuordnung für bessere Organisation"
            )
        
        return report