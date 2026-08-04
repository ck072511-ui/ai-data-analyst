import os
import sys
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# Adjust path to find backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set environment variables for testing
os.environ["DATABASE_URL"] = "sqlite:///./test_analytics.db"
os.environ["SECRET_KEY"] = "test-secret-key-must-be-long-enough-32-chars-at-least"
os.environ["ENVIRONMENT"] = "development"

from app.services.pdf_report_generator import PDFReportGenerator
from app.services.docx_report_generator import DOCXReportGenerator
from app.services.pptx_report_generator import PPTXReportGenerator
from app.services.report_service import ReportService


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_pdf_compilation():
    file_path = "test_doc_output.pdf"
    data = {
        "title": "Test PDF Report Title",
        "timestamp": "2026-07-28 12:00:00 UTC",
        "final_answer": "Final grounding test.",
        "kpis": [{"title": "Indicator X", "value": 45}],
        "sql": "SELECT 1",
        "citations": [{"filename": "doc.pdf", "page_number": 1, "text_content": "some text"}],
        "insights": ["Insight 1"]
    }
    branding = {"company_name": "Test Company", "version": "1.0.0"}

    # Generate
    PDFReportGenerator.generate(file_path, data, branding)

    assert os.path.exists(file_path)
    assert os.path.getsize(file_path) > 0

    # Cleanup
    if os.path.exists(file_path):
        os.remove(file_path)


def test_docx_compilation():
    file_path = "test_doc_output.docx"
    data = {
        "title": "Test DOCX Report Title",
        "timestamp": "2026-07-28 12:00:00 UTC",
        "final_answer": "Final grounding test.",
        "kpis": [{"title": "Indicator X", "value": 45}],
        "sql": "SELECT 1",
        "citations": [{"filename": "doc.docx", "page_number": 1, "text_content": "some text"}],
        "insights": ["Insight 1"]
    }
    branding = {"company_name": "Test Company", "version": "1.0.0"}

    # Generate
    DOCXReportGenerator.generate(file_path, data, branding)

    assert os.path.exists(file_path)
    assert os.path.getsize(file_path) > 0

    # Cleanup
    if os.path.exists(file_path):
        os.remove(file_path)


def test_pptx_compilation():
    file_path = "test_doc_output.pptx"
    data = {
        "title": "Test PPTX Slide Title",
        "timestamp": "2026-07-28 12:00:00 UTC",
        "final_answer": "Final grounding test.",
        "kpis": [{"title": "Indicator X", "value": 45}],
        "sql": "SELECT 1",
        "citations": [{"filename": "doc.pptx", "page_number": 1, "text_content": "some text"}],
        "insights": ["Insight 1"]
    }
    branding = {"company_name": "Test Company", "version": "1.0.0"}

    # Generate
    PPTXReportGenerator.generate(file_path, data, branding)

    assert os.path.exists(file_path)
    assert os.path.getsize(file_path) > 0

    # Cleanup
    if os.path.exists(file_path):
        os.remove(file_path)


@pytest.mark.anyio
async def test_report_service_async_trigger(anyio_backend):
    service = ReportService()
    
    mock_report = MagicMock()
    mock_report.id = "report-uuid"
    mock_report.title = "Executive Report Analysis Summary"
    mock_report.report_type = "executive"
    mock_report.file_format = "pdf"
    mock_report.branding = {"company_name": "Test Company"}
    mock_report.status = "pending"

    with patch("app.services.report_service.AsyncSessionLocal") as mock_session_class:
        mock_session = AsyncMock()
        mock_session_class.return_value.__aenter__.return_value = mock_session

        res = await service.trigger_generation(
            execution_id="exec-uuid",
            report_type="executive",
            file_format="pdf",
            branding={"company_name": "Test Company"},
            user_id="user-uuid"
        )

        assert res["title"] == "Executive Analysis Summary"
        assert res["status"] == "pending"
