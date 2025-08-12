"""Simplified 3-point workflow menu for Paperless NGX integration.

This module provides a streamlined CLI interface with exactly three main workflows
for quarterly accounting document processing.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import print as rprint

from src.paperless_ngx.domain.value_objects import DateRange, QuickDateOption
from src.paperless_ngx.application.services.smart_tag_matcher import SmartTagMatcher
from src.paperless_ngx.application.services.email_fetcher_service import EmailFetcherService
from src.paperless_ngx.infrastructure.config import get_settings
from src.paperless_ngx.infrastructure.llm.litellm_client import LiteLLMClient
from src.paperless_ngx.infrastructure.paperless.api_client import PaperlessApiClient
from src.paperless_ngx.infrastructure.logging import setup_logging

logger = logging.getLogger(__name__)
console = Console()


class SimplifiedWorkflowCLI:
    """Simplified 3-point workflow CLI interface."""
    
    def __init__(self):
        """Initialize the CLI with necessary services."""
        self.settings = get_settings()
        setup_logging(self.settings.log_level)
        
        # Initialize services
        self.paperless_client = PaperlessApiClient(self.settings)
        self.llm_client = LiteLLMClient(self.settings)
        self.email_fetcher = EmailFetcherService(self.settings)
        self.tag_matcher = SmartTagMatcher(
            paperless_client=self.paperless_client,
            llm_client=self.llm_client,
            similarity_threshold=0.95
        )
        
        # Staging directory for downloads
        self.staging_dir = Path("staging")
        self.staging_dir.mkdir(exist_ok=True)
    
    def show_main_menu(self) -> int:
        """Display the main 3-point workflow menu.
        
        Returns:
            Selected workflow number (1-3) or 0 to exit
        """
        console.clear()
        
        # Create menu panel
        menu_text = """
[bold cyan]Paperless NGX - Vereinfachter Workflow[/bold cyan]

[bold]Wählen Sie Ihren Workflow:[/bold]

[bold green]1.[/bold green] 📧 [bold]Email-Dokumente abrufen[/bold]
   • Zeitraum wählen (YYYY-MM Format)
   • Email-Anhänge herunterladen
   • Nach Monat organisiert speichern
   • Automatische PDF-Erkennung

[bold yellow]2.[/bold yellow] 📄 [bold]Dokumente verarbeiten & Metadaten anreichern[/bold]
   • OCR-Text aus Paperless extrahieren
   • LLM-Analyse für Metadaten (OpenAI/Ollama)
   • Intelligentes Tag-Matching (95% Threshold)
   • Keine falschen Vereinheitlichungen

[bold blue]3.[/bold blue] 📊 [bold]Quality Scan & Report[/bold]
   • Zeitraum-basierte Qualitätsprüfung
   • Fehlende Metadaten identifizieren
   • Tag-Qualitätsanalyse
   • CSV-Report generieren

