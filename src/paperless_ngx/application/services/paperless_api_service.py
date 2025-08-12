"""High-level service for Paperless NGX API operations.

This module provides business logic and orchestration for document management,
including pagination, chunked retrieval, and entity management.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set, Tuple, TYPE_CHECKING

from rapidfuzz import fuzz, process

from ...domain.exceptions import (
    DocumentNotFoundError,
    PaperlessAPIError,
    ValidationError,
)
from ...infrastructure.config import get_settings
from ...infrastructure.paperless import PaperlessApiClient
from ..use_cases.metadata_extraction import MetadataExtractor

if TYPE_CHECKING:
    from ...domain.value_objects.date_range import DateRange

logger = logging.getLogger(__name__)


class PaperlessApiService:
    """High-level service for Paperless NGX operations.
    
    This service provides:
    - Document management with chunked retrieval
    - Intelligent tag management with fuzzy matching
    - Correspondent and document type management
    - Batch operations with progress tracking
    - Date-based filtering
    """
    
    def __init__(self, api_client: Optional[PaperlessApiClient] = None):
        """Initialize the Paperless API service.
        
        Args:
            api_client: Optional pre-configured API client
        """
        self.api_client = api_client or PaperlessApiClient()
        self.metadata_extractor = MetadataExtractor()
        
        # Caches for entities to reduce API calls
        self._tag_cache: Optional[List[Dict[str, Any]]] = None
        self._correspondent_cache: Optional[List[Dict[str, Any]]] = None
        self._document_type_cache: Optional[List[Dict[str, Any]]] = None
        
        logger.info("Initialized Paperless API service")
    
    # Document Operations
    
    def get_documents_chunked(
        self,
        chunk_size: int = 100,
        since_date: Optional[datetime] = None,
        until_date: Optional[datetime] = None,
        correspondent_id: Optional[int] = None,
        document_type_id: Optional[int] = None,
        tag_ids: Optional[List[int]] = None,
        has_ocr: Optional[bool] = None,
        ordering: str = '-created',
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """Get documents in chunks for memory-efficient processing.
        
        Args:
            chunk_size: Number of documents per chunk
            since_date: Filter documents created after this date
            until_date: Filter documents created before this date
            correspondent_id: Filter by correspondent
            document_type_id: Filter by document type
            tag_ids: Filter by tags (documents with ANY of these tags)
            has_ocr: Filter by OCR status
            ordering: Sort order (e.g., '-created', 'title')
            
        Yields:
            Chunks of document dictionaries
        """
        filters = {}
        filters['format'] = 'json'  # CRITICAL: Force JSON response
        
        # Date filtering
        if since_date:
            filters['created__date__gte'] = since_date.date().isoformat()
        if until_date:
            filters['created__date__lte'] = until_date.date().isoformat()
        
        # Entity filtering
        if correspondent_id:
            filters['correspondent__id'] = correspondent_id
        if document_type_id:
            filters['document_type__id'] = document_type_id
        if tag_ids:
            filters['tags__id__in'] = ','.join(map(str, tag_ids))
        
        # OCR filtering
        if has_ocr is not None:
            filters['has_ocr'] = 'true' if has_ocr else 'false'
        
        page = 1
        total_documents = 0
        
        while True:
            try:
                data = self.api_client.get_documents(
                    page=page,
                    page_size=chunk_size,
                    ordering=ordering,
                    **filters
                )
                
                documents = data['results']
                if not documents:
                    break
                
                total_documents += len(documents)
                logger.debug(f"Retrieved chunk {page} with {len(documents)} documents (total: {total_documents})")
                
                yield documents
                
                if not data['next']:
                    break
                
                page += 1
                
            except KeyError as e:
                logger.error(f"API response missing expected field '{e}' in chunk {page}")
                logger.error(f"Response keys: {list(data.keys()) if 'data' in locals() else 'No data'}")
                # API might return empty or different format when no documents
                break
            except Exception as e:
                logger.error(f"Error retrieving documents chunk {page}: {e}")
                # Don't raise, just stop iteration
                break
        
        logger.info(f"Retrieved {total_documents} documents in {page} chunks")
    
    def get_documents_for_quarter(
        self,
        year: int,
        quarter: int,
        chunk_size: int = 100
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """Get documents for a specific quarter.
        
        Args:
            year: Year (e.g., 2024)
            quarter: Quarter (1-4)
            chunk_size: Documents per chunk
            
        Yields:
            Chunks of document dictionaries
        """
        if quarter not in [1, 2, 3, 4]:
            raise ValidationError(f"Invalid quarter: {quarter}. Must be 1-4.")
        
        # Calculate quarter date range
        quarter_start_month = (quarter - 1) * 3 + 1
        since_date = datetime(year, quarter_start_month, 1)
        
        if quarter == 4:
            until_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            until_date = datetime(year, quarter_start_month + 3, 1) - timedelta(days=1)
        
        logger.info(f"Retrieving documents for Q{quarter}/{year} ({since_date.date()} to {until_date.date()})")
        
        yield from self.get_documents_chunked(
            chunk_size=chunk_size,
            since_date=since_date,
            until_date=until_date
        )
    
    def get_documents_in_range(
        self,
        date_range: 'DateRange',
        chunk_size: int = 100
    ) -> List[Dict[str, Any]]:
        """Get all documents within a date range (synchronous version).
        
        Args:
            date_range: DateRange object specifying the period
            chunk_size: Documents per chunk for pagination
            
        Returns:
            List of document dictionaries
        """
        logger.info(f"Retrieving documents for range: {date_range}")
        
        documents = []
        try:
            for chunk in self.get_documents_chunked(
                chunk_size=chunk_size,
                since_date=date_range.start_date,
                until_date=date_range.end_date
            ):
                documents.extend(chunk)
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            # Return empty list on error instead of raising
            return []
        
        logger.info(f"Retrieved {len(documents)} documents in date range")
        return documents
    
    async def get_documents_in_range_async(
        self,
        date_range: 'DateRange',
        chunk_size: int = 100
    ) -> List[Dict[str, Any]]:
        """Get all documents within a date range (async version).
        
        Args:
            date_range: DateRange object specifying the period
            chunk_size: Documents per chunk for pagination
            
        Returns:
            List of document dictionaries
        """
        # Just call the sync version for now
        return self.get_documents_in_range(date_range, chunk_size)
    
    def get_document_with_ocr(self, document_id: int) -> Dict[str, Any]:
        """Get document with OCR text included.
        
        Args:
            document_id: Document ID
            
        Returns:
            Document dictionary with OCR text
            
        Raises:
            DocumentNotFoundError: If document not found
        """
        try:
            document = self.api_client.get_document(document_id)
            
            # Ensure OCR text is available
            if not document.get('content') and not document.get('ocr'):
                logger.warning(f"Document {document_id} has no OCR text")
            
            return document
            
        except PaperlessAPIError as e:
            if "404" in str(e):
                raise DocumentNotFoundError(document_id)
            raise
    
    def update_document_metadata(
        self,
        document_id: int,
        title: Optional[str] = None,
        correspondent: Optional[str] = None,
        document_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        description: Optional[str] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Update document metadata with intelligent entity resolution.
        
        Args:
            document_id: Document ID
            title: New title
            correspondent: Correspondent name (will be created if needed)
            document_type: Document type name (will be created if needed)
            tags: Tag names (will be created if needed)
            description: Document description
            custom_fields: Custom field values
            
        Returns:
            Updated document dictionary
        """
        update_data = {}
        
        if title:
            update_data['title'] = title
        
        if correspondent:
            correspondent_id = self.get_or_create_correspondent(correspondent)
            update_data['correspondent'] = correspondent_id
        
        if document_type:
            document_type_id = self.get_or_create_document_type(document_type)
            update_data['document_type'] = document_type_id
        
        if tags is not None:
            tag_ids = [self.get_or_create_tag(tag) for tag in tags]
            update_data['tags'] = tag_ids
        
        if description:
            # Use native notes field instead of custom field
            update_data['notes'] = description
        
        if custom_fields:
            update_data['custom_fields'] = custom_fields
        
        logger.info(f"Updating document {document_id} metadata")
        return self.api_client.update_document(document_id, update_data)
    
    def batch_update_documents(
        self,
        document_updates: List[Dict[str, Any]],
        progress_callback: Optional[callable] = None
    ) -> Tuple[int, int, List[Dict[str, Any]]]:
        """Batch update multiple documents.
        
        Args:
            document_updates: List of dicts with 'id' and update fields
            progress_callback: Optional callback(current, total, document_id)
            
        Returns:
            Tuple of (successful_count, failed_count, errors)
        """
        successful = 0
        failed = 0
        errors = []
        total = len(document_updates)
        
        for idx, update in enumerate(document_updates, 1):
            document_id = update.pop('id')
            
            if progress_callback:
                progress_callback(idx, total, document_id)
            
            try:
                self.api_client.update_document(document_id, update)
                successful += 1
                logger.debug(f"Updated document {document_id} ({idx}/{total})")
                
            except Exception as e:
                failed += 1
                errors.append({
                    'document_id': document_id,
                    'error': str(e)
                })
                logger.error(f"Failed to update document {document_id}: {e}")
        
        logger.info(f"Batch update complete: {successful} successful, {failed} failed")
        return successful, failed, errors
    
    # Tag Management
    
    def get_or_create_tag(self, tag_name: str, color: Optional[str] = None) -> int:
        """Get existing tag ID or create new tag.
        
        Args:
            tag_name: Tag name
            color: Optional hex color (e.g., '#FF0000')
            
        Returns:
            Tag ID
        """
        # Refresh cache if needed
        if self._tag_cache is None:
            self._tag_cache = self.api_client.get_all_tags()
        
        # Case-insensitive search
        tag_name_lower = tag_name.lower().strip()
        
        for tag in self._tag_cache:
            if tag['name'].lower() == tag_name_lower:
                logger.debug(f"Found existing tag: {tag['name']} (ID: {tag['id']})")
                return tag['id']
        
        # Create new tag
        logger.info(f"Creating new tag: {tag_name}")
        new_tag = self.api_client.create_tag(tag_name, color=color)
        
        # Update cache
        self._tag_cache.append(new_tag)
        
        return new_tag['id']
    
    def find_similar_tags(
        self,
        similarity_threshold: float = 85.0
    ) -> List[List[Dict[str, Any]]]:
        """Find groups of similar tags using fuzzy matching.
        
        Args:
            similarity_threshold: Minimum similarity percentage (0-100)
            
        Returns:
            List of tag groups that are similar
        """
        if self._tag_cache is None:
            self._tag_cache = self.api_client.get_all_tags()
        
        tag_groups = []
        processed_ids = set()
        
        for tag in self._tag_cache:
            if tag['id'] in processed_ids:
                continue
            
            # Find similar tags
            similar_group = [tag]
            tag_name = tag['name'].lower()
            
            for other_tag in self._tag_cache:
                if other_tag['id'] == tag['id'] or other_tag['id'] in processed_ids:
                    continue
                
                similarity = fuzz.ratio(tag_name, other_tag['name'].lower())
                
                if similarity >= similarity_threshold:
                    similar_group.append(other_tag)
                    processed_ids.add(other_tag['id'])
            
            if len(similar_group) > 1:
                processed_ids.add(tag['id'])
                tag_groups.append(similar_group)
                
                logger.info(f"Found similar tag group: {[t['name'] for t in similar_group]}")
        
        return tag_groups
    
    def unify_tags(
        self,
        tag_groups: List[List[Dict[str, Any]]],
        selection_strategy: str = 'most_used',
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Unify similar tags by merging them.
        
        Args:
            tag_groups: Groups of similar tags to unify
            selection_strategy: How to select the primary tag ('most_used', 'first', 'shortest')
            progress_callback: Optional callback(current, total, tag_name)
            
        Returns:
            Summary of unification results
        """
        results = {
            'unified_groups': 0,
            'tags_removed': 0,
            'documents_updated': 0,
            'errors': []
        }
        
        total_groups = len(tag_groups)
        
        for idx, group in enumerate(tag_groups, 1):
            if progress_callback:
                progress_callback(idx, total_groups, group[0]['name'])
            
            try:
                # Select primary tag based on strategy
                if selection_strategy == 'most_used':
                    primary_tag = max(group, key=lambda t: t.get('document_count', 0))
                elif selection_strategy == 'shortest':
                    primary_tag = min(group, key=lambda t: len(t['name']))
                else:  # 'first'
                    primary_tag = group[0]
                
                # Update documents with other tags to use primary tag
                for tag in group:
                    if tag['id'] == primary_tag['id']:
                        continue
                    
                    # Find documents with this tag
                    docs_with_tag = list(self.api_client.get_documents_generator(
                        tags__id__in=str(tag['id'])
                    ))
                    
                    # Update documents to use primary tag
                    for doc in docs_with_tag:
                        current_tags = doc.get('tags', [])
                        # Remove old tag, add primary tag if not present
                        new_tags = [t for t in current_tags if t != tag['id']]
                        if primary_tag['id'] not in new_tags:
                            new_tags.append(primary_tag['id'])
                        
                        self.api_client.update_document(doc['id'], {'tags': new_tags})
                        results['documents_updated'] += 1
                    
                    # Delete the redundant tag
                    self.api_client.delete_tag(tag['id'])
                    results['tags_removed'] += 1
                
                results['unified_groups'] += 1
                logger.info(f"Unified tag group: {[t['name'] for t in group]} -> {primary_tag['name']}")
                
            except Exception as e:
                error = f"Failed to unify group {[t['name'] for t in group]}: {e}"
                results['errors'].append(error)
                logger.error(error)
        
        # Clear cache after unification
        self._tag_cache = None
        
        return results
    
    # Correspondent Management
    
    def get_or_create_correspondent(self, name: str) -> int:
        """Get existing correspondent ID or create new one.
        
        Args:
            name: Correspondent name
            
        Returns:
            Correspondent ID
        """
        # Refresh cache if needed
        if self._correspondent_cache is None:
            page = 1
            self._correspondent_cache = []
            while True:
                data = self.api_client.get_correspondents(page=page)
                self._correspondent_cache.extend(data['results'])
                if not data['next']:
                    break
                page += 1
        
        # Case-insensitive search
        name_lower = name.lower().strip()
        
        for correspondent in self._correspondent_cache:
            if correspondent['name'].lower() == name_lower:
                logger.debug(f"Found existing correspondent: {correspondent['name']} (ID: {correspondent['id']})")
                return correspondent['id']
        
        # Create new correspondent
        logger.info(f"Creating new correspondent: {name}")
        new_correspondent = self.api_client.create_correspondent(name)
        
        # Update cache
        self._correspondent_cache.append(new_correspondent)
        
        return new_correspondent['id']
    
    # Document Type Management
    
    def get_or_create_document_type(self, name: str) -> int:
        """Get existing document type ID or create new one.
        
        Args:
            name: Document type name
            
        Returns:
            Document type ID
        """
        # Refresh cache if needed
        if self._document_type_cache is None:
            page = 1
            self._document_type_cache = []
            while True:
                data = self.api_client.get_document_types(page=page)
                self._document_type_cache.extend(data['results'])
                if not data['next']:
                    break
                page += 1
        
        # Case-insensitive search
        name_lower = name.lower().strip()
        
        for doc_type in self._document_type_cache:
            if doc_type['name'].lower() == name_lower:
                logger.debug(f"Found existing document type: {doc_type['name']} (ID: {doc_type['id']})")
                return doc_type['id']
        
        # Create new document type
        logger.info(f"Creating new document type: {name}")
        new_doc_type = self.api_client.create_document_type(name)
        
        # Update cache
        self._document_type_cache.append(new_doc_type)
        
        return new_doc_type['id']
    
    # Quality Analysis Methods
    
    def get_documents_for_quality_analysis(
        self,
        chunk_size: int = 100,
        min_ocr_length: int = 50,
        since_date: Optional[datetime] = None
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """Get documents for quality analysis with OCR content.
        
        Args:
            chunk_size: Number of documents per chunk
            min_ocr_length: Minimum OCR text length required
            since_date: Optional date filter
            
        Yields:
            Chunks of documents with OCR content for analysis
        """
        for chunk in self.get_documents_chunked(
            chunk_size=chunk_size,
            since_date=since_date,
            has_ocr=True
        ):
            # Filter documents with sufficient OCR content
            filtered_chunk = []
            for doc in chunk:
                ocr_text = doc.get('content') or doc.get('ocr', '')
                if ocr_text and len(ocr_text) >= min_ocr_length:
                    filtered_chunk.append(doc)
                else:
                    logger.debug(f"Document {doc.get('id')} has insufficient OCR content")
            
            if filtered_chunk:
                yield filtered_chunk
    
    def get_documents_for_quarterly_processing(
        self,
        year: int,
        quarter: int,
        chunk_size: int = 100,
        include_ocr: bool = True
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """Get documents for quarterly processing.
        
        Args:
            year: Year (e.g., 2024)
            quarter: Quarter (1-4)
            chunk_size: Documents per chunk
            include_ocr: Whether to include OCR content
            
        Yields:
            Chunks of documents for the specified quarter
        """
        # Use existing method with OCR filter if needed
        for chunk in self.get_documents_for_quarter(
            year=year,
            quarter=quarter,
            chunk_size=chunk_size
        ):
            if include_ocr:
                # Fetch full document details with OCR for each document
                enriched_chunk = []
                for doc in chunk:
                    try:
                        full_doc = self.get_document_with_ocr(doc['id'])
                        enriched_chunk.append(full_doc)
                    except Exception as e:
                        logger.warning(f"Failed to get OCR for document {doc['id']}: {e}")
                        enriched_chunk.append(doc)
                yield enriched_chunk
            else:
                yield chunk
    
    def update_document_metadata_batch(
        self,
        document_updates: List[Dict[str, Any]],
        validate: bool = True,
        progress_callback: Optional[callable] = None
    ) -> Tuple[int, int, List[Dict[str, Any]]]:
        """Batch update documents with validation.
        
        Args:
            document_updates: List of updates with document_id and metadata
            validate: Whether to validate metadata before updating
            progress_callback: Optional callback(current, total, document_id)
            
        Returns:
            Tuple of (successful_count, failed_count, errors)
        """
        successful = 0
        failed = 0
        errors = []
        total = len(document_updates)
        
        for idx, update_info in enumerate(document_updates, 1):
            document_id = update_info.get('document_id') or update_info.get('id')
            
            if not document_id:
                failed += 1
                errors.append({
                    'document_id': None,
                    'error': 'Missing document ID'
                })
                continue
            
            if progress_callback:
                progress_callback(idx, total, document_id)
            
            try:
                # Validate metadata if requested
                if validate:
                    validation_errors = self._validate_document_metadata(update_info)
                    if validation_errors:
                        failed += 1
                        errors.append({
                            'document_id': document_id,
                            'error': f"Validation failed: {', '.join(validation_errors)}"
                        })
                        continue
                
                # Apply the update
                self.update_document_metadata(
                    document_id=document_id,
                    title=update_info.get('title'),
                    correspondent=update_info.get('correspondent'),
                    document_type=update_info.get('document_type'),
                    tags=update_info.get('tags'),
                    description=update_info.get('description'),
                    custom_fields=update_info.get('custom_fields')
                )
                successful += 1
                logger.debug(f"Updated document {document_id} ({idx}/{total})")
                
            except Exception as e:
                failed += 1
                errors.append({
                    'document_id': document_id,
                    'error': str(e)
                })
                logger.error(f"Failed to update document {document_id}: {e}")
        
        logger.info(f"Batch metadata update complete: {successful} successful, {failed} failed")
        return successful, failed, errors
    
    def _validate_document_metadata(self, metadata: Dict[str, Any]) -> List[str]:
        """Validate document metadata according to business rules.
        
        Args:
            metadata: Metadata to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        settings = get_settings()
        
        # Validate correspondent (ensure Daniel/EBN is never sender)
        correspondent = metadata.get('correspondent', '')
        if correspondent:
            daniel_variants = ['daniel', 'schindler', 'ebn', 'veranstaltungen']
            correspondent_lower = correspondent.lower()
            if any(variant in correspondent_lower for variant in daniel_variants):
                errors.append(
                    f"Invalid correspondent '{correspondent}': "
                    f"Daniel/EBN ist immer Empfänger, nie Absender"
                )
        
        # Validate tags count
        tags = metadata.get('tags', [])
        if tags:
            if len(tags) < settings.min_tags:
                errors.append(f"Zu wenige Tags: {len(tags)} (mindestens {settings.min_tags} erforderlich)")
            elif len(tags) > settings.max_tags:
                errors.append(f"Zu viele Tags: {len(tags)} (maximal {settings.max_tags} erlaubt)")
        
        # Validate description length
        description = metadata.get('description', '')
        if description and len(description) > settings.max_description_length:
            errors.append(
                f"Beschreibung zu lang: {len(description)} Zeichen "
                f"(maximal {settings.max_description_length} erlaubt)"
            )
        
        # Validate title
        title = metadata.get('title', '')
        if title and len(title) > 255:
            errors.append(f"Titel zu lang: {len(title)} Zeichen (maximal 255 erlaubt)")
        
        return errors
    
    # Statistics and Analysis
    
    def get_document_statistics(
        self,
        since_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get document statistics.
        
        Args:
            since_date: Optional date filter
            
        Returns:
            Statistics dictionary
        """
        stats = {
            'total_documents': 0,
            'documents_with_ocr': 0,
            'documents_without_ocr': 0,
            'documents_by_correspondent': {},
            'documents_by_type': {},
            'documents_by_month': {},
            'top_tags': []
        }
        
        # Get all documents in chunks
        for chunk in self.get_documents_chunked(since_date=since_date):
            for doc in chunk:
                stats['total_documents'] += 1
                
                # OCR status
                if doc.get('content') or doc.get('ocr'):
                    stats['documents_with_ocr'] += 1
                else:
                    stats['documents_without_ocr'] += 1
                
                # By correspondent
                correspondent = doc.get('correspondent_name', 'Unassigned')
                stats['documents_by_correspondent'][correspondent] = \
                    stats['documents_by_correspondent'].get(correspondent, 0) + 1
                
                # By type
                doc_type = doc.get('document_type_name', 'Unassigned')
                stats['documents_by_type'][doc_type] = \
                    stats['documents_by_type'].get(doc_type, 0) + 1
                
                # By month
                created = doc.get('created')
                if created:
                    month_key = created[:7]  # YYYY-MM
                    stats['documents_by_month'][month_key] = \
                        stats['documents_by_month'].get(month_key, 0) + 1
        
        # Get top tags
        if self._tag_cache is None:
            self._tag_cache = self.api_client.get_all_tags()
        
        sorted_tags = sorted(
            self._tag_cache,
            key=lambda t: t.get('document_count', 0),
            reverse=True
        )
        stats['top_tags'] = [
            {'name': t['name'], 'count': t.get('document_count', 0)}
            for t in sorted_tags[:10]
        ]
        
        return stats
    
    # Utility Methods
    
    def test_connection(self) -> bool:
        """Test connection to Paperless API.
        
        Returns:
            True if connection successful
        """
        return self.api_client.test_connection()
    
    def clear_caches(self) -> None:
        """Clear all entity caches."""
        self._tag_cache = None
        self._correspondent_cache = None
        self._document_type_cache = None
        logger.debug("Cleared all entity caches")
    
    def close(self) -> None:
        """Close the API client connection."""
        self.api_client.close()
    
    def __enter__(self) -> 'PaperlessApiService':
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()