import csv
import io
from datetime import datetime
from typing import List, Dict, Optional
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import logging

from ..models import ClientProfile, ClientLocationData, WhiteLabelSettings

User = get_user_model()
logger = logging.getLogger(__name__)


class ClientExportService:
    """Service for exporting client data in various formats."""

    def export_client_locations_csv(self, user: User, client_id: str, 
                                  export_options: Dict) -> HttpResponse:
        """
        Export client locations to CSV format.
        
        Args:
            user: User instance
            client_id: Client UUID
            export_options: Export configuration
            
        Returns:
            HttpResponse with CSV data
        """
        try:
            client = ClientProfile.objects.get(id=client_id, user=user)
        except ClientProfile.DoesNotExist:
            raise ValueError("Client not found or not accessible")

        # Get locations with filters
        locations = self._get_filtered_locations(client, export_options)

        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        filename = f"{client.client_name.replace(' ', '_')}_locations_{datetime.now().strftime('%Y%m%d')}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)

        # Write header
        headers = ['Business Name', 'Address', 'City', 'State', 'ZIP Code']
        
        if export_options.get('include_contact_info', True):
            headers.extend(['Phone', 'Email', 'Website'])
        
        if export_options.get('include_ratings', True):
            headers.extend(['Google Rating', 'Total Reviews'])
        
        headers.extend(['Priority Score', 'Status', 'Priority'])
        
        if export_options.get('include_notes', True):
            headers.append('Client Notes')
        
        headers.extend(['Search Name', 'Date Added'])
        
        writer.writerow(headers)

        # Write data rows
        for location in locations:
            row = [
                location.location_data.name,
                location.location_data.address,
                location.client_profile.client_city,
                location.client_profile.client_state,
                location.client_profile.client_zip_code,
            ]
            
            if export_options.get('include_contact_info', True):
                row.extend([
                    location.location_data.phone or '',
                    location.location_data.email or '',
                    location.location_data.website or ''
                ])
            
            if export_options.get('include_ratings', True):
                row.extend([
                    str(location.location_data.google_rating) if location.location_data.google_rating else '',
                    str(location.location_data.google_user_ratings_total) if location.location_data.google_user_ratings_total else ''
                ])
            
            row.extend([
                str(location.location_data.priority_score),
                location.get_status_display(),
                str(location.priority)
            ])
            
            if export_options.get('include_notes', True):
                row.append(location.notes or '')
            
            row.extend([
                location.saved_search.search_name,
                location.created_at.strftime('%Y-%m-%d')
            ])
            
            writer.writerow(row)

        logger.info(f"Exported {len(locations)} locations to CSV for client {client.client_name}")
        return response

    def export_client_locations_pdf(self, user: User, client_id: str, 
                                  export_options: Dict) -> HttpResponse:
        """
        Export client locations to PDF format with custom branding.
        
        Args:
            user: User instance
            client_id: Client UUID
            export_options: Export configuration
            
        Returns:
            HttpResponse with PDF data
        """
        try:
            client = ClientProfile.objects.get(id=client_id, user=user)
        except ClientProfile.DoesNotExist:
            raise ValueError("Client not found or not accessible")

        # Get white label settings if available
        whitelabel = None
        if export_options.get('use_custom_branding', True):
            try:
                whitelabel = WhiteLabelSettings.objects.get(user=user, is_active=True)
            except WhiteLabelSettings.DoesNotExist:
                pass

        # Get locations with filters
        locations = self._get_filtered_locations(client, export_options)

        # Create PDF response
        response = HttpResponse(content_type='application/pdf')
        filename = f"{client.client_name.replace(' ', '_')}_locations_{datetime.now().strftime('%Y%m%d')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        # Create PDF document
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        
        # Build PDF content
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor(whitelabel.primary_color if whitelabel else '#fb6d00')
        )
        
        # Add logo if available
        if whitelabel and whitelabel.company_logo:
            try:
                logo = Image(whitelabel.company_logo.path, width=2*inch, height=1*inch)
                story.append(logo)
                story.append(Spacer(1, 12))
            except:
                pass

        # Title
        company_name = whitelabel.company_name if whitelabel else "Vending Hive"
        title = Paragraph(f"Location Report for {client.client_name}", title_style)
        story.append(title)
        story.append(Spacer(1, 12))

        # Report info
        report_info = f"""
        <b>Prepared by:</b> {company_name}<br/>
        <b>Client:</b> {client.client_name}<br/>
        <b>Contact:</b> {client.client_contact_name or 'N/A'}<br/>
        <b>Report Date:</b> {datetime.now().strftime('%B %d, %Y')}<br/>
        <b>Total Locations:</b> {len(locations)}
        """
        story.append(Paragraph(report_info, styles['Normal']))
        story.append(Spacer(1, 20))

        # Create table data
        table_data = [['Business Name', 'Address', 'Phone', 'Status', 'Priority']]
        
        for location in locations:
            table_data.append([
                location.location_data.name[:30] + ('...' if len(location.location_data.name) > 30 else ''),
                location.location_data.address[:40] + ('...' if len(location.location_data.address) > 40 else ''),
                location.location_data.phone or 'N/A',
                location.get_status_display(),
                str(location.priority)
            ])

        # Create table
        table = Table(table_data, colWidths=[2*inch, 2.5*inch, 1.2*inch, 1*inch, 0.8*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(whitelabel.primary_color if whitelabel else '#fb6d00')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        story.append(Spacer(1, 20))

        # Footer
        if not (whitelabel and whitelabel.remove_vending_hive_branding):
            footer_text = "Generated by Vending Hive - AI-Powered Location Discovery"
            story.append(Paragraph(footer_text, styles['Normal']))

        # Build PDF
        doc.build(story)
        buffer.seek(0)
        response.write(buffer.getvalue())
        buffer.close()

        logger.info(f"Exported {len(locations)} locations to PDF for client {client.client_name}")
        return response

    def _get_filtered_locations(self, client: ClientProfile, 
                              export_options: Dict) -> List[ClientLocationData]:
        """Get filtered locations based on export options."""
        queryset = client.client_locations.select_related('location_data', 'saved_search')
        
        # Status filter
        status_filter = export_options.get('status_filter')
        if status_filter:
            queryset = queryset.filter(status__in=status_filter)
        
        # Priority filter
        priority_min = export_options.get('priority_min')
        if priority_min is not None:
            queryset = queryset.filter(priority__gte=priority_min)
        
        return queryset.order_by('-priority', '-created_at')