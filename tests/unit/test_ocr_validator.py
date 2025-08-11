"""Comprehensive unit tests for OCR validator module.

Tests OCR text quality validation including length checks, confidence scoring,
language detection, and OCR artifact detection.
"""

import pytest
from unittest.mock import Mock, patch

from src.paperless_ngx.domain.validators.ocr_validator import OCRValidator


class TestOCRValidator:
    """Test suite for OCR text validation."""
    
    @pytest.fixture
    def validator(self):
        """Create OCR validator instance with default settings."""
        return OCRValidator(
            min_length=50,
            min_confidence=0.7,
            detect_language=True
        )
    
    @pytest.fixture
    def validator_no_language(self):
        """Create OCR validator without language detection."""
        return OCRValidator(
            min_length=50,
            min_confidence=0.7,
            detect_language=False
        )
    
    # ============= Minimum Length Tests =============
    
    def test_validate_text_too_short(self, validator):
        """Test validation fails for text shorter than minimum."""
        text = "Too short"  # 9 characters
        is_valid, errors, metrics = validator.validate(text)
        
        assert not is_valid
        assert any("OCR-Text zu kurz" in error for error in errors)
        assert metrics['text_length'] == 9
        assert metrics['quality_score'] < 0.5
    
    def test_validate_text_exactly_minimum_length(self, validator):
        """Test validation passes for text exactly at minimum length."""
        text = "a" * 50  # Exactly 50 characters
        is_valid, errors, metrics = validator.validate(text)
        
        # May have other issues but length should be OK
        assert not any("OCR-Text zu kurz" in error for error in errors)
        assert metrics['text_length'] == 50
    
    def test_validate_empty_text(self, validator):
        """Test validation fails for empty text."""
        is_valid, errors, metrics = validator.validate("")
        
        assert not is_valid
        assert "Kein OCR-Text vorhanden" in errors
        assert metrics['text_length'] == 0
        assert metrics['quality_score'] == 0.0
    
    def test_validate_none_text(self, validator):
        """Test validation fails for None text."""
        is_valid, errors, metrics = validator.validate(None)
        
        assert not is_valid
        assert "Kein OCR-Text vorhanden" in errors
        assert metrics['text_length'] == 0
    
    # ============= Confidence Score Tests =============
    
    def test_validate_low_confidence(self, validator):
        """Test validation fails for low confidence score."""
        text = "This is a valid length text with enough characters to pass the minimum requirement"
        is_valid, errors, metrics = validator.validate(text, confidence=0.5)
        
        assert any("OCR-Konfidenz zu niedrig" in error for error in errors)
        assert metrics['confidence'] == 0.5
    
    def test_validate_high_confidence(self, validator):
        """Test validation passes for high confidence score."""
        text = "Dies ist ein deutscher Text mit ausreichender Länge und guter Qualität für die Validierung"
        is_valid, errors, metrics = validator.validate(text, confidence=0.95)
        
        assert not any("OCR-Konfidenz zu niedrig" in error for error in errors)
        assert metrics['confidence'] == 0.95
        assert metrics['quality_score'] > 0.5
    
    def test_validate_exactly_minimum_confidence(self, validator):
        """Test validation passes for confidence exactly at minimum."""
        text = "Dies ist ein deutscher Text mit ausreichender Länge und guter Qualität für die Validierung"
        is_valid, errors, metrics = validator.validate(text, confidence=0.7)
        
        assert not any("OCR-Konfidenz zu niedrig" in error for error in errors)
        assert metrics['confidence'] == 0.7
    
    def test_validate_no_confidence_provided(self, validator):
        """Test validation handles missing confidence score."""
        text = "Dies ist ein deutscher Text mit ausreichender Länge und guter Qualität für die Validierung"
        is_valid, errors, metrics = validator.validate(text, confidence=None)
        
        assert not any("OCR-Konfidenz" in error for error in errors)
        assert metrics['confidence'] is None
    
    # ============= Language Detection Tests =============
    
    def test_detect_german_text(self, validator, german_text_sample):
        """Test German language detection."""
        is_valid, errors, metrics = validator.validate(german_text_sample)
        
        assert metrics['language'] == 'german'
        assert metrics['language_confidence'] > 0.5
        assert not any("nicht auf Deutsch" in error for error in errors)
    
    def test_detect_english_text(self, validator, english_text_sample):
        """Test English language detection."""
        is_valid, errors, metrics = validator.validate(english_text_sample)
        
        assert metrics['language'] == 'english'
        assert any("nicht auf Deutsch" in error for error in errors)
    
    def test_detect_mixed_language_text(self, validator):
        """Test mixed language detection."""
        mixed_text = """
        This is English text. Dies ist deutscher Text. 
        The system should detect mixed content und sollte gemischten Inhalt erkennen.
        """
        is_valid, errors, metrics = validator.validate(mixed_text)
        
        # Should detect dominant language
        assert metrics['language'] in ['german', 'english']
        assert metrics['language_confidence'] > 0
    
    def test_detect_unknown_language(self, validator):
        """Test unknown language detection."""
        unknown_text = "あいうえお かきくけこ さしすせそ" * 10  # Japanese text
        is_valid, errors, metrics = validator.validate(unknown_text)
        
        assert metrics['language'] == 'unknown'
        assert metrics['language_confidence'] == 0.0
        assert "Sprache konnte nicht erkannt werden" in errors
    
    def test_language_detection_disabled(self, validator_no_language):
        """Test validator with language detection disabled."""
        text = "This is English text that should not trigger language detection"
        is_valid, errors, metrics = validator_no_language.validate(text)
        
        assert 'language' not in metrics or metrics['language'] is None
        assert not any("Sprache" in error for error in errors)
    
    # ============= OCR Error Pattern Tests =============
    
    def test_detect_long_number_sequences(self, validator):
        """Test detection of excessively long number sequences."""
        text = "Valid text with 12345678901234567890 long number sequence and more text to meet minimum"
        is_valid, errors, metrics = validator.validate(text)
        
        assert any("Mögliche OCR-Fehler erkannt" in error for error in errors)
        assert any("Übermäßig lange Zahlenfolgen" in str(errors) for error in errors)
    
    def test_detect_excessive_special_characters(self, validator):
        """Test detection of excessive special characters."""
        text = "Text with &&&&&&&&&&& excessive special characters ############ and more valid content here"
        is_valid, errors, metrics = validator.validate(text)
        
        assert any("Mögliche OCR-Fehler erkannt" in error for error in errors)
        assert any("Zu viele Sonderzeichen" in str(errors) for error in errors)
    
    def test_detect_repeated_characters(self, validator):
        """Test detection of repeated characters."""
        text = "Text with aaaaaaaa repeated characters and bbbbbbb more repeated chars with valid content"
        is_valid, errors, metrics = validator.validate(text)
        
        assert any("Mögliche OCR-Fehler erkannt" in error for error in errors)
        assert any("Wiederholte Zeichen" in str(errors) for error in errors)
    
    def test_detect_long_uppercase_sequences(self, validator):
        """Test detection of long uppercase sequences."""
        text = "Text with AAAAAAAAAAAAAAAAAAAAAAAAAA long uppercase sequence and more normal text content"
        is_valid, errors, metrics = validator.validate(text)
        
        assert any("Mögliche OCR-Fehler erkannt" in error for error in errors)
        assert any("Lange Großbuchstabenfolgen" in str(errors) for error in errors)
    
    def test_detect_multiple_ocr_errors(self, validator, ocr_error_text_sample):
        """Test detection of multiple OCR error patterns."""
        # Extend the sample to meet minimum length
        text = ocr_error_text_sample + " more text" * 10
        is_valid, errors, metrics = validator.validate(text)
        
        assert not is_valid
        assert any("Mögliche OCR-Fehler erkannt" in error for error in errors)
        assert metrics['quality_score'] < 0.5
    
    # ============= Text Metrics Tests =============
    
    def test_calculate_text_metrics(self, validator):
        """Test calculation of various text quality metrics."""
        text = "Dies ist ein Beispieltext! Mit Zahlen 123 und GROSSBUCHSTABEN."
        is_valid, errors, metrics = validator.validate(text)
        
        assert metrics['word_count'] > 0
        assert metrics['avg_word_length'] > 0
        assert 0 <= metrics['special_char_ratio'] <= 1
        assert 0 <= metrics['uppercase_ratio'] <= 1
        assert 0 <= metrics['numeric_ratio'] <= 1
    
    def test_metrics_for_high_special_char_ratio(self, validator):
        """Test quality score penalty for high special character ratio."""
        text = "Text!!! with@@@ many### special$$$ characters%%% throughout^^^ the&&& entire*** content((("
        is_valid, errors, metrics = validator.validate(text)
        
        assert metrics['special_char_ratio'] > 0.2
        assert metrics['quality_score'] < 0.8
    
    def test_metrics_for_high_uppercase_ratio(self, validator):
        """Test quality score penalty for high uppercase ratio."""
        text = "THIS TEXT IS MOSTLY IN UPPERCASE WHICH IS UNUSUAL FOR NORMAL DOCUMENTS"
        is_valid, errors, metrics = validator.validate(text)
        
        assert metrics['uppercase_ratio'] > 0.5
        assert metrics['quality_score'] < 0.8
    
    def test_metrics_for_high_numeric_ratio(self, validator):
        """Test quality score penalty for high numeric ratio."""
        text = "12345 67890 12345 67890 12345 67890 12345 67890 12345 67890 12345 67890"
        is_valid, errors, metrics = validator.validate(text)
        
        assert metrics['numeric_ratio'] > 0.3
        assert metrics['quality_score'] < 0.8
    
    # ============= Quality Score Tests =============
    
    def test_quality_score_perfect_document(self, validator):
        """Test quality score for a perfect German document."""
        text = """
        Dies ist eine Rechnung von der Firma Beispiel GmbH für die Lieferung 
        von Büromaterialien. Die Bestellung wurde am fünfzehnten März 
        zweitausendvierundzwanzig aufgegeben und umfasst verschiedene Artikel 
        wie Papier, Stifte und Ordner. Der Gesamtbetrag beläuft sich auf 
        hundertfünfzig Euro inklusive Mehrwertsteuer.
        """
        is_valid, errors, metrics = validator.validate(text, confidence=0.95)
        
        assert is_valid
        assert len(errors) == 0
        assert metrics['quality_score'] >= 0.8
        assert metrics['language'] == 'german'
    
    def test_quality_score_poor_document(self, validator):
        """Test quality score for a poor quality document."""
        text = "SHORT" + "!!!" * 20  # Short with many special chars
        is_valid, errors, metrics = validator.validate(text, confidence=0.3)
        
        assert not is_valid
        assert len(errors) > 0
        assert metrics['quality_score'] < 0.5
    
    def test_quality_score_with_errors(self, validator):
        """Test quality score decreases with validation errors."""
        text = "1234567890" * 10  # All numbers, will trigger errors
        is_valid, errors, metrics = validator.validate(text)
        
        assert len(errors) > 0
        assert metrics['quality_score'] < 0.7
    
    # ============= Batch Validation Tests =============
    
    def test_validate_batch_empty_list(self, validator):
        """Test batch validation with empty document list."""
        results = validator.validate_batch([])
        
        assert results == []
    
    def test_validate_batch_multiple_documents(self, validator, sample_documents):
        """Test batch validation with multiple documents."""
        results = validator.validate_batch(sample_documents)
        
        assert len(results) == len(sample_documents)
        
        # Check each result has required fields
        for result in results:
            assert 'document_id' in result
            assert 'is_valid' in result
            assert 'errors' in result
            assert 'metrics' in result
            assert 'quality_score' in result
    
    def test_validate_batch_with_various_quality(self, validator):
        """Test batch validation with documents of various quality."""
        documents = [
            {
                'id': 1,
                'content': 'Dies ist ein guter deutscher Text mit ausreichender Länge und Qualität für Tests.',
                'ocr_confidence': 0.95
            },
            {
                'id': 2,
                'content': 'Short',
                'ocr_confidence': 0.3
            },
            {
                'id': 3,
                'ocr': 'Text from ocr field instead of content field with enough length for validation',
                'ocr_confidence': 0.8
            },
            {
                'id': 4,
                'content': None,
                'ocr': None
            }
        ]
        
        results = validator.validate_batch(documents)
        
        assert results[0]['is_valid'] is True  # Good document
        assert results[1]['is_valid'] is False  # Too short
        assert results[2]['is_valid'] is True  # From OCR field
        assert results[3]['is_valid'] is False  # No text
    
    # ============= Summary Statistics Tests =============
    
    def test_get_quality_summary_empty(self, validator):
        """Test quality summary for empty results."""
        summary = validator.get_quality_summary([])
        
        assert summary['total_documents'] == 0
        assert summary['valid_documents'] == 0
        assert summary['invalid_documents'] == 0
        assert summary['average_quality_score'] == 0.0
        assert summary['common_errors'] == {}
        assert summary['language_distribution'] == {}
    
    def test_get_quality_summary_with_results(self, validator):
        """Test quality summary generation."""
        validation_results = [
            {
                'is_valid': True,
                'errors': [],
                'metrics': {'quality_score': 0.9, 'language': 'german'}
            },
            {
                'is_valid': False,
                'errors': ['OCR-Text zu kurz: 10 Zeichen'],
                'metrics': {'quality_score': 0.3, 'language': 'english'}
            },
            {
                'is_valid': False,
                'errors': ['OCR-Text zu kurz: 5 Zeichen', 'Sprache konnte nicht erkannt werden'],
                'metrics': {'quality_score': 0.2, 'language': 'unknown'}
            }
        ]
        
        summary = validator.get_quality_summary(validation_results)
        
        assert summary['total_documents'] == 3
        assert summary['valid_documents'] == 1
        assert summary['invalid_documents'] == 2
        assert summary['validation_rate'] == pytest.approx(1/3, rel=0.01)
        assert summary['average_quality_score'] == pytest.approx(0.467, rel=0.01)
        assert 'OCR-Text zu kurz' in summary['common_errors']
        assert summary['common_errors']['OCR-Text zu kurz'] == 2
        assert summary['language_distribution']['german'] == 1
        assert summary['language_distribution']['english'] == 1
        assert summary['language_distribution']['unknown'] == 1
    
    def test_quality_distribution_in_summary(self, validator):
        """Test quality distribution categorization in summary."""
        validation_results = [
            {'is_valid': True, 'errors': [], 'metrics': {'quality_score': 0.95}},
            {'is_valid': True, 'errors': [], 'metrics': {'quality_score': 0.85}},
            {'is_valid': True, 'errors': [], 'metrics': {'quality_score': 0.75}},
            {'is_valid': False, 'errors': ['error'], 'metrics': {'quality_score': 0.6}},
            {'is_valid': False, 'errors': ['error'], 'metrics': {'quality_score': 0.4}},
        ]
        
        summary = validator.get_quality_summary(validation_results)
        
        assert summary['quality_distribution']['excellent'] == 1  # >= 0.9
        assert summary['quality_distribution']['good'] == 2  # 0.7-0.9
        assert summary['quality_distribution']['fair'] == 1  # 0.5-0.7
        assert summary['quality_distribution']['poor'] == 1  # < 0.5
    
    # ============= Edge Cases and Special Scenarios =============
    
    @pytest.mark.parametrize("min_length,text,expected_valid", [
        (0, "", True),  # No minimum length
        (10, "123456789", False),  # Just under minimum
        (10, "1234567890", True),  # Exactly minimum
        (100, "a" * 99, False),  # Large minimum, just under
        (100, "a" * 100, True),  # Large minimum, exactly
    ])
    def test_various_minimum_lengths(self, min_length, text, expected_valid):
        """Test validator with various minimum length settings."""
        validator = OCRValidator(min_length=min_length, min_confidence=0.5)
        is_valid, errors, metrics = validator.validate(text)
        
        if expected_valid:
            assert not any("OCR-Text zu kurz" in error for error in errors)
        else:
            assert any("OCR-Text zu kurz" in error for error in errors)
    
    @pytest.mark.parametrize("confidence,min_conf,expected_error", [
        (0.9, 0.8, False),  # Above minimum
        (0.8, 0.8, False),  # Exactly minimum
        (0.79, 0.8, True),  # Just below minimum
        (0.0, 0.5, True),  # Zero confidence
        (1.0, 0.9, False),  # Perfect confidence
    ])
    def test_various_confidence_thresholds(self, confidence, min_conf, expected_error):
        """Test validator with various confidence thresholds."""
        validator = OCRValidator(min_length=10, min_confidence=min_conf)
        text = "This is a valid test text with sufficient length"
        is_valid, errors, metrics = validator.validate(text, confidence=confidence)
        
        has_confidence_error = any("OCR-Konfidenz zu niedrig" in error for error in errors)
        assert has_confidence_error == expected_error
    
    def test_whitespace_handling(self, validator):
        """Test handling of various whitespace in text."""
        text = "   \n\n  Text   with   various\t\twhitespace   \n\n   patterns   " + " " * 50
        is_valid, errors, metrics = validator.validate(text)
        
        # Should handle whitespace gracefully
        assert metrics['text_length'] > 0
        assert metrics['word_count'] > 0
    
    def test_unicode_text_handling(self, validator):
        """Test handling of Unicode characters."""
        text = "Text with emojis 😀🎉 and special chars € £ ¥ § ¶ with enough length for validation"
        is_valid, errors, metrics = validator.validate(text)
        
        # Should handle Unicode gracefully
        assert metrics['text_length'] > 0
        assert metrics['word_count'] > 0
    
    def test_very_long_text(self, validator):
        """Test handling of very long text."""
        text = "Dies ist ein sehr langer Text. " * 1000  # Very long text
        is_valid, errors, metrics = validator.validate(text)
        
        # Should handle long text efficiently
        assert metrics['text_length'] > 10000
        assert metrics['word_count'] > 1000
        assert is_valid  # Should be valid if it's good German text
    
    def test_text_with_only_numbers(self, validator):
        """Test text containing only numbers."""
        text = "1234567890 " * 10
        is_valid, errors, metrics = validator.validate(text)
        
        assert metrics['numeric_ratio'] == pytest.approx(0.909, rel=0.01)  # High numeric ratio
        assert metrics['quality_score'] < 0.7  # Penalized for high numeric content
    
    def test_text_with_mixed_case_tags(self, validator):
        """Test language detection with mixed case."""
        text = "Der DIE das UND oder ABER für MIT von BEI nach AUS auf ÜBER zusätzlicher Text hier"
        is_valid, errors, metrics = validator.validate(text)
        
        # Should still detect German despite mixed case
        assert metrics['language'] == 'german'