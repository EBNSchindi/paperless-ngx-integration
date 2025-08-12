"""Paperless NGX API client implementation with retry logic and connection pooling.

This module provides a robust HTTP client for interacting with the Paperless NGX REST API,
including authentication, retry mechanisms, and efficient connection management.

CRITICAL: This client automatically adds format=json to all API requests to ensure
JSON responses instead of HTML browsable API responses from Django REST Framework.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple, Union
from urllib.parse import urljoin, urlparse, parse_qs, urlencode

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError, HTTPError, RequestException, Timeout
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)
from urllib3.util.retry import Retry

from ...domain.exceptions import (
    PaperlessAPIError,
    PaperlessAuthenticationError,
    PaperlessConnectionError,
    PaperlessRateLimitError,
    PaperlessTimeoutError,
)
from ..config import get_settings

logger = logging.getLogger(__name__)


class ApiRequestBuilder:
    """Builder class for constructing API requests with proper formatting.
    
    This class ensures all API requests include the format=json parameter
    to prevent Django REST Framework from returning HTML responses.
    """
    
    def __init__(self, base_url: str):
        """Initialize the request builder.
        
        Args:
            base_url: Base URL for the API
        """
        self.base_url = base_url.rstrip('/')
    
    def build_url(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Tuple[str, Dict[str, Any]]:
        """Build a complete URL with format=json parameter.
        
        Args:
            endpoint: API endpoint (relative to base_url)
            params: Query parameters
            
        Returns:
            Tuple of (complete_url, updated_params)
        """
        # Ensure endpoint starts with /
        if not endpoint.startswith('/'):
            endpoint = f'/{endpoint}'
        
        # Build full URL
        url = urljoin(self.base_url, endpoint)
        
        # Ensure params dict exists and includes format=json
        if params is None:
            params = {}
        
        # CRITICAL: Always add format=json to force JSON responses
        params['format'] = 'json'
        
        return url, params
    
    def ensure_json_format(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Ensure params include format=json.
        
        Args:
            params: Existing parameters
            
        Returns:
            Updated parameters with format=json
        """
        if params is None:
            params = {}
        params['format'] = 'json'
        return params


