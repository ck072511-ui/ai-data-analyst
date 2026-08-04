import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import Any, Dict
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors

class PDFReportGenerator:
    @staticmethod
    def generate(file_path: str, data: Dict[str, Any], branding: Dict[str, Any]):
        """Builds a multi-section structured PDF document using ReportLab flowables."""
        doc = SimpleDocTemplate(file_path, pagesize=letter)
        styles = getSampleStyleSheet()

        # Custom paragraph styles
        title_style = ParagraphStyle(
            'CoverTitle',
            parent=styles['Title'],
            fontName='Helvetica-Bold',
            fontSize=28,
            leading=34,
            textColor=colors.HexColor('#1e3a8a'),
            alignment=1, # center
            spaceAfter=20
        )
        subtitle_style = ParagraphStyle(
            'CoverSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=14,
            leading=18,
            textColor=colors.HexColor('#64748b'),
            alignment=1,
            spaceAfter=50
        )
        h1_style = ParagraphStyle(
            'SectionH1',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=18,
            leading=22,
            textColor=colors.HexColor('#1e3a8a'),
            spaceBefore=15,
            spaceAfter=10
        )
        body_style = ParagraphStyle(
            'SectionBody',
            parent=styles['BodyText'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#334155'),
            spaceAfter=8
        )

        story = []

        # 1. Cover Page
        story.append(Spacer(1, 100))
        story.append(Paragraph(data.get("title", "Enterprise Analytics Report"), title_style))
        story.append(Paragraph(f"Sub-header Summary | Compiled Offline with Local LLMs", subtitle_style))
        
        company_name = branding.get("company_name", "Enterprise Systems")
        version = branding.get("version", "1.0.0")
        story.append(Paragraph(f"<b>Organization:</b> {company_name}", body_style))
        story.append(Paragraph(f"<b>Report Version:</b> {version}", body_style))
        story.append(Paragraph(f"<b>Timestamp:</b> {data.get('timestamp')}", body_style))
        story.append(Spacer(1, 40))

        # 2. Executive Summary
        story.append(Paragraph("Executive Summary", h1_style))
        story.append(Paragraph(data.get("final_answer", "Analyzed dataset metrics successfully."), body_style))
        story.append(Spacer(1, 15))

        # 3. KPIs
        story.append(Paragraph("Key Performance Indicators", h1_style))
        kpis = data.get("kpis", [])
        if kpis:
            kpi_data = [["Indicator", "Value"]]
            for k in kpis[:4]:
                kpi_data.append([k.get("title", ""), str(k.get("value", ""))])
            
            kpi_table = Table(kpi_data, colWidths=[200, 150])
            kpi_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (1,0), colors.HexColor('#1e3a8a')),
                ('TEXTCOLOR', (0,0), (1,0), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1'))
            ]))
            story.append(kpi_table)
        else:
            story.append(Paragraph("No KPIs recommended for this dataset view.", body_style))
        story.append(Spacer(1, 15))

        # 4. Embedded Matplotlib Chart
        story.append(Paragraph("Visualized Trend Line", h1_style))
        chart_img_path = f"{file_path}.png"
        try:
            plt.figure(figsize=(6, 3))
            plt.plot([1, 2, 3, 4], [10, 20, 25, 30], label="Sales Value", marker='o', color='#1e3a8a')
            plt.title("Sample Performance Metrics Trend")
            plt.grid(True)
            plt.legend()
            plt.tight_layout()
            plt.savefig(chart_img_path)
            plt.close()
            
            story.append(Image(chart_img_path, width=400, height=200))
        except Exception as e:
            story.append(Paragraph(f"Failed to generate chart graphic: {e}", body_style))
        story.append(Spacer(1, 15))

        # 5. AI Insights & SQL Summary
        story.append(Paragraph("AI Business Insights & SQL Context", h1_style))
        insights = data.get("insights", [])
        for ins in insights[:3]:
            story.append(Paragraph(f"• {ins}", body_style))
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"<b>Executed SQL Query:</b> {data.get('sql', 'No query run.')}", body_style))
        story.append(Spacer(1, 15))

        # 6. Citations & RAG Evidence
        story.append(Paragraph("Cited Offline Sources", h1_style))
        citations = data.get("citations", [])
        if citations:
            for c in citations[:2]:
                story.append(Paragraph(f"<i>Source: {c.get('filename')} (Pg {c.get('page_number')})</i> - {c.get('text_content')}", body_style))
        else:
            story.append(Paragraph("No document citations cited for this summary answer.", body_style))

        # Build PDF
        doc.build(story)
        
        # Cleanup temp chart image
        if os.path.exists(chart_img_path):
            try:
                os.remove(chart_img_path)
            except:
                pass
