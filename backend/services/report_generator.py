"""
CarbonShip CBAM Report Generator
Generates EU-compliant PDF reports for CBAM submissions

Uses reportlab for PDF generation (free, no external API needed)
"""

import os
import json
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass
from io import BytesIO

# Check if reportlab is available
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.lib.colors import HexColor, black, white
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
        Image, PageBreak, HRFlowable
    )
    from reportlab.graphics.shapes import Drawing, Rect, String
    from reportlab.graphics.charts.piecharts import Pie
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("WARNING: reportlab not installed. PDF generation disabled.")
    print("Install with: pip install reportlab")


@dataclass
class CBAMReportData:
    """Data structure for CBAM report"""
    # Company Info
    exporter_name: str
    exporter_address: str
    exporter_gstin: str
    
    # Product Info
    product_type: str
    product_cn_code: str
    weight_tonnes: float
    
    # Route Info
    origin_port: str
    destination_port: str
    route_name: str
    
    # Emissions
    manufacturing_co2: float
    transport_co2: float
    port_handling_co2: float
    total_co2: float
    
    # CBAM Tax
    ets_price_eur: float
    cbam_tax_eur: float
    cbam_tax_inr: float
    
    # Metadata
    calculation_date: str
    report_id: str
    methodology: str
    sources: list


def generate_report_id() -> str:
    """Generate unique report ID"""
    now = datetime.now()
    return f"CBAM-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}"


