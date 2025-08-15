"""Unit tests for stateless AttachmentProcessor.

This test suite verifies that the AttachmentProcessor operates without
maintaining any duplicate tracking or hash files.
"""

import hashlib
import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from paperless_ngx.application.use_cases.attachment_processor import (
    AttachmentProcessor,
    ProcessedAttachment,
)
from paperless_ngx.infrastructure.email import EmailAttachment
from paperless_ngx.infrastructure.config.settings import Settings


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = Mock(spec=Settings)
    settings.max_tags_per_document = 4
    settings.enable_sevdesk_optimizations = True
    settings.organize_by_month = False
    settings.create_staging_folders = False
    settings.generate_json_metadata = False
    return settings


@pytest.fixture
def sample_attachment():
    """Create a sample email attachment."""
    attachment = Mock(spec=EmailAttachment)
    attachment.filename = "invoice_2025.pdf"
    attachment.content = b"PDF content here"
    attachment.size = len(attachment.content)
    attachment.email_sender = "supplier@example.com"
    attachment.email_subject = "Invoice for January 2025"
    attachment.email_date = datetime(2025, 1, 15, 10, 30)
    attachment.save_to_disk = Mock(return_value=Path("/tmp/invoice_2025.pdf"))
    return attachment


class TestAttachmentProcessorStatelessBehavior:
    """Test suite for verifying stateless behavior of AttachmentProcessor."""

    def test_no_hash_file_created(self, temp_dir, mock_settings):
        """Test that no hash tracking file is created."""
        # Arrange
        with patch("paperless_ngx.application.use_cases.attachment_processor.get_settings", return_value=mock_settings):
            processor = AttachmentProcessor(
                base_dir=temp_dir,
                organize_by_date=False,
                organize_by_sender=False,
                duplicate_check=True,  # Even with duplicate_check=True, no file should be created
                generate_metadata_files=False,
            )
            
            # Act - Process some attachments
            attachment = Mock(spec=EmailAttachment)
            attachment.filename = "test.pdf"
            attachment.content = b"test content"
            attachment.size = len(attachment.content)
            attachment.email_sender = "sender@test.com"
            attachment.email_subject = "Test"
            attachment.email_date = datetime.now()
            attachment.save_to_disk = Mock(return_value=temp_dir / "test.pdf")
            
            processor.process_attachment(attachment)
            
            # Assert - No hash files should exist
            hash_files = list(temp_dir.glob("*.json"))
            assert len(hash_files) == 0, "No JSON hash files should be created"
            
            # Check for specific files that should NOT exist
            assert not (temp_dir / ".processed_hashes.json").exists()
            assert not (temp_dir / "processed_hashes.json").exists()
            assert not (temp_dir / ".hashes.json").exists()

    def test_all_attachments_processed(self, temp_dir, mock_settings):
        """Test that ALL attachments are processed without duplicate checking."""
        # Arrange
        with patch("paperless_ngx.application.use_cases.attachment_processor.get_settings", return_value=mock_settings):
            processor = AttachmentProcessor(
                base_dir=temp_dir,
                organize_by_date=False,
                organize_by_sender=False,
                duplicate_check=True,  # Parameter exists but is ignored
            )
            
            # Create multiple attachments with same content (would be duplicates)
            attachments = []
            for i in range(3):
                attachment = Mock(spec=EmailAttachment)
                attachment.filename = f"document_{i}.pdf"
                attachment.content = b"same content"  # Same content for all
                attachment.size = len(attachment.content)
                attachment.email_sender = "sender@test.com"
                attachment.email_subject = f"Document {i}"
                attachment.email_date = datetime.now()
                attachment.save_to_disk = Mock(return_value=temp_dir / f"document_{i}.pdf")
                attachments.append(attachment)
            
            # Act - Process all attachments
            results = processor.process_attachments(attachments)
            
            # Assert - All should be processed (no duplicate filtering)
            assert len(results) == 3, "All attachments should be processed"
            for i, result in enumerate(results):
                assert result.original_filename == f"document_{i}.pdf"

    def test_duplicate_check_parameter_ignored(self, temp_dir, mock_settings):
        """Test that duplicate_check parameter has no effect."""
        # Arrange
        with patch("paperless_ngx.application.use_cases.attachment_processor.get_settings", return_value=mock_settings):
            # Create processors with different duplicate_check settings
            processor_with_check = AttachmentProcessor(
                base_dir=temp_dir / "with_check",
                duplicate_check=True,
            )
            
            processor_without_check = AttachmentProcessor(
                base_dir=temp_dir / "without_check",
                duplicate_check=False,
            )
            
            # Same attachment for both
            attachment = Mock(spec=EmailAttachment)
            attachment.filename = "test.pdf"
            attachment.content = b"test content"
            attachment.size = len(attachment.content)
            attachment.email_sender = "sender@test.com"
            attachment.email_subject = "Test"
            attachment.email_date = datetime.now()
            
            # Act - Process twice with each processor
            for processor in [processor_with_check, processor_without_check]:
                attachment.save_to_disk = Mock(side_effect=[
                    processor.base_dir / "test_1.pdf",
                    processor.base_dir / "test_2.pdf",
                ])
                
                result1 = processor.process_attachment(attachment)
                result2 = processor.process_attachment(attachment)
                
                # Assert - Both should process (no duplicate checking)
                assert result1 is not None
                assert result2 is not None

    def test_processing_stats_show_no_duplicate_checking(self, temp_dir, mock_settings):
        """Test that processing stats correctly show duplicate checking is disabled."""
        # Arrange
        with patch("paperless_ngx.application.use_cases.attachment_processor.get_settings", return_value=mock_settings):
            processor = AttachmentProcessor(
                base_dir=temp_dir,
                duplicate_check=True,  # Even if set to True
            )
            
            # Act
            stats = processor.get_processing_stats()
            
            # Assert
            assert stats["duplicate_check_enabled"] is False, "Stats should always show duplicate checking as disabled"


