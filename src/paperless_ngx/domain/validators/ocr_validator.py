"""OCR quality validation module.

This module provides validation for OCR text quality, including
length checks, confidence scoring, and language detection.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class OCRValidator:
    """Validator for OCR text quality and characteristics.
    
    This validator checks:
    - Minimum text length requirements
    - OCR confidence scores
    - Language detection
    - Text quality indicators
    """
    
    # Common OCR error patterns
    OCR_ERROR_PATTERNS = [
        r'\b[0-9]{10,}\b',  # Long number sequences (often OCR errors)
        r'[^\w\s]{5,}',     # Excessive special characters
        r'(\w)\1{4,}',      # Repeated characters (e.g., "aaaaa")
        r'[A-Z]{20,}',      # Long uppercase sequences
    ]
    
    # German stop words for language detection
    GERMAN_STOP_WORDS = {
        'der', 'die', 'das', 'den', 'dem', 'des', 'ein', 'eine', 'einen',
        'einem', 'einer', 'eines', 'und', 'oder', 'aber', 'als', 'am',
        'an', 'auf', 'aus', 'bei', 'bis', 'durch', 'für', 'gegen', 'in',
        'mit', 'nach', 'seit', 'über', 'um', 'unter', 'von', 'vor', 'zu',
        'zur', 'zum', 'ich', 'du', 'er', 'sie', 'es', 'wir', 'ihr', 'Sie',
        'ist', 'sind', 'war', 'waren', 'hat', 'haben', 'hatte', 'hatten',
        'wird', 'werden', 'wurde', 'wurden', 'kann', 'können', 'muss',
        'müssen', 'soll', 'sollen', 'will', 'wollen', 'nicht', 'kein',
        'keine', 'sehr', 'auch', 'noch', 'nur', 'schon', 'immer', 'mehr'
    }
    
    # English stop words for comparison
    ENGLISH_STOP_WORDS = {
        'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
        'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
        'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her',
        'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there',
        'their', 'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get',
        'which', 'go', 'me', 'when', 'make', 'can', 'like', 'time', 'no',
        'just', 'him', 'know', 'take', 'people', 'into', 'year', 'your',
        'good', 'some', 'could', 'them', 'see', 'other', 'than', 'then',
        'now', 'look', 'only', 'come', 'its', 'over', 'think', 'also'
    }
    
    def __init__(
        self,
        min_length: int = 50,
        min_confidence: float = 0.7,
        detect_language: bool = True
    ):
        """Initialize OCR validator.
        
        Args:
            min_length: Minimum required text length
            min_confidence: Minimum confidence score (0-1)
            detect_language: Whether to perform language detection
        """
        self.min_length = min_length
        self.min_confidence = min_confidence
        self.detect_language = detect_language
    
    def validate(
        self,
        text: str,
        confidence: Optional[float] = None
    ) -> Tuple[bool, List[str], Dict[str, any]]:
        """Validate OCR text quality.
        
        Args:
            text: OCR text to validate
            confidence: Optional OCR confidence score (0-1)
            
        Returns:
            Tuple of (is_valid, errors, metrics)
        """
        errors = []
        metrics = {
            'text_length': len(text) if text else 0,
            'confidence': confidence,
            'language': None,
            'quality_score': 0.0,
            'word_count': 0,
            'avg_word_length': 0.0,
            'special_char_ratio': 0.0,
            'uppercase_ratio': 0.0,
            'numeric_ratio': 0.0
        }
        
        # Check if text exists
        if not text:
            errors.append("Kein OCR-Text vorhanden")
            return False, errors, metrics
        
        # Clean and prepare text
        cleaned_text = text.strip()
        metrics['text_length'] = len(cleaned_text)
        
        # Check minimum length
        if metrics['text_length'] < self.min_length:
            errors.append(
                f"OCR-Text zu kurz: {metrics['text_length']} Zeichen "
                f"(mindestens {self.min_length} erforderlich)"
            )
        
        # Check confidence score
        if confidence is not None:
            metrics['confidence'] = confidence
            if confidence < self.min_confidence:
                errors.append(
                    f"OCR-Konfidenz zu niedrig: {confidence:.2%} "
                    f"(mindestens {self.min_confidence:.2%} erforderlich)"
                )
        
        # Calculate text metrics
        metrics.update(self._calculate_text_metrics(cleaned_text))
        
        # Check for OCR error patterns
        error_patterns_found = self._check_ocr_error_patterns(cleaned_text)
        if error_patterns_found:
            errors.append(f"Mögliche OCR-Fehler erkannt: {', '.join(error_patterns_found)}")
        
        # Detect language
        if self.detect_language:
            language, lang_confidence = self._detect_language(cleaned_text)
            metrics['language'] = language
            metrics['language_confidence'] = lang_confidence
            
            if language == 'unknown':
                errors.append("Sprache konnte nicht erkannt werden")
            elif language != 'german' and lang_confidence > 0.7:
                errors.append(f"Text ist möglicherweise nicht auf Deutsch (erkannt: {language})")
        
        # Calculate overall quality score
        metrics['quality_score'] = self._calculate_quality_score(metrics, len(errors))
        
        # Determine if valid
        is_valid = len(errors) == 0 or (
            metrics['quality_score'] >= 0.5 and
            metrics['text_length'] >= self.min_length
        )
        
        return is_valid, errors, metrics
    
    def _calculate_text_metrics(self, text: str) -> Dict[str, float]:
        """Calculate various text quality metrics.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary of text metrics
        """
        if not text:
            return {}
        
        # Word analysis
        words = text.split()
        word_count = len(words)
        avg_word_length = sum(len(word) for word in words) / word_count if word_count > 0 else 0
        
        # Character type analysis
        total_chars = len(text)
        special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace())
        uppercase_chars = sum(1 for c in text if c.isupper())
        numeric_chars = sum(1 for c in text if c.isdigit())
        
        return {
            'word_count': word_count,
            'avg_word_length': round(avg_word_length, 2),
            'special_char_ratio': round(special_chars / total_chars, 3) if total_chars > 0 else 0,
            'uppercase_ratio': round(uppercase_chars / total_chars, 3) if total_chars > 0 else 0,
            'numeric_ratio': round(numeric_chars / total_chars, 3) if total_chars > 0 else 0
        }
    
    def _check_ocr_error_patterns(self, text: str) -> List[str]:
        """Check for common OCR error patterns.
        
        Args:
            text: Text to check
            
        Returns:
            List of detected error pattern descriptions
        """
        errors_found = []
        
        for pattern in self.OCR_ERROR_PATTERNS:
            if re.search(pattern, text):
                if '0-9' in pattern and '10' in pattern:
                    errors_found.append("Übermäßig lange Zahlenfolgen")
                elif r'[^\w\s]' in pattern:
                    errors_found.append("Zu viele Sonderzeichen")
                elif r'(\w)\1' in pattern:
                    errors_found.append("Wiederholte Zeichen")
                elif 'A-Z' in pattern:
                    errors_found.append("Lange Großbuchstabenfolgen")
        
        return errors_found
    
    def _detect_language(self, text: str) -> Tuple[str, float]:
        """Detect the language of the text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (language, confidence)
        """
        if not text:
            return 'unknown', 0.0
        
        # Convert to lowercase and extract words
        words = set(word.lower() for word in re.findall(r'\b[a-zäöüß]+\b', text.lower()))
        
        if not words:
            return 'unknown', 0.0
        
        # Count stop words
        german_count = len(words & self.GERMAN_STOP_WORDS)
        english_count = len(words & self.ENGLISH_STOP_WORDS)
        total_words = len(words)
        
        # Calculate ratios
        german_ratio = german_count / total_words if total_words > 0 else 0
        english_ratio = english_count / total_words if total_words > 0 else 0
        
        # Determine language
        if german_ratio > english_ratio and german_ratio > 0.05:
            return 'german', min(german_ratio * 5, 1.0)  # Scale up confidence
        elif english_ratio > german_ratio and english_ratio > 0.05:
            return 'english', min(english_ratio * 5, 1.0)
        else:
            return 'unknown', 0.0
    
    def _calculate_quality_score(
        self,
        metrics: Dict[str, any],
        error_count: int
    ) -> float:
        """Calculate overall OCR quality score.
        
        Args:
            metrics: Text metrics
            error_count: Number of validation errors
            
        Returns:
            Quality score between 0 and 1
        """
        score = 1.0
        
        # Penalize for errors
        score -= error_count * 0.15
        
        # Penalize for poor metrics
        if metrics.get('special_char_ratio', 0) > 0.2:
            score -= 0.1
        if metrics.get('uppercase_ratio', 0) > 0.5:
            score -= 0.1
        if metrics.get('numeric_ratio', 0) > 0.3:
            score -= 0.1
        if metrics.get('avg_word_length', 0) < 3 or metrics.get('avg_word_length', 0) > 15:
            score -= 0.1
        if metrics.get('word_count', 0) < 10:
            score -= 0.2
        
        # Bonus for good confidence
        if metrics.get('confidence') and metrics['confidence'] > 0.9:
            score += 0.1
        
        # Bonus for German language
        if metrics.get('language') == 'german':
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def validate_batch(
        self,
        documents: List[Dict[str, any]]
    ) -> List[Dict[str, any]]:
        """Validate OCR quality for multiple documents.
        
        Args:
            documents: List of documents with OCR text
            
        Returns:
            List of validation results
        """
        results = []
        
        for doc in documents:
            doc_id = doc.get('id')
            ocr_text = doc.get('content') or doc.get('ocr', '')
            confidence = doc.get('ocr_confidence')
            
            is_valid, errors, metrics = self.validate(ocr_text, confidence)
            
            results.append({
                'document_id': doc_id,
                'is_valid': is_valid,
                'errors': errors,
                'metrics': metrics,
                'quality_score': metrics.get('quality_score', 0.0)
            })
            
            if not is_valid:
                logger.warning(
                    f"Document {doc_id} failed OCR validation: {', '.join(errors)}"
                )
        
        return results
    
    def get_quality_summary(
        self,
        validation_results: List[Dict[str, any]]
    ) -> Dict[str, any]:
        """Generate summary statistics from validation results.
        
        Args:
            validation_results: List of validation results
            
        Returns:
            Summary statistics
        """
        if not validation_results:
            return {
                'total_documents': 0,
                'valid_documents': 0,
                'invalid_documents': 0,
                'average_quality_score': 0.0,
                'common_errors': {},
                'language_distribution': {}
            }
        
        valid_count = sum(1 for r in validation_results if r['is_valid'])
        invalid_count = len(validation_results) - valid_count
        
        # Calculate average quality score
        quality_scores = [r['metrics']['quality_score'] for r in validation_results]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        # Count common errors
        error_counts = {}
        for result in validation_results:
            for error in result.get('errors', []):
                error_type = error.split(':')[0] if ':' in error else error
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        # Language distribution
        language_counts = {}
        for result in validation_results:
            language = result.get('metrics', {}).get('language', 'unknown')
            language_counts[language] = language_counts.get(language, 0) + 1
        
        return {
            'total_documents': len(validation_results),
            'valid_documents': valid_count,
            'invalid_documents': invalid_count,
            'validation_rate': valid_count / len(validation_results) if validation_results else 0.0,
            'average_quality_score': round(avg_quality, 3),
            'common_errors': dict(sorted(error_counts.items(), key=lambda x: x[1], reverse=True)),
            'language_distribution': language_counts,
            'quality_distribution': {
                'excellent': sum(1 for s in quality_scores if s >= 0.9),
                'good': sum(1 for s in quality_scores if 0.7 <= s < 0.9),
                'fair': sum(1 for s in quality_scores if 0.5 <= s < 0.7),
                'poor': sum(1 for s in quality_scores if s < 0.5)
            }
        }