class PaperlessApiClient:
    """Low-level client for Paperless NGX API interactions.
    
    This class handles:
    - HTTP session management with connection pooling
    - Authentication via API token
    - Automatic retry with exponential backoff
    - Rate limiting
    - Pagination support
    - Error handling and logging
    - Automatic format=json parameter injection
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout: Optional[Tuple[int, int]] = None,
        max_retries: int = 3,
        rate_limit: Optional[float] = None,
    ):
        """Initialize the Paperless API client.
        
        Args:
            base_url: Base URL for Paperless NGX API (e.g., 'http://localhost:8000/api')
            api_token: API authentication token
            timeout: Tuple of (connect_timeout, read_timeout) in seconds
            max_retries: Maximum number of retry attempts
            rate_limit: Maximum requests per second (0 for no limit)
        """
        settings = get_settings()
        
        self.base_url = (base_url or settings.paperless_base_url).rstrip('/')
        self.api_token = api_token or settings.get_secret_value('paperless_api_token')
        
        if not self.api_token:
            raise PaperlessAuthenticationError("API token is required")
        
        self.timeout = timeout or (
            settings.paperless_timeout_connect,
            settings.paperless_timeout_read
        )
        self.max_retries = max_retries
        self.rate_limit = rate_limit or settings.paperless_rate_limit
        
        # Track last request time for rate limiting
        self._last_request_time = 0.0
        
        # Create request builder for URL construction
        self.request_builder = ApiRequestBuilder(self.base_url)
        
        # Create session with connection pooling
        self.session = self._create_session()
        
        logger.info(f"Initialized Paperless API client for {self.base_url} with automatic format=json")
    
    def _create_session(self) -> requests.Session:
        """Create HTTP session with connection pooling and retry logic.
        
        Returns:
            Configured requests Session
        """
        session = requests.Session()
        
        # Set authentication header
        session.headers.update({
            'Authorization': f'Token {self.api_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })
        
        # Configure connection pooling and retries
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"],
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20,
            pool_block=False,
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _apply_rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        if self.rate_limit > 0:
            current_time = time.time()
            time_since_last = current_time - self._last_request_time
            min_interval = 1.0 / self.rate_limit
            
            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.3f}s")
                time.sleep(sleep_time)
            
            self._last_request_time = time.time()
    
    @retry(
        retry=retry_if_exception_type((ConnectionError, Timeout)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        files: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ) -> requests.Response:
        """Make HTTP request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint (relative to base_url)
            params: Query parameters
            json_data: JSON data for request body
            data: Form data for request body
            files: Files for multipart upload
            stream: Whether to stream the response
            
        Returns:
            HTTP response object
            
        Raises:
            PaperlessAPIError: For API-specific errors
            PaperlessAuthenticationError: For authentication failures
            PaperlessRateLimitError: When rate limited
            PaperlessTimeoutError: For timeout errors
            PaperlessConnectionError: For connection errors
        """
        # Apply rate limiting
        self._apply_rate_limit()
        
        # Build full URL
        # Fix urljoin behavior - ensure /api is preserved
        if not self.base_url.endswith('/'):
            base = self.base_url + '/'
        else:
            base = self.base_url
        url = urljoin(base, endpoint.lstrip('/'))
        
        # CRITICAL: Ensure format=json is ALWAYS in params
        if params is None:
            params = {}
        
        # Force format=json to prevent HTML responses
        params['format'] = 'json'
        
        # Log the full URL with params for debugging
        param_string = urlencode(params) if params else ""
        full_url = f"{url}?{param_string}" if param_string else url
        logger.debug(f"{method} {full_url}")
        logger.debug(f"Request params: {params}")
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                data=data,
                files=files,
                timeout=self.timeout,
                stream=stream,
            )
            
            # Check for specific error conditions
            if response.status_code == 401:
                raise PaperlessAuthenticationError("Invalid API token or unauthorized access")
            elif response.status_code == 429:
                retry_after = response.headers.get('Retry-After', '60')
                raise PaperlessRateLimitError(f"Rate limited. Retry after {retry_after} seconds")
            elif response.status_code >= 500:
                raise PaperlessAPIError(f"Server error: {response.status_code} - {response.text}")
            
            # Raise for other HTTP errors
            response.raise_for_status()
            
            return response
            
        except Timeout as e:
            raise PaperlessTimeoutError(f"Request timed out: {e}")
        except ConnectionError as e:
            raise PaperlessConnectionError(f"Connection error: {e}")
        except HTTPError as e:
            if e.response is not None:
                error_detail = e.response.text
                logger.error(f"HTTP error {e.response.status_code}: {error_detail}")
                raise PaperlessAPIError(f"HTTP {e.response.status_code}: {error_detail}")
            raise PaperlessAPIError(f"HTTP error: {e}")
        except RequestException as e:
            raise PaperlessAPIError(f"Request failed: {e}")
    
    # Document operations
    
    def get_documents(
        self,
        page: int = 1,
        page_size: int = 100,
        ordering: Optional[str] = None,
        **filters: Any
    ) -> Dict[str, Any]:
        """Get paginated list of documents.
        
        Args:
            page: Page number (1-based)
            page_size: Number of documents per page
            ordering: Field to order by (e.g., '-created', 'title')
            **filters: Additional filters (e.g., correspondent__id=1, tags__id__in=1,2,3)
            
        Returns:
            Dictionary with 'count', 'next', 'previous', and 'results' keys
        """
        params = {
            'page': page,
            'page_size': page_size,
        }
        
        if ordering:
            params['ordering'] = ordering
        
        # Add any additional filters
        params.update(filters)
        
        # CRITICAL: Force JSON response (must be AFTER update to not get overwritten!)
        params['format'] = 'json'
        
        response = self._make_request('GET', '/documents/', params=params)
        return response.json()
    
    def get_documents_generator(
        self,
        page_size: int = 100,
        ordering: Optional[str] = None,
        **filters: Any
    ) -> Generator[Dict[str, Any], None, None]:
        """Get all documents as a generator for memory efficiency.
        
        Args:
            page_size: Number of documents per page
            ordering: Field to order by
            **filters: Additional filters
            
        Yields:
            Individual document dictionaries
        """
        page = 1
        
        while True:
            data = self.get_documents(
                page=page,
                page_size=page_size,
                ordering=ordering,
                **filters
            )
            
            for document in data['results']:
                yield document
            
            if not data['next']:
                break
            
            page += 1
    
    def get_document(self, document_id: int) -> Dict[str, Any]:
        """Get single document by ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            Document dictionary
        """
        response = self._make_request('GET', f'/documents/{document_id}/')
        return response.json()
    
    def update_document(
        self,
        document_id: int,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update document metadata.
        
        Args:
            document_id: Document ID
            data: Updated document data
            
        Returns:
            Updated document dictionary
        """
        response = self._make_request('PATCH', f'/documents/{document_id}/', json_data=data)
        return response.json()
    
    def delete_document(self, document_id: int) -> None:
        """Delete a document.
        
        Args:
            document_id: Document ID
        """
        self._make_request('DELETE', f'/documents/{document_id}/')
    
    def upload_document(
        self,
        file_path: Path,
        title: Optional[str] = None,
        correspondent_id: Optional[int] = None,
        document_type_id: Optional[int] = None,
        tag_ids: Optional[List[int]] = None,
        notes: Optional[str] = None,
        custom_fields: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Upload a new document.
        
        Args:
            file_path: Path to document file
            title: Document title
            correspondent_id: Correspondent ID
            document_type_id: Document type ID
            tag_ids: List of tag IDs
            notes: Document notes/summary
            custom_fields: List of custom field values
            
        Returns:
            Created document dictionary
        """
        with open(file_path, 'rb') as f:
            files = {'document': (file_path.name, f, 'application/octet-stream')}
            
            data = {}
            if title:
                data['title'] = title
            if correspondent_id:
                data['correspondent'] = correspondent_id
            if document_type_id:
                data['document_type'] = document_type_id
            if tag_ids:
                data['tags'] = ','.join(map(str, tag_ids))
            if notes:
                data['notes'] = notes
            if custom_fields:
                data['custom_fields'] = custom_fields
            
            response = self._make_request('POST', '/documents/post_document/', data=data, files=files)
            return response.json()
    
    # Correspondent operations
    
    def get_correspondents(self, page: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """Get paginated list of correspondents.
        
        Args:
            page: Page number
            page_size: Items per page
            
        Returns:
            Paginated response dictionary
        """
        params = {'page': page, 'page_size': page_size}
        params['format'] = 'json'  # Force JSON response
        response = self._make_request('GET', '/correspondents/', params=params)
        return response.json()
    
    def get_correspondent(self, correspondent_id: int) -> Dict[str, Any]:
        """Get single correspondent by ID.
        
        Args:
            correspondent_id: Correspondent ID
            
        Returns:
            Correspondent dictionary
        """
        response = self._make_request('GET', f'/correspondents/{correspondent_id}/')
        return response.json()
    
    def create_correspondent(self, name: str, **kwargs: Any) -> Dict[str, Any]:
        """Create a new correspondent.
        
        Args:
            name: Correspondent name
            **kwargs: Additional fields (match_text, matching_algorithm, is_insensitive)
            
        Returns:
            Created correspondent dictionary
        """
        data = {'name': name, **kwargs}
        response = self._make_request('POST', '/correspondents/', json_data=data)
        return response.json()
    
    def update_correspondent(
        self,
        correspondent_id: int,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update correspondent.
        
        Args:
            correspondent_id: Correspondent ID
            data: Updated correspondent data
            
        Returns:
            Updated correspondent dictionary
        """
        response = self._make_request('PATCH', f'/correspondents/{correspondent_id}/', json_data=data)
        return response.json()
    
    # Tag operations
    
    def get_tags(self, page: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """Get paginated list of tags.
        
        Args:
            page: Page number
            page_size: Items per page
            
        Returns:
            Paginated response dictionary
        """
        params = {'page': page, 'page_size': page_size}
        params['format'] = 'json'  # Force JSON response
        response = self._make_request('GET', '/tags/', params=params)
        return response.json()
    
    def get_all_tags(self) -> List[Dict[str, Any]]:
        """Get all tags (unpaginated).
        
        Returns:
            List of all tag dictionaries
        """
        all_tags = []
        page = 1
        
        while True:
            data = self.get_tags(page=page, page_size=100)
            all_tags.extend(data['results'])
            
            if not data['next']:
                break
            
            page += 1
        
        return all_tags
    
    def get_tag(self, tag_id: int) -> Dict[str, Any]:
        """Get single tag by ID.
        
        Args:
            tag_id: Tag ID
            
        Returns:
            Tag dictionary
        """
        response = self._make_request('GET', f'/tags/{tag_id}/')
        return response.json()
    
    def create_tag(self, name: str, color: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        """Create a new tag.
        
        Args:
            name: Tag name
            color: Tag color (hex format)
            **kwargs: Additional fields
            
        Returns:
            Created tag dictionary
        """
        data = {'name': name}
        if color:
            data['color'] = color
        data.update(kwargs)
        
        response = self._make_request('POST', '/tags/', json_data=data)
        return response.json()
    
    def update_tag(self, tag_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update tag.
        
        Args:
            tag_id: Tag ID
            data: Updated tag data
            
        Returns:
            Updated tag dictionary
        """
        response = self._make_request('PATCH', f'/tags/{tag_id}/', json_data=data)
        return response.json()
    
    def delete_tag(self, tag_id: int) -> None:
        """Delete a tag.
        
        Args:
            tag_id: Tag ID
        """
        self._make_request('DELETE', f'/tags/{tag_id}/')
    
    # Document type operations
    
    def get_document_types(self, page: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """Get paginated list of document types.
        
        Args:
            page: Page number
            page_size: Items per page
            
        Returns:
            Paginated response dictionary
        """
        params = {'page': page, 'page_size': page_size}
        params['format'] = 'json'  # Force JSON response
        response = self._make_request('GET', '/document_types/', params=params)
        return response.json()
    
    def get_document_type(self, document_type_id: int) -> Dict[str, Any]:
        """Get single document type by ID.
        
        Args:
            document_type_id: Document type ID
            
        Returns:
            Document type dictionary
        """
        response = self._make_request('GET', f'/document_types/{document_type_id}/')
        return response.json()
    
    def create_document_type(self, name: str, **kwargs: Any) -> Dict[str, Any]:
        """Create a new document type.
        
        Args:
            name: Document type name
            **kwargs: Additional fields
            
        Returns:
            Created document type dictionary
        """
        data = {'name': name, **kwargs}
        response = self._make_request('POST', '/document_types/', json_data=data)
        return response.json()
    
    # Custom field operations
    
    def get_custom_fields(self) -> List[Dict[str, Any]]:
        """Get list of custom fields.
        
        Returns:
            List of custom field dictionaries
        """
        response = self._make_request('GET', '/custom_fields/')
        return response.json()['results']
    
    def get_custom_field(self, field_id: int) -> Dict[str, Any]:
        """Get single custom field by ID.
        
        Args:
            field_id: Custom field ID
            
        Returns:
            Custom field dictionary
        """
        response = self._make_request('GET', f'/custom_fields/{field_id}/')
        return response.json()
    
    # Search operations
    
    def search_documents(
        self,
        query: str,
        page: int = 1,
        page_size: int = 100,
        **filters: Any
    ) -> Dict[str, Any]:
        """Search documents with full-text search.
        
        Args:
            query: Search query string
            page: Page number
            page_size: Items per page
            **filters: Additional filters
            
        Returns:
            Search results dictionary
        """
        params = {
            'query': query,
            'page': page,
            'page_size': page_size,
        }
        params.update(filters)
        
        response = self._make_request('GET', '/documents/', params=params)
        return response.json()
    
    # Utility methods
    
    def test_connection(self) -> bool:
        """Test connection to Paperless API.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Test with minimal page size - format=json added automatically
            response = self._make_request('GET', '/documents/', params={'page_size': 1})
            
            # Also verify we get JSON response
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Check for expected JSON structure
                    if 'results' in data or 'count' in data:
                        logger.info("Connection test successful - JSON response received")
                        return True
                    else:
                        logger.warning(f"Unexpected JSON structure: {list(data.keys())}")
                        return False
                except ValueError:
                    logger.error("Connection test failed - response is not JSON")
                    return False
            return False
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def get_raw_response(self, endpoint: str, **params: Any) -> Dict[str, Any]:
        """Get raw response from API for debugging.
        
        Args:
            endpoint: API endpoint
            **params: Query parameters
            
        Returns:
            Raw response dictionary
        """
        try:
            response = self._make_request('GET', endpoint, params=params)
            return {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'content_type': response.headers.get('Content-Type', ''),
                'is_json': 'application/json' in response.headers.get('Content-Type', ''),
                'data': response.json() if 'application/json' in response.headers.get('Content-Type', '') else response.text[:500]
            }
        except Exception as e:
            return {
                'error': str(e),
                'status_code': None,
                'headers': {},
                'content_type': '',
                'is_json': False,
                'data': None
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get Paperless statistics.
        
        Returns:
            Statistics dictionary
        """
        response = self._make_request('GET', '/statistics/')
        return response.json()
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get server information.
        
        Returns:
            Server info dictionary
        """
        response = self._make_request('GET', '/ui_settings/')
        return response.json()
    
    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()
        logger.debug("Closed Paperless API client session")
    
    def __enter__(self) -> 'PaperlessApiClient':
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()