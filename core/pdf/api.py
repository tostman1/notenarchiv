"""Immutable byte inputs and private bounded staging around isolated parsers."""

import hashlib
import json
import os
import stat
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

from core.pdf.types import DocumentInfo, Limits, PageInfo, PdfError, Selection
from core.processes import ProcessFailed, ProcessTimeout, run_process

_CODES = {"INVALID_PDF", "ENCRYPTED_PDF", "LIMIT_EXCEEDED", "UNSUPPORTED_ANNOTATION", "INVALID_PAGE"}


class Processor:
    """One invocation stages at most 100 MiB input and one bounded output.

    Supply an existing private scratch root on bounded local storage. Archive
    callers read authorized stable snapshots; no source/destination path enters
    the PDF parser API. Returned bytes are unapproved derivatives, never CLEAN.
    """

    def __init__(self, scratch_root: Path, *, limits=None, checkpoint=lambda: None):
        root = Path(scratch_root).absolute()
        if root != root.resolve(strict=True) or not root.is_dir():
            raise ValueError("PDF scratch root must be a canonical existing directory")
        if os.name != "nt" and root.stat().st_mode & 0o077:
            raise ValueError("PDF scratch root must be private")
        self.root, self.limits, self.checkpoint = root, limits or Limits(), checkpoint

    def inspect(self, data: bytes, *, include_text=False) -> DocumentInfo:
        result = self._invoke("inspect", [data], include_text=bool(include_text))
        return DocumentInfo(
            hashlib.sha256(data).hexdigest(),
            tuple(
                PageInfo(**{**page, "media_box": tuple(page["media_box"]), "crop_box": tuple(page["crop_box"])})
                for page in result["pages"]
            ),
            tuple(result["text"]) if include_text else None,
        )

    def extract_text(self, data: bytes) -> tuple[str, ...]:
        return self.inspect(data, include_text=True).text

    def render(self, data: bytes, page=0, *, dpi=144) -> bytes:
        if type(dpi) is not int or not 1 <= dpi <= 600:
            raise ValueError("PDF rendering DPI must be between 1 and 600")
        return self._invoke("render", [data], page=self._page(page), dpi=dpi)

    def thumbnail(self, data: bytes, page=0, *, max_edge=256) -> bytes:
        if type(max_edge) is not int or not 1 <= max_edge <= 2048:
            raise ValueError("PDF thumbnail edge must be between 1 and 2048")
        return self._invoke("render", [data], page=self._page(page), max_edge=max_edge)

    def merge(self, selections: tuple[Selection, ...]) -> bytes:
        if not isinstance(selections, (list, tuple)) or not 1 <= len(selections) <= 16:
            raise ValueError("Select between 1 and 16 PDF inputs")
        pages = []
        for selection in selections:
            if not isinstance(selection, Selection):
                raise TypeError("Expected PDF selections")
            if selection.pages is not None:
                if not isinstance(selection.pages, tuple) or not 1 <= len(selection.pages) <= self.limits.max_pages:
                    raise ValueError("Invalid PDF selection size")
                pages.append([self._page(page) for page in selection.pages])
            else:
                pages.append(None)
        return self._invoke("merge", [selection.data for selection in selections], selections=pages)

    def _page(self, page):
        if type(page) is not int or not 0 <= page < self.limits.max_pages:
            raise ValueError("Invalid PDF page index")
        return page

    def _invoke(self, operation, inputs, **options):
        total = 0
        for data in inputs:
            if not isinstance(data, bytes):
                raise TypeError("PDF inputs must be immutable bytes")
            total += len(data)
            if not data or total > self.limits.max_bytes:
                raise PdfError("LIMIT_EXCEEDED")
        self.checkpoint()
        with tempfile.TemporaryDirectory(prefix="pdf-", dir=self.root) as directory:
            stage = Path(directory)
            for index, data in enumerate(inputs):
                self.checkpoint()
                self._write(stage / f"{index}.pdf", data)
            self._write(
                stage / "request.json",
                json.dumps(
                    {"operation": operation, "inputs": len(inputs), "limits": asdict(self.limits), **options}
                ).encode("utf-8"),
            )
            try:
                run_process(
                    [sys.executable, "-m", "core.pdf._worker", str(stage)],
                    timeout=self.limits.timeout_seconds,
                    memory_bytes=self.limits.memory_bytes,
                    cpu_seconds=self.limits.cpu_seconds,
                    file_bytes=max(self.limits.max_output_bytes, 8_388_608),
                    checkpoint=self.checkpoint,
                )
            except ProcessTimeout:
                raise PdfError("TIMEOUT") from None
            except ProcessFailed:
                raise PdfError("PROCESS_FAILED") from None
            response = self._read(stage / "response.json", 8_388_608)
            try:
                result = json.loads(response)
            except (ValueError, UnicodeError):
                raise PdfError("PROCESS_FAILED") from None
            if result.get("error"):
                raise PdfError(result["error"] if result["error"] in _CODES else "PROCESS_FAILED")
            self.checkpoint()
            if operation == "inspect":
                return result
            return self._read(stage / "output", self.limits.max_output_bytes)

    @staticmethod
    def _write(path, data):
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)

    @staticmethod
    def _read(path, maximum):
        try:
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
                raise PdfError("LIMIT_EXCEEDED")
            with path.open("rb") as stream:
                data = stream.read(maximum + 1)
            if len(data) > maximum:
                raise PdfError("LIMIT_EXCEEDED")
            return data
        except OSError:
            raise PdfError("PROCESS_FAILED") from None
