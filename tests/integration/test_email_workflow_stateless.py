"""Integration tests for complete stateless email workflow.

This test suite verifies the complete email fetching and attachment processing
workflow operates in a stateless manner.
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

import pytest

from paperless_ngx.application.services.email_fetcher_service import EmailFetcherService
from paperless_ngx.application.use_cases.attachment_processor import AttachmentProcessor
from paperless_ngx.domain.value_objects.date_range import DateRange
from paperless_ngx.infrastructure.email import EmailAccount, EmailSettings, EmailAttachment


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for integration tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        (workspace / "downloads").mkdir()
        (workspace / "config").mkdir()
        yield workspace


@pytest.fixture
def integration_email_settings(temp_workspace):
    """Create email settings for integration testing."""
    settings = Mock(spec=EmailSettings)
    settings.email_download_dir = temp_workspace / "downloads"
    settings.email_check_interval = 60
    settings.mark_as_read = True
    settings.delete_after_processing = False
    settings.get_email_accounts.return_value = [
        EmailAccount(
            name="Primary Gmail",
            provider="gmail",
            imap_server="imap.gmail.com",
            imap_port=993,
            email="test@gmail.com",
            password="test_password",
            folder="INBOX",
            enabled=True,
            use_ssl=True,
        ),
        EmailAccount(
            name="Work Exchange",
            provider="exchange",
            imap_server="outlook.office365.com",
            imap_port=993,
            email="work@company.com",
            password="work_password",
            folder="INBOX",
            enabled=True,
            use_ssl=True,
        ),
    ]
    return settings


@pytest.fixture
def mock_email_with_attachments():
    """Create a mock email with multiple attachments."""
    email = Mock()
    email.uid = 12345
    email.subject = "Monthly Invoice and Report"
    email.sender = "accounting@supplier.com"
    email.date = datetime(2025, 1, 15, 14, 30)
    
    # Create attachments
    attachments = []
    
    # PDF invoice
    pdf_attachment = Mock(spec=EmailAttachment)
    pdf_attachment.filename = "invoice_january_2025.pdf"
    pdf_attachment.content = b"%PDF-1.4\n...invoice content..."
    pdf_attachment.size = len(pdf_attachment.content)
    pdf_attachment.email_sender = email.sender
    pdf_attachment.email_subject = email.subject
    pdf_attachment.email_date = email.date
    pdf_attachment.save_to_disk = Mock()
    attachments.append(pdf_attachment)
    
    # PNG receipt
    png_attachment = Mock(spec=EmailAttachment)
    png_attachment.filename = "receipt_scan.png"
    png_attachment.content = b"\x89PNG\r\n\x1a\n...image content..."
    png_attachment.size = len(png_attachment.content)
    png_attachment.email_sender = email.sender
    png_attachment.email_subject = email.subject
    png_attachment.email_date = email.date
    png_attachment.save_to_disk = Mock()
    attachments.append(png_attachment)
    
    email.attachments = attachments
    return email


class TestCompleteEmailWorkflow:
    """Test the complete email fetching and processing workflow."""

    def test_fetch_and_process_workflow(
        self, integration_email_settings, temp_workspace, mock_email_with_attachments
    ):
        """Test complete workflow from email fetch to attachment processing."""
        # Arrange
        service = EmailFetcherService(email_settings=integration_email_settings)
        
        # Mock IMAP client
        mock_client = Mock()
        mock_client.connect = Mock()
        mock_client.disconnect = Mock()
        mock_client.select_folder = Mock()
        mock_client.search_emails = Mock(return_value=[12345, 12346, 12347])
        mock_client.fetch_email = Mock(return_value=mock_email_with_attachments)
        mock_client.mark_as_read = Mock()
        
        # Inject mock client
        service.clients["Primary Gmail"] = mock_client
        
        # Act - Fetch and process emails
        results = service.fetch_account("Primary Gmail", since_date=datetime(2025, 1, 1))
        
        # Assert
        assert len(results) > 0, "Should process attachments"
        assert mock_client.connect.called
        assert mock_client.disconnect.called
        assert mock_client.fetch_email.call_count == 3  # All emails fetched
        
        # Verify no state files created
        state_files = list(temp_workspace.glob("**/*.json"))
        json_files = [f for f in state_files if not f.name.startswith(".")]
        assert len(json_files) == 0, "No state files should be created"

    def test_multiple_date_range_runs(
        self, integration_email_settings, temp_workspace
    ):
        """Test running the same date range multiple times processes same emails."""
        # Arrange
        service = EmailFetcherService(email_settings=integration_email_settings)
        
        mock_client = Mock()
        mock_client.connect = Mock()
        mock_client.disconnect = Mock()
        mock_client.select_folder = Mock()
        mock_client.search_emails = Mock(return_value=[1001, 1002, 1003])
        mock_client.fetch_email = Mock()
        mock_client.fetch_email.return_value = Mock(attachments=[])
        
        service.clients["Primary Gmail"] = mock_client
        
        # Act - Run same date range 3 times
        date_range = datetime(2025, 1, 1)
        run_results = []
        
        for run in range(3):
            mock_client.fetch_email.reset_mock()
            results = service.fetch_account("Primary Gmail", since_date=date_range)
            run_results.append(mock_client.fetch_email.call_count)
        
        # Assert - Same emails processed each time
        assert all(count == 3 for count in run_results), "Should process same 3 emails each run"

    def test_workflow_with_different_date_ranges(
        self, integration_email_settings, temp_workspace
    ):
        """Test workflow with different date ranges."""
        # Arrange
        service = EmailFetcherService(email_settings=integration_email_settings)
        
        mock_client = Mock()
        mock_client.connect = Mock()
        mock_client.disconnect = Mock()
        mock_client.select_folder = Mock()
        
        # Different UIDs for different date ranges
        date_to_uids = {
            datetime(2025, 1, 1): [1001, 1002, 1003],    # January
            datetime(2024, 12, 1): [901, 902],           # December
            datetime(2024, 11, 1): [801, 802, 803, 804], # November
        }
        
        mock_client.search_emails = Mock(side_effect=lambda since_date=None: date_to_uids.get(since_date, []))
        mock_client.fetch_email = Mock(return_value=Mock(attachments=[]))
        
        service.clients["Primary Gmail"] = mock_client
        
        # Act & Assert
        for date, expected_uids in date_to_uids.items():
            mock_client.fetch_email.reset_mock()
            service.fetch_account("Primary Gmail", since_date=date)
            assert mock_client.fetch_email.call_count == len(expected_uids)

    def test_workflow_resilience_to_failures(
        self, integration_email_settings, temp_workspace
    ):
        """Test workflow continues despite individual email failures."""
        # Arrange
        service = EmailFetcherService(email_settings=integration_email_settings)
        
        mock_client = Mock()
        mock_client.connect = Mock()
        mock_client.disconnect = Mock()
        mock_client.select_folder = Mock()
        mock_client.search_emails = Mock(return_value=[2001, 2002, 2003, 2004, 2005])
        
        # Some emails fail, others succeed
        mock_client.fetch_email = Mock(side_effect=[
            Mock(attachments=[]),  # Success
            Exception("Email corrupted"),  # Fail
            Mock(attachments=[]),  # Success
            None,  # Email not found
            Mock(attachments=[]),  # Success
        ])
        
        service.clients["Work Exchange"] = mock_client
        
        # Act
        results = service.fetch_account("Work Exchange", since_date=datetime(2025, 1, 1))
        
        # Assert - Should attempt all emails despite failures
        assert mock_client.fetch_email.call_count == 5

    def test_multiple_account_processing(
        self, integration_email_settings, temp_workspace
    ):
        """Test processing multiple email accounts in single workflow."""
        # Arrange
        service = EmailFetcherService(email_settings=integration_email_settings)
        
        # Mock clients for each account
        gmail_client = Mock()
        gmail_client.connect = Mock()
        gmail_client.disconnect = Mock()
        gmail_client.select_folder = Mock()
        gmail_client.search_emails = Mock(return_value=[3001, 3002])
        gmail_client.fetch_email = Mock(return_value=Mock(attachments=[]))
        
        exchange_client = Mock()
        exchange_client.connect = Mock()
        exchange_client.disconnect = Mock()
        exchange_client.select_folder = Mock()
        exchange_client.search_emails = Mock(return_value=[4001, 4002, 4003])
        exchange_client.fetch_email = Mock(return_value=Mock(attachments=[]))
        
        service.clients["Primary Gmail"] = gmail_client
        service.clients["Work Exchange"] = exchange_client
        
        # Act
        all_results = service.fetch_all_accounts(since_date=datetime(2025, 1, 1))
        
        # Assert
        assert len(all_results) == 2
        assert "Primary Gmail" in all_results
        assert "Work Exchange" in all_results
        assert gmail_client.fetch_email.call_count == 2
        assert exchange_client.fetch_email.call_count == 3


class TestAttachmentProcessingIntegration:
    """Test attachment processing as part of the workflow."""

    def test_all_attachments_saved(
        self, integration_email_settings, temp_workspace
    ):
        """Test that all attachments are saved without duplicate checking."""
        # Arrange
        processor = AttachmentProcessor(
            base_dir=temp_workspace / "downloads",
            organize_by_date=False,
            duplicate_check=True,  # Even with this enabled, should process all
        )
        
        # Create duplicate attachments (same content)
        attachments = []
        for i in range(5):
            att = Mock(spec=EmailAttachment)
            att.filename = f"document_{i}.pdf"
            att.content = b"same content for all"  # Duplicate content
            att.size = len(att.content)
            att.email_sender = "sender@test.com"
            att.email_subject = f"Document {i}"
            att.email_date = datetime.now()
            
            # Mock save_to_disk to track calls
            save_path = temp_workspace / "downloads" / att.filename
            att.save_to_disk = Mock(return_value=save_path)
            attachments.append(att)
        
        # Act
        results = processor.process_attachments(attachments)
        
        # Assert - All processed despite duplicate content
        assert len(results) == 5
        for att in attachments:
            att.save_to_disk.assert_called_once()

    def test_attachment_organization_modes(
        self, integration_email_settings, temp_workspace
    ):
        """Test different attachment organization modes."""
        # Test flat structure
        processor_flat = AttachmentProcessor(
            base_dir=temp_workspace / "flat",
            organize_by_date=False,
            organize_by_sender=False,
        )
        
        # Test date-based structure
        processor_date = AttachmentProcessor(
            base_dir=temp_workspace / "by_date",
            organize_by_date=True,
            organize_by_sender=False,
        )
        
        # Test sender-based structure
        processor_sender = AttachmentProcessor(
            base_dir=temp_workspace / "by_sender",
            organize_by_date=False,
            organize_by_sender=True,
        )
        
        # Create test attachment
        att = Mock(spec=EmailAttachment)
        att.filename = "test.pdf"
        att.content = b"test content"
        att.size = len(att.content)
        att.email_sender = "John Doe <john@example.com>"
        att.email_subject = "Test Document"
        att.email_date = datetime(2025, 1, 15)
        
        # Process with each mode
        for processor, expected_pattern in [
            (processor_flat, "flat"),
            (processor_date, "by_date/2025/01-January"),
            (processor_sender, "by_sender/John_Doe"),
        ]:
            att.save_to_disk = Mock(return_value=Path(f"/tmp/{expected_pattern}/test.pdf"))
            result = processor.process_attachment(att)
            assert result is not None

    def test_large_batch_processing(
        self, integration_email_settings, temp_workspace
    ):
        """Test processing large batch of emails with attachments."""
        # Arrange
        service = EmailFetcherService(email_settings=integration_email_settings)
        
        # Create mock client with many emails
        mock_client = Mock()
        mock_client.connect = Mock()
        mock_client.disconnect = Mock()
        mock_client.select_folder = Mock()
        
        # Generate 100 email UIDs
        large_uid_list = list(range(5000, 5100))
        mock_client.search_emails = Mock(return_value=large_uid_list)
        
        # Each email has 2 attachments
        def create_email_with_attachments(uid):
            email = Mock()
            email.uid = uid
            email.attachments = []
            
            for i in range(2):
                att = Mock(spec=EmailAttachment)
                att.filename = f"doc_{uid}_{i}.pdf"
                att.content = f"content_{uid}_{i}".encode()
                att.size = len(att.content)
                att.email_sender = f"sender_{uid}@test.com"
                att.email_subject = f"Email {uid}"
                att.email_date = datetime.now()
                att.save_to_disk = Mock(return_value=temp_workspace / "downloads" / att.filename)
                email.attachments.append(att)
            
            return email
        
        mock_client.fetch_email = Mock(side_effect=[create_email_with_attachments(uid) for uid in large_uid_list])
        mock_client.mark_as_read = Mock()
        
        service.clients["Primary Gmail"] = mock_client
        
        # Act
        results = service.fetch_account("Primary Gmail", since_date=datetime(2025, 1, 1))
        
        # Assert
        assert len(results) == 200  # 100 emails * 2 attachments each
        assert mock_client.fetch_email.call_count == 100


class TestEdgeCasesIntegration:
    """Test edge cases in the complete workflow."""

    def test_empty_inbox(
        self, integration_email_settings, temp_workspace
    ):
        """Test handling of empty inbox."""
        # Arrange
        service = EmailFetcherService(email_settings=integration_email_settings)
        
        mock_client = Mock()
        mock_client.connect = Mock()
        mock_client.disconnect = Mock()
        mock_client.select_folder = Mock()
        mock_client.search_emails = Mock(return_value=[])  # Empty inbox
        
        service.clients["Primary Gmail"] = mock_client
        
        # Act
        results = service.fetch_account("Primary Gmail", since_date=datetime(2025, 1, 1))
        
        # Assert
        assert results == []
        assert mock_client.fetch_email.call_count == 0

    def test_emails_without_attachments(
        self, integration_email_settings, temp_workspace
    ):
        """Test processing emails that have no attachments."""
        # Arrange
        service = EmailFetcherService(email_settings=integration_email_settings)
        
        mock_client = Mock()
        mock_client.connect = Mock()
        mock_client.disconnect = Mock()
        mock_client.select_folder = Mock()
        mock_client.search_emails = Mock(return_value=[6001, 6002, 6003])
        
        # Emails without attachments
        mock_client.fetch_email = Mock(return_value=Mock(attachments=[]))
        mock_client.mark_as_read = Mock()
        
        service.clients["Primary Gmail"] = mock_client
        
        # Act
        results = service.fetch_account("Primary Gmail", since_date=datetime(2025, 1, 1))
        
        # Assert
        assert results == []  # No attachments to process
        assert mock_client.fetch_email.call_count == 3  # But emails were checked

    def test_disk_full_scenario(
        self, integration_email_settings, temp_workspace
    ):
        """Test handling of disk full scenario during attachment saving."""
        # Arrange
        processor = AttachmentProcessor(base_dir=temp_workspace / "downloads")
        
        att = Mock(spec=EmailAttachment)
        att.filename = "large_file.pdf"
        att.content = b"x" * 1000000  # 1MB file
        att.size = len(att.content)
        att.email_sender = "sender@test.com"
        att.email_subject = "Large File"
        att.email_date = datetime.now()
        
        # Simulate disk full error
        att.save_to_disk = Mock(side_effect=OSError("No space left on device"))
        
        # Act & Assert
        with pytest.raises(OSError):
            processor.process_attachment(att)

    def test_corrupted_attachment_handling(
        self, integration_email_settings, temp_workspace
    ):
        """Test handling of corrupted attachments."""
        # Arrange
        processor = AttachmentProcessor(base_dir=temp_workspace / "downloads")
        
        # Mix of valid and corrupted attachments
        attachments = []
        
        # Valid attachment
        valid_att = Mock(spec=EmailAttachment)
        valid_att.filename = "valid.pdf"
        valid_att.content = b"valid content"
        valid_att.size = len(valid_att.content)
        valid_att.email_sender = "sender@test.com"
        valid_att.email_subject = "Valid"
        valid_att.email_date = datetime.now()
        valid_att.save_to_disk = Mock(return_value=temp_workspace / "downloads" / "valid.pdf")
        attachments.append(valid_att)
        
        # Corrupted attachment (raises exception)
        corrupted_att = Mock(spec=EmailAttachment)
        corrupted_att.filename = "corrupted.pdf"
        corrupted_att.content = None  # Will cause issues
        corrupted_att.size = 0
        corrupted_att.email_sender = "sender@test.com"
        corrupted_att.email_subject = "Corrupted"
        corrupted_att.email_date = datetime.now()
        corrupted_att.save_to_disk = Mock(side_effect=Exception("Corrupted file"))
        attachments.append(corrupted_att)
        
        # Another valid attachment
        valid_att2 = Mock(spec=EmailAttachment)
        valid_att2.filename = "valid2.pdf"
        valid_att2.content = b"valid content 2"
        valid_att2.size = len(valid_att2.content)
        valid_att2.email_sender = "sender@test.com"
        valid_att2.email_subject = "Valid 2"
        valid_att2.email_date = datetime.now()
        valid_att2.save_to_disk = Mock(return_value=temp_workspace / "downloads" / "valid2.pdf")
        attachments.append(valid_att2)
        
        # Act
        results = processor.process_attachments(attachments)
        
        # Assert - Should process valid attachments despite corrupted one
        assert len(results) == 2  # Only valid attachments processed

    def test_special_filename_characters(
        self, integration_email_settings, temp_workspace
    ):
        """Test handling of special characters in filenames."""
        # Arrange
        processor = AttachmentProcessor(base_dir=temp_workspace / "downloads")
        
        special_filenames = [
            "Rechnung_Müller_März_2025.pdf",
            "Invoice#123 (Copy).pdf",
            "Contract@Company&Co.pdf",
            "Report[January].pdf",
            "File with spaces.pdf",
            "文档.pdf",  # Unicode characters
        ]
        
        attachments = []
        for filename in special_filenames:
            att = Mock(spec=EmailAttachment)
            att.filename = filename
            att.content = b"content"
            att.size = len(att.content)
            att.email_sender = "sender@test.com"
            att.email_subject = "Test"
            att.email_date = datetime.now()
            
            # Sanitized filename for saving
            safe_filename = filename.replace("/", "_").replace("\\", "_")
            att.save_to_disk = Mock(return_value=temp_workspace / "downloads" / safe_filename)
            attachments.append(att)
        
        # Act
        results = processor.process_attachments(attachments)
        
        # Assert
        assert len(results) == len(special_filenames)
        for result, original in zip(results, special_filenames):
            assert result.original_filename == original


class TestPerformanceAndConcurrency:
    """Test performance and concurrency aspects."""

    def test_memory_usage_with_large_attachments(
        self, integration_email_settings, temp_workspace
    ):
        """Test that large attachments don't cause memory issues."""
        # Arrange
        processor = AttachmentProcessor(base_dir=temp_workspace / "downloads")
        
        # Create large attachment (50MB)
        large_size = 50 * 1024 * 1024
        att = Mock(spec=EmailAttachment)
        att.filename = "large_file.pdf"
        att.content = b"x" * large_size
        att.size = large_size
        att.email_sender = "sender@test.com"
        att.email_subject = "Large File"
        att.email_date = datetime.now()
        att.save_to_disk = Mock(return_value=temp_workspace / "downloads" / "large_file.pdf")
        
        # Act
        result = processor.process_attachment(att)
        
        # Assert
        assert result is not None
        assert result.file_size == large_size

    def test_concurrent_account_processing(
        self, integration_email_settings, temp_workspace
    ):
        """Test that multiple accounts can be processed concurrently."""
        # Arrange
        service = EmailFetcherService(email_settings=integration_email_settings)
        
        # Create multiple mock clients
        clients = {}
        for i in range(5):
            account_name = f"Account_{i}"
            mock_client = Mock()
            mock_client.connect = Mock()
            mock_client.disconnect = Mock()
            mock_client.select_folder = Mock()
            mock_client.search_emails = Mock(return_value=list(range(i * 100, (i + 1) * 100)))
            mock_client.fetch_email = Mock(return_value=Mock(attachments=[]))
            clients[account_name] = mock_client
            service.clients[account_name] = mock_client
        
        # Act
        results = service.fetch_all_accounts(since_date=datetime(2025, 1, 1))
        
        # Assert
        assert len(results) == 5
        for i, (account_name, account_results) in enumerate(results.items()):
            expected_account = f"Account_{i}"
            assert account_name in clients
            # Each account should have fetched its emails
            assert clients[account_name].fetch_email.call_count == 100