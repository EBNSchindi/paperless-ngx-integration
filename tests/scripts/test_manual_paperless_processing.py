#!/usr/bin/env python3
"""Manual integration test for Paperless NGX metadata processing.

This test script allows manual verification of document metadata extraction
and update functionality with the Paperless NGX API.

Usage:
    python test_manual_paperless_processing.py [--count N] [--random]
"""

import sys
import os
import json
import random
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Confirm, Prompt

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.paperless_ngx.application.services.paperless_api_service import PaperlessApiService
from src.paperless_ngx.application.use_cases.metadata_extraction import MetadataExtractor
from src.paperless_ngx.infrastructure.logging.logger import setup_logging
from src.paperless_ngx.infrastructure.config import get_settings

console = Console()
logger = setup_logging("test_paperless_processing")


class PaperlessProcessingTester:
    """Manual Paperless NGX processing test utility."""
    
    def __init__(self):
        """Initialize the tester."""
        self.service = None
        self.metadata_extractor = None
        self.settings = None
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "documents_tested": [],
            "metadata_extracted": [],
            "updates_performed": [],
            "errors": []
        }
    
    def setup(self) -> bool:
        """Setup Paperless service and test connection."""
        console.print("\n[bold blue]📄 Paperless Processing Test Setup[/bold blue]\n")
        
        try:
            # Load settings
            self.settings = get_settings()
            console.print(f"✅ Loaded configuration")
            console.print(f"   API URL: {self.settings.paperless_url}")
            console.print(f"   LLM Provider: {self.settings.llm_provider}")
            
            # Initialize services
            self.service = PaperlessApiService()
            self.metadata_extractor = MetadataExtractor()
            
            # Test connection
            console.print("\n🔌 Testing Paperless API connection...")
            if self.service.test_connection():
                console.print("✅ Connection successful")
                
                # Get statistics
                stats = self.service.get_document_statistics()
                console.print(f"\n📊 Paperless Statistics:")
                console.print(f"   Total documents: {stats['total_documents']}")
                console.print(f"   Documents with OCR: {stats['documents_with_ocr']}")
                console.print(f"   Documents without OCR: {stats['documents_without_ocr']}")
                
                return True
            else:
                console.print("[red]❌ Connection failed[/red]")
                return False
                
        except Exception as e:
            console.print(f"[red]❌ Setup failed: {e}[/red]")
            logger.error(f"Setup failed: {e}", exc_info=True)
            return False
    
    def get_random_documents(self, count: int = 3) -> List[Dict[str, Any]]:
        """Get random documents from Paperless.
        
        Args:
            count: Number of documents to retrieve
            
        Returns:
            List of document dictionaries
        """
        console.print(f"\n[cyan]🎲 Selecting {count} random documents...[/cyan]")
        
        documents = []
        
        try:
            # Get all documents with OCR
            all_docs = []
            for chunk in self.service.get_documents_chunked(has_ocr=True, chunk_size=100):
                all_docs.extend(chunk)
                if len(all_docs) >= count * 10:  # Get enough to choose from
                    break
            
            if len(all_docs) < count:
                console.print(f"[yellow]Only found {len(all_docs)} documents with OCR[/yellow]")
                count = min(count, len(all_docs))
            
            # Select random documents
            selected = random.sample(all_docs, min(count, len(all_docs)))
            
            # Get full document details including OCR
            for doc in selected:
                full_doc = self.service.get_document_with_ocr(doc['id'])
                documents.append(full_doc)
                console.print(f"   Selected: [{doc['id']}] {doc.get('title', 'Untitled')}")
            
        except Exception as e:
            console.print(f"[red]Error getting documents: {e}[/red]")
            logger.error(f"Error getting documents: {e}", exc_info=True)
        
        return documents
    
    def get_recent_documents(self, days: int = 7, count: int = 3) -> List[Dict[str, Any]]:
        """Get recent documents from Paperless.
        
        Args:
            days: Get documents from last N days
            count: Maximum number of documents
            
        Returns:
            List of document dictionaries
        """
        console.print(f"\n[cyan]📅 Getting recent documents (last {days} days)...[/cyan]")
        
        documents = []
        since_date = datetime.now() - timedelta(days=days)
        
        try:
            for chunk in self.service.get_documents_chunked(
                since_date=since_date,
                has_ocr=True,
                chunk_size=count,
                ordering='-created'
            ):
                for doc in chunk[:count]:
                    full_doc = self.service.get_document_with_ocr(doc['id'])
                    documents.append(full_doc)
                    console.print(f"   Selected: [{doc['id']}] {doc.get('title', 'Untitled')}")
                break
                
        except Exception as e:
            console.print(f"[red]Error getting documents: {e}[/red]")
            logger.error(f"Error getting documents: {e}", exc_info=True)
        
        return documents
    
    def display_document_info(self, document: Dict[str, Any]):
        """Display detailed document information.
        
        Args:
            document: Document dictionary
        """
        doc_id = document.get('id', 'Unknown')
        
        # Create info table
        info = Table(title=f"Document #{doc_id}", show_header=False)
        info.add_column("Field", style="cyan")
        info.add_column("Value")
        
        info.add_row("Title", document.get('title', 'Untitled'))
        info.add_row("Created", document.get('created', 'Unknown'))
        info.add_row("Correspondent", document.get('correspondent_name', 'None'))
        info.add_row("Document Type", document.get('document_type_name', 'None'))
        
        # Tags
        tags = document.get('tags', [])
        if isinstance(tags, list) and tags:
            if isinstance(tags[0], dict):
                tag_names = [t.get('name', str(t)) for t in tags]
            else:
                tag_names = [str(t) for t in tags]
            info.add_row("Tags", ", ".join(tag_names))
        else:
            info.add_row("Tags", "None")
        
        # OCR status
        ocr_text = document.get('content') or document.get('ocr', '')
        ocr_length = len(ocr_text) if ocr_text else 0
        info.add_row("OCR Text Length", f"{ocr_length:,} characters")
        
        # Custom fields
        custom_fields = document.get('custom_fields', [])
        if custom_fields:
            for field in custom_fields:
                info.add_row(f"Custom Field {field.get('field', '?')}", 
                           field.get('value', 'Empty'))
        
        console.print(info)
        
        # Show OCR preview if available
        if ocr_text and ocr_length > 0:
            preview_length = min(500, ocr_length)
            preview = ocr_text[:preview_length]
            if ocr_length > preview_length:
                preview += "..."
            
            console.print(Panel(preview, title="OCR Text Preview", border_style="dim"))
    
    def extract_metadata(self, document: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract metadata from document using LLM.
        
        Args:
            document: Document dictionary
            
        Returns:
            Extracted metadata or None if failed
        """
        doc_id = document.get('id', 'Unknown')
        console.print(f"\n[yellow]🤖 Extracting metadata for document #{doc_id}...[/yellow]")
        
        try:
            # Get OCR text
            ocr_text = document.get('content') or document.get('ocr', '')
            
            if not ocr_text:
                console.print("[red]No OCR text available[/red]")
                return None
            
            # Extract metadata
            with console.status("Processing with LLM..."):
                metadata = self.metadata_extractor.extract_metadata(ocr_text)
            
            if metadata:
                # Display extracted metadata
                meta_table = Table(title="Extracted Metadata")
                meta_table.add_column("Field", style="cyan")
                meta_table.add_column("Value", style="green")
                
                meta_table.add_row("Title", metadata.get('title', 'Not extracted'))
                meta_table.add_row("Correspondent", metadata.get('correspondent', 'Not extracted'))
                meta_table.add_row("Document Type", metadata.get('document_type', 'Not extracted'))
                meta_table.add_row("Description", metadata.get('description', 'Not extracted'))
                
                # Tags
                tags = metadata.get('tags', [])
                if tags:
                    meta_table.add_row("Tags", ", ".join(tags))
                else:
                    meta_table.add_row("Tags", "None")
                
                console.print(meta_table)
                
                # Store in results
                self.test_results["metadata_extracted"].append({
                    "document_id": doc_id,
                    "metadata": metadata
                })
                
                return metadata
            else:
                console.print("[red]Failed to extract metadata[/red]")
                return None
                
        except Exception as e:
            error_msg = f"Error extracting metadata: {e}"
            console.print(f"[red]{error_msg}[/red]")
            logger.error(error_msg, exc_info=True)
            self.test_results["errors"].append({
                "document_id": doc_id,
                "error": str(e),
                "phase": "extraction"
            })
            return None
    
    def update_document(self, document_id: int, metadata: Dict[str, Any]) -> bool:
        """Update document with extracted metadata.
        
        Args:
            document_id: Document ID
            metadata: Metadata to apply
            
        Returns:
            Success status
        """
        console.print(f"\n[green]📝 Updating document #{document_id}...[/green]")
        
        try:
            # Show what will be updated
            console.print("Updates to apply:")
            for key, value in metadata.items():
                if value:
                    console.print(f"   {key}: {value}")
            
            # Confirm update
            if not Confirm.ask("Apply these updates?", default=True):
                console.print("[yellow]Update cancelled[/yellow]")
                return False
            
            # Perform update
            with console.status("Updating document..."):
                updated_doc = self.service.update_document_metadata(
                    document_id=document_id,
                    title=metadata.get('title'),
                    correspondent=metadata.get('correspondent'),
                    document_type=metadata.get('document_type'),
                    tags=metadata.get('tags'),
                    description=metadata.get('description')
                )
            
            console.print("✅ Document updated successfully")
            
            # Store in results
            self.test_results["updates_performed"].append({
                "document_id": document_id,
                "metadata_applied": metadata,
                "timestamp": datetime.now().isoformat()
            })
            
            return True
            
        except Exception as e:
            error_msg = f"Error updating document: {e}"
            console.print(f"[red]{error_msg}[/red]")
            logger.error(error_msg, exc_info=True)
            self.test_results["errors"].append({
                "document_id": document_id,
                "error": str(e),
                "phase": "update"
            })
            return False
    
    def process_document(self, document: Dict[str, Any], auto_update: bool = False) -> bool:
        """Process a single document: display, extract, optionally update.
        
        Args:
            document: Document to process
            auto_update: Automatically apply updates without confirmation
            
        Returns:
            Success status
        """
        doc_id = document.get('id', 'Unknown')
        
        console.print("\n" + "="*60)
        console.print(f"[bold magenta]Processing Document #{doc_id}[/bold magenta]")
        console.print("="*60)
        
        # Store in results
        self.test_results["documents_tested"].append({
            "document_id": doc_id,
            "title": document.get('title', 'Untitled'),
            "created": document.get('created', 'Unknown')
        })
        
        # Display current info
        self.display_document_info(document)
        
        # Extract metadata
        metadata = self.extract_metadata(document)
        
        if metadata:
            # Optionally update
            if auto_update:
                return self.update_document(doc_id, metadata)
            else:
                if Confirm.ask("\nWould you like to update this document?", default=False):
                    return self.update_document(doc_id, metadata)
        
        return metadata is not None
    
    def batch_process(self, documents: List[Dict[str, Any]], auto_update: bool = False):
        """Process multiple documents.
        
        Args:
            documents: List of documents to process
            auto_update: Automatically apply updates
        """
        console.print(f"\n[bold cyan]📚 Batch Processing {len(documents)} Documents[/bold cyan]")
        
        successful = 0
        failed = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            
            task = progress.add_task("Processing documents...", total=len(documents))
            
            for i, doc in enumerate(documents, 1):
                progress.update(task, description=f"Processing document {i}/{len(documents)}")
                
                if self.process_document(doc, auto_update):
                    successful += 1
                else:
                    failed += 1
                
                progress.advance(task)
        
        # Summary
        console.print("\n[bold yellow]📊 Batch Processing Summary[/bold yellow]")
        console.print(f"   Successful: {successful}")
        console.print(f"   Failed: {failed}")
        console.print(f"   Total: {len(documents)}")
    
    def test_search_functionality(self):
        """Test document search capabilities."""
        console.print("\n[bold cyan]🔍 Testing Search Functionality[/bold cyan]")
        
        # Test different search scenarios
        test_cases = [
            {
                "name": "Recent documents (last 7 days)",
                "params": {"since_date": datetime.now() - timedelta(days=7)}
            },
            {
                "name": "Documents with OCR",
                "params": {"has_ocr": True}
            },
            {
                "name": "Documents without correspondent",
                "params": {"correspondent_id": None}
            }
        ]
        
        results_table = Table(title="Search Test Results")
        results_table.add_column("Test Case", style="cyan")
        results_table.add_column("Documents Found", justify="right")
        results_table.add_column("Time", justify="right")
        
        for test_case in test_cases:
            start_time = datetime.now()
            count = 0
            
            try:
                for chunk in self.service.get_documents_chunked(
                    chunk_size=100,
                    **test_case["params"]
                ):
                    count += len(chunk)
                    break  # Just get first chunk for testing
                
                elapsed = (datetime.now() - start_time).total_seconds()
                results_table.add_row(
                    test_case["name"],
                    str(count),
                    f"{elapsed:.2f}s"
                )
                
            except Exception as e:
                results_table.add_row(
                    test_case["name"],
                    f"Error: {str(e)[:30]}",
                    "-"
                )
        
        console.print(results_table)
    
    def save_results(self, filename: str = "test_paperless_processing_results.json"):
        """Save test results to JSON file.
        
        Args:
            filename: Output filename
        """
        output_path = Path(filename)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        console.print(f"\n[green]✅ Results saved to {output_path}[/green]")
    
    def run_interactive(self):
        """Run interactive test menu."""
        while True:
            console.print("\n" + "="*60)
            console.print("[bold cyan]Paperless Processing Test Menu[/bold cyan]")
            console.print("="*60)
            console.print("1. Test connection and show statistics")
            console.print("2. Process random documents")
            console.print("3. Process recent documents")
            console.print("4. Process specific document by ID")
            console.print("5. Test search functionality")
            console.print("6. Show tag statistics")
            console.print("7. Find similar tags")
            console.print("8. Test metadata extraction only (no updates)")
            console.print("9. Save results and exit")
            console.print("0. Exit without saving")
            
            choice = console.input("\n[bold]Select option (0-9): [/bold]")
            
            if choice == "1":
                self.setup()
                
            elif choice == "2":
                count = int(console.input("How many random documents? (default 3): ") or "3")
                docs = self.get_random_documents(count)
                if docs:
                    auto = Confirm.ask("Auto-update documents?", default=False)
                    self.batch_process(docs, auto_update=auto)
                    
            elif choice == "3":
                days = int(console.input("Documents from last N days (default 7): ") or "7")
                count = int(console.input("How many documents? (default 3): ") or "3")
                docs = self.get_recent_documents(days, count)
                if docs:
                    auto = Confirm.ask("Auto-update documents?", default=False)
                    self.batch_process(docs, auto_update=auto)
                    
            elif choice == "4":
                doc_id = console.input("Enter document ID: ")
                try:
                    doc = self.service.get_document_with_ocr(int(doc_id))
                    self.process_document(doc)
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")
                    
            elif choice == "5":
                self.test_search_functionality()
                
            elif choice == "6":
                stats = self.service.get_document_statistics()
                console.print("\n[bold]Top Tags:[/bold]")
                for tag in stats.get('top_tags', []):
                    console.print(f"   {tag['name']}: {tag['count']} documents")
                    
            elif choice == "7":
                threshold = float(console.input("Similarity threshold (0-100, default 85): ") or "85")
                similar_groups = self.service.find_similar_tags(threshold)
                if similar_groups:
                    console.print(f"\nFound {len(similar_groups)} groups of similar tags:")
                    for group in similar_groups:
                        tags = [t['name'] for t in group]
                        console.print(f"   • {', '.join(tags)}")
                else:
                    console.print("No similar tags found")
                    
            elif choice == "8":
                count = int(console.input("How many documents to test? (default 3): ") or "3")
                docs = self.get_random_documents(count)
                for doc in docs:
                    console.print("\n" + "="*60)
                    self.display_document_info(doc)
                    self.extract_metadata(doc)
                    
            elif choice == "9":
                self.save_results()
                break
                
            elif choice == "0":
                break
                
            else:
                console.print("[red]Invalid option[/red]")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test Paperless NGX metadata processing")
    parser.add_argument("--count", type=int, default=3, help="Number of documents to process")
    parser.add_argument("--random", action="store_true", help="Select random documents")
    parser.add_argument("--recent", type=int, help="Process documents from last N days")
    parser.add_argument("--auto-update", action="store_true", help="Auto-update documents")
    parser.add_argument("--interactive", action="store_true", help="Run interactive menu")
    
    args = parser.parse_args()
    
    # Create tester
    tester = PaperlessProcessingTester()
    
    # Setup
    if not tester.setup():
        console.print("[red]Setup failed. Exiting.[/red]")
        return 1
    
    # Run tests
    if args.interactive:
        tester.run_interactive()
    else:
        # Get documents
        if args.random:
            documents = tester.get_random_documents(args.count)
        elif args.recent:
            documents = tester.get_recent_documents(args.recent, args.count)
        else:
            # Default to recent
            documents = tester.get_recent_documents(7, args.count)
        
        if documents:
            # Process documents
            tester.batch_process(documents, auto_update=args.auto_update)
        else:
            console.print("[red]No documents found to process[/red]")
            return 1
        
        # Save results
        tester.save_results()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())