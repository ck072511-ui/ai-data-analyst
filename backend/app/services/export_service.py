import tempfile
from io import BytesIO
from typing import Any, Dict

from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


class ExportService:
    async def export_to_pdf(self, data: Dict[str, Any]) -> str:
        buffer = BytesIO()
        report = canvas.Canvas(buffer, pagesize=letter)
        report.drawString(72, 750, "AI Data Analyst Report")
        report.drawString(72, 730, f"Rows: {len(data.get('data', []))}")
        report.save()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as output:
            output.write(buffer.getvalue())
            return output.name

    async def export_to_excel(self, data: Dict[str, Any]) -> str:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as output:
            workbook = Workbook()
            worksheet = workbook.active
            rows = data.get("data", [])
            if rows:
                headers = list(rows[0].keys())
                worksheet.append(headers)
                for row in rows:
                    worksheet.append([row.get(header) for header in headers])
            workbook.save(output.name)
            return output.name