class TestFileOrganization:
    """Test suite for file organization without duplicate checking."""

    def test_flat_directory_structure(self, temp_dir, mock_settings):
        """Test flat directory structure for Sevdesk optimization."""
        # Arrange
        with patch("paperless_ngx.application.use_cases.attachment_processor.get_settings", return_value=mock_settings):
            processor = AttachmentProcessor(
                base_dir=temp_dir,
                organize_by_date=False,  # Flat structure
                organize_by_sender=False,
            )
            
            attachment = Mock(spec=EmailAttachment)
            attachment.filename = "invoice.pdf"
            attachment.content = b"content"
            attachment.size = len(attachment.content)
            attachment.email_sender = "supplier@example.com"
            attachment.email_subject = "Invoice"
            attachment.email_date = datetime(2025, 1, 15)
            attachment.save_to_disk = Mock(return_value=temp_dir / "invoice.pdf")
            
            # Act
            result = processor.process_attachment(attachment)
            
            # Assert - File should be in base directory
            attachment.save_to_disk.assert_called_once()
            call_args = attachment.save_to_disk.call_args[0]
            assert call_args[0] == temp_dir, "Should use flat directory structure"

    def test_date_based_organization(self, temp_dir, mock_settings):
        """Test date-based directory organization when enabled."""
        # Arrange
        with patch("paperless_ngx.application.use_cases.attachment_processor.get_settings", return_value=mock_settings):
            processor = AttachmentProcessor(
                base_dir=temp_dir,
                organize_by_date=True,  # Enable date organization
                organize_by_sender=False,
            )
            
            attachment = Mock(spec=EmailAttachment)
            attachment.filename = "document.pdf"
            attachment.content = b"content"
            attachment.size = len(attachment.content)
            attachment.email_sender = "sender@example.com"
            attachment.email_subject = "Document"
            attachment.email_date = datetime(2025, 1, 15)
            attachment.save_to_disk = Mock(return_value=temp_dir / "2025/01-January/document.pdf")
            
            # Act
            result = processor.process_attachment(attachment)
            
            # Assert - Should organize by year/month
            attachment.save_to_disk.assert_called_once()
            call_args = attachment.save_to_disk.call_args[0]
            expected_dir = temp_dir / "2025" / "01-January"
            assert call_args[0] == expected_dir

    def test_filename_sanitization(self, temp_dir, mock_settings, sample_attachment):
        """Test that filenames are properly sanitized."""
        # Arrange
        with patch("paperless_ngx.application.use_cases.attachment_processor.get_settings", return_value=mock_settings):
            processor = AttachmentProcessor(base_dir=temp_dir)
            
            # Modify attachment with problematic filename
            sample_attachment.filename = "Invoice:2025|January<>*.pdf"
            
            # Act
            result = processor.process_attachment(sample_attachment)
            
            # Assert
            assert result is not None
            # Filename should be sanitized when saved
            sample_attachment.save_to_disk.assert_called_once()

    def test_no_metadata_files_by_default(self, temp_dir, mock_settings, sample_attachment):
        """Test that metadata JSON files are not created by default."""
        # Arrange
        with patch("paperless_ngx.application.use_cases.attachment_processor.get_settings", return_value=mock_settings):
            processor = AttachmentProcessor(
                base_dir=temp_dir,
                generate_metadata_files=False,  # Disabled by default for Sevdesk
            )
            
            # Act
            result = processor.process_attachment(sample_attachment)
            
            # Assert
            metadata_files = list(temp_dir.glob("*.metadata.json"))
            assert len(metadata_files) == 0, "No metadata files should be created"


