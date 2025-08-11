"""Document metadata validation module.

This module provides validation for document metadata according to
business rules and German language requirements.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class MetadataValidator:
    """Validator for document metadata according to business rules.
    
    This validator ensures:
    - Required fields are present
    - German sender/recipient rules (Daniel/EBN always recipient)
    - Tag count and quality validation
    - Filename format compliance
    - Date format validation
    """
    
    # Daniel/EBN variants that indicate recipient (never sender)
    RECIPIENT_INDICATORS = {
        'daniel', 'schindler', 'ebn', 'veranstaltungen', 'consulting',
        'alexiusstr', 'ettlingen', '76275'
    }
    
    # Common German document types
    VALID_DOCUMENT_TYPES = {
        'Rechnung', 'Quittung', 'Vertrag', 'Angebot', 'Bestellung',
        'Lieferschein', 'Mahnung', 'Gutschrift', 'Stornierung',
        'Kontoauszug', 'Bescheinigung', 'Bestätigung', 'Mitteilung',
        'Schreiben', 'Brief', 'E-Mail', 'Notiz', 'Protokoll',
        'Bericht', 'Antrag', 'Formular', 'Bescheid', 'Urkunde',
        'Zeugnis', 'Zertifikat', 'Nachweis', 'Versicherung',
        'Kündigung', 'Widerspruch', 'Einspruch', 'Stellungnahme'
    }
    
    # Required metadata fields
    REQUIRED_FIELDS = {'title', 'correspondent', 'document_type'}
    
    # Optional but recommended fields
    RECOMMENDED_FIELDS = {'tags', 'description', 'created'}
    
    def __init__(
        self,
        min_tags: int = 3,
        max_tags: int = 7,
        max_description_length: int = 128,
        validate_german: bool = True
    ):
        """Initialize metadata validator.
        
        Args:
            min_tags: Minimum number of tags required
            max_tags: Maximum number of tags allowed
            max_description_length: Maximum description length
            validate_german: Whether to validate German language rules
        """
        self.min_tags = min_tags
        self.max_tags = max_tags
        self.max_description_length = max_description_length
        self.validate_german = validate_german
    
    def validate(
        self,
        metadata: Dict[str, Any],
        strict: bool = False
    ) -> Tuple[bool, List[str], Dict[str, Any]]:
        """Validate document metadata.
        
        Args:
            metadata: Metadata dictionary to validate
            strict: Whether to enforce all rules strictly
            
        Returns:
            Tuple of (is_valid, errors, suggestions)
        """
        errors = []
        warnings = []
        suggestions = {}
        
        # Check required fields
        missing_fields = self.REQUIRED_FIELDS - set(metadata.keys())
        if missing_fields:
            if strict:
                errors.extend([f"Pflichtfeld fehlt: {field}" for field in missing_fields])
            else:
                warnings.extend([f"Empfohlenes Feld fehlt: {field}" for field in missing_fields])
        
        # Validate title
        title_errors = self._validate_title(metadata.get('title'))
        errors.extend(title_errors)
        
        # Validate correspondent (sender/recipient rules)
        correspondent_errors, correspondent_suggestion = self._validate_correspondent(
            metadata.get('correspondent')
        )
        errors.extend(correspondent_errors)
        if correspondent_suggestion:
            suggestions['correspondent'] = correspondent_suggestion
        
        # Validate document type
        doc_type_errors, doc_type_suggestion = self._validate_document_type(
            metadata.get('document_type')
        )
        if strict:
            errors.extend(doc_type_errors)
        else:
            warnings.extend(doc_type_errors)
        if doc_type_suggestion:
            suggestions['document_type'] = doc_type_suggestion
        
        # Validate tags
        tag_errors, tag_suggestions = self._validate_tags(metadata.get('tags', []))
        errors.extend(tag_errors)
        if tag_suggestions:
            suggestions['tags'] = tag_suggestions
        
        # Validate description
        desc_errors = self._validate_description(metadata.get('description'))
        errors.extend(desc_errors)
        
        # Validate dates
        date_errors = self._validate_dates(metadata)
        warnings.extend(date_errors)
        
        # Validate filename if present
        if 'filename' in metadata:
            filename_errors, filename_suggestion = self._validate_filename(
                metadata['filename'],
                metadata.get('created'),
                metadata.get('correspondent'),
                metadata.get('document_type')
            )
            warnings.extend(filename_errors)
            if filename_suggestion:
                suggestions['filename'] = filename_suggestion
        
        # Determine overall validity
        is_valid = len(errors) == 0
        
        # Combine errors and warnings for output
        all_issues = errors + ([f"Warnung: {w}" for w in warnings] if not strict else [])
        
        return is_valid, all_issues, suggestions
    
    def _validate_title(self, title: Optional[str]) -> List[str]:
        """Validate document title.
        
        Args:
            title: Document title
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if not title:
            errors.append("Titel fehlt")
            return errors
        
        if len(title) < 3:
            errors.append(f"Titel zu kurz: {len(title)} Zeichen (mindestens 3 erforderlich)")
        elif len(title) > 255:
            errors.append(f"Titel zu lang: {len(title)} Zeichen (maximal 255 erlaubt)")
        
        # Check for placeholder titles
        placeholder_patterns = [
            r'^untitled',
            r'^document\d*$',
            r'^scan\d*$',
            r'^img_?\d*$',
            r'^[0-9]+$'
        ]
        
        for pattern in placeholder_patterns:
            if re.match(pattern, title.lower()):
                errors.append(f"Titel scheint ein Platzhalter zu sein: '{title}'")
                break
        
        return errors
    
    def _validate_correspondent(
        self,
        correspondent: Optional[str]
    ) -> Tuple[List[str], Optional[str]]:
        """Validate correspondent with German business rules.
        
        Args:
            correspondent: Correspondent name
            
        Returns:
            Tuple of (errors, suggested_correction)
        """
        errors = []
        suggestion = None
        
        if not correspondent:
            errors.append("Korrespondent fehlt")
            return errors, suggestion
        
        # Check if Daniel/EBN is incorrectly set as sender
        correspondent_lower = correspondent.lower()
        
        # Check for recipient indicators
        is_recipient_indicated = any(
            indicator in correspondent_lower
            for indicator in self.RECIPIENT_INDICATORS
        )
        
        if is_recipient_indicated:
            errors.append(
                f"Ungültiger Korrespondent '{correspondent}': "
                f"Daniel Schindler / EBN ist immer der EMPFÄNGER, niemals der Absender. "
                f"Der Korrespondent sollte der ABSENDER des Dokuments sein."
            )
            suggestion = "Bitte den tatsächlichen Absender des Dokuments angeben"
        
        # Check for invalid characters
        if re.search(r'[<>:"/\\|?*]', correspondent):
            errors.append(f"Korrespondent enthält ungültige Zeichen: '{correspondent}'")
        
        # Check minimum length
        if len(correspondent) < 2:
            errors.append(f"Korrespondent zu kurz: '{correspondent}'")
        
        return errors, suggestion
    
    def _validate_document_type(
        self,
        document_type: Optional[str]
    ) -> Tuple[List[str], Optional[str]]:
        """Validate document type.
        
        Args:
            document_type: Document type
            
        Returns:
            Tuple of (errors, suggested_type)
        """
        errors = []
        suggestion = None
        
        if not document_type:
            errors.append("Dokumenttyp fehlt")
            return errors, suggestion
        
        # Check against valid types if German validation is enabled
        if self.validate_german:
            if document_type not in self.VALID_DOCUMENT_TYPES:
                # Find closest match
                from rapidfuzz import process, fuzz
                
                matches = process.extract(
                    document_type,
                    self.VALID_DOCUMENT_TYPES,
                    scorer=fuzz.ratio,
                    limit=3
                )
                
                if matches and matches[0][1] >= 80:
                    suggestion = matches[0][0]
                    errors.append(
                        f"Unbekannter Dokumenttyp '{document_type}'. "
                        f"Meinten Sie '{suggestion}'?"
                    )
                else:
                    errors.append(
                        f"Unbekannter Dokumenttyp '{document_type}'. "
                        f"Verwenden Sie einen der Standardtypen."
                    )
        
        return errors, suggestion
    
    def _validate_tags(
        self,
        tags: Optional[List[str]]
    ) -> Tuple[List[str], List[str]]:
        """Validate document tags.
        
        Args:
            tags: List of tags
            
        Returns:
            Tuple of (errors, suggestions)
        """
        errors = []
        suggestions = []
        
        if not tags:
            errors.append(f"Tags fehlen (mindestens {self.min_tags} erforderlich)")
            return errors, suggestions
        
        # Check tag count
        tag_count = len(tags)
        if tag_count < self.min_tags:
            errors.append(
                f"Zu wenige Tags: {tag_count} "
                f"(mindestens {self.min_tags} erforderlich)"
            )
        elif tag_count > self.max_tags:
            errors.append(
                f"Zu viele Tags: {tag_count} "
                f"(maximal {self.max_tags} erlaubt)"
            )
        
        # Check individual tags
        invalid_tags = []
        for tag in tags:
            if not tag or len(tag) < 2:
                invalid_tags.append(tag)
            elif len(tag) > 50:
                invalid_tags.append(f"{tag[:47]}...")
            elif re.search(r'^[0-9]+$', tag):
                invalid_tags.append(tag)
        
        if invalid_tags:
            errors.append(f"Ungültige Tags gefunden: {', '.join(map(str, invalid_tags))}")
        
        # Check for duplicate tags (case-insensitive)
        lower_tags = [tag.lower() for tag in tags if tag]
        if len(lower_tags) != len(set(lower_tags)):
            errors.append("Doppelte Tags gefunden")
            
            # Find duplicates and suggest removing them
            seen = set()
            duplicates = set()
            for tag in lower_tags:
                if tag in seen:
                    duplicates.add(tag)
                seen.add(tag)
            
            suggestions = [tag for tag in tags if tag.lower() not in duplicates]
        
        # Suggest German keywords if validate_german is enabled
        if self.validate_german and not errors:
            # Check if tags are in German
            non_german_tags = []
            for tag in tags:
                if tag and not self._is_likely_german(tag):
                    non_german_tags.append(tag)
            
            if non_german_tags:
                suggestions.append(f"Erwägen Sie deutsche Übersetzungen für: {', '.join(non_german_tags)}")
        
        return errors, suggestions
    
    def _validate_description(self, description: Optional[str]) -> List[str]:
        """Validate document description.
        
        Args:
            description: Document description
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if description:
            if len(description) > self.max_description_length:
                errors.append(
                    f"Beschreibung zu lang: {len(description)} Zeichen "
                    f"(maximal {self.max_description_length} erlaubt)"
                )
            elif len(description) < 10:
                errors.append(
                    f"Beschreibung zu kurz: {len(description)} Zeichen "
                    f"(mindestens 10 empfohlen)"
                )
        
        return errors
    
    def _validate_dates(self, metadata: Dict[str, Any]) -> List[str]:
        """Validate date fields in metadata.
        
        Args:
            metadata: Metadata dictionary
            
        Returns:
            List of validation errors
        """
        errors = []
        date_fields = ['created', 'modified', 'added']
        
        for field in date_fields:
            if field in metadata:
                date_value = metadata[field]
                
                # Check if it's a valid date format
                if isinstance(date_value, str):
                    try:
                        # Try to parse ISO format
                        datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                    except ValueError:
                        errors.append(f"Ungültiges Datumsformat für {field}: '{date_value}'")
                elif not isinstance(date_value, datetime):
                    errors.append(f"Ungültiger Datumstyp für {field}: {type(date_value).__name__}")
        
        # Check date logic
        if 'created' in metadata and 'modified' in metadata:
            try:
                created = metadata['created']
                modified = metadata['modified']
                
                if isinstance(created, str):
                    created = datetime.fromisoformat(created.replace('Z', '+00:00'))
                if isinstance(modified, str):
                    modified = datetime.fromisoformat(modified.replace('Z', '+00:00'))
                
                if created > modified:
                    errors.append("Erstellungsdatum liegt nach Änderungsdatum")
            except Exception:
                pass  # Already handled above
        
        return errors
    
    def _validate_filename(
        self,
        filename: str,
        created_date: Optional[Any],
        correspondent: Optional[str],
        document_type: Optional[str]
    ) -> Tuple[List[str], Optional[str]]:
        """Validate and suggest filename format.
        
        Expected format: YYYY-MM-DD_Sender_Type.ext
        
        Args:
            filename: Current filename
            created_date: Document creation date
            correspondent: Document correspondent
            document_type: Document type
            
        Returns:
            Tuple of (errors, suggested_filename)
        """
        errors = []
        suggestion = None
        
        # Extract base name and extension
        path = Path(filename)
        base_name = path.stem
        extension = path.suffix
        
        # Check for date prefix (YYYY-MM-DD)
        date_pattern = r'^\d{4}-\d{2}-\d{2}'
        if not re.match(date_pattern, base_name):
            errors.append("Dateiname sollte mit Datum beginnen (YYYY-MM-DD)")
        
        # Generate suggested filename
        if created_date and correspondent and document_type:
            try:
                if isinstance(created_date, str):
                    date_obj = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                else:
                    date_obj = created_date
                
                date_str = date_obj.strftime('%Y-%m-%d')
                
                # Clean correspondent and document type for filename
                clean_correspondent = re.sub(r'[^\w\s-]', '', correspondent)[:30]
                clean_correspondent = re.sub(r'[-\s]+', '-', clean_correspondent)
                
                clean_doc_type = re.sub(r'[^\w\s-]', '', document_type)[:20]
                clean_doc_type = re.sub(r'[-\s]+', '-', clean_doc_type)
                
                suggestion = f"{date_str}_{clean_correspondent}_{clean_doc_type}{extension}"
                
                if suggestion != filename:
                    errors.append(f"Dateiname-Format empfohlen: {suggestion}")
                
            except Exception as e:
                logger.debug(f"Could not generate filename suggestion: {e}")
        
        return errors, suggestion
    
    def _is_likely_german(self, text: str) -> bool:
        """Check if text is likely German.
        
        Args:
            text: Text to check
            
        Returns:
            True if likely German
        """
        # Common German word endings and patterns
        german_patterns = [
            r'ung$', r'heit$', r'keit$', r'schaft$', r'tum$',
            r'nis$', r'sal$', r'ling$', r'reich$', r'los$',
            r'bar$', r'haft$', r'sam$', r'lich$', r'isch$',
            r'ig$', r'ern$', r'eln$'
        ]
        
        # Check for German-specific characters
        if any(char in text.lower() for char in 'äöüß'):
            return True
        
        # Check for German patterns
        for pattern in german_patterns:
            if re.search(pattern, text.lower()):
                return True
        
        # Check against common German words
        common_german = {
            'der', 'die', 'das', 'und', 'oder', 'aber', 'für',
            'mit', 'von', 'bei', 'nach', 'aus', 'auf', 'über'
        }
        
        words = text.lower().split()
        german_word_count = sum(1 for word in words if word in common_german)
        
        return german_word_count > 0
    
    def validate_batch(
        self,
        documents: List[Dict[str, Any]],
        strict: bool = False
    ) -> List[Dict[str, Any]]:
        """Validate metadata for multiple documents.
        
        Args:
            documents: List of documents with metadata
            strict: Whether to enforce all rules strictly
            
        Returns:
            List of validation results
        """
        results = []
        
        for doc in documents:
            doc_id = doc.get('id')
            
            # Extract metadata fields
            metadata = {
                'title': doc.get('title'),
                'correspondent': doc.get('correspondent') or doc.get('correspondent_name'),
                'document_type': doc.get('document_type') or doc.get('document_type_name'),
                'tags': doc.get('tags', []),
                'description': doc.get('description'),
                'created': doc.get('created'),
                'modified': doc.get('modified'),
                'filename': doc.get('original_filename') or doc.get('filename')
            }
            
            # Handle tag format (might be list of dicts or strings)
            if metadata['tags'] and isinstance(metadata['tags'][0], dict):
                metadata['tags'] = [tag.get('name', '') for tag in metadata['tags']]
            
            is_valid, errors, suggestions = self.validate(metadata, strict)
            
            results.append({
                'document_id': doc_id,
                'is_valid': is_valid,
                'errors': errors,
                'suggestions': suggestions
            })
            
            if not is_valid:
                logger.warning(
                    f"Document {doc_id} failed metadata validation: {', '.join(errors[:3])}"
                )
        
        return results
    
    def get_validation_summary(
        self,
        validation_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
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
                'common_errors': {},
                'field_coverage': {}
            }
        
        valid_count = sum(1 for r in validation_results if r['is_valid'])
        invalid_count = len(validation_results) - valid_count
        
        # Count common errors
        error_counts = {}
        for result in validation_results:
            for error in result.get('errors', []):
                # Extract error type
                if ':' in error:
                    error_type = error.split(':')[0]
                else:
                    error_type = error
                
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        # Count suggestions
        suggestion_counts = {}
        for result in validation_results:
            for field, suggestion in result.get('suggestions', {}).items():
                suggestion_counts[field] = suggestion_counts.get(field, 0) + 1
        
        return {
            'total_documents': len(validation_results),
            'valid_documents': valid_count,
            'invalid_documents': invalid_count,
            'validation_rate': valid_count / len(validation_results) if validation_results else 0.0,
            'common_errors': dict(sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            'fields_needing_correction': dict(sorted(suggestion_counts.items(), key=lambda x: x[1], reverse=True)),
            'error_categories': {
                'missing_fields': sum(1 for e in error_counts if 'fehlt' in e.lower()),
                'invalid_format': sum(1 for e in error_counts if 'format' in e.lower() or 'ungültig' in e.lower()),
                'business_rules': sum(1 for e in error_counts if 'empfänger' in e.lower() or 'absender' in e.lower()),
                'length_issues': sum(1 for e in error_counts if 'lang' in e.lower() or 'kurz' in e.lower())
            }
        }