class CBAMReportGenerator:
    """
    Generates EU-compliant CBAM reports in PDF format
    """
    
    # Brand colors
    PRIMARY_COLOR = HexColor('#22c55e')  # Green
    SECONDARY_COLOR = HexColor('#10b981')  # Emerald
    DARK_COLOR = HexColor('#1f2937')  # Dark gray
    LIGHT_COLOR = HexColor('#f3f4f6')  # Light gray
    
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.styles = getSampleStyleSheet() if REPORTLAB_AVAILABLE else None
        
        if REPORTLAB_AVAILABLE:
            self._setup_styles()
    
    def _setup_styles(self):
        """Set up custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='CBAMTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=self.PRIMARY_COLOR,
            spaceAfter=20,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='CBAMSubtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=self.DARK_COLOR,
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=self.SECONDARY_COLOR,
            spaceBefore=20,
            spaceAfter=10,
            borderPadding=5
        ))
        
        self.styles.add(ParagraphStyle(
            name='DataLabel',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=HexColor('#6b7280')
        ))
        
        self.styles.add(ParagraphStyle(
            name='DataValue',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=self.DARK_COLOR,
            fontName='Helvetica-Bold'
        ))
    
    def generate_pdf(self, data: CBAMReportData, filename: Optional[str] = None) -> str:
        """
        Generate PDF report for CBAM submission
        
        Args:
            data: CBAMReportData object with all emission information
            filename: Optional custom filename
            
        Returns:
            Path to generated PDF file
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab is required for PDF generation. Install with: pip install reportlab")
        
        if not filename:
            filename = f"{data.report_id}.pdf"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # Create PDF document
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=1*cm,
            leftMargin=1*cm,
            topMargin=1*cm,
            bottomMargin=1*cm
        )
        
        # Build content
        story = []
        
        # Header
        story.append(Paragraph("CarbonShip", self.styles['CBAMTitle']))
        story.append(Paragraph("CBAM Emission Calculation Report", self.styles['CBAMSubtitle']))
        story.append(HRFlowable(width="100%", thickness=2, color=self.PRIMARY_COLOR))
        story.append(Spacer(1, 20))
        
        # Report ID and Date
        report_info = [
            ["Report ID:", data.report_id],
            ["Generated:", data.calculation_date],
            ["Status:", "DRAFT - Not Verified"]
        ]
        report_table = Table(report_info, colWidths=[3*cm, 10*cm])
        report_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), self.DARK_COLOR),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ]))
        story.append(report_table)
        story.append(Spacer(1, 20))
        
        # Section 1: Exporter Information
        story.append(Paragraph("1. Exporter Information", self.styles['SectionHeader']))
        exporter_data = [
            ["Company Name:", data.exporter_name],
            ["Address:", data.exporter_address],
            ["GSTIN:", data.exporter_gstin],
        ]
        exporter_table = Table(exporter_data, colWidths=[4*cm, 12*cm])
        exporter_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(exporter_table)
        story.append(Spacer(1, 15))
        
        # Section 2: Product Information
        story.append(Paragraph("2. Product Information", self.styles['SectionHeader']))
        product_data = [
            ["Product Type:", data.product_type.replace('_', ' ').title()],
            ["CN Code:", data.product_cn_code],
            ["Weight:", f"{data.weight_tonnes:,.2f} tonnes"],
        ]
        product_table = Table(product_data, colWidths=[4*cm, 12*cm])
        product_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(product_table)
        story.append(Spacer(1, 15))
        
        # Section 3: Shipping Route
        story.append(Paragraph("3. Shipping Route", self.styles['SectionHeader']))
        route_data = [
            ["Origin Port:", data.origin_port],
            ["Destination Port:", data.destination_port],
            ["Route:", data.route_name],
        ]
        route_table = Table(route_data, colWidths=[4*cm, 12*cm])
        route_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(route_table)
        story.append(Spacer(1, 15))
        
        # Section 4: Emission Breakdown
        story.append(Paragraph("4. Embedded Emissions Breakdown", self.styles['SectionHeader']))
        
        # Calculate percentages
        total = data.total_co2
        mfg_pct = (data.manufacturing_co2 / total * 100) if total > 0 else 0
        trans_pct = (data.transport_co2 / total * 100) if total > 0 else 0
        port_pct = (data.port_handling_co2 / total * 100) if total > 0 else 0
        
        emission_data = [
            ["Source", "CO2 (tonnes)", "Percentage"],
            ["Manufacturing", f"{data.manufacturing_co2:,.3f}", f"{mfg_pct:.1f}%"],
            ["Transport", f"{data.transport_co2:,.3f}", f"{trans_pct:.1f}%"],
            ["Port Handling", f"{data.port_handling_co2:,.3f}", f"{port_pct:.1f}%"],
            ["TOTAL", f"{data.total_co2:,.3f}", "100%"],
        ]
        
        emission_table = Table(emission_data, colWidths=[6*cm, 5*cm, 5*cm])
        emission_table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            # Total row
            ('BACKGROUND', (0, -1), (-1, -1), self.LIGHT_COLOR),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            # All cells
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, self.DARK_COLOR),
        ]))
        story.append(emission_table)
        story.append(Spacer(1, 20))
        
        # Section 5: CBAM Tax Calculation
        story.append(Paragraph("5. CBAM Tax Calculation", self.styles['SectionHeader']))
        
        tax_data = [
            ["EU ETS Carbon Price:", f"€{data.ets_price_eur:.2f} per tonne CO2"],
            ["Total Embedded Emissions:", f"{data.total_co2:,.3f} tonnes CO2"],
            ["", ""],
            ["CBAM Tax (EUR):", f"€{data.cbam_tax_eur:,.2f}"],
            ["CBAM Tax (INR):", f"₹{data.cbam_tax_inr:,.2f}"],
        ]
        
        tax_table = Table(tax_data, colWidths=[6*cm, 10*cm])
        tax_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            # Highlight tax amounts
            ('BACKGROUND', (0, -2), (-1, -1), self.LIGHT_COLOR),
            ('FONTNAME', (1, -2), (1, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (1, -2), (1, -2), HexColor('#dc2626')),  # Red for EUR
        ]))
        story.append(tax_table)
        story.append(Spacer(1, 20))
        
        # Section 6: Methodology
        story.append(Paragraph("6. Calculation Methodology", self.styles['SectionHeader']))
        story.append(Paragraph(
            f"<b>Methodology:</b> {data.methodology}",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 10))
        story.append(Paragraph("<b>Data Sources:</b>", self.styles['Normal']))
        for source in data.sources:
            story.append(Paragraph(f"• {source}", self.styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Disclaimer
        story.append(HRFlowable(width="100%", thickness=1, color=self.LIGHT_COLOR))
        story.append(Spacer(1, 10))
        disclaimer_style = ParagraphStyle(
            'Disclaimer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=HexColor('#9ca3af')
        )
        story.append(Paragraph(
            "<b>DISCLAIMER:</b> This report is generated using default emission factors from IPCC and GLEC Framework. "
            "For official CBAM submissions, emissions data must be verified by an EU-accredited verification body. "
            "This report is for informational purposes only and does not constitute legal or regulatory advice.",
            disclaimer_style
        ))
        story.append(Spacer(1, 10))
        story.append(Paragraph(
            f"Generated by CarbonShip - AI-Powered CBAM Compliance Platform | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            disclaimer_style
        ))
        
        # Build PDF
        doc.build(story)
        
        return filepath
    
    def generate_from_calculation(self, calc_result: dict, exporter_info: dict) -> str:
        """
        Generate PDF from emission calculation result
        
        Args:
            calc_result: Result from EmissionCalculator
            exporter_info: Dict with exporter_name, exporter_address, exporter_gstin
            
        Returns:
            Path to generated PDF
        """
        # Get CN code for product
        cn_codes = {
            'steel_hot_rolled': '7208',
            'steel_cold_rolled': '7209',
            'steel_pipes': '7304',
            'aluminium_primary': '7601',
            'aluminium_products': '7604',
            'cement_clinker': '2523',
            'ammonia': '2814',
            'urea': '3102',
        }
        
        data = CBAMReportData(
            exporter_name=exporter_info.get('exporter_name', 'Not Specified'),
            exporter_address=exporter_info.get('exporter_address', 'Not Specified'),
            exporter_gstin=exporter_info.get('exporter_gstin', 'Not Specified'),
            product_type=calc_result['product_type'],
            product_cn_code=cn_codes.get(calc_result['product_type'], 'XXXX'),
            weight_tonnes=calc_result['weight_tonnes'],
            origin_port=exporter_info.get('origin_port', 'Mumbai'),
            destination_port=exporter_info.get('destination_port', 'Rotterdam'),
            route_name=calc_result['route'],
            manufacturing_co2=float(calc_result['manufacturing_co2']),
            transport_co2=float(calc_result['transport_co2']),
            port_handling_co2=float(calc_result['port_handling_co2']),
            total_co2=float(calc_result['total_co2']),
            ets_price_eur=float(calc_result['cbam_tax_eur']) / float(calc_result['total_co2']),
            cbam_tax_eur=float(calc_result['cbam_tax_eur']),
            cbam_tax_inr=float(calc_result['cbam_tax_inr']),
            calculation_date=datetime.now().strftime('%Y-%m-%d %H:%M'),
            report_id=generate_report_id(),
            methodology=calc_result.get('methodology', 'CBAM Default Values + GLEC Framework'),
            sources=calc_result.get('sources', ['IPCC EFDB', 'GLEC Framework v3.0'])
        )
        
        return self.generate_pdf(data)


# API function for easy use
def generate_cbam_report(
    product_type: str,
    weight_tonnes: float,
    emissions: dict,
    cbam_tax: dict,
    exporter_info: dict,
    route_info: dict
) -> str:
    """
    Quick function to generate CBAM PDF report
    
    Returns: Path to generated PDF file
    """
    generator = CBAMReportGenerator()
    
    data = CBAMReportData(
        exporter_name=exporter_info.get('name', 'Test Company'),
        exporter_address=exporter_info.get('address', 'Mumbai, India'),
        exporter_gstin=exporter_info.get('gstin', 'XXXXXXXXXXXXX'),
        product_type=product_type,
        product_cn_code=exporter_info.get('cn_code', '7208'),
        weight_tonnes=weight_tonnes,
        origin_port=route_info.get('origin', 'Mumbai'),
        destination_port=route_info.get('destination', 'Rotterdam'),
        route_name=route_info.get('name', 'Suez Canal'),
        manufacturing_co2=emissions['manufacturing'],
        transport_co2=emissions['transport'],
        port_handling_co2=emissions['port_handling'],
        total_co2=emissions['total'],
        ets_price_eur=cbam_tax['ets_price'],
        cbam_tax_eur=cbam_tax['eur'],
        cbam_tax_inr=cbam_tax['inr'],
        calculation_date=datetime.now().strftime('%Y-%m-%d %H:%M'),
        report_id=generate_report_id(),
        methodology='CBAM Default Values + GLEC Framework',
        sources=['IPCC Emission Factor Database', 'GLEC Framework v3.0', 'EU ETS']
    )
    
    return generator.generate_pdf(data)


if __name__ == "__main__":
    # Test report generation
    print("=" * 50)
    print("CBAM REPORT GENERATOR TEST")
    print("=" * 50)
    
    if not REPORTLAB_AVAILABLE:
        print("Install reportlab: pip install reportlab")
    else:
        # Sample data
        test_data = CBAMReportData(
            exporter_name="Steel Exports Pvt Ltd",
            exporter_address="123 Industrial Area, Mumbai 400001, India",
            exporter_gstin="27AABCU9603R1ZM",
            product_type="steel_hot_rolled",
            product_cn_code="7208",
            weight_tonnes=100.0,
            origin_port="Mumbai (Mundra)",
            destination_port="Rotterdam, Netherlands",
            route_name="Mumbai → Rotterdam (Suez Canal)",
            manufacturing_co2=185.0,
            transport_co2=18.776,
            port_handling_co2=2.7,
            total_co2=206.476,
            ets_price_eur=85.0,
            cbam_tax_eur=17550.46,
            cbam_tax_inr=1579541.4,
            calculation_date=datetime.now().strftime('%Y-%m-%d %H:%M'),
            report_id=generate_report_id(),
            methodology="CBAM Default Values + GLEC Framework",
            sources=["IPCC Emission Factor Database", "GLEC Framework v3.0", "EU ETS"]
        )
        
        generator = CBAMReportGenerator()
        filepath = generator.generate_pdf(test_data)
        print(f"\n✅ Report generated: {filepath}")
