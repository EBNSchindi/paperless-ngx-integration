"""Document metadata extraction use case.

This module implements the core business logic for extracting and validating
metadata from OCR text using LLMs, following Clean Architecture principles.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.paperless_ngx.domain.exceptions.custom_exceptions import (
    DocumentMetadataError,
    CorrespondentValidationError,
    RecipientAsSenderError,
    ValidationError,
    LLMInvalidResponseError,
    retry_on_transient_error
)
from src.paperless_ngx.infrastructure.llm.litellm_client import get_llm_client
from src.paperless_ngx.infrastructure.logging.logger import (
    get_struct_logger,
    LoggingMixin,
    RequestContext
)
from src.paperless_ngx.infrastructure.config.settings import get_settings

logger = get_struct_logger(__name__)


class MetadataExtractor(LoggingMixin):
    """Extract metadata from document OCR text using LLMs."""
    
    def __init__(self):
        """Initialize metadata extractor."""
        self.settings = get_settings()
        self.llm_client = get_llm_client()
        self.default_recipient = self.settings.default_recipient
        self.recipient_address = self.settings.recipient_address
        
    def _build_extraction_prompt(self, ocr_text: str) -> str:
        """Build the prompt for metadata extraction.
        
        Args:
            ocr_text: OCR text from the document
            
        Returns:
            Formatted prompt for the LLM
        """
        return f"""WICHTIG: Deine Antwort MUSS ein JSON-Objekt sein, KEINE Erklärungen oder Markdown!

Analysiere den folgenden OCR-Text. Ich ({self.default_recipient}, {self.recipient_address}) bin der EMPFÄNGER, nicht der Absender des Dokuments.

Extrahiere folgende Informationen:
1. Korrespondent: Die absendende Organisation oder Person (der ABSENDER, NICHT der Empfänger).
2. Dokumententyp: Präzise deutsche Bezeichnung (z.B. "Rechnung", "Angebot", "Versicherungspolice", "Steuerbescheid").
3. Dateiname: Format YYYY-MM-DD_Absender_Dokumententyp, verwende Unterstriche statt Leerzeichen.
4. Tags: {self.settings.min_tags}-{self.settings.max_tags} präzise deutsche Schlagwörter, die den Inhalt kategorisieren und die Suche erleichtern.
5. Zusammenfassung: Kurze, informative Beschreibung des Hauptinhalts (max. {self.settings.max_description_length} Zeichen).

Wichtige Hinweise:
- Der KORRESPONDENT ist IMMER der ABSENDER, NICHT {self.default_recipient.split('/')[0].strip()}.
- Bei Rechnungen: Erfasse Rechnungsnummer, Betrag und relevante Produkte/Dienstleistungen in den Tags.
- Bei Behördendokumenten: Identifiziere die spezifische Behörde, z.B. "Finanzamt Karlsruhe" statt nur "Finanzamt".
- Bei Versicherungen: Nenne den genauen Versicherungstyp und betroffene Versicherungsgegenstände.
- Bei Bankdokumenten: Identifiziere die Bank und die Art der Mitteilung (Kontoauszug, Kreditinfo, etc.).
- Bei Vertragsunterlagen: Nenne die Vertragsart und den Vertragsgegenstand.
- Verwende niemals unpräzise Begriffe wie "Sonstiges" oder "Unbekannt" als Dokumententyp.
- Wenn im Dokument ein Datum erkennbar ist, verwende dieses im Dateinamen (nicht das aktuelle Datum).

DEINE ANTWORT MUSS EIN REINES JSON-OBJEKT sein mit den Schlüsseln:
"correspondent", "document_type", "file_name", "tags", "description".

Beispiel des erwarteten Formats:
{{
  "correspondent": "Sparkasse Karlsruhe",
  "document_type": "Kontoauszug",
  "file_name": "2025-04-15_Sparkasse_Karlsruhe_Kontoauszug",
  "tags": ["Konto", "Girokonto", "Bankgebühren", "Auszug", "April 2025"],
  "description": "Kontoauszug April 2025 für Girokonto, Kontostand 1.234,56 EUR"
}}

