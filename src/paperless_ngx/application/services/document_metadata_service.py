"""Document metadata service for handling Paperless NGX document updates.

This service provides a clean interface for updating document metadata with proper
ID mapping and error handling, following Clean Architecture principles.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from ...domain.exceptions import (
    DocumentNotFoundError,
    PaperlessAPIError,
    ValidationError,
)
from ...infrastructure.paperless import PaperlessApiClient
from .paperless_api_service import PaperlessApiService
from ..use_cases.metadata_extraction import MetadataExtractor

logger = logging.getLogger(__name__)


class DocumentMetadataService:
    """Service for managing document metadata with proper ID resolution.
    
    This service acts as an orchestration layer between the presentation layer
    and the infrastructure layer, ensuring proper ID mapping for all entities.
    """
    
    def __init__(
        self,
        api_client: Optional[PaperlessApiClient] = None,
        api_service: Optional[PaperlessApiService] = None
    ):
        """Initialize the document metadata service.
        
        Args:
            api_client: Optional pre-configured API client
            api_service: Optional pre-configured API service
        """
        self.api_client = api_client or PaperlessApiClient()
        self.api_service = api_service or PaperlessApiService(self.api_client)
        self.metadata_extractor = MetadataExtractor()
        
        # Track operations for reporting
        self._operation_stats = {
            'documents_processed': 0,
            'correspondents_created': set(),
            'document_types_created': set(),
            'tags_created': set(),
            'errors': []
        }
        
        logger.info("Initialized DocumentMetadataService")
    
    def update_document_with_metadata(
        self,
        document_id: int,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a document with metadata, handling all ID mappings.
        
        This method takes metadata with string values (names) and converts them
        to the appropriate numeric IDs required by the Paperless NGX API.
        
        Args:
            document_id: The numeric ID of the document to update
            metadata: Dictionary containing metadata fields with string values:
                - title: Document title
                - correspondent: Correspondent name (string)
                - document_type: Document type name (string)
                - tags: List of tag names (strings)
                - description/notes: Document notes
                - custom_fields: Additional custom fields
        
        Returns:
            Updated document dictionary from the API
            
        Raises:
            DocumentNotFoundError: If the document doesn't exist
            ValidationError: If metadata validation fails
            PaperlessAPIError: If the API request fails
        """
        try:
            # Prepare update data with proper ID mapping
            update_data = self._prepare_update_data(metadata)
            
            # Log the transformation for debugging
            logger.debug(f"Transformed metadata for document {document_id}:")
            logger.debug(f"  Input: {metadata}")
            logger.debug(f"  Output: {update_data}")
            
            # Update the document using the API client directly
            result = self.api_client.update_document(document_id, update_data)
            
            # Track statistics
            self._operation_stats['documents_processed'] += 1
            
            logger.info(f"Successfully updated document {document_id}")
            return result
            
        except PaperlessAPIError as e:
            error_msg = f"Failed to update document {document_id}: {str(e)}"
            logger.error(error_msg)
            self._operation_stats['errors'].append({
                'document_id': document_id,
                'error': str(e)
            })
            raise
        except Exception as e:
            error_msg = f"Unexpected error updating document {document_id}: {str(e)}"
            logger.error(error_msg)
            self._operation_stats['errors'].append({
                'document_id': document_id,
                'error': str(e)
            })
            raise PaperlessAPIError(error_msg) from e
    
    def _prepare_update_data(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare update data with proper ID mappings.
        
        Converts string names to numeric IDs for correspondent, document_type, and tags.
        
        Args:
            metadata: Raw metadata with string values
            
        Returns:
            Update data with numeric IDs
        """
        update_data = {}
        
        # Handle title (no conversion needed)
        if 'title' in metadata:
            update_data['title'] = metadata['title']
        
        # Handle correspondent (convert name to ID)
        if 'correspondent' in metadata and metadata['correspondent']:
            correspondent_name = metadata['correspondent']
            correspondent_id = self.api_service.get_or_create_correspondent(correspondent_name)
            update_data['correspondent'] = correspondent_id
            logger.debug(f"Mapped correspondent '{correspondent_name}' to ID {correspondent_id}")
        
        # Handle document type (convert name to ID)
        if 'document_type' in metadata and metadata['document_type']:
            doc_type_name = metadata['document_type']
            doc_type_id = self.api_service.get_or_create_document_type(doc_type_name)
            update_data['document_type'] = doc_type_id
            logger.debug(f"Mapped document_type '{doc_type_name}' to ID {doc_type_id}")
        
        # Handle tags (convert names to IDs)
        if 'tags' in metadata and metadata['tags']:
            tag_ids = []
            for tag_name in metadata['tags']:
                if tag_name:  # Skip empty strings
                    tag_id = self.api_service.get_or_create_tag(tag_name)
                    tag_ids.append(tag_id)
                    logger.debug(f"Mapped tag '{tag_name}' to ID {tag_id}")
            if tag_ids:
                update_data['tags'] = tag_ids
        
        # Handle description/notes (map to the correct field)
        if 'description' in metadata:
            update_data['notes'] = metadata['description']
        elif 'notes' in metadata:
            update_data['notes'] = metadata['notes']
        
        # Handle custom fields (pass through as-is)
        if 'custom_fields' in metadata:
            update_data['custom_fields'] = metadata['custom_fields']
        
        # Pass through any other numeric fields that don't need conversion
        for key in ['archive_serial_number', 'original_filename']:
            if key in metadata:
                update_data[key] = metadata[key]
        
        return update_data
    
    def batch_update_documents(
        self,
        documents: List[Dict[str, Any]],
        metadata_list: List[Dict[str, Any]],
        progress_callback: Optional[callable] = None
    ) -> Tuple[int, int, List[Dict[str, Any]]]:
        """Batch update multiple documents with metadata.
        
        Args:
            documents: List of document dictionaries (must have 'id' field)
            metadata_list: List of metadata dictionaries (parallel to documents)
            progress_callback: Optional callback(current, total, document_name)
            
        Returns:
            Tuple of (successful_count, failed_count, errors)
        """
        if len(documents) != len(metadata_list):
            raise ValidationError(
                f"Documents count ({len(documents)}) doesn't match metadata count ({len(metadata_list)})"
            )
        
        successful = 0
        failed = 0
        errors = []
        total = len(documents)
        
        for idx, (doc, metadata) in enumerate(zip(documents, metadata_list), 1):
            document_id = doc.get('id')
            document_name = doc.get('title', f"Document {document_id}")
            
            if not document_id:
                logger.error(f"Document at index {idx} missing 'id' field")
                failed += 1
                errors.append({
                    'document': document_name,
                    'error': "Missing document ID"
                })
                continue
            
            if progress_callback:
                progress_callback(idx, total, document_name)
            
            try:
                self.update_document_with_metadata(document_id, metadata)
                successful += 1
                logger.debug(f"Updated document {document_id} ({idx}/{total})")
                
            except Exception as e:
                failed += 1
                error_msg = str(e)[:200]  # Truncate long error messages
                errors.append({
                    'document': document_name,
                    'document_id': document_id,
                    'error': error_msg
                })
                logger.error(f"Failed to update document {document_id}: {error_msg}")
        
        logger.info(f"Batch update complete: {successful} successful, {failed} failed")
        return successful, failed, errors
    
    def extract_and_update_metadata(
        self,
        document: Dict[str, Any],
        force_update: bool = False
    ) -> Dict[str, Any]:
        """Extract metadata from document content and update the document.
        
        Args:
            document: Document dictionary with 'id' and 'content' fields
            force_update: Update even if metadata already exists
            
        Returns:
            Updated document dictionary
        """
        document_id = document.get('id')
        if not document_id:
            raise ValidationError("Document missing 'id' field")
        
        # Check if update is needed
        if not force_update:
            has_metadata = all([
                document.get('correspondent'),
                document.get('document_type'),
                document.get('tags')
            ])
            if has_metadata:
                logger.debug(f"Document {document_id} already has metadata, skipping")
                return document
        
        # Extract content for analysis
        content = document.get('content', '')
        if not content:
            logger.warning(f"Document {document_id} has no content for extraction")
            return document
        
        # Extract metadata using the metadata extractor
        extracted = self.metadata_extractor.extract_metadata(content)
        
        # Update the document with extracted metadata
        return self.update_document_with_metadata(document_id, extracted)
    
    def get_operation_stats(self) -> Dict[str, Any]:
        """Get statistics about operations performed.
        
        Returns:
            Dictionary with operation statistics
        """
        return {
            'documents_processed': self._operation_stats['documents_processed'],
            'correspondents_created': len(self._operation_stats['correspondents_created']),
            'document_types_created': len(self._operation_stats['document_types_created']),
            'tags_created': len(self._operation_stats['tags_created']),
            'errors_count': len(self._operation_stats['errors']),
            'errors': self._operation_stats['errors'][:10]  # Limit error list
        }
    
    def reset_stats(self):
        """Reset operation statistics."""
        self._operation_stats = {
            'documents_processed': 0,
            'correspondents_created': set(),
            'document_types_created': set(),
            'tags_created': set(),
            'errors': []
        }
        logger.debug("Reset operation statistics")