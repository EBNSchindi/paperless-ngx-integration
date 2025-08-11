"""Service for generating reports in various formats.

This module provides report generation capabilities with streaming support
for large datasets, including CSV, JSON, and PDF formats.
"""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime
from io import StringIO, BytesIO
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Union

logger = logging.getLogger(__name__)


class ReportGeneratorService:
    """Service for generating reports from document and quality data.
    
    This service provides:
    - CSV generation with streaming for large datasets
    - JSON export with pretty formatting
    - PDF report generation (requires reportlab)
    - Progress tracking integration
    - German language headers and formatting
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize the report generator service.
        
        Args:
            output_dir: Directory for saving reports (default: current directory)
        """
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized ReportGeneratorService with output dir: {self.output_dir}")
    
    def generate_csv_streaming(
        self,
        data_generator: Generator[Dict[str, Any], None, None],
        output_file: Union[str, Path],
        headers: Optional[List[str]] = None,
        german_headers: bool = True,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Generate CSV report with streaming for memory efficiency.
        
        Args:
            data_generator: Generator yielding data rows
            output_file: Output file path
            headers: Column headers (auto-detected if None)
            german_headers: Use German column headers
            progress_callback: Optional callback(rows_written, current_row)
            
        Returns:
            Report generation statistics
        """
        output_path = self.output_dir / output_file if not Path(output_file).is_absolute() else Path(output_file)
        
        # German header translations
        header_translations = {
            'document_id': 'Dokument-ID',
            'title': 'Titel',
            'correspondent': 'Korrespondent',
            'correspondent_name': 'Korrespondent',
            'document_type': 'Dokumenttyp',
            'document_type_name': 'Dokumenttyp',
            'created': 'Erstellt',
            'modified': 'Geändert',
            'tags': 'Tags',
            'has_ocr': 'OCR vorhanden',
            'issue_type': 'Problem-Typ',
            'severity': 'Schweregrad',
            'description': 'Beschreibung',
            'file_size': 'Dateigröße',
            'page_count': 'Seitenanzahl',
            'archive_serial_number': 'Archivnummer'
        }
        
        rows_written = 0
        first_row = None
        
        try:
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = None
                
                for row in data_generator:
                    # Initialize writer with headers from first row
                    if writer is None:
                        first_row = row
                        
                        if headers is None:
                            headers = list(row.keys())
                        
                        # Translate headers if requested
                        if german_headers:
                            display_headers = [
                                header_translations.get(h, h) for h in headers
                            ]
                        else:
                            display_headers = headers
                        
                        writer = csv.DictWriter(
                            csvfile,
                            fieldnames=headers,
                            extrasaction='ignore'
                        )
                        
                        # Write custom headers
                        csvfile.write(','.join(display_headers) + '\n')
                    
                    # Process special fields
                    processed_row = self._process_csv_row(row)
                    
                    # Write row
                    writer.writerow(processed_row)
                    rows_written += 1
                    
                    if progress_callback:
                        progress_callback(rows_written, processed_row)
                    
                    if rows_written % 100 == 0:
                        logger.debug(f"Written {rows_written} rows to CSV")
            
            logger.info(f"CSV report generated: {output_path} ({rows_written} rows)")
            
            return {
                'success': True,
                'output_file': str(output_path),
                'rows_written': rows_written,
                'file_size': output_path.stat().st_size,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate CSV report: {e}")
            return {
                'success': False,
                'error': str(e),
                'rows_written': rows_written
            }
    
    def _process_csv_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Process row data for CSV export.
        
        Args:
            row: Raw data row
            
        Returns:
            Processed row suitable for CSV
        """
        processed = row.copy()
        
        # Convert lists to comma-separated strings
        for key, value in processed.items():
            if isinstance(value, list):
                if all(isinstance(item, dict) for item in value):
                    # Extract names or IDs from dict lists
                    if value and 'name' in value[0]:
                        processed[key] = ', '.join(str(item.get('name', '')) for item in value)
                    else:
                        processed[key] = ', '.join(str(item) for item in value)
                else:
                    processed[key] = ', '.join(str(item) for item in value)
            elif isinstance(value, dict):
                # Convert dict to string representation
                processed[key] = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, bool):
                processed[key] = 'Ja' if value else 'Nein'
            elif value is None:
                processed[key] = ''
        
        return processed
    
    def generate_json_report(
        self,
        data: Union[List[Dict[str, Any]], Dict[str, Any]],
        output_file: Union[str, Path],
        pretty: bool = True,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """Generate JSON report.
        
        Args:
            data: Data to export
            output_file: Output file path
            pretty: Use pretty formatting with indentation
            include_metadata: Include report metadata
            
        Returns:
            Report generation statistics
        """
        output_path = self.output_dir / output_file if not Path(output_file).is_absolute() else Path(output_file)
        
        try:
            report_data = {
                'data': data,
            }
            
            if include_metadata:
                report_data['metadata'] = {
                    'generated_at': datetime.now().isoformat(),
                    'generator': 'Paperless NGX Report Generator',
                    'version': '1.0.0',
                    'record_count': len(data) if isinstance(data, list) else 1
                }
            
            with open(output_path, 'w', encoding='utf-8') as jsonfile:
                if pretty:
                    json.dump(report_data, jsonfile, ensure_ascii=False, indent=2)
                else:
                    json.dump(report_data, jsonfile, ensure_ascii=False)
            
            logger.info(f"JSON report generated: {output_path}")
            
            return {
                'success': True,
                'output_file': str(output_path),
                'file_size': output_path.stat().st_size,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate JSON report: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_pdf_report(
        self,
        title: str,
        sections: List[Dict[str, Any]],
        output_file: Union[str, Path],
        include_charts: bool = False
    ) -> Dict[str, Any]:
        """Generate PDF report.
        
        Args:
            title: Report title
            sections: Report sections with content
            output_file: Output file path
            include_charts: Include visual charts
            
        Returns:
            Report generation statistics
        """
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import (
                SimpleDocTemplate, Table, TableStyle, Paragraph,
                Spacer, PageBreak, Image
            )
            from reportlab.lib.enums import TA_CENTER, TA_RIGHT
        except ImportError:
            logger.error("reportlab not installed. Install with: pip install reportlab")
            return {
                'success': False,
                'error': 'reportlab library not installed'
            }
        
        output_path = self.output_dir / output_file if not Path(output_file).is_absolute() else Path(output_file)
        
        try:
            # Create PDF document
            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )
            
            # Container for the 'Flowable' objects
            elements = []
            
            # Define styles
            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(
                name='CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#2E86C1'),
                spaceAfter=30,
                alignment=TA_CENTER
            ))
            styles.add(ParagraphStyle(
                name='SectionHeader',
                parent=styles['Heading2'],
                fontSize=16,
                textColor=colors.HexColor('#34495E'),
                spaceAfter=12
            ))
            
            # Add title
            elements.append(Paragraph(title, styles['CustomTitle']))
            elements.append(Spacer(1, 12))
            
            # Add metadata
            metadata = Paragraph(
                f"Erstellt am: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                styles['Normal']
            )
            elements.append(metadata)
            elements.append(Spacer(1, 20))
            
            # Process sections
            for section in sections:
                # Section header
                if 'title' in section:
                    elements.append(Paragraph(section['title'], styles['SectionHeader']))
                    elements.append(Spacer(1, 12))
                
                # Section content
                if 'content' in section:
                    if isinstance(section['content'], str):
                        elements.append(Paragraph(section['content'], styles['Normal']))
                    elif isinstance(section['content'], list):
                        for item in section['content']:
                            elements.append(Paragraph(f"• {item}", styles['Normal']))
                    elements.append(Spacer(1, 12))
                
                # Tables
                if 'table' in section:
                    table_data = section['table']
                    if table_data:
                        t = Table(table_data)
                        t.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, 0), 12),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black)
                        ]))
                        elements.append(t)
                        elements.append(Spacer(1, 12))
                
                # Page break after section if requested
                if section.get('page_break', False):
                    elements.append(PageBreak())
            
            # Build PDF
            doc.build(elements)
            
            logger.info(f"PDF report generated: {output_path}")
            
            return {
                'success': True,
                'output_file': str(output_path),
                'file_size': output_path.stat().st_size,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate PDF report: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_quality_report(
        self,
        quality_data: Dict[str, Any],
        format: str = 'csv',
        output_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate quality analysis report in specified format.
        
        Args:
            quality_data: Quality analysis data
            format: Output format ('csv', 'json', 'pdf')
            output_file: Output filename (auto-generated if None)
            
        Returns:
            Report generation statistics
        """
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"quality_report_{timestamp}.{format}"
        
        if format == 'csv':
            # Convert quality data to flat structure for CSV
            rows = []
            
            if 'issues' in quality_data:
                for issue in quality_data['issues']:
                    rows.append({
                        'document_id': issue.get('document_id'),
                        'issue_type': issue.get('issue_type'),
                        'severity': issue.get('severity'),
                        'description': issue.get('description'),
                        'timestamp': issue.get('timestamp')
                    })
            
            # Create generator from list
            def data_gen():
                for row in rows:
                    yield row
            
            return self.generate_csv_streaming(data_gen(), output_file)
        
        elif format == 'json':
            return self.generate_json_report(quality_data, output_file)
        
        elif format == 'pdf':
            sections = self._prepare_quality_report_sections(quality_data)
            return self.generate_pdf_report(
                title="Qualitätsanalyse-Bericht",
                sections=sections,
                output_file=output_file
            )
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _prepare_quality_report_sections(
        self,
        quality_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Prepare sections for PDF quality report.
        
        Args:
            quality_data: Quality analysis data
            
        Returns:
            List of report sections
        """
        sections = []
        
        # Summary section
        if 'summary' in quality_data:
            summary = quality_data['summary']
            sections.append({
                'title': 'Zusammenfassung',
                'content': [
                    f"Gesamtzahl der Probleme: {summary.get('total_issues', 0)}",
                    f"Betroffene Dokumente: {summary.get('affected_documents', 0)}",
                    f"Kritische Probleme: {summary.get('critical_issues', 0)}",
                    f"Hohe Priorität: {summary.get('high_issues', 0)}",
                    f"Mittlere Priorität: {summary.get('medium_issues', 0)}",
                    f"Niedrige Priorität: {summary.get('low_issues', 0)}"
                ]
            })
        
        # Issues by type
        if 'by_type' in quality_data:
            issue_types = quality_data['by_type']
            table_data = [['Problem-Typ', 'Anzahl']]
            for issue_type, count in issue_types.items():
                table_data.append([issue_type, str(count)])
            
            sections.append({
                'title': 'Probleme nach Typ',
                'table': table_data
            })
        
        # Recommendations
        if 'recommendations' in quality_data:
            sections.append({
                'title': 'Empfehlungen',
                'content': quality_data['recommendations']
            })
        
        # Top affected documents
        if 'top_affected_documents' in quality_data:
            table_data = [['Dokument-ID', 'Anzahl Probleme']]
            for doc in quality_data['top_affected_documents'][:10]:
                table_data.append([
                    str(doc.get('document_id')),
                    str(doc.get('issue_count'))
                ])
            
            sections.append({
                'title': 'Am stärksten betroffene Dokumente',
                'table': table_data
            })
        
        return sections
    
    def generate_statistics_report(
        self,
        statistics: Dict[str, Any],
        format: str = 'json',
        output_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate statistics report.
        
        Args:
            statistics: Statistics data
            format: Output format
            output_file: Output filename
            
        Returns:
            Report generation statistics
        """
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"statistics_{timestamp}.{format}"
        
        if format == 'json':
            return self.generate_json_report(statistics, output_file)
        
        elif format == 'pdf':
            sections = self._prepare_statistics_sections(statistics)
            return self.generate_pdf_report(
                title="Dokumenten-Statistik",
                sections=sections,
                output_file=output_file
            )
        
        else:
            raise ValueError(f"Unsupported format for statistics: {format}")
    
    def _prepare_statistics_sections(
        self,
        statistics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Prepare sections for PDF statistics report.
        
        Args:
            statistics: Statistics data
            
        Returns:
            List of report sections
        """
        sections = []
        
        # Overview
        sections.append({
            'title': 'Übersicht',
            'content': [
                f"Gesamtzahl Dokumente: {statistics.get('total_documents', 0)}",
                f"Dokumente mit OCR: {statistics.get('documents_with_ocr', 0)}",
                f"Dokumente ohne OCR: {statistics.get('documents_without_ocr', 0)}"
            ]
        })
        
        # Documents by correspondent
        if 'documents_by_correspondent' in statistics:
            table_data = [['Korrespondent', 'Anzahl']]
            for correspondent, count in sorted(
                statistics['documents_by_correspondent'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:20]:
                table_data.append([correspondent, str(count)])
            
            sections.append({
                'title': 'Dokumente nach Korrespondent (Top 20)',
                'table': table_data
            })
        
        # Documents by type
        if 'documents_by_type' in statistics:
            table_data = [['Dokumenttyp', 'Anzahl']]
            for doc_type, count in sorted(
                statistics['documents_by_type'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:15]:
                table_data.append([doc_type, str(count)])
            
            sections.append({
                'title': 'Dokumente nach Typ (Top 15)',
                'table': table_data
            })
        
        # Top tags
        if 'top_tags' in statistics:
            table_data = [['Tag', 'Anzahl']]
            for tag_info in statistics['top_tags']:
                table_data.append([
                    tag_info.get('name', ''),
                    str(tag_info.get('count', 0))
                ])
            
            sections.append({
                'title': 'Häufigste Tags',
                'table': table_data
            })
        
        return sections