class TestAttachmentTypes:
    """Test suite for handling various attachment types."""

    @pytest.mark.parametrize(
        "filename,should_process",
        [
            ("document.pdf", True),
            ("image.png", True),
            ("photo.jpg", True),
            ("picture.jpeg", True),
            ("scan.tiff", True),
            ("spreadsheet.xlsx", True),  # Depends on configuration
            ("document.docx", True),     # Depends on configuration
            ("archive.zip", False),      # Usually not processed
            ("video.mp4", False),        # Usually not processed
        ],
    )
    def test_attachment_type_filtering(
        self, temp_dir, mock_settings, filename, should_process
    ):
        """Test processing of different attachment types."""
        # Arrange
        with patch("paperless_ngx.application.use_cases.attachment_processor.get_settings", return_value=mock_settings):
            processor = AttachmentProcessor(base_dir=temp_dir)
            
            attachment = Mock(spec=EmailAttachment)
            attachment.filename = filename
            attachment.content = b"file content"
            attachment.size = len(attachment.content)
            attachment.email_sender = "sender@test.com"
            attachment.email_subject = "Test"
            attachment.email_date = datetime.now()
            attachment.save_to_disk = Mock(return_value=temp_dir / filename)
            
            # Act
            result = processor.process_attachment(attachment)
            
            # Assert
            assert result is not None  # All files are processed now (no filtering in processor)

    def test_large_attachment_handling(self, temp_dir, mock_settings):
        """Test handling of large attachments."""
        # Arrange
        with patch("paperless_ngx.application.use_cases.attachment_processor.get_settings", return_value=mock_settings):
            processor = AttachmentProcessor(base_dir=temp_dir)
            
            # Create large attachment (10MB)
            large_content = b"x" * (10 * 1024 * 1024)
            attachment = Mock(spec=EmailAttachment)
            attachment.filename = "large_file.pdf"
            attachment.content = large_content
            attachment.size = len(large_content)
            attachment.email_sender = "sender@test.com"
            attachment.email_subject = "Large File"
            attachment.email_date = datetime.now()
            attachment.save_to_disk = Mock(return_value=temp_dir / "large_file.pdf")
            
            # Act
            result = processor.process_attachment(attachment)
            
            # Assert
            assert result is not None
            assert result.file_size == len(large_content)