OCR-Text:
{ocr_text}"""
    
    def _extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from LLM response with multiple fallback strategies.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Extracted JSON dictionary or None
        """
        # Strategy 1: Direct JSON parsing
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Extract from code blocks
        if "```" in response:
            blocks = response.split("```")
            for i in range(1, len(blocks), 2):
                block = blocks[i].strip()
                if block.lower().startswith("json"):
                    block = block[4:].strip()
                try:
                    return json.loads(block)
                except json.JSONDecodeError:
                    continue
        
        # Strategy 3: Regular expression for JSON objects
        json_pattern = r'(\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\})'
        matches = re.findall(json_pattern, response)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        # Strategy 4: Extract key-value pairs
        if ":" in response:
            kv_pattern = r'"([^"]+)"\s*:\s*(?:"([^"]*)"|\[([^\]]*)\]|(\d+)|([^,}\s]+))'
            matches = re.findall(kv_pattern, response)
            if matches:
                try:
                    result = {}
                    for match in matches:
                        key = match[0]
                        value = next((v for v in match[1:] if v), "")
                        if value.startswith('[') and value.endswith(']'):
                            try:
                                value = json.loads(value)
                            except:
                                value = [v.strip(' "\'') for v in value[1:-1].split(',')]
                        result[key] = value
                    if result:
                        return result
                except Exception:
                    pass
        
        return None
    
    def _fallback_json_generation(self, text: str) -> Optional[Dict[str, Any]]:
        """Generate JSON from non-structured text using a second LLM call.
        
        Args:
            text: Non-JSON text containing metadata information
            
        Returns:
            Generated JSON dictionary or None
        """
        prompt = f"""Wandle den folgenden Text in ein JSON-Objekt mit den Schlüsseln 
"correspondent", "document_type", "file_name", "tags" (Liste), "description" um.
Extrahiere diese Informationen aus dem Text.

STRENGE ANFORDERUNG: Antworte NUR mit einem validen JSON-Objekt, ohne Erklärungen oder Markdown.

TEXT ZUR UMWANDLUNG:
{text}

Beispiel eines erwarteten JSON-Formats:
{{
  "correspondent": "Name des Absenders",
  "document_type": "Art des Dokuments",
  "file_name": "YYYY-MM-DD_Absender_Dokumententyp",
  "tags": ["Tag1", "Tag2", "Tag3"],
  "description": "Kurze Beschreibung"
}}"""
        
        self.log_info("Attempting JSON generation from non-structured text")
        
        try:
            response, metadata = self.llm_client.complete_sync(prompt)
            json_data = self._extract_json_from_response(response)
            
            if json_data:
                self.log_info("JSON generation from text successful")
                return json_data
            else:
                self.log_error("JSON generation failed")
                return None
                
        except Exception as e:
            self.log_error(f"Fallback JSON generation failed: {e}")
            return None
    
    @retry_on_transient_error(max_attempts=3)
    def extract_metadata(self, ocr_text: str, document_id: Optional[int] = None) -> Dict[str, Any]:
        """Extract metadata from OCR text using LLM.
        
        Args:
            ocr_text: OCR text from the document
            document_id: Optional document ID for tracking
            
        Returns:
            Extracted metadata dictionary
            
        Raises:
            DocumentMetadataError: If metadata extraction fails
            LLMInvalidResponseError: If LLM response is invalid
        """
        with RequestContext() as ctx:
            self.log_info(
                "Starting metadata extraction",
                document_id=document_id,
                ocr_text_length=len(ocr_text)
            )
            
            # Build and send prompt to LLM
            prompt = self._build_extraction_prompt(ocr_text)
            
            try:
                response, llm_metadata = self.llm_client.complete_sync(
                    prompt,
                    metadata={"document_id": document_id, "task": "metadata_extraction"}
                )
                
                self.log_info(
                    "LLM response received",
                    provider=llm_metadata.get("provider"),
                    model=llm_metadata.get("model"),
                    elapsed_time=llm_metadata.get("elapsed_time")
                )
                
            except Exception as e:
                self.log_error(f"LLM call failed: {e}", exc_info=True)
                raise DocumentMetadataError(
                    document_id=document_id or 0,
                    metadata_errors={"llm_error": str(e)}
                )
            
            # Extract JSON from response
            metadata = self._extract_json_from_response(response)
            
            # Fallback if JSON extraction failed
            if metadata is None:
                self.log_warning("Primary JSON extraction failed, attempting fallback")
                metadata = self._fallback_json_generation(response)
                
                if metadata is None:
                    raise LLMInvalidResponseError(
                        provider=llm_metadata.get("provider", "unknown"),
                        response=response[:500]
                    )
            
            # Add metadata about the extraction
            metadata["_extraction_metadata"] = {
                "request_id": ctx.request_id,
                "provider": llm_metadata.get("provider"),
                "model": llm_metadata.get("model"),
                "timestamp": datetime.now().isoformat()
            }
            
            self.log_info(
                "Metadata extraction successful",
                correspondent=metadata.get("correspondent"),
                document_type=metadata.get("document_type")
            )
            
            return metadata