[bold red]0.[/bold red] 🚪 [bold]Beenden[/bold]
        """
        
        panel = Panel(
            menu_text,
            title="🗂️ Quartalsweise Buchhaltung",
            border_style="bright_blue",
            padding=(1, 2)
        )
        
        console.print(panel)
        
        # Get user choice
        choice = Prompt.ask(
            "\n[bold]Ihre Auswahl[/bold]",
            choices=["0", "1", "2", "3"],
            default="1"
        )
        
        return int(choice)
    
    def select_date_range(self, purpose: str = "Verarbeitung") -> DateRange:
        """Interactive date range selection.
        
        Args:
            purpose: Purpose description for the date range
            
        Returns:
            Selected DateRange
        """
        console.print(f"\n[bold cyan]Zeitraum für {purpose} wählen[/bold cyan]\n")
        
        # Quick options table
        table = Table(title="Quick-Options")
        table.add_column("Option", style="cyan")
        table.add_column("Zeitraum", style="green")
        
        table.add_row("1", "Letztes Quartal")
        table.add_row("2", "Letzte 3 Monate")
        table.add_row("3", "Letzter Monat")
        table.add_row("4", "Aktueller Monat")
        table.add_row("5", "Aktuelles Quartal")
        table.add_row("6", "Benutzerdefiniert (YYYY-MM)")
        
        console.print(table)
        
        choice = Prompt.ask("\nOption wählen", choices=["1", "2", "3", "4", "5", "6"], default="2")
        
        if choice == "1":
            date_range = DateRange.last_quarter()
        elif choice == "2":
            date_range = DateRange.last_three_months()
        elif choice == "3":
            date_range = DateRange.last_month()
        elif choice == "4":
            date_range = DateRange.current_month()
        elif choice == "5":
            date_range = DateRange.current_quarter()
        else:
            # Custom range
            start_month = Prompt.ask("Start-Monat (YYYY-MM)", default="2024-10")
            end_month = Prompt.ask("End-Monat (YYYY-MM)", default="2024-12")
            
            try:
                date_range = DateRange.from_yyyy_mm(start_month, end_month)
            except ValueError as e:
                console.print(f"[red]Ungültiges Datumsformat: {e}[/red]")
                return self.select_date_range(purpose)
        
        console.print(f"\n[green]Gewählter Zeitraum:[/green] {date_range.format_display()}")
        console.print(f"[dim]Monate: {', '.join(date_range.get_months())}[/dim]\n")
        
        return date_range
    
    async def workflow_1_email_fetch(self):
        """Workflow 1: Email-Dokumente abrufen."""
        console.print("\n[bold cyan]Workflow 1: Email-Dokumente abrufen[/bold cyan]\n")
        
        # Select date range
        date_range = self.select_date_range("Email-Abruf")
        
        # Get available email accounts
        accounts = self.email_fetcher.get_configured_accounts()
        if not accounts:
            console.print("[red]Keine Email-Konten konfiguriert![/red]")
            console.print("[dim]Bitte konfigurieren Sie Email-Konten in der .env Datei[/dim]")
            return
        
        # Select account
        console.print("\n[bold]Verfügbare Email-Konten:[/bold]")
        for i, account in enumerate(accounts, 1):
            console.print(f"  {i}. {account}")
        console.print(f"  0. Alle Konten")
        
        account_choice = Prompt.ask("\nKonto wählen", default="0")
        
        if account_choice == "0":
            selected_accounts = accounts
        else:
            try:
                idx = int(account_choice) - 1
                selected_accounts = [accounts[idx]]
            except (ValueError, IndexError):
                console.print("[red]Ungültige Auswahl[/red]")
                return
        
        # Fetch emails with progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            
            for account in selected_accounts:
                task = progress.add_task(f"Verarbeite {account}...", total=100)
                
                try:
                    # Connect to email
                    progress.update(task, advance=20, description=f"Verbinde mit {account}...")
                    await self.email_fetcher.connect(account)
                    
                    # Fetch emails in date range
                    progress.update(task, advance=30, description=f"Suche Emails...")
                    emails = await self.email_fetcher.fetch_emails_in_range(
                        account=account,
                        date_range=date_range
                    )
                    
                    console.print(f"[green]Gefunden: {len(emails)} Emails mit Anhängen[/green]")
                    
                    # Download attachments by month
                    for month in date_range.get_months():
                        month_dir = self.staging_dir / month
                        month_dir.mkdir(exist_ok=True)
                        
                        month_emails = [e for e in emails if e['date'].strftime('%Y-%m') == month]
                        if not month_emails:
                            continue
                        
                        progress.update(
                            task,
                            advance=30/len(date_range.get_months()),
                            description=f"Lade {month}: {len(month_emails)} Dokumente..."
                        )
                        
                        for email in month_emails:
                            for attachment in email.get('attachments', []):
                                if attachment['type'].lower() in ['.pdf', '.png', '.jpg', '.jpeg']:
                                    filepath = month_dir / attachment['filename']
                                    await self.email_fetcher.download_attachment(
                                        attachment['data'],
                                        filepath
                                    )
                        
                        console.print(f"  [green]✓[/green] {month}: {len(month_emails)} Dokumente gespeichert")
                    
                    progress.update(task, advance=20, description=f"Trenne Verbindung...")
                    await self.email_fetcher.disconnect(account)
                    
                    progress.update(task, completed=100, description=f"[green]✓ {account} abgeschlossen[/green]")
                    
                except Exception as e:
                    console.print(f"[red]Fehler bei {account}: {e}[/red]")
                    logger.error(f"Email fetch error for {account}: {e}")
        
        # Summary
        console.print("\n[bold green]Email-Abruf abgeschlossen![/bold green]")
        total_files = sum(len(list((self.staging_dir / month).glob("*"))) 
                         for month in date_range.get_months() 
                         if (self.staging_dir / month).exists())
        console.print(f"Gesamt: {total_files} Dokumente heruntergeladen")
        console.print(f"Gespeichert in: {self.staging_dir.absolute()}")
    
    async def workflow_2_process_documents(self):
        """Workflow 2: Dokumente verarbeiten & Metadaten anreichern."""
        console.print("\n[bold yellow]Workflow 2: Dokumente verarbeiten & Metadaten anreichern[/bold yellow]\n")
        
        # Select processing source
        console.print("[bold]Dokumentenquelle wählen:[/bold]")
        console.print("  1. Staging-Verzeichnis (heruntergeladene Emails)")
        console.print("  2. Paperless NGX (bereits hochgeladene Dokumente)")
        
        source_choice = Prompt.ask("Quelle", choices=["1", "2"], default="1")
        
        if source_choice == "1":
            await self._process_staging_documents()
        else:
            await self._process_paperless_documents()
    
    async def _process_staging_documents(self):
        """Process documents from staging directory."""
        # Get available months in staging
        available_months = [d.name for d in self.staging_dir.iterdir() if d.is_dir()]
        
        if not available_months:
            console.print("[red]Keine Dokumente im Staging-Verzeichnis gefunden![/red]")
            console.print("[dim]Nutzen Sie zuerst Workflow 1 zum Herunterladen[/dim]")
            return
        
        console.print(f"\n[bold]Verfügbare Monate:[/bold] {', '.join(sorted(available_months))}")
        
        # Select months to process
        months_input = Prompt.ask(
            "Monate zur Verarbeitung (komma-getrennt oder 'alle')",
            default="alle"
        )
        
        if months_input.lower() == "alle":
            selected_months = available_months
        else:
            selected_months = [m.strip() for m in months_input.split(",")]
        
        # Collect all documents
        documents = []
        for month in selected_months:
            month_dir = self.staging_dir / month
            if not month_dir.exists():
                console.print(f"[yellow]Warnung: {month} nicht gefunden[/yellow]")
                continue
            
            for file_path in month_dir.glob("*.pdf"):
                documents.append({
                    'path': file_path,
                    'month': month,
                    'filename': file_path.name
                })
        
        if not documents:
            console.print("[red]Keine PDF-Dokumente gefunden![/red]")
            return
        
        console.print(f"\n[green]Gefunden: {len(documents)} Dokumente zur Verarbeitung[/green]")
        
        # Process documents with progress
        await self._process_document_batch(documents, source="staging")
    
    async def _process_paperless_documents(self):
        """Process documents already in Paperless."""
        # Select date range
        date_range = self.select_date_range("Dokumenten-Verarbeitung")
        
        # Query Paperless for documents
        console.print("\n[dim]Lade Dokumente aus Paperless...[/dim]")
        
        try:
            documents = await self.paperless_client.get_documents_in_range(date_range)
            
            if not documents:
                console.print("[red]Keine Dokumente im gewählten Zeitraum gefunden![/red]")
                return
            
            console.print(f"\n[green]Gefunden: {len(documents)} Dokumente zur Verarbeitung[/green]")
            
            # Process documents
            await self._process_document_batch(documents, source="paperless")
            
        except Exception as e:
            console.print(f"[red]Fehler beim Abruf aus Paperless: {e}[/red]")
            logger.error(f"Paperless query error: {e}")
    
    async def _process_document_batch(self, documents: List[Dict], source: str = "staging"):
        """Process a batch of documents with LLM and smart tagging.
        
        Args:
            documents: List of documents to process
            source: Source of documents ("staging" or "paperless")
        """
        console.print(f"\n[bold]Verarbeitung von {len(documents)} Dokumenten[/bold]")
        console.print(f"[dim]LLM Provider: {self.settings.llm_provider}[/dim]")
        console.print(f"[dim]Tag-Matching Threshold: 95%[/dim]\n")
        
        # Get existing tags for matching
        existing_tags = await self.tag_matcher.get_existing_tags()
        console.print(f"[dim]Existierende Tags geladen: {len(existing_tags)}[/dim]\n")
        
        processed = 0
        errors = []
        new_tags_created = set()
        tag_matches = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            
            task = progress.add_task("Verarbeite Dokumente...", total=len(documents))
            
            for i, doc in enumerate(documents):
                doc_name = doc.get('filename', doc.get('title', f'Dokument {i+1}'))
                
                try:
                    progress.update(task, description=f"[{i+1}/{len(documents)}] {doc_name[:30]}...")
                    
                    # Extract OCR text
                    if source == "staging":
                        # Upload to Paperless first for OCR
                        ocr_text = await self._upload_and_get_ocr(doc['path'])
                    else:
                        # Get OCR from Paperless
                        ocr_text = doc.get('content', '') or doc.get('ocr', '')
                    
                    if not ocr_text or len(ocr_text) < 50:
                        console.print(f"  [yellow]⚠[/yellow] {doc_name}: OCR-Text zu kurz oder fehlt")
                        errors.append(doc_name)
                        progress.advance(task)
                        continue
                    
                    # LLM metadata extraction
                    progress.update(task, description=f"LLM-Analyse: {doc_name[:30]}...")
                    metadata = await self.llm_client.extract_metadata(
                        ocr_text=ocr_text,
                        filename=doc_name,
                        prompt_template="german_business"
                    )
                    
                    # Smart tag matching
                    progress.update(task, description=f"Tag-Matching: {doc_name[:30]}...")
                    original_tags = metadata.get('tags', [])
                    matched_tags = []
                    
                    for tag in original_tags:
                        match_result = await self.tag_matcher.match_tag(tag, existing_tags)
                        
                        if match_result.is_new_tag:
                            matched_tags.append(tag)
                            new_tags_created.add(tag)
                            existing_tags.append(tag)  # Add to cache
                            console.print(f"    [green]✓[/green] Neuer Tag: '{tag}'")
                        else:
                            matched_tags.append(match_result.matched_tag)
                            if tag != match_result.matched_tag:
                                tag_matches.append((tag, match_result.matched_tag, match_result.similarity_score))
                                console.print(f"    [cyan]→[/cyan] Tag-Match: '{tag}' → '{match_result.matched_tag}' ({match_result.similarity_score:.0%})")
                    
                    metadata['tags'] = list(set(matched_tags))  # Remove duplicates
                    
                    # Update in Paperless
                    if source == "paperless":
                        await self.paperless_client.update_document(doc['id'], metadata)
                    
                    processed += 1
                    progress.advance(task)
                    
                except Exception as e:
                    console.print(f"  [red]✗[/red] {doc_name}: {str(e)[:50]}")
                    errors.append(doc_name)
                    logger.error(f"Processing error for {doc_name}: {e}")
                    progress.advance(task)
        
        # Summary
        console.print("\n" + "="*60)
        console.print("[bold green]Verarbeitung abgeschlossen![/bold green]\n")
        
        # Statistics table
        stats_table = Table(title="Verarbeitungsstatistik")
        stats_table.add_column("Metrik", style="cyan")
        stats_table.add_column("Wert", style="green")
        
        stats_table.add_row("Dokumente verarbeitet", str(processed))
        stats_table.add_row("Fehler", str(len(errors)))
        stats_table.add_row("Neue Tags erstellt", str(len(new_tags_created)))
        stats_table.add_row("Tags gematcht", str(len(tag_matches)))
        stats_table.add_row("Erfolgsrate", f"{(processed/len(documents)*100):.1f}%")
        
        console.print(stats_table)
        
        if new_tags_created:
            console.print(f"\n[bold]Neue Tags:[/bold] {', '.join(sorted(new_tags_created))}")
        
        if tag_matches:
            console.print("\n[bold]Tag-Matches (Top 5):[/bold]")
            for orig, matched, score in tag_matches[:5]:
                console.print(f"  • '{orig}' → '{matched}' ({score:.0%})")
    
    async def workflow_3_quality_scan(self):
        """Workflow 3: Quality Scan & Report."""
        console.print("\n[bold blue]Workflow 3: Quality Scan & Report[/bold blue]\n")
        
        # Select date range
        date_range = self.select_date_range("Qualitätsprüfung")
        
        # Query documents
        console.print("\n[dim]Lade Dokumente für Qualitätsprüfung...[/dim]")
        
        try:
            documents = await self.paperless_client.get_documents_in_range(date_range)
            
            if not documents:
                console.print("[red]Keine Dokumente im gewählten Zeitraum gefunden![/red]")
                return
            
            console.print(f"\n[green]Prüfe {len(documents)} Dokumente...[/green]\n")
            
            # Quality checks
            issues = {
                'missing_title': [],
                'missing_correspondent': [],
                'missing_tags': [],
                'few_tags': [],
                'missing_ocr': [],
                'missing_date': [],
                'wrong_period': []
            }
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                console=console
            ) as progress:
                
                task = progress.add_task("Qualitätsprüfung...", total=len(documents))
                
                for doc in documents:
                    # Check title
                    if not doc.get('title') or doc['title'].startswith('scan_'):
                        issues['missing_title'].append(doc)
                    
                    # Check correspondent
                    if not doc.get('correspondent'):
                        issues['missing_correspondent'].append(doc)
                    
                    # Check tags
                    tags = doc.get('tags', [])
                    if not tags:
                        issues['missing_tags'].append(doc)
                    elif len(tags) < 3:
                        issues['few_tags'].append(doc)
                    
                    # Check OCR
                    ocr_text = doc.get('content', '') or doc.get('ocr', '')
                    if not ocr_text or len(ocr_text) < 50:
                        issues['missing_ocr'].append(doc)
                    
                    # Check date
                    if not doc.get('created'):
                        issues['missing_date'].append(doc)
                    else:
                        # Check if in correct period
                        doc_date = datetime.fromisoformat(doc['created'].replace('Z', '+00:00'))
                        if not date_range.contains(doc_date):
                            issues['wrong_period'].append(doc)
                    
                    progress.advance(task)
            
            # Display results
            console.print("\n[bold]Qualitätsprüfung abgeschlossen[/bold]\n")
            
            # Issues table
            issues_table = Table(title="Gefundene Probleme")
            issues_table.add_column("Problem", style="yellow")
            issues_table.add_column("Anzahl", style="red")
            issues_table.add_column("Prozent", style="dim")
            
            total_docs = len(documents)
            issues_table.add_row("Fehlender/schlechter Titel", str(len(issues['missing_title'])), 
                               f"{len(issues['missing_title'])/total_docs*100:.1f}%")
            issues_table.add_row("Fehlender Korrespondent", str(len(issues['missing_correspondent'])),
                               f"{len(issues['missing_correspondent'])/total_docs*100:.1f}%")
            issues_table.add_row("Keine Tags", str(len(issues['missing_tags'])),
                               f"{len(issues['missing_tags'])/total_docs*100:.1f}%")
            issues_table.add_row("Zu wenige Tags (<3)", str(len(issues['few_tags'])),
                               f"{len(issues['few_tags'])/total_docs*100:.1f}%")
            issues_table.add_row("Fehlender/kurzer OCR", str(len(issues['missing_ocr'])),
                               f"{len(issues['missing_ocr'])/total_docs*100:.1f}%")
            issues_table.add_row("Fehlendes Datum", str(len(issues['missing_date'])),
                               f"{len(issues['missing_date'])/total_docs*100:.1f}%")
            issues_table.add_row("Falscher Zeitraum", str(len(issues['wrong_period'])),
                               f"{len(issues['wrong_period'])/total_docs*100:.1f}%")
            
            console.print(issues_table)
            
            # Calculate quality score
            total_issues = sum(len(issue_list) for issue_list in issues.values())
            quality_score = max(0, 100 - (total_issues / total_docs * 100))
            
            console.print(f"\n[bold]Qualitäts-Score: {quality_score:.1f}%[/bold]")
            
            if quality_score >= 90:
                console.print("[green]Ausgezeichnete Dokumentenqualität![/green]")
            elif quality_score >= 70:
                console.print("[yellow]Gute Qualität mit Verbesserungspotential[/yellow]")
            else:
                console.print("[red]Qualität sollte verbessert werden[/red]")
            
            # Export report
            if Confirm.ask("\nReport als CSV exportieren?"):
                report_path = self._export_quality_report(documents, issues, date_range)
                console.print(f"\n[green]Report gespeichert:[/green] {report_path}")
            
        except Exception as e:
            console.print(f"[red]Fehler bei Qualitätsprüfung: {e}[/red]")
            logger.error(f"Quality scan error: {e}")
    
    def _export_quality_report(self, documents: List[Dict], issues: Dict, date_range: DateRange) -> Path:
        """Export quality report as CSV.
        
        Args:
            documents: All documents
            issues: Found issues
            date_range: Date range of scan
            
        Returns:
            Path to exported report
        """
        import csv
        
        report_name = f"quality_report_{date_range.start_date.strftime('%Y-%m')}_{date_range.end_date.strftime('%Y-%m')}.csv"
        report_path = Path("reports") / report_name
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['document_id', 'title', 'created', 'issues', 'action_needed']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            
            for doc in documents:
                doc_issues = []
                
                # Check which issues apply
                for issue_type, issue_docs in issues.items():
                    if doc in issue_docs:
                        doc_issues.append(issue_type)
                
                if doc_issues:
                    writer.writerow({
                        'document_id': doc.get('id', ''),
                        'title': doc.get('title', 'Kein Titel'),
                        'created': doc.get('created', ''),
                        'issues': ', '.join(doc_issues),
                        'action_needed': 'Metadaten ergänzen' if doc_issues else 'Keine'
                    })
        
        return report_path
    
    async def _upload_and_get_ocr(self, file_path: Path) -> str:
        """Upload document to Paperless and get OCR text.
        
        Args:
            file_path: Path to document file
            
        Returns:
            OCR text from document
        """
        # This would upload to Paperless and trigger OCR
        # For now, return placeholder
        return f"OCR text for {file_path.name}"
    
    async def run(self):
        """Main run loop for the CLI."""
        console.print("[bold cyan]Willkommen zum Paperless NGX Workflow-System![/bold cyan]\n")
        
        while True:
            try:
                choice = self.show_main_menu()
                
                if choice == 0:
                    console.print("\n[bold]Auf Wiedersehen![/bold]")
                    break
                elif choice == 1:
                    await self.workflow_1_email_fetch()
                elif choice == 2:
                    await self.workflow_2_process_documents()
                elif choice == 3:
                    await self.workflow_3_quality_scan()
                
                if choice != 0:
                    input("\n[dim]Drücken Sie Enter um fortzufahren...[/dim]")
                    
            except KeyboardInterrupt:
                console.print("\n\n[yellow]Unterbrochen durch Benutzer[/yellow]")
                if Confirm.ask("Wirklich beenden?"):
                    break
            except Exception as e:
                console.print(f"\n[red]Fehler: {e}[/red]")
                logger.error(f"Unexpected error: {e}", exc_info=True)
                input("\n[dim]Drücken Sie Enter um fortzufahren...[/dim]")


@click.command()
@click.option('--workflow', type=int, help='Direkt zu Workflow springen (1-3)')
def main(workflow: Optional[int] = None):
    """Paperless NGX Simplified Workflow CLI."""
    cli = SimplifiedWorkflowCLI()
    
    if workflow:
        # Direct workflow execution
        asyncio.run(run_single_workflow(cli, workflow))
    else:
        # Interactive menu
        asyncio.run(cli.run())


async def run_single_workflow(cli: SimplifiedWorkflowCLI, workflow: int):
    """Run a single workflow directly.
    
    Args:
        cli: CLI instance
        workflow: Workflow number (1-3)
    """
    if workflow == 1:
        await cli.workflow_1_email_fetch()
    elif workflow == 2:
        await cli.workflow_2_process_documents()
    elif workflow == 3:
        await cli.workflow_3_quality_scan()
    else:
        console.print(f"[red]Ungültiger Workflow: {workflow}[/red]")
        console.print("[dim]Verwenden Sie 1, 2 oder 3[/dim]")


if __name__ == "__main__":
    main()