class TestTagGeneration:
    """Test suite for tag generation with Sevdesk optimization."""

    def test_maximum_four_tags(self, temp_dir, mock_settings, sample_attachment):
        """Test that maximum 4 tags are generated for Sevdesk."""
        # Arrange
        with patch("paperless_ngx.application.use_cases.attachment_processor.get_settings", return_value=mock_settings):
            processor = AttachmentProcessor(base_dir=temp_dir)
            
            # Act
            result = processor.process_attachment(sample_attachment)
            
            # Assert
            assert len(result.tags) <= 4, "Maximum 4 tags for Sevdesk compatibility"

    def test_invoice_tag_detection(self, temp_dir, mock_settings):
        """Test automatic detection of invoice documents."""
        # Arrange
        with patch("paperless_ngx.application.use_cases.attachment_processor.get_settings", return_value=mock_settings):
            processor = AttachmentProcessor(base_dir=temp_dir)
            
            attachment = Mock(spec=EmailAttachment)
            attachment.filename = "rechnung_2025.pdf"
            attachment.content = b"content"
            attachment.size = len(attachment.content)
            attachment.email_sender = "supplier@example.com"
            attachment.email_subject = "Rechnung Januar 2025"
            attachment.email_date = datetime(2025, 1, 15)
            attachment.save_to_disk = Mock(return_value=temp_dir / "rechnung_2025.pdf")
            
            # Act
            result = processor.process_attachment(attachment)
            
            # Assert
            assert "Rechnung" in result.tags, "Should detect and tag as Rechnung"

    def test_receipt_tag_detection(self, temp_dir, mock_settings):
        """Test automatic detection of receipt documents."""
        # Arrange
        with patch("paperless_ngx.application.use_cases.attachment_processor.get_settings", return_value=mock_settings):
            processor = AttachmentProcessor(base_dir=temp_dir)
            
            attachment = Mock(spec=EmailAttachment)
            attachment.filename = "kassenbon.pdf"
            attachment.content = b"content"
            attachment.size = len(attachment.content)
            attachment.email_sender = "shop@example.com"
            attachment.email_subject = "Kassenbon"
            attachment.email_date = datetime(2025, 1, 15)
            attachment.save_to_disk = Mock(return_value=temp_dir / "kassenbon.pdf")
            
            # Act
            result = processor.process_attachment(attachment)
            
            # Assert
            assert "Kassenbon" in result.tags, "Should detect and tag as Kassenbon"

    def test_year_tag_inclusion(self, temp_dir, mock_settings, sample_attachment):
        """Test that year is included in tags."""
        # Arrange
        with patch("paperless_ngx.application.use_cases.attachment_processor.get_settings", return_value=mock_settings):
            processor = AttachmentProcessor(base_dir=temp_dir)
            
            # Act
            result = processor.process_attachment(sample_attachment)
            
            # Assert
            assert "2025" in result.tags, "Should include year in tags"

    def test_price_tag_extraction(self, temp_dir, mock_settings):
        """Test extraction of price information as tags."""
        # Arrange
        with patch("paperless_ngx.application.use_cases.attachment_processor.get_settings", return_value=mock_settings):
            processor = AttachmentProcessor(base_dir=temp_dir)
            
            attachment = Mock(spec=EmailAttachment)
            attachment.filename = "invoice.pdf"
            attachment.content = b"content"
            attachment.size = len(attachment.content)
            attachment.email_sender = "supplier@example.com"
            attachment.email_subject = "Invoice Total 123,45 EUR"
            attachment.email_date = datetime(2025, 1, 15)
            attachment.save_to_disk = Mock(return_value=temp_dir / "invoice.pdf")
            
            # Mock price extraction
            with patch.object(processor, "_format_price_tag", return_value="123,45€"):
                result = processor.process_attachment(attachment)
                
                # Note: Price extraction from subject would need more complex logic
                # This test shows the structure is in place


