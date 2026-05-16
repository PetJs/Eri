"""Shared pytest fixtures for the Eri backend test suite."""
from __future__ import annotations

import pytest


# Minimal valid PDF (magic bytes + structure — content mocked in all tests).
_SAMPLE_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<</Type /Catalog /Pages 2 0 R>>\nendobj\n"
    b"2 0 obj\n<</Type /Pages /Kids [3 0 R] /Count 1>>\nendobj\n"
    b"3 0 obj\n<</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]>>\nendobj\n"
    b"xref\n0 4\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"0000000115 00000 n \n"
    b"trailer\n<</Size 4 /Root 1 0 R>>\nstartxref\n195\n%%EOF\n"
)


@pytest.fixture
def sample_invoice_pdf() -> bytes:
    """Minimal PDF bytes that pass the %PDF magic-bytes check."""
    return _SAMPLE_PDF