class MetadataValidator(LoggingMixin):
    """Validate and correct extracted metadata."""
    
    def __init__(self):
        """Initialize metadata validator."""
        self.settings = get_settings()
        self.llm_client = get_llm_client()
        self.default_recipient = self.settings.default_recipient
        self.recipient_variants = self._get_recipient_variants()
        
    def _get_recipient_variants(self) -> List[str]:
        """Get all variants of the recipient name for validation.
        
        Returns:
            List of recipient name variants
        """
        variants = [
            self.default_recipient,
            "Daniel Schindler",
            "EBN Veranstaltungen und Consulting GmbH",
            "EBN Veranstaltungen",
            "EBN",
            "D. Schindler"
        ]
        return [v.lower() for v in variants]
    
    def _is_recipient_as_sender(self, correspondent: str) -> bool:
        """Check if the correspondent is actually the recipient.
        
        Args:
            correspondent: The correspondent name to check
            
        Returns:
            True if correspondent is the recipient
        """
        if not correspondent:
            return False
            
        corr_lower = correspondent.lower()
        return any(variant in corr_lower for variant in self.recipient_variants)
    
    def _extract_actual_sender(self, ocr_text: str, invalid_correspondent: str) -> str:
        """Extract the actual sender from OCR text.
        
        Args:
            ocr_text: OCR text from the document
            invalid_correspondent: The incorrectly identified correspondent
            
        Returns:
            The actual sender name
        """
        prompt = f"""Im folgenden OCR-Text ist '{invalid_correspondent}' definitiv der EMPFÄNGER, nicht der Absender.
Identifiziere den tatsächlichen ABSENDER/Korrespondenten des Dokuments.
Gib NUR den Namen des Absenders zurück, keine zusätzlichen Erklärungen.

OCR-Text:
{ocr_text}"""
        
        try:
            response, _ = self.llm_client.complete_sync(
                prompt,
                metadata={"task": "sender_correction"}
            )
            
            actual_sender = response.strip()
            
            # Verify the extracted sender is not the recipient
            if not self._is_recipient_as_sender(actual_sender):
                return actual_sender
            else:
                return "Unbekannter Absender"
                
        except Exception as e:
            self.log_error(f"Failed to extract actual sender: {e}")
            return "Unbekannter Absender"
    
    def _validate_tags(self, tags: Any) -> List[str]:
        """Validate and correct tags.
        
        Args:
            tags: Tags to validate (may be list or string)
            
        Returns:
            Validated list of tags
        """
        # Ensure tags is a list
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(",")]
        elif not isinstance(tags, list):
            tags = []
        
        # Filter and clean tags
        cleaned_tags = []
        for tag in tags:
            if isinstance(tag, str):
                tag = tag.strip()
                if tag and len(tag) > 1:  # Minimum tag length
                    cleaned_tags.append(tag)
        
        # Ensure we have the right number of tags
        if len(cleaned_tags) < self.settings.min_tags:
            cleaned_tags.extend([f"Tag{i+1}" for i in range(self.settings.min_tags - len(cleaned_tags))])
        elif len(cleaned_tags) > self.settings.max_tags:
            cleaned_tags = cleaned_tags[:self.settings.max_tags]
        
        return cleaned_tags
    
    def _validate_filename(self, metadata: Dict[str, Any]) -> str:
        """Validate and correct filename.
        
        Args:
            metadata: Metadata dictionary
            
        Returns:
            Valid filename
        """
        filename = metadata.get("file_name", "")
        
        if not filename or filename == "Unbenannt":
            # Generate filename from metadata
            correspondent = metadata.get("correspondent", "Unbekannt")
            document_type = metadata.get("document_type", "Dokument")
            
            # Try to extract date from filename or use current date
            date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', filename)
            if date_match:
                date_str = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
            else:
                date_str = datetime.now().strftime("%Y-%m-%d")
            
            filename = f"{date_str}_{correspondent}_{document_type}"
        
        # Clean filename
        filename = filename.replace(" ", "_")
        filename = re.sub(r'[^\w\-_.]', '', filename)
        
        return filename
    
    def _validate_description(self, description: str) -> str:
        """Validate and truncate description.
        
        Args:
            description: Description to validate
            
        Returns:
            Valid description
        """
        if not description:
            return "Keine Beschreibung verfügbar"
        
        # Truncate to max length
        if len(description) > self.settings.max_description_length:
            description = description[:self.settings.max_description_length - 3] + "..."
        
        return description
    
    def validate_metadata(
        self,
        ocr_text: str,
        metadata: Dict[str, Any],
        document_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Validate and correct extracted metadata.
        
        Args:
            ocr_text: Original OCR text
            metadata: Extracted metadata to validate
            document_id: Optional document ID for tracking
            
        Returns:
            Validated and corrected metadata
            
        Raises:
            RecipientAsSenderError: If recipient is identified as sender
        """
        with RequestContext() as ctx:
            self.log_info(
                "Starting metadata validation",
                document_id=document_id,
                correspondent=metadata.get("correspondent")
            )
            
            validated = metadata.copy()
            validation_notes = []
            
            # 1. Critical validation: Check correspondent
            correspondent = validated.get("correspondent", "")
            if self._is_recipient_as_sender(correspondent):
                self.log_warning(
                    f"Recipient incorrectly identified as sender",
                    invalid_correspondent=correspondent
                )
                
                # Try to extract actual sender
                actual_sender = self._extract_actual_sender(ocr_text, correspondent)
                validated["correspondent"] = actual_sender
                validation_notes.append(
                    f"Korrespondent korrigiert von '{correspondent}' zu '{actual_sender}'"
                )
                
                # Log the correction
                self.log_info(
                    "Correspondent corrected",
                    from_value=correspondent,
                    to_value=actual_sender
                )
            
            # 2. Validate tags
            tags = validated.get("tags", [])
            validated["tags"] = self._validate_tags(tags)
            if validated["tags"] != tags:
                validation_notes.append("Tags wurden angepasst")
            
            # 3. Validate filename
            validated["file_name"] = self._validate_filename(validated)
            
            # 4. Validate description
            validated["description"] = self._validate_description(
                validated.get("description", "")
            )
            
            # 5. Ensure all required fields are present
            required_fields = ["correspondent", "document_type", "file_name", "tags", "description"]
            for field in required_fields:
                if field not in validated:
                    if field == "tags":
                        validated[field] = []
                    else:
                        validated[field] = "Unbekannt"
                    validation_notes.append(f"Fehlendes Feld '{field}' wurde hinzugefügt")
            
            # Add validation metadata
            if validation_notes:
                validated["_validation_notes"] = validation_notes
                self.log_info(
                    "Validation completed with corrections",
                    corrections=len(validation_notes),
                    notes=validation_notes
                )
            else:
                self.log_info("Validation completed without corrections")
            
            validated["_validation_metadata"] = {
                "request_id": ctx.request_id,
                "validated": True,
                "timestamp": datetime.now().isoformat()
            }
            
            return validated


class MetadataExtractionUseCase(LoggingMixin):
    """Main use case for document metadata extraction and validation."""
    
    def __init__(self):
        """Initialize metadata extraction use case."""
        self.extractor = MetadataExtractor()
        self.validator = MetadataValidator()
        
    def process_document(
        self,
        ocr_text: str,
        document_id: Optional[int] = None,
        skip_validation: bool = False
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Process a document to extract and validate metadata.
        
        Args:
            ocr_text: OCR text from the document
            document_id: Optional document ID for tracking
            skip_validation: Skip validation step if True
            
        Returns:
            Tuple of (metadata, processing_info)
        """
        with RequestContext() as ctx:
            self.log_info(
                "Starting document processing",
                document_id=document_id,
                ocr_length=len(ocr_text),
                skip_validation=skip_validation
            )
            
            processing_info = {
                "request_id": ctx.request_id,
                "document_id": document_id,
                "started_at": datetime.now().isoformat(),
                "steps": []
            }
            
            try:
                # Step 1: Extract metadata
                self.log_info("Extracting metadata")
                metadata = self.extractor.extract_metadata(ocr_text, document_id)
                processing_info["steps"].append({
                    "step": "extraction",
                    "status": "success",
                    "timestamp": datetime.now().isoformat()
                })
                
                # Step 2: Validate metadata (unless skipped)
                if not skip_validation:
                    self.log_info("Validating metadata")
                    metadata = self.validator.validate_metadata(
                        ocr_text, metadata, document_id
                    )
                    processing_info["steps"].append({
                        "step": "validation",
                        "status": "success",
                        "timestamp": datetime.now().isoformat()
                    })
                
                processing_info["completed_at"] = datetime.now().isoformat()
                processing_info["status"] = "success"
                
                self.log_info(
                    "Document processing completed",
                    correspondent=metadata.get("correspondent"),
                    document_type=metadata.get("document_type"),
                    tags_count=len(metadata.get("tags", []))
                )
                
                return metadata, processing_info
                
            except Exception as e:
                processing_info["completed_at"] = datetime.now().isoformat()
                processing_info["status"] = "failed"
                processing_info["error"] = str(e)
                
                self.log_error(
                    "Document processing failed",
                    error=str(e),
                    exc_info=True
                )
                
                raise


# Convenience function for backward compatibility
def enrich_metadata(ocr_text: str) -> Optional[Dict[str, Any]]:
    """Extract metadata from OCR text (backward compatibility wrapper).
    
    Args:
        ocr_text: OCR text from the document
        
    Returns:
        Extracted and validated metadata or None on error
    """
    try:
        use_case = MetadataExtractionUseCase()
        metadata, _ = use_case.process_document(ocr_text)
        return metadata
    except Exception as e:
        logger.error(f"Metadata enrichment failed: {e}")
        return None


def validate_metadata(ocr_text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Validate metadata (backward compatibility wrapper).
    
    Args:
        ocr_text: Original OCR text
        metadata: Metadata to validate
        
    Returns:
        Validated metadata
    """
    try:
        validator = MetadataValidator()
        return validator.validate_metadata(ocr_text, metadata)
    except Exception as e:
        logger.error(f"Metadata validation failed: {e}")
        return metadata