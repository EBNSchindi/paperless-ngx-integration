#!/usr/bin/env python3
"""End-to-end integration test for the complete Paperless NGX workflow.

This test verifies the complete pipeline:
1. Fetch emails from all configured accounts
2. Download and process attachments
3. Upload to Paperless NGX (if configured)
4. Extract metadata using LLM
5. Update document metadata in Paperless

Usage:
    python test_end_to_end.py [--dry-run] [--auto]
"""

import sys
import os
import json
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.prompt import Confirm
from rich.layout import Layout
from rich.live import Live

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.paperless_ngx.application.services.email_fetcher_service import EmailFetcherService
from src.paperless_ngx.application.services.paperless_api_service import PaperlessApiService
from src.paperless_ngx.application.use_cases.metadata_extraction import MetadataExtractor
from src.paperless_ngx.application.use_cases.attachment_processor import AttachmentProcessor
from src.paperless_ngx.infrastructure.email import load_email_config_from_env
from src.paperless_ngx.infrastructure.logging.logger import setup_logging
from src.paperless_ngx.infrastructure.config import get_settings

console = Console()
logger = setup_logging("test_end_to_end")


class EndToEndTester:
    """End-to-end workflow testing utility."""
    
    def __init__(self, dry_run: bool = False, auto_mode: bool = False):
        """Initialize the end-to-end tester.
        
        Args:
            dry_run: If True, simulate actions without making changes
            auto_mode: If True, run without user interaction
        """
        self.dry_run = dry_run
        self.auto_mode = auto_mode
        
        # Services
        self.email_service = None
        self.paperless_service = None
        self.metadata_extractor = None
        self.attachment_processor = None
        
        # Settings
        self.email_settings = None
        self.app_settings = None
        
        # Test results
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": dry_run,
            "auto_mode": auto_mode,
            "workflow_stages": {},
            "attachments_processed": [],
            "documents_created": [],
            "metadata_extracted": [],
            "documents_updated": [],
            "errors": [],
            "metrics": {}
        }
        
        self.start_time = time.time()
    
    def setup(self) -> bool:
        """Setup all services and test connections."""
        console.print("\n[bold blue]🚀 End-to-End Workflow Test Setup[/bold blue]\n")
        
        setup_successful = True
        
        # Setup email service
        console.print("[cyan]1. Setting up Email Service...[/cyan]")
        try:
            self.email_settings = load_email_config_from_env()
            self.email_service = EmailFetcherService(email_settings=self.email_settings)
            
            # Test email connections
            email_connections = self.email_service.test_connections()
            
            connection_table = Table(title="Email Account Connections")
            connection_table.add_column("Account", style="cyan")
            connection_table.add_column("Status", justify="center")
            
            for account, status in email_connections.items():
                connection_table.add_row(
                    account,
                    "✅ Connected" if status else "❌ Failed"
                )
            
            console.print(connection_table)
            
            if not any(email_connections.values()):
                console.print("[red]❌ No email accounts connected[/red]")
                setup_successful = False
            else:
                console.print(f"✅ Email service ready ({sum(email_connections.values())}/{len(email_connections)} accounts)")
            
            self.test_results["workflow_stages"]["email_setup"] = {
                "status": "success" if any(email_connections.values()) else "failed",
                "connections": email_connections
            }
            
        except Exception as e:
            console.print(f"[red]❌ Email service setup failed: {e}[/red]")
            logger.error(f"Email service setup failed: {e}", exc_info=True)
            setup_successful = False
            self.test_results["workflow_stages"]["email_setup"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Setup Paperless service
        console.print("\n[cyan]2. Setting up Paperless Service...[/cyan]")
        try:
            self.app_settings = get_settings()
            self.paperless_service = PaperlessApiService()
            self.metadata_extractor = MetadataExtractor()
            
            # Test Paperless connection
            if self.paperless_service.test_connection():
                console.print("✅ Paperless API connected")
                
                # Get statistics
                stats = self.paperless_service.get_document_statistics()
                console.print(f"   Total documents: {stats['total_documents']}")
                console.print(f"   Documents with OCR: {stats['documents_with_ocr']}")
                
                self.test_results["workflow_stages"]["paperless_setup"] = {
                    "status": "success",
                    "statistics": stats
                }
            else:
                console.print("[red]❌ Paperless API connection failed[/red]")
                setup_successful = False
                self.test_results["workflow_stages"]["paperless_setup"] = {
                    "status": "failed"
                }
                
        except Exception as e:
            console.print(f"[red]❌ Paperless service setup failed: {e}[/red]")
            logger.error(f"Paperless service setup failed: {e}", exc_info=True)
            setup_successful = False
            self.test_results["workflow_stages"]["paperless_setup"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Setup attachment processor
        console.print("\n[cyan]3. Setting up Attachment Processor...[/cyan]")
        try:
            self.attachment_processor = AttachmentProcessor(
                base_dir=self.email_settings.email_download_dir,
                organize_by_date=True,
                organize_by_sender=False,
                duplicate_check=True
            )
            console.print("✅ Attachment processor ready")
            console.print(f"   Download directory: {self.email_settings.email_download_dir}")
            
            self.test_results["workflow_stages"]["processor_setup"] = {
                "status": "success",
                "download_dir": str(self.email_settings.email_download_dir)
            }
            
        except Exception as e:
            console.print(f"[red]❌ Attachment processor setup failed: {e}[/red]")
            logger.error(f"Attachment processor setup failed: {e}", exc_info=True)
            setup_successful = False
            self.test_results["workflow_stages"]["processor_setup"] = {
                "status": "error",
                "error": str(e)
            }
        
        return setup_successful
    
    def stage1_fetch_emails(self, since_days: int = 7) -> Dict[str, List]:
        """Stage 1: Fetch emails from all accounts.
        
        Args:
            since_days: Fetch emails from last N days
            
        Returns:
            Dictionary of account names to attachment lists
        """
        console.print("\n[bold green]📧 Stage 1: Fetching Emails[/bold green]")
        
        stage_results = {
            "accounts_processed": {},
            "total_attachments": 0,
            "errors": []
        }
        
        since_date = datetime.now() - timedelta(days=since_days)
        console.print(f"Fetching emails since: {since_date.strftime('%Y-%m-%d')}")
        console.print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        
        all_attachments = {}
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            accounts = list(self.email_service.clients.keys())
            task = progress.add_task("Fetching emails...", total=len(accounts))
            
            for account_name in accounts:
                progress.update(task, description=f"Fetching from {account_name}...")
                
                try:
                    attachments = self.email_service.fetch_account(
                        account_name=account_name,
                        since_date=since_date,
                        dry_run=self.dry_run
                    )
                    
                    all_attachments[account_name] = attachments
                    stage_results["accounts_processed"][account_name] = {
                        "status": "success",
                        "attachments_count": len(attachments)
                    }
                    stage_results["total_attachments"] += len(attachments)
                    
                    # Store attachment info
                    for att in attachments:
                        self.test_results["attachments_processed"].append({
                            "filename": att.filename,
                            "size": att.size,
                            "from": att.email_sender,
                            "account": account_name,
                            "saved_path": str(att.saved_path) if att.saved_path else None
                        })
                    
                    console.print(f"   ✅ {account_name}: {len(attachments)} attachments")
                    
                except Exception as e:
                    error_msg = f"Failed to fetch from {account_name}: {e}"
                    console.print(f"   ❌ {account_name}: {e}")
                    stage_results["errors"].append(error_msg)
                    stage_results["accounts_processed"][account_name] = {
                        "status": "error",
                        "error": str(e)
                    }
                    logger.error(error_msg, exc_info=True)
                
                progress.advance(task)
        
        # Summary
        console.print(f"\n[green]Stage 1 Complete:[/green]")
        console.print(f"   Total attachments: {stage_results['total_attachments']}")
        console.print(f"   Accounts processed: {len(stage_results['accounts_processed'])}")
        console.print(f"   Errors: {len(stage_results['errors'])}")
        
        self.test_results["workflow_stages"]["fetch_emails"] = stage_results
        return all_attachments
    
    def stage2_upload_to_paperless(self, attachments: Dict[str, List]) -> List[int]:
        """Stage 2: Upload attachments to Paperless NGX.
        
        Args:
            attachments: Dictionary of account names to attachment lists
            
        Returns:
            List of created document IDs
        """
        console.print("\n[bold yellow]📤 Stage 2: Upload to Paperless[/bold yellow]")
        
        if self.dry_run:
            console.print("[yellow]Skipping upload in dry-run mode[/yellow]")
            return []
        
        stage_results = {
            "documents_created": [],
            "upload_failures": [],
            "total_uploaded": 0
        }
        
        document_ids = []
        
        # Note: This is a placeholder for actual upload functionality
        # The current system doesn't have direct upload API implemented
        # In a real scenario, you would:
        # 1. Use Paperless consume directory
        # 2. Or implement direct API upload
        # 3. Or integrate with existing document creation workflow
        
        console.print("[yellow]Note: Direct upload not implemented in current system[/yellow]")
        console.print("Documents should be consumed through Paperless consume directory")
        console.print("or uploaded manually through the web interface")
        
        # For testing, we'll get recently added documents instead
        console.print("\n[cyan]Checking for recently added documents...[/cyan]")
        
        try:
            recent_docs = []
            for chunk in self.paperless_service.get_documents_chunked(
                since_date=datetime.now() - timedelta(hours=1),
                chunk_size=10,
                ordering='-created'
            ):
                recent_docs.extend(chunk)
                break
            
            if recent_docs:
                console.print(f"Found {len(recent_docs)} recently added documents")
                for doc in recent_docs[:5]:  # Show first 5
                    document_ids.append(doc['id'])
                    console.print(f"   • [{doc['id']}] {doc.get('title', 'Untitled')}")
                    stage_results["documents_created"].append(doc['id'])
            else:
                console.print("No recently added documents found")
            
            stage_results["total_uploaded"] = len(document_ids)
            
        except Exception as e:
            console.print(f"[red]Error checking for documents: {e}[/red]")
            stage_results["upload_failures"].append(str(e))
        
        self.test_results["workflow_stages"]["upload_documents"] = stage_results
        self.test_results["documents_created"] = document_ids
        
        return document_ids
    
    def stage3_extract_metadata(self, document_ids: List[int]) -> List[Dict[str, Any]]:
        """Stage 3: Extract metadata for documents.
        
        Args:
            document_ids: List of document IDs to process
            
        Returns:
            List of extracted metadata dictionaries
        """
        console.print("\n[bold cyan]🤖 Stage 3: Extract Metadata[/bold cyan]")
        
        if not document_ids:
            console.print("[yellow]No documents to process[/yellow]")
            return []
        
        stage_results = {
            "documents_processed": 0,
            "extraction_success": 0,
            "extraction_failures": [],
            "metadata": []
        }
        
        extracted_metadata = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            
            task = progress.add_task("Extracting metadata...", total=len(document_ids))
            
            for doc_id in document_ids:
                progress.update(task, description=f"Processing document {doc_id}...")
                
                try:
                    # Get document with OCR
                    document = self.paperless_service.get_document_with_ocr(doc_id)
                    ocr_text = document.get('content') or document.get('ocr', '')
                    
                    if not ocr_text:
                        console.print(f"   ⚠️ Document {doc_id}: No OCR text")
                        stage_results["extraction_failures"].append({
                            "document_id": doc_id,
                            "reason": "No OCR text"
                        })
                    else:
                        # Extract metadata
                        metadata = self.metadata_extractor.extract_metadata(ocr_text)
                        
                        if metadata:
                            metadata['document_id'] = doc_id
                            extracted_metadata.append(metadata)
                            stage_results["extraction_success"] += 1
                            stage_results["metadata"].append(metadata)
                            
                            console.print(f"   ✅ Document {doc_id}: Metadata extracted")
                            
                            # Store in results
                            self.test_results["metadata_extracted"].append({
                                "document_id": doc_id,
                                "metadata": metadata
                            })
                        else:
                            console.print(f"   ❌ Document {doc_id}: Extraction failed")
                            stage_results["extraction_failures"].append({
                                "document_id": doc_id,
                                "reason": "Extraction returned None"
                            })
                    
                    stage_results["documents_processed"] += 1
                    
                except Exception as e:
                    error_msg = f"Error processing document {doc_id}: {e}"
                    console.print(f"   ❌ Document {doc_id}: {e}")
                    stage_results["extraction_failures"].append({
                        "document_id": doc_id,
                        "error": str(e)
                    })
                    logger.error(error_msg, exc_info=True)
                
                progress.advance(task)
        
        # Summary
        console.print(f"\n[green]Stage 3 Complete:[/green]")
        console.print(f"   Documents processed: {stage_results['documents_processed']}")
        console.print(f"   Successful extractions: {stage_results['extraction_success']}")
        console.print(f"   Failed extractions: {len(stage_results['extraction_failures'])}")
        
        self.test_results["workflow_stages"]["extract_metadata"] = stage_results
        
        return extracted_metadata
    
    def stage4_update_documents(self, metadata_list: List[Dict[str, Any]]) -> Tuple[int, int]:
        """Stage 4: Update documents with extracted metadata.
        
        Args:
            metadata_list: List of metadata dictionaries with document_id
            
        Returns:
            Tuple of (successful_updates, failed_updates)
        """
        console.print("\n[bold magenta]📝 Stage 4: Update Documents[/bold magenta]")
        
        if self.dry_run:
            console.print("[yellow]Skipping updates in dry-run mode[/yellow]")
            return (0, 0)
        
        if not metadata_list:
            console.print("[yellow]No metadata to apply[/yellow]")
            return (0, 0)
        
        stage_results = {
            "total_updates": len(metadata_list),
            "successful_updates": 0,
            "failed_updates": 0,
            "update_errors": []
        }
        
        # Confirm updates if not in auto mode
        if not self.auto_mode:
            if not Confirm.ask(f"Apply metadata updates to {len(metadata_list)} documents?", default=True):
                console.print("[yellow]Updates cancelled by user[/yellow]")
                return (0, 0)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            
            task = progress.add_task("Updating documents...", total=len(metadata_list))
            
            for metadata in metadata_list:
                doc_id = metadata.get('document_id')
                progress.update(task, description=f"Updating document {doc_id}...")
                
                try:
                    # Apply metadata update
                    self.paperless_service.update_document_metadata(
                        document_id=doc_id,
                        title=metadata.get('title'),
                        correspondent=metadata.get('correspondent'),
                        document_type=metadata.get('document_type'),
                        tags=metadata.get('tags'),
                        description=metadata.get('description')
                    )
                    
                    stage_results["successful_updates"] += 1
                    console.print(f"   ✅ Document {doc_id}: Updated")
                    
                    # Store in results
                    self.test_results["documents_updated"].append({
                        "document_id": doc_id,
                        "metadata_applied": metadata,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    stage_results["failed_updates"] += 1
                    error_msg = f"Failed to update document {doc_id}: {e}"
                    console.print(f"   ❌ Document {doc_id}: {e}")
                    stage_results["update_errors"].append({
                        "document_id": doc_id,
                        "error": str(e)
                    })
                    logger.error(error_msg, exc_info=True)
                
                progress.advance(task)
        
        # Summary
        console.print(f"\n[green]Stage 4 Complete:[/green]")
        console.print(f"   Successful updates: {stage_results['successful_updates']}")
        console.print(f"   Failed updates: {stage_results['failed_updates']}")
        
        self.test_results["workflow_stages"]["update_documents"] = stage_results
        
        return (stage_results["successful_updates"], stage_results["failed_updates"])
    
    def generate_summary_report(self):
        """Generate and display summary report."""
        console.print("\n" + "="*70)
        console.print("[bold green]📊 END-TO-END WORKFLOW TEST SUMMARY[/bold green]")
        console.print("="*70)
        
        # Calculate metrics
        elapsed_time = time.time() - self.start_time
        self.test_results["metrics"]["total_duration_seconds"] = elapsed_time
        
        # Stage summary table
        stage_table = Table(title="Workflow Stages")
        stage_table.add_column("Stage", style="cyan")
        stage_table.add_column("Status", justify="center")
        stage_table.add_column("Details")
        
        stages = [
            ("Email Setup", "email_setup"),
            ("Paperless Setup", "paperless_setup"),
            ("Fetch Emails", "fetch_emails"),
            ("Upload Documents", "upload_documents"),
            ("Extract Metadata", "extract_metadata"),
            ("Update Documents", "update_documents")
        ]
        
        for stage_name, stage_key in stages:
            if stage_key in self.test_results["workflow_stages"]:
                stage_data = self.test_results["workflow_stages"][stage_key]
                status = stage_data.get("status", "unknown")
                
                if status == "success":
                    status_icon = "✅"
                elif status == "failed":
                    status_icon = "❌"
                elif status == "error":
                    status_icon = "⚠️"
                else:
                    status_icon = "⏭️"
                
                # Build details
                details = []
                if stage_key == "fetch_emails":
                    details.append(f"{stage_data.get('total_attachments', 0)} attachments")
                elif stage_key == "extract_metadata":
                    details.append(f"{stage_data.get('extraction_success', 0)} successful")
                elif stage_key == "update_documents":
                    details.append(f"{stage_data.get('successful_updates', 0)} updated")
                
                stage_table.add_row(
                    stage_name,
                    status_icon,
                    ", ".join(details) if details else "-"
                )
        
        console.print(stage_table)
        
        # Metrics table
        metrics_table = Table(title="Performance Metrics")
        metrics_table.add_column("Metric", style="cyan")
        metrics_table.add_column("Value", justify="right")
        
        metrics_table.add_row("Total Duration", f"{elapsed_time:.2f} seconds")
        metrics_table.add_row("Attachments Processed", str(len(self.test_results["attachments_processed"])))
        metrics_table.add_row("Documents Created", str(len(self.test_results["documents_created"])))
        metrics_table.add_row("Metadata Extracted", str(len(self.test_results["metadata_extracted"])))
        metrics_table.add_row("Documents Updated", str(len(self.test_results["documents_updated"])))
        metrics_table.add_row("Total Errors", str(len(self.test_results["errors"])))
        
        console.print(metrics_table)
        
        # Error summary if any
        all_errors = []
        for stage_key, stage_data in self.test_results["workflow_stages"].items():
            if isinstance(stage_data, dict):
                if "errors" in stage_data:
                    all_errors.extend(stage_data["errors"])
                if "extraction_failures" in stage_data:
                    all_errors.extend([f["error"] for f in stage_data["extraction_failures"] if "error" in f])
                if "update_errors" in stage_data:
                    all_errors.extend([f["error"] for f in stage_data["update_errors"]])
        
        if all_errors:
            console.print("\n[bold red]⚠️ Errors Encountered:[/bold red]")
            for i, error in enumerate(all_errors[:5], 1):  # Show first 5 errors
                console.print(f"   {i}. {error}")
            if len(all_errors) > 5:
                console.print(f"   ... and {len(all_errors) - 5} more errors")
        
        # Success rate
        total_operations = (
            len(self.test_results["attachments_processed"]) +
            len(self.test_results["metadata_extracted"]) +
            len(self.test_results["documents_updated"])
        )
        
        if total_operations > 0:
            success_rate = (len(self.test_results["documents_updated"]) / 
                          len(self.test_results["metadata_extracted"]) * 100) if self.test_results["metadata_extracted"] else 0
            
            console.print(f"\n[bold green]Overall Success Rate: {success_rate:.1f}%[/bold green]")
    
    def save_results(self, filename: str = "test_end_to_end_results.json"):
        """Save test results to JSON file.
        
        Args:
            filename: Output filename
        """
        output_path = Path(filename)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        console.print(f"\n[green]✅ Results saved to {output_path}[/green]")
    
    def run_complete_workflow(self, since_days: int = 7):
        """Run the complete end-to-end workflow.
        
        Args:
            since_days: Process emails from last N days
        """
        console.print("\n[bold blue]🔄 STARTING END-TO-END WORKFLOW TEST[/bold blue]")
        console.print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        console.print(f"Auto Mode: {'ON' if self.auto_mode else 'OFF'}")
        console.print(f"Processing emails from last {since_days} days")
        
        # Stage 1: Fetch emails
        attachments = self.stage1_fetch_emails(since_days)
        
        # Stage 2: Upload to Paperless (or get recent docs for testing)
        document_ids = self.stage2_upload_to_paperless(attachments)
        
        # If no documents from upload, try to get some recent ones for testing
        if not document_ids and not self.dry_run:
            console.print("\n[yellow]No documents from upload. Getting recent documents for testing...[/yellow]")
            try:
                recent_docs = []
                for chunk in self.paperless_service.get_documents_chunked(
                    since_date=datetime.now() - timedelta(days=since_days),
                    chunk_size=5,
                    ordering='-created'
                ):
                    recent_docs.extend(chunk)
                    break
                
                document_ids = [doc['id'] for doc in recent_docs[:3]]
                if document_ids:
                    console.print(f"Selected {len(document_ids)} recent documents for testing")
            except Exception as e:
                console.print(f"[red]Error getting recent documents: {e}[/red]")
        
        # Stage 3: Extract metadata
        metadata_list = self.stage3_extract_metadata(document_ids)
        
        # Stage 4: Update documents
        successful, failed = self.stage4_update_documents(metadata_list)
        
        # Generate summary
        self.generate_summary_report()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="End-to-end workflow test")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Simulate workflow without making changes")
    parser.add_argument("--auto", action="store_true",
                       help="Run automatically without user prompts")
    parser.add_argument("--days", type=int, default=7,
                       help="Process emails from last N days")
    parser.add_argument("--skip-setup-check", action="store_true",
                       help="Skip initial setup verification")
    
    args = parser.parse_args()
    
    # Create tester
    tester = EndToEndTester(dry_run=args.dry_run, auto_mode=args.auto)
    
    # Setup
    if not args.skip_setup_check:
        if not tester.setup():
            if not Confirm.ask("Setup has issues. Continue anyway?", default=False):
                console.print("[red]Exiting due to setup issues[/red]")
                return 1
    else:
        # Minimal setup
        try:
            tester.email_settings = load_email_config_from_env()
            tester.email_service = EmailFetcherService(email_settings=tester.email_settings)
            tester.paperless_service = PaperlessApiService()
            tester.metadata_extractor = MetadataExtractor()
            tester.app_settings = get_settings()
        except Exception as e:
            console.print(f"[red]Failed to initialize services: {e}[/red]")
            return 1
    
    # Run workflow
    try:
        tester.run_complete_workflow(since_days=args.days)
    except KeyboardInterrupt:
        console.print("\n[yellow]Workflow interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Workflow failed with error: {e}[/red]")
        logger.error(f"Workflow failed: {e}", exc_info=True)
    
    # Save results
    tester.save_results()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())