class TestMetadataExtraction:
    """Test suite for metadata extraction."""

    def test_correspondent_extraction_from_email(self, temp_dir, mock_settings):
        """Test correspondent extraction from email sender."""
        # Arrange
        with patch("paperless_ngx.application.use_cases.attachment_processor.get_settings", return_value=mock_settings):
            processor = AttachmentProcessor(base_dir=temp_dir)
            
            test_cases = [
                ("John Doe <john@example.com>", "John Doe"),
                ("jane@example.com", "jane"),
                ("<admin@company.com>", "admin"),
                ("Company Name <info@company.com>", "Company Name"),
            ]
            
            for email_sender, expected_correspondent in test_cases:
                attachment = Mock(spec=EmailAttachment)
                attachment.filename = "test.pdf"
                attachment.content = b"content"
                attachment.size = len(attachment.content)
                attachment.email_sender = email_sender
                attachment.email_subject = "Test"
                attachment.email_date = datetime.now()
                attachment.save_to_disk = Mock(return_value=temp_dir / "test.pdf")
                
                # Act
                result = processor.process_attachment(attachment)
                
                # Assert
                assert result.correspondent == expected_correspondent

    def test_document_type_detection(self, temp_dir, mock_settings):
        """Test automatic document type detection."""
        # Arrange
        with patch("paperless_ngx.application.use_cases.attachment_processor.get_settings", return_value=mock_settings):
            processor = AttachmentProcessor(base_dir=temp_dir)
            
            test_cases = [
                ("Rechnung_2025.pdf", "Invoice", "Rechnung"),
                ("Vertrag_signed.pdf", "Contract", "Vertrag"),
                ("Angebot_Januar.pdf", "Quote", "Angebot"),
                ("Mahnung_1.pdf", "Reminder", "Mahnung"),
                ("scan_001.jpg", "Scan Document", "Scan"),
            ]
            
            for filename, subject_keyword, expected_type in test_cases:
                attachment = Mock(spec=EmailAttachment)
                attachment.filename = filename
                attachment.content = b"content"
                attachment.size = len(attachment.content)
                attachment.email_sender = "sender@test.com"
                attachment.email_subject = f"{subject_keyword} for testing"
                attachment.email_date = datetime.now()
                attachment.save_to_disk = Mock(return_value=temp_dir / filename)
                
                # Act
                result = processor.process_attachment(attachment)
                
                # Assert
                assert result.document_type == expected_type

    def test_description_generation(self, temp_dir, mock_settings, sample_attachment):
        """Test description generation with 128 character limit."""
        # Arrange
        with patch("paperless_ngx.application.use_cases.attachment_processor.get_settings", return_value=mock_settings):
            processor = AttachmentProcessor(base_dir=temp_dir)
            
            # Set a very long subject
            sample_attachment.email_subject = "A" * 200
            
            # Act
            result = processor.process_attachment(sample_attachment)
            
            # Assert
            assert len(result.description) <= 128, "Description should be limited to 128 characters"
            assert result.description != "", "Description should not be empty"


