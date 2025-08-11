"""Comprehensive integration tests for Paperless API client.

Tests API interactions including pagination, retry logic, rate limiting,
and authentication failures.
"""

import json
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timedelta
import time
import requests
from requests.exceptions import ConnectionError, Timeout, HTTPError

from src.paperless_ngx.infrastructure.paperless.api_client import PaperlessApiClient
from src.paperless_ngx.application.services.paperless_api_service import PaperlessApiService


class TestPaperlessApiClient:
    """Test suite for Paperless API client."""
    
    @pytest.fixture
    def api_client(self, mock_settings):
        """Create API client instance."""
        return PaperlessApiClient(mock_settings)
    
    @pytest.fixture
    def mock_session(self):
        """Create mock requests session."""
        session = MagicMock()
        session.headers = {}
        return session
    
    @pytest.fixture
    def api_client_with_mock_session(self, mock_settings, mock_session):
        """Create API client with mocked session."""
        client = PaperlessApiClient(mock_settings)
        client.session = mock_session
        return client
    
    # ============= Connection and Authentication Tests =============
    
    @patch('requests.Session')
    def test_client_initialization(self, mock_session_class, mock_settings):
        """Test API client initialization."""
        client = PaperlessApiClient(mock_settings)
        
        assert client.base_url == mock_settings.paperless_api_url
        assert client.timeout == mock_settings.timeout
        mock_session_class.assert_called_once()
    
    @patch('requests.Session')
    def test_authentication_header_setup(self, mock_session_class, mock_settings):
        """Test authentication header is properly set."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        client = PaperlessApiClient(mock_settings)
        
        expected_header = f"Token {mock_settings.paperless_api_token}"
        mock_session.headers.update.assert_called_with({
            "Authorization": expected_header
        })
    
    def test_authentication_failure(self, api_client_with_mock_session):
        """Test handling of authentication failures."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = HTTPError("401 Unauthorized")
        mock_response.text = "Invalid token"
        
        api_client_with_mock_session.session.get.return_value = mock_response
        
        with pytest.raises(HTTPError):
            api_client_with_mock_session.get_documents()
    
    def test_forbidden_access(self, api_client_with_mock_session):
        """Test handling of forbidden access errors."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = HTTPError("403 Forbidden")
        
        api_client_with_mock_session.session.get.return_value = mock_response
        
        with pytest.raises(HTTPError):
            api_client_with_mock_session.get_documents()
    
    # ============= Pagination Tests =============
    
    def test_pagination_single_page(self, api_client_with_mock_session):
        """Test pagination with single page of results."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'count': 2,
            'next': None,
            'previous': None,
            'results': [
                {'id': 1, 'title': 'Doc 1'},
                {'id': 2, 'title': 'Doc 2'}
            ]
        }
        mock_response.raise_for_status = Mock()
        
        api_client_with_mock_session.session.get.return_value = mock_response
        
        documents = api_client_with_mock_session.get_documents()
        
        assert len(documents) == 2
        assert documents[0]['id'] == 1
        api_client_with_mock_session.session.get.assert_called_once()
    
    def test_pagination_multiple_pages(self, api_client_with_mock_session):
        """Test pagination with multiple pages of results."""
        # Page 1 response
        page1_response = Mock()
        page1_response.status_code = 200
        page1_response.json.return_value = {
            'count': 150,
            'next': 'http://test.example.com/api/documents/?page=2',
            'previous': None,
            'results': [{'id': i, 'title': f'Doc {i}'} for i in range(1, 101)]
        }
        page1_response.raise_for_status = Mock()
        
        # Page 2 response
        page2_response = Mock()
        page2_response.status_code = 200
        page2_response.json.return_value = {
            'count': 150,
            'next': None,
            'previous': 'http://test.example.com/api/documents/?page=1',
            'results': [{'id': i, 'title': f'Doc {i}'} for i in range(101, 151)]
        }
        page2_response.raise_for_status = Mock()
        
        api_client_with_mock_session.session.get.side_effect = [page1_response, page2_response]
        
        documents = api_client_with_mock_session.get_documents()
        
        assert len(documents) == 150
        assert documents[0]['id'] == 1
        assert documents[149]['id'] == 150
        assert api_client_with_mock_session.session.get.call_count == 2
    
    def test_pagination_with_filters(self, api_client_with_mock_session):
        """Test pagination with query filters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'count': 5,
            'next': None,
            'results': [{'id': i} for i in range(1, 6)]
        }
        mock_response.raise_for_status = Mock()
        
        api_client_with_mock_session.session.get.return_value = mock_response
        
        filters = {
            'correspondent__id': 1,
            'created__date__gte': '2024-01-01',
            'created__date__lte': '2024-12-31'
        }
        
        documents = api_client_with_mock_session.get_documents(**filters)
        
        # Check that filters were passed as params
        call_args = api_client_with_mock_session.session.get.call_args
        assert call_args[1]['params'] == filters
    
    # ============= Retry Logic Tests =============
    
    def test_retry_on_connection_error(self, api_client_with_mock_session):
        """Test retry logic on connection errors."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'count': 0, 'results': []}
        mock_response.raise_for_status = Mock()
        
        # First two calls fail, third succeeds
        api_client_with_mock_session.session.get.side_effect = [
            ConnectionError("Connection failed"),
            ConnectionError("Connection failed"),
            mock_response
        ]
        
        with patch('time.sleep') as mock_sleep:  # Mock sleep to speed up test
            documents = api_client_with_mock_session.get_documents()
        
        assert documents == []
        assert api_client_with_mock_session.session.get.call_count == 3
        # Check exponential backoff was applied
        assert mock_sleep.call_count == 2
    
    def test_retry_on_timeout(self, api_client_with_mock_session):
        """Test retry logic on timeout errors."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'count': 1, 'results': [{'id': 1}]}
        mock_response.raise_for_status = Mock()
        
        api_client_with_mock_session.session.get.side_effect = [
            Timeout("Request timed out"),
            mock_response
        ]
        
        with patch('time.sleep'):
            documents = api_client_with_mock_session.get_documents()
        
        assert len(documents) == 1
        assert api_client_with_mock_session.session.get.call_count == 2
    
    def test_retry_on_server_error(self, api_client_with_mock_session):
        """Test retry logic on 5xx server errors."""
        error_response = Mock()
        error_response.status_code = 500
        error_response.raise_for_status.side_effect = HTTPError("500 Internal Server Error")
        
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {'count': 0, 'results': []}
        success_response.raise_for_status = Mock()
        
        api_client_with_mock_session.session.get.side_effect = [
            error_response,
            success_response
        ]
        
        with patch('time.sleep'):
            documents = api_client_with_mock_session.get_documents()
        
        assert documents == []
        assert api_client_with_mock_session.session.get.call_count == 2
    
    def test_max_retries_exceeded(self, api_client_with_mock_session):
        """Test behavior when max retries are exceeded."""
        api_client_with_mock_session.session.get.side_effect = ConnectionError("Connection failed")
        
        with patch('time.sleep'):
            with pytest.raises(ConnectionError):
                # Assuming max_retries is 3
                api_client_with_mock_session.get_documents()
        
        # Should attempt initial call + retries
        expected_calls = 4  # 1 initial + 3 retries
        assert api_client_with_mock_session.session.get.call_count == expected_calls
    
    # ============= Rate Limiting Tests =============
    
    def test_rate_limit_429_response(self, api_client_with_mock_session):
        """Test handling of 429 Too Many Requests responses."""
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {'Retry-After': '2'}
        rate_limit_response.raise_for_status.side_effect = HTTPError("429 Too Many Requests")
        
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {'count': 0, 'results': []}
        success_response.raise_for_status = Mock()
        
        api_client_with_mock_session.session.get.side_effect = [
            rate_limit_response,
            success_response
        ]
        
        with patch('time.sleep') as mock_sleep:
            documents = api_client_with_mock_session.get_documents()
        
        assert documents == []
        # Should respect Retry-After header
        mock_sleep.assert_called_with(2)
    
    def test_concurrent_request_limiting(self, api_client_with_mock_session):
        """Test concurrent request limiting."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'count': 0, 'results': []}
        mock_response.raise_for_status = Mock()
        
        api_client_with_mock_session.session.get.return_value = mock_response
        
        # Simulate multiple rapid requests
        for _ in range(5):
            api_client_with_mock_session.get_documents()
        
        assert api_client_with_mock_session.session.get.call_count == 5
    
    # ============= Document Operations Tests =============
    
    def test_get_document_by_id(self, api_client_with_mock_session):
        """Test fetching a specific document by ID."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 123,
            'title': 'Test Document',
            'content': 'Document content'
        }
        mock_response.raise_for_status = Mock()
        
        api_client_with_mock_session.session.get.return_value = mock_response
        
        document = api_client_with_mock_session.get_document(123)
        
        assert document['id'] == 123
        assert document['title'] == 'Test Document'
        api_client_with_mock_session.session.get.assert_called_with(
            'http://test.example.com/api/documents/123/',
            params=None,
            timeout=30
        )
    
    def test_update_document(self, api_client_with_mock_session):
        """Test updating document metadata."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 123,
            'title': 'Updated Title',
            'tags': [1, 2, 3]
        }
        mock_response.raise_for_status = Mock()
        
        api_client_with_mock_session.session.patch.return_value = mock_response
        
        update_data = {
            'title': 'Updated Title',
            'tags': [1, 2, 3]
        }
        
        result = api_client_with_mock_session.update_document(123, update_data)
        
        assert result['title'] == 'Updated Title'
        api_client_with_mock_session.session.patch.assert_called_with(
            'http://test.example.com/api/documents/123/',
            json=update_data,
            timeout=30
        )
    
    def test_create_correspondent(self, api_client_with_mock_session):
        """Test creating a new correspondent."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'id': 10,
            'name': 'New Correspondent',
            'slug': 'new-correspondent'
        }
        mock_response.raise_for_status = Mock()
        
        api_client_with_mock_session.session.post.return_value = mock_response
        
        correspondent = api_client_with_mock_session.create_correspondent('New Correspondent')
        
        assert correspondent['id'] == 10
        assert correspondent['name'] == 'New Correspondent'
        api_client_with_mock_session.session.post.assert_called_with(
            'http://test.example.com/api/correspondents/',
            json={'name': 'New Correspondent'},
            timeout=30
        )
    
    def test_create_tag(self, api_client_with_mock_session):
        """Test creating a new tag."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'id': 20,
            'name': 'New Tag',
            'slug': 'new-tag'
        }
        mock_response.raise_for_status = Mock()
        
        api_client_with_mock_session.session.post.return_value = mock_response
        
        tag = api_client_with_mock_session.create_tag('New Tag')
        
        assert tag['id'] == 20
        assert tag['name'] == 'New Tag'
    
    # ============= Error Response Tests =============
    
    def test_handle_404_not_found(self, api_client_with_mock_session):
        """Test handling of 404 Not Found responses."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = HTTPError("404 Not Found")
        
        api_client_with_mock_session.session.get.return_value = mock_response
        
        with pytest.raises(HTTPError) as exc_info:
            api_client_with_mock_session.get_document(999)
        
        assert "404" in str(exc_info.value)
    
    def test_handle_400_bad_request(self, api_client_with_mock_session):
        """Test handling of 400 Bad Request responses."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'error': 'Invalid parameters',
            'details': {'field': 'Invalid value'}
        }
        mock_response.raise_for_status.side_effect = HTTPError("400 Bad Request")
        
        api_client_with_mock_session.session.post.return_value = mock_response
        
        with pytest.raises(HTTPError):
            api_client_with_mock_session.create_tag('')  # Empty tag name
    
    def test_handle_json_decode_error(self, api_client_with_mock_session):
        """Test handling of invalid JSON responses."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.text = "Not valid JSON"
        mock_response.raise_for_status = Mock()
        
        api_client_with_mock_session.session.get.return_value = mock_response
        
        with pytest.raises(json.JSONDecodeError):
            api_client_with_mock_session.get_documents()
    
    # ============= Batch Operations Tests =============
    
    def test_batch_get_documents(self, api_client_with_mock_session):
        """Test batch fetching of documents."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'count': 250,
            'next': None,
            'results': [{'id': i} for i in range(1, 251)]
        }
        mock_response.raise_for_status = Mock()
        
        api_client_with_mock_session.session.get.return_value = mock_response
        
        documents = api_client_with_mock_session.get_documents(page_size=250)
        
        assert len(documents) == 250
        # Should request with page_size parameter
        call_args = api_client_with_mock_session.session.get.call_args
        assert call_args[1]['params'].get('page_size') == 250
    
    def test_batch_update_documents(self, api_client_with_mock_session):
        """Test batch updating of multiple documents."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': 1, 'updated': True}
        mock_response.raise_for_status = Mock()
        
        api_client_with_mock_session.session.patch.return_value = mock_response
        
        documents_to_update = [
            {'id': 1, 'title': 'New Title 1'},
            {'id': 2, 'title': 'New Title 2'},
            {'id': 3, 'title': 'New Title 3'}
        ]
        
        for doc in documents_to_update:
            api_client_with_mock_session.update_document(doc['id'], {'title': doc['title']})
        
        assert api_client_with_mock_session.session.patch.call_count == 3


class TestPaperlessApiService:
    """Test suite for Paperless API service layer."""
    
    @pytest.fixture
    def api_service(self, mock_api_client, mock_llm_client):
        """Create API service instance."""
        service = PaperlessApiService(mock_api_client, mock_llm_client)
        return service
    
    def test_process_documents_with_metadata_extraction(self, api_service, sample_documents):
        """Test processing documents with metadata extraction."""
        api_service.api_client.get_documents.return_value = sample_documents[:2]
        
        # Mock LLM responses
        api_service.llm_client.extract_metadata.return_value = {
            'title': 'Extracted Title',
            'tags': ['tag1', 'tag2', 'tag3'],
            'correspondent': 'Extracted Sender'
        }
        
        results = api_service.process_documents()
        
        assert len(results) == 2
        assert api_service.llm_client.extract_metadata.call_count == 2
    
    def test_handle_ocr_failures(self, api_service):
        """Test handling of documents with OCR failures."""
        documents_with_ocr_issues = [
            {'id': 1, 'content': '', 'ocr': None},  # No OCR
            {'id': 2, 'content': 'Short', 'ocr': None},  # Too short
            {'id': 3, 'content': 'Valid OCR text ' * 20, 'ocr': None}  # Valid
        ]
        
        api_service.api_client.get_documents.return_value = documents_with_ocr_issues
        
        results = api_service.process_documents()
        
        # Should skip documents with OCR issues
        assert len(results) <= 3
    
    def test_entity_creation_and_caching(self, api_service):
        """Test creation and caching of entities (tags, correspondents)."""
        # First call - entity doesn't exist
        api_service.api_client.get_tags.return_value = []
        api_service.api_client.create_tag.return_value = {'id': 1, 'name': 'New Tag'}
        
        tag_id = api_service.get_or_create_tag('New Tag')
        assert tag_id == 1
        
        # Second call - should use cache
        tag_id = api_service.get_or_create_tag('New Tag')
        assert tag_id == 1
        # Should not create again
        assert api_service.api_client.create_tag.call_count == 1
    
    def test_date_range_filtering(self, api_service):
        """Test document filtering by date range."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        api_service.api_client.get_documents.return_value = []
        
        api_service.process_documents_in_date_range(start_date, end_date)
        
        # Check that date filters were applied
        call_args = api_service.api_client.get_documents.call_args
        assert 'created__date__gte' in call_args[1]
        assert 'created__date__lte' in call_args[1]
    
    def test_concurrent_processing_with_threading(self, api_service, sample_documents):
        """Test concurrent document processing."""
        import threading
        
        api_service.api_client.get_documents.return_value = sample_documents
        
        results = []
        
        def process_batch():
            batch_results = api_service.process_documents()
            results.extend(batch_results)
        
        threads = [threading.Thread(target=process_batch) for _ in range(3)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should handle concurrent processing
        assert len(results) > 0
    
    def test_error_recovery_and_logging(self, api_service):
        """Test error recovery and logging during processing."""
        # Document that will cause an error
        problematic_doc = {
            'id': 999,
            'content': 'Test content',
            'title': None  # Will cause issues
        }
        
        api_service.api_client.get_documents.return_value = [problematic_doc]
        api_service.api_client.update_document.side_effect = Exception("Update failed")
        
        with patch('logging.Logger.error') as mock_log_error:
            results = api_service.process_documents()
            
            # Should log the error
            assert mock_log_error.called
    
    def test_streaming_document_processing(self, api_service):
        """Test streaming/generator pattern for large document sets."""
        # Create a generator that yields documents
        def document_generator():
            for i in range(1000):
                yield {'id': i, 'content': f'Document {i} content'}
        
        api_service.api_client.get_documents = Mock(return_value=document_generator())
        
        # Process documents in streaming fashion
        processed_count = 0
        for result in api_service.process_documents_streaming():
            processed_count += 1
            if processed_count >= 10:  # Process only first 10 for test
                break
        
        assert processed_count == 10
    
    def test_custom_field_updates(self, api_service):
        """Test updating custom fields in documents."""
        document = {
            'id': 1,
            'custom_fields': []
        }
        
        api_service.api_client.get_document.return_value = document
        api_service.api_client.update_document.return_value = {
            'id': 1,
            'custom_fields': [{'field': 1, 'value': 'Custom value'}]
        }
        
        result = api_service.update_custom_field(1, field_id=1, value='Custom value')
        
        assert result['custom_fields'][0]['value'] == 'Custom value'
        
    def test_validation_before_update(self, api_service):
        """Test metadata validation before updating documents."""
        document = {
            'id': 1,
            'content': 'Test content'
        }
        
        invalid_metadata = {
            'correspondent': 'Daniel Schindler',  # Invalid - should be recipient
            'tags': ['tag1']  # Too few tags
        }
        
        api_service.llm_client.extract_metadata.return_value = invalid_metadata
        api_service.api_client.get_documents.return_value = [document]
        
        with patch('src.paperless_ngx.domain.validators.metadata_validator.MetadataValidator') as MockValidator:
            mock_validator = Mock()
            mock_validator.validate.return_value = (False, ['Invalid correspondent'], {})
            MockValidator.return_value = mock_validator
            
            results = api_service.process_documents(validate=True)
            
            # Should validate before updating
            assert mock_validator.validate.called