"""Comprehensive unit tests for metadata validator module.

Tests document metadata validation according to business rules,
especially the German sender/recipient rules and tag validation.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.paperless_ngx.domain.validators.metadata_validator import MetadataValidator


class TestMetadataValidator:
    """Test suite for document metadata validation."""
    
    @pytest.fixture
    def validator(self):
        """Create metadata validator with default settings."""
        return MetadataValidator(
            min_tags=3,
            max_tags=7,
            max_description_length=128,
            validate_german=True
        )
    
    @pytest.fixture
    def validator_no_german(self):
        """Create metadata validator without German validation."""
        return MetadataValidator(
            min_tags=3,
            max_tags=7,
            max_description_length=128,
            validate_german=False
        )
    
    @pytest.fixture
    def valid_metadata(self):
        """Create valid metadata sample."""
        return {
            'title': 'Rechnung Amazon März 2024',
            'correspondent': 'Amazon EU S.a.r.l.',
            'document_type': 'Rechnung',
            'tags': ['Online-Shopping', 'Elektronik', '2024', 'Amazon', 'März'],
            'description': 'Rechnung für Elektronikbestellung im März',
            'created': '2024-03-15T10:00:00Z',
            'modified': '2024-03-15T10:30:00Z',
            'filename': '2024-03-15_Amazon_Rechnung.pdf'
        }
    
    # ============= Required Fields Tests =============
    
    def test_validate_all_required_fields_present(self, validator, valid_metadata):
        """Test validation passes when all required fields are present."""
        is_valid, errors, suggestions = validator.validate(valid_metadata)
        
        assert is_valid
        assert len(errors) == 0
        assert not any("Pflichtfeld fehlt" in error for error in errors)
    
    def test_validate_missing_title(self, validator):
        """Test validation fails when title is missing."""
        metadata = {
            'correspondent': 'Test Sender',
            'document_type': 'Rechnung',
            'tags': ['tag1', 'tag2', 'tag3']
        }
        is_valid, errors, suggestions = validator.validate(metadata, strict=True)
        
        assert not is_valid
        assert any("Pflichtfeld fehlt: title" in error for error in errors)
    
    def test_validate_missing_correspondent(self, validator):
        """Test validation fails when correspondent is missing."""
        metadata = {
            'title': 'Test Document',
            'document_type': 'Rechnung',
            'tags': ['tag1', 'tag2', 'tag3']
        }
        is_valid, errors, suggestions = validator.validate(metadata, strict=True)
        
        assert not is_valid
        assert any("Pflichtfeld fehlt: correspondent" in error for error in errors)
    
    def test_validate_missing_document_type(self, validator):
        """Test validation fails when document type is missing."""
        metadata = {
            'title': 'Test Document',
            'correspondent': 'Test Sender',
            'tags': ['tag1', 'tag2', 'tag3']
        }
        is_valid, errors, suggestions = validator.validate(metadata, strict=True)
        
        assert not is_valid
        assert any("Pflichtfeld fehlt: document_type" in error for error in errors)
    
    def test_validate_non_strict_mode(self, validator):
        """Test validation in non-strict mode treats missing fields as warnings."""
        metadata = {
            'title': 'Test Document'
        }
        is_valid, errors, suggestions = validator.validate(metadata, strict=False)
        
        # Should have warnings but not be invalid
        assert any("Empfohlenes Feld fehlt" in error for error in errors)
    
    # ============= Title Validation Tests =============
    
    def test_validate_title_too_short(self, validator):
        """Test validation fails for title too short."""
        metadata = {
            'title': 'AB',  # 2 characters
            'correspondent': 'Test Sender',
            'document_type': 'Rechnung',
            'tags': ['tag1', 'tag2', 'tag3']
        }
        is_valid, errors, suggestions = validator.validate(metadata)
        
        assert not is_valid
        assert any("Titel zu kurz" in error for error in errors)
    
    def test_validate_title_too_long(self, validator):
        """Test validation fails for title too long."""
        metadata = {
            'title': 'A' * 256,  # 256 characters
            'correspondent': 'Test Sender',
            'document_type': 'Rechnung',
            'tags': ['tag1', 'tag2', 'tag3']
        }
        is_valid, errors, suggestions = validator.validate(metadata)
        
        assert not is_valid
        assert any("Titel zu lang" in error for error in errors)
    
    @pytest.mark.parametrize("placeholder_title", [
        "untitled",
        "untitled_document",
        "document1",
        "document",
        "scan001",
        "scan_001",
        "img_001",
        "img001",
        "12345",
        "000001"
    ])
    def test_validate_placeholder_titles(self, validator, placeholder_title):
        """Test detection of placeholder titles."""
        metadata = {
            'title': placeholder_title,
            'correspondent': 'Test Sender',
            'document_type': 'Rechnung',
            'tags': ['tag1', 'tag2', 'tag3']
        }
        is_valid, errors, suggestions = validator.validate(metadata)
        
        assert not is_valid
        assert any("Titel scheint ein Platzhalter zu sein" in error for error in errors)
    
    def test_validate_empty_title(self, validator):
        """Test validation fails for empty title."""
        metadata = {
            'title': '',
            'correspondent': 'Test Sender',
            'document_type': 'Rechnung',
            'tags': ['tag1', 'tag2', 'tag3']
        }
        is_valid, errors, suggestions = validator.validate(metadata)
        
        assert not is_valid
        assert any("Titel fehlt" in error for error in errors)
    
    # ============= Correspondent Validation Tests (German Business Rules) =============
    
    @pytest.mark.parametrize("invalid_correspondent", [
        "Daniel Schindler",
        "daniel schindler",
        "DANIEL SCHINDLER",
        "D. Schindler",
        "Herr Daniel Schindler",
        "EBN Veranstaltungen",
        "EBN Consulting",
        "EBN Veranstaltungen und Consulting GmbH",
        "Alexiusstr. 6",
        "76275 Ettlingen",
        "Daniel Schindler, Ettlingen"
    ])
    def test_validate_daniel_ebn_as_sender(self, validator, invalid_correspondent):
        """Test validation fails when Daniel/EBN is set as sender."""
        metadata = {
            'title': 'Test Document',
            'correspondent': invalid_correspondent,
            'document_type': 'Rechnung',
            'tags': ['tag1', 'tag2', 'tag3']
        }
        is_valid, errors, suggestions = validator.validate(metadata)
        
        assert not is_valid
        assert any("Daniel Schindler / EBN ist immer der EMPFÄNGER" in error for error in errors)
        assert suggestions.get('correspondent') == "Bitte den tatsächlichen Absender des Dokuments angeben"
    
    def test_validate_valid_correspondents(self, validator):
        """Test validation passes for valid correspondents."""
        valid_correspondents = [
            "Amazon EU S.a.r.l.",
            "Deutsche Telekom AG",
            "Finanzamt Karlsruhe",
            "Stadt Ettlingen",
            "DHL Paket GmbH"
        ]
        
        for correspondent in valid_correspondents:
            metadata = {
                'title': 'Test Document',
                'correspondent': correspondent,
                'document_type': 'Rechnung',
                'tags': ['tag1', 'tag2', 'tag3']
            }
            is_valid, errors, suggestions = validator.validate(metadata)
            
            assert not any("Daniel Schindler / EBN ist immer der EMPFÄNGER" in error for error in errors)
    
    def test_validate_correspondent_invalid_characters(self, validator):
        """Test validation fails for correspondent with invalid characters."""
        metadata = {
            'title': 'Test Document',
            'correspondent': 'Test<>Sender:With|Invalid*Chars',
            'document_type': 'Rechnung',
            'tags': ['tag1', 'tag2', 'tag3']
        }
        is_valid, errors, suggestions = validator.validate(metadata)
        
        assert not is_valid
        assert any("Korrespondent enthält ungültige Zeichen" in error for error in errors)
    
    def test_validate_correspondent_too_short(self, validator):
        """Test validation fails for correspondent too short."""
        metadata = {
            'title': 'Test Document',
            'correspondent': 'A',
            'document_type': 'Rechnung',
            'tags': ['tag1', 'tag2', 'tag3']
        }
        is_valid, errors, suggestions = validator.validate(metadata)
        
        assert not is_valid
        assert any("Korrespondent zu kurz" in error for error in errors)
    
    # ============= Document Type Validation Tests =============
    
    def test_validate_known_document_types(self, validator):
        """Test validation passes for known German document types."""
        known_types = ['Rechnung', 'Vertrag', 'Lieferschein', 'Mahnung', 'Angebot']
        
        for doc_type in known_types:
            metadata = {
                'title': 'Test Document',
                'correspondent': 'Test Sender',
                'document_type': doc_type,
                'tags': ['tag1', 'tag2', 'tag3']
            }
            is_valid, errors, suggestions = validator.validate(metadata, strict=True)
            
            assert not any("Unbekannter Dokumenttyp" in error for error in errors)
    
    @patch('src.paperless_ngx.domain.validators.metadata_validator.process')
    @patch('src.paperless_ngx.domain.validators.metadata_validator.fuzz')
    def test_validate_unknown_document_type_with_suggestion(self, mock_fuzz, mock_process, validator):
        """Test validation suggests similar document type for unknown types."""
        mock_process.extract.return_value = [
            ('Rechnung', 85, 0),
            ('Quittung', 70, 1),
            ('Vertrag', 60, 2)
        ]
        mock_fuzz.ratio.return_value = 85
        
        metadata = {
            'title': 'Test Document',
            'correspondent': 'Test Sender',
            'document_type': 'Rechnng',  # Typo
            'tags': ['tag1', 'tag2', 'tag3']
        }
        is_valid, errors, suggestions = validator.validate(metadata, strict=True)
        
        assert any("Meinten Sie 'Rechnung'" in error for error in errors)
        assert suggestions.get('document_type') == 'Rechnung'
    
    def test_validate_document_type_without_german_validation(self, validator_no_german):
        """Test document type validation with German validation disabled."""
        metadata = {
            'title': 'Test Document',
            'correspondent': 'Test Sender',
            'document_type': 'Invoice',  # English type
            'tags': ['tag1', 'tag2', 'tag3']
        }
        is_valid, errors, suggestions = validator_no_german.validate(metadata, strict=True)
        
        # Should not validate against German types
        assert not any("Unbekannter Dokumenttyp" in error for error in errors)
    
    # ============= Tag Validation Tests =============
    
    def test_validate_tags_correct_count(self, validator):
        """Test validation passes with correct number of tags."""
        metadata = {
            'title': 'Test Document',
            'correspondent': 'Test Sender',
            'document_type': 'Rechnung',
            'tags': ['tag1', 'tag2', 'tag3', 'tag4', 'tag5']  # 5 tags (between 3-7)
        }
        is_valid, errors, suggestions = validator.validate(metadata)
        
        assert not any("Tags" in error for error in errors)
    
    def test_validate_tags_too_few(self, validator):
        """Test validation fails with too few tags."""
        metadata = {
            'title': 'Test Document',
            'correspondent': 'Test Sender',
            'document_type': 'Rechnung',
            'tags': ['tag1', 'tag2']  # Only 2 tags
        }
        is_valid, errors, suggestions = validator.validate(metadata)
        
        assert not is_valid
        assert any("Zu wenige Tags: 2" in error for error in errors)
    
    def test_validate_tags_too_many(self, validator):
        """Test validation fails with too many tags."""
        metadata = {
            'title': 'Test Document',
            'correspondent': 'Test Sender',
            'document_type': 'Rechnung',
            'tags': ['tag1', 'tag2', 'tag3', 'tag4', 'tag5', 'tag6', 'tag7', 'tag8']  # 8 tags
        }
        is_valid, errors, suggestions = validator.validate(metadata)
        
        assert not is_valid
        assert any("Zu viele Tags: 8" in error for error in errors)
    
    def test_validate_tags_missing(self, validator):
        """Test validation fails when tags are missing."""
        metadata = {
            'title': 'Test Document',
            'correspondent': 'Test Sender',
            'document_type': 'Rechnung',
            'tags': []
        }
        is_valid, errors, suggestions = validator.validate(metadata)
        
        assert not is_valid
        assert any("Tags fehlen" in error for error in errors)
    
    def test_validate_tags_invalid(self, validator):
        """Test validation fails for invalid tags."""
        metadata = {
            'title': 'Test Document',
            'correspondent': 'Test Sender',
            'document_type': 'Rechnung',
            'tags': ['', 'a', '12345', 'valid_tag', 'a' * 51]  # Various invalid tags
        }
        is_valid, errors, suggestions = validator.validate(metadata)
        
        assert not is_valid
        assert any("Ungültige Tags gefunden" in error for error in errors)
    
    def test_validate_duplicate_tags(self, validator):
        """Test validation fails for duplicate tags."""
        metadata = {
            'title': 'Test Document',
            'correspondent': 'Test Sender',
            'document_type': 'Rechnung',
            'tags': ['tag1', 'tag1', 'TAG1', 'tag2', 'tag3']
        }
        is_valid, errors, suggestions = validator.validate(metadata)
        
        assert not is_valid
        assert any("Doppelte Tags gefunden" in error for error in errors)
        # Should suggest removing duplicates
        assert len(suggestions.get('tags', [])) > 0
    
    def test_validate_german_tag_suggestion(self, validator):
        """Test German tag suggestions for non-German tags."""
        metadata = {
            'title': 'Test Document',
            'correspondent': 'Test Sender',
            'document_type': 'Rechnung',
            'tags': ['invoice', 'payment', 'online', 'shopping', 'march']
        }
        is_valid, errors, suggestions = validator.validate(metadata)
        
        # Should suggest German translations
        assert any("deutsche Übersetzungen" in str(suggestions) for s in suggestions)
    
    # ============= Description Validation Tests =============
    
    def test_validate_description_correct_length(self, validator):
        """Test validation passes for description with correct length."""
        metadata = {
            'title': 'Test Document',
            'correspondent': 'Test Sender',
            'document_type': 'Rechnung',
            'tags': ['tag1', 'tag2', 'tag3'],
            'description': 'This is a valid description with appropriate length.'
        }
        is_valid, errors, suggestions = validator.validate(metadata)
        
        assert not any("Beschreibung" in error for error in errors)
    
    def test_validate_description_too_long(self, validator):
        """Test validation fails for description too long."""
        metadata = {
            'title': 'Test Document',
            'correspondent': 'Test Sender',
            'document_type': 'Rechnung',
            'tags': ['tag1', 'tag2', 'tag3'],
            'description': 'A' * 129  # 129 characters
        }
        is_valid, errors, suggestions = validator.validate(metadata)
        
        assert not is_valid
        assert any("Beschreibung zu lang: 129 Zeichen" in error for error in errors)
    
    def test_validate_description_too_short(self, validator):
        """Test validation warns for description too short."""
        metadata = {
            'title': 'Test Document',
            'correspondent': 'Test Sender',
            'document_type': 'Rechnung',
            'tags': ['tag1', 'tag2', 'tag3'],
            'description': 'Short'  # Less than 10 characters
        }
        is_valid, errors, suggestions = validator.validate(metadata)
        
        assert not is_valid
        assert any("Beschreibung zu kurz" in error for error in errors)
    
    # ============= Date Validation Tests =============
    
    def test_validate_dates_valid_iso_format(self, validator):
        """Test validation passes for valid ISO date format."""
        metadata = {
            'title': 'Test Document',
            'correspondent': 'Test Sender',
            'document_type': 'Rechnung',
            'tags': ['tag1', 'tag2', 'tag3'],
            'created': '2024-03-15T10:00:00Z',
            'modified': '2024-03-15T11:00:00Z'
        }
        is_valid, errors, suggestions = validator.validate(metadata)
        
        assert not any("Ungültiges Datumsformat" in error for error in errors)
    
    def test_validate_dates_invalid_format(self, validator):
        """Test validation fails for invalid date format."""
        metadata = {
            'title': 'Test Document',
            'correspondent': 'Test Sender',
            'document_type': 'Rechnung',
            'tags': ['tag1', 'tag2', 'tag3'],
            'created': 'not-a-date',
            'modified': '2024/03/15'
        }
        is_valid, errors, suggestions = validator.validate(metadata)
        
        assert any("Ungültiges Datumsformat" in error for error in errors)
    
    def test_validate_dates_logic_error(self, validator):
        """Test validation fails when created date is after modified date."""
        metadata = {
            'title': 'Test Document',
            'correspondent': 'Test Sender',
            'document_type': 'Rechnung',
            'tags': ['tag1', 'tag2', 'tag3'],
            'created': '2024-03-15T12:00:00Z',
            'modified': '2024-03-15T10:00:00Z'  # Modified before created
        }
        is_valid, errors, suggestions = validator.validate(metadata)
        
        assert any("Erstellungsdatum liegt nach Änderungsdatum" in error for error in errors)
    
    def test_validate_dates_with_datetime_objects(self, validator):
        """Test validation handles datetime objects."""
        metadata = {
            'title': 'Test Document',
            'correspondent': 'Test Sender',
            'document_type': 'Rechnung',
            'tags': ['tag1', 'tag2', 'tag3'],
            'created': datetime(2024, 3, 15, 10, 0, 0),
            'modified': datetime(2024, 3, 15, 11, 0, 0)
        }
        is_valid, errors, suggestions = validator.validate(metadata)
        
        assert not any("Datumsformat" in error for error in errors)
        assert not any("Datumstyp" in error for error in errors)
    
    # ============= Filename Validation Tests =============
    
    def test_validate_filename_correct_format(self, validator):
        """Test validation passes for correctly formatted filename."""
        metadata = {
            'title': 'Test Document',
            'correspondent': 'Test Sender',
            'document_type': 'Rechnung',
            'tags': ['tag1', 'tag2', 'tag3'],
            'created': '2024-03-15T10:00:00Z',
            'filename': '2024-03-15_Test-Sender_Rechnung.pdf'
        }
        is_valid, errors, suggestions = validator.validate(metadata)
        
        # Should not have filename errors
        assert not any("Dateiname sollte mit Datum beginnen" in error for error in errors)
    
    def test_validate_filename_missing_date_prefix(self, validator):
        """Test validation warns for filename without date prefix."""
        metadata = {
            'title': 'Test Document',
            'correspondent': 'Test Sender',
            'document_type': 'Rechnung',
            'tags': ['tag1', 'tag2', 'tag3'],
            'filename': 'Test_Document.pdf'
        }
        is_valid, errors, suggestions = validator.validate(metadata)
        
        assert any("Dateiname sollte mit Datum beginnen" in error for error in errors)
    
    def test_validate_filename_suggestion(self, validator):
        """Test filename suggestion generation."""
        metadata = {
            'title': 'Test Document',
            'correspondent': 'Test Sender GmbH & Co. KG',
            'document_type': 'Rechnung',
            'tags': ['tag1', 'tag2', 'tag3'],
            'created': '2024-03-15T10:00:00Z',
            'filename': 'wrong_format.pdf'
        }
        is_valid, errors, suggestions = validator.validate(metadata)
        
        assert 'filename' in suggestions
        assert suggestions['filename'].startswith('2024-03-15_')
        assert 'Test-Sender' in suggestions['filename']
        assert 'Rechnung' in suggestions['filename']
    
    # ============= Batch Validation Tests =============
    
    def test_validate_batch_empty_list(self, validator):
        """Test batch validation with empty document list."""
        results = validator.validate_batch([])
        
        assert results == []
    
    def test_validate_batch_multiple_documents(self, validator, sample_documents):
        """Test batch validation with multiple documents."""
        results = validator.validate_batch(sample_documents)
        
        assert len(results) == len(sample_documents)
        
        # Check structure
        for result in results:
            assert 'document_id' in result
            assert 'is_valid' in result
            assert 'errors' in result
            assert 'suggestions' in result
    
    def test_validate_batch_strict_mode(self, validator, sample_documents):
        """Test batch validation in strict mode."""
        results = validator.validate_batch(sample_documents, strict=True)
        
        # More documents should fail in strict mode
        invalid_count = sum(1 for r in results if not r['is_valid'])
        assert invalid_count > 0
    
    # ============= Summary Statistics Tests =============
    
    def test_get_validation_summary_empty(self, validator):
        """Test validation summary for empty results."""
        summary = validator.get_validation_summary([])
        
        assert summary['total_documents'] == 0
        assert summary['valid_documents'] == 0
        assert summary['invalid_documents'] == 0
        assert summary['common_errors'] == {}
        assert summary['field_coverage'] == {}
    
    def test_get_validation_summary_with_results(self, validator):
        """Test validation summary generation."""
        validation_results = [
            {
                'is_valid': True,
                'errors': [],
                'suggestions': {}
            },
            {
                'is_valid': False,
                'errors': ['Titel fehlt', 'Tags fehlen'],
                'suggestions': {'title': 'Suggested Title'}
            },
            {
                'is_valid': False,
                'errors': ['Titel fehlt', 'Korrespondent fehlt'],
                'suggestions': {'correspondent': 'Suggested Sender'}
            }
        ]
        
        summary = validator.get_validation_summary(validation_results)
        
        assert summary['total_documents'] == 3
        assert summary['valid_documents'] == 1
        assert summary['invalid_documents'] == 2
        assert summary['validation_rate'] == pytest.approx(1/3, rel=0.01)
        assert 'Titel fehlt' in summary['common_errors']
        assert summary['common_errors']['Titel fehlt'] == 2
    
    def test_error_categorization_in_summary(self, validator):
        """Test error categorization in validation summary."""
        validation_results = [
            {'is_valid': False, 'errors': ['Titel fehlt', 'Tags fehlen'], 'suggestions': {}},
            {'is_valid': False, 'errors': ['Ungültiges Datumsformat', 'Titel zu lang'], 'suggestions': {}},
            {'is_valid': False, 'errors': ['Daniel Schindler / EBN ist immer der EMPFÄNGER'], 'suggestions': {}}
        ]
        
        summary = validator.get_validation_summary(validation_results)
        
        assert summary['error_categories']['missing_fields'] >= 2
        assert summary['error_categories']['invalid_format'] >= 1
        assert summary['error_categories']['business_rules'] >= 1
        assert summary['error_categories']['length_issues'] >= 1
    
    # ============= Edge Cases and Integration Tests =============
    
    def test_validate_complete_invalid_document(self, validator):
        """Test validation with document having multiple issues."""
        metadata = {
            'title': 'scan_001',  # Placeholder title
            'correspondent': 'Daniel Schindler',  # Invalid - recipient not sender
            'document_type': 'UnknownType',  # Unknown type
            'tags': ['a', 'b'],  # Too few and too short
            'description': 'x' * 200,  # Too long
            'created': 'invalid-date',  # Invalid date
            'filename': 'scan.pdf'  # No date prefix
        }
        is_valid, errors, suggestions = validator.validate(metadata, strict=True)
        
        assert not is_valid
        assert len(errors) > 5  # Multiple errors
        assert len(suggestions) > 0  # Should have suggestions
    
    def test_validate_minimal_valid_document(self, validator):
        """Test validation with minimal valid metadata."""
        metadata = {
            'title': 'Valid Title',
            'correspondent': 'Valid Sender',
            'document_type': 'Rechnung',
            'tags': ['tag1', 'tag2', 'tag3']
        }
        is_valid, errors, suggestions = validator.validate(metadata)
        
        assert is_valid
        assert len([e for e in errors if not e.startswith("Warnung:")]) == 0
    
    def test_handle_tag_format_variations(self, validator):
        """Test handling of different tag formats."""
        # Tags as list of dicts
        metadata1 = {
            'title': 'Test',
            'correspondent': 'Sender',
            'document_type': 'Rechnung',
            'tags': [{'name': 'tag1'}, {'name': 'tag2'}, {'name': 'tag3'}]
        }
        
        # Process through validate_batch to test dict handling
        results = validator.validate_batch([{
            'id': 1,
            'title': 'Test',
            'correspondent': 'Sender',
            'document_type': 'Rechnung',
            'tags': [{'name': 'tag1'}, {'name': 'tag2'}, {'name': 'tag3'}]
        }])
        
        assert len(results) == 1
        # Should extract tag names from dicts
    
    @pytest.mark.parametrize("custom_min,custom_max,tag_count,expected_valid", [
        (1, 10, 5, True),   # Within custom range
        (5, 5, 5, True),    # Exactly at min and max
        (5, 10, 4, False),  # Below minimum
        (1, 3, 4, False),   # Above maximum
        (0, 100, 50, True), # Very permissive range
    ])
    def test_custom_tag_limits(self, custom_min, custom_max, tag_count, expected_valid):
        """Test validator with custom tag count limits."""
        validator = MetadataValidator(
            min_tags=custom_min,
            max_tags=custom_max
        )
        
        metadata = {
            'title': 'Test Document',
            'correspondent': 'Test Sender',
            'document_type': 'Rechnung',
            'tags': [f'tag{i}' for i in range(tag_count)]
        }
        
        is_valid, errors, suggestions = validator.validate(metadata)
        
        if expected_valid:
            assert not any("Tags" in error and ("wenige" in error or "viele" in error) for error in errors)
        else:
            assert any("Tags" in error and ("wenige" in error or "viele" in error) for error in errors)
    
    def test_unicode_handling_in_metadata(self, validator):
        """Test handling of Unicode characters in metadata."""
        metadata = {
            'title': 'Rechnung für Büromaterial 📄',
            'correspondent': 'Müller & Söhne GmbH',
            'document_type': 'Rechnung',
            'tags': ['Büro', 'München', 'Österreich', 'Zürich', '2024'],
            'description': 'Beschreibung mit Umlauten: äöüß ÄÖÜ'
        }
        
        is_valid, errors, suggestions = validator.validate(metadata)
        
        # Should handle Unicode/German characters properly
        assert not any("ungültige Zeichen" in error for error in errors)