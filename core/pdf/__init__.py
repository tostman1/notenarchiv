"""Safe PDF primitives. Callers own authorization, snapshots and publication."""

from core.pdf.api import Processor
from core.pdf.types import DocumentInfo, Limits, PageInfo, PdfError, Selection

__all__ = ["DocumentInfo", "Limits", "PageInfo", "PdfError", "Processor", "Selection"]