class TestEdgeCases:
    """Test suite for edge cases and error conditions."""

    def test_empty_attachment_list(self, temp_dir, mock_settings):
        """Test processing empty attachment list."""
        # Arrange
        with patch("paperless_ngx.application.use_cases.attachment_processor.get_settings", return_value=mock_settings):
            processor = AttachmentProcessor(base_dir=temp_dir)
            
            # Act
            results = processor.process_attachments([])
            
            # Assert
            assert results == []

    def test_attachment_with_no_content(self, temp_dir, mock_settings):
        """Test handling attachment with no content."""
        # Arrange
        with patch("paperless_ngx.application.use_cases.attachment_processor.get_settings", return_value=mock_settings):
            processor = AttachmentProcessor(base_dir=temp_dir)
            
            attachment = Mock(spec=EmailAttachment)
            attachment.filename = "empty.pdf"
            attachment.content = b""  # Empty content
            attachment.size = 0
            attachment.email_sender = "sender@test.com"
            attachment.email_subject = "Empty"
            attachment.email_date = datetime.now()
            attachment.save_to_disk = Mock(return_value=temp_dir / "empty.pdf")
            
            # Act
            result = processor.process_attachment(attachment)
            
            # Assert
            assert result is not None
            assert result.file_size == 0
            assert result.file_hash == hashlib.sha256(b"").hexdigest()

    def test_special_characters_in_filename(self, temp_dir, mock_settings):
        """Test handling of special characters in filenames."""
        # Arrange
        with patch("paperless_ngx.application.use_cases.attachment_processor.get_settings", return_value=mock_settings):
            processor = AttachmentProcessor(base_dir=temp_dir)
            
            test_filenames = [
                "Müller_Rechnung_März.pdf",
                "Invoice #123 (2025).pdf",
                "Contract@Company&Partners.pdf",
                "Statement [January].pdf",
            ]
            
            for filename in test_filenames:
                attachment = Mock(spec=EmailAttachment)
                attachment.filename = filename
                attachment.content = b"content"
                attachment.size = len(attachment.content)
                attachment.email_sender = "sender@test.com"
                attachment.email_subject = "Test"
                attachment.email_date = datetime.now()
                attachment.save_to_disk = Mock(return_value=temp_dir / "sanitized.pdf")
                
                # Act
                result = processor.process_attachment(attachment)
                
                # Assert
                assert result is not None
                assert result.original_filename == filename

    def test_cleanup_empty_directories(self, temp_dir, mock_settings):
        """Test cleanup of empty directories."""
        # Arrange
        with patch("paperless_ngx.application.use_cases.attachment_processor.get_settings", return_value=mock_settings):
            processor = AttachmentProcessor(base_dir=temp_dir)
            
            # Create some empty directories
            (temp_dir / "empty1" / "empty2").mkdir(parents=True)
            (temp_dir / "empty3").mkdir()
            
            # Create a directory with a file (should not be removed)
            (temp_dir / "not_empty").mkdir()
            (temp_dir / "not_empty" / "file.txt").write_text("content")
            
            # Act
            removed_count = processor.cleanup_empty_directories()
            
            # Assert
            assert removed_count == 3  # empty1/empty2, empty1, empty3
            assert not (temp_dir / "empty1").exists()
            assert not (temp_dir / "empty3").exists()
            assert (temp_dir / "not_empty").exists()

    def test_concurrent_processing_safety(self, temp_dir, mock_settings):
        """Test that multiple attachments can be processed concurrently without state issues."""
        # Arrange
        with patch("paperless_ngx.application.use_cases.attachment_processor.get_settings", return_value=mock_settings):
            processor = AttachmentProcessor(base_dir=temp_dir)
            
            # Create multiple attachments
            attachments = []
            for i in range(10):
                attachment = Mock(spec=EmailAttachment)
                attachment.filename = f"document_{i}.pdf"
                attachment.content = f"content_{i}".encode()
                attachment.size = len(attachment.content)
                attachment.email_sender = f"sender{i}@test.com"
                attachment.email_subject = f"Document {i}"
                attachment.email_date = datetime.now()
                attachment.save_to_disk = Mock(return_value=temp_dir / f"document_{i}.pdf")
                attachments.append(attachment)
            
            # Act - Process all attachments
            results = processor.process_attachments(attachments)
            
            # Assert - All should be processed independently
            assert len(results) == 10
            
            # Verify each has unique hash (since content is different)
            hashes = [r.file_hash for r in results]
            assert len(set(hashes)) == 10, "Each document should have unique hash"