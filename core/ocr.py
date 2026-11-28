"""Local OCR of verified immutable pages; evidence never approves music.

Tesseract's CLI is used through the existing owned process runner rather than
pytesseract's separate subprocess lifecycle. No shell or public text output.
"""

import csv
import hashlib
import io
import json
import math
import re
from dataclasses import asdict, dataclass
from importlib.metadata import version
from pathlib import Path

from core.pdf import Processor
from core.pdf.recovery import PARSER_ACTIVE_MARKER
from core.processes import ProcessFailed, ProcessTimeout, run_process


class OcrError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def parse_tsv(data, *, maximum=2048):
    """Bounded word evidence in rendered-selection pixels, top-left origin."""
    if not isinstance(data, bytes) or len(data) > 4_194_304:
        raise OcrError("OUTPUT_LIMIT")
    try:
        reader = csv.DictReader(io.StringIO(data.decode("utf-8")), delimiter="\t")
        required = {"level", "left", "top", "width", "height", "conf", "text"}
        if not required <= set(reader.fieldnames or ()):
            raise ValueError
        words = []
        for row in reader:
            if row["level"] != "5":
                continue
            if not isinstance(row["text"], str):
                raise ValueError
            if not row["text"].strip():
                continue
            if len(words) >= maximum:
                raise OcrError("OUTPUT_LIMIT")
            x, y, w, h = (int(row[k]) for k in ("left", "top", "width", "height"))
            confidence = float(row["conf"])
            if min(x, y) < 0 or min(w, h) <= 0 or max(x + w, y + h) > 100000:
                raise ValueError
            if not math.isfinite(confidence) or not 0 <= confidence <= 100 or len(row["text"]) > 512:
                raise ValueError
            word = {"text": row["text"], "box": [x, y, x + w, y + h], "confidence": confidence / 100}
            line_fields = ("page_num", "block_num", "par_num", "line_num")
            if set(line_fields) <= set(reader.fieldnames):
                line = [int(row[field]) for field in line_fields]
                if any(not 0 <= identifier <= 100000 for identifier in line):
                    raise ValueError
                word["line"] = line
            words.append(word)
        return words
    except OcrError:
        raise
    except (ValueError, KeyError, TypeError, csv.Error):
        raise OcrError("INVALID_OUTPUT") from None


@dataclass(frozen=True)
class Profile:
    languages: str = "deu+eng"
    dpi: int = 200
    timeout: int = 60
    max_words: int = 2048
    version: str = "page-v2"

    def __post_init__(self):
        if not re.fullmatch(r"[a-z]{3}(?:\+[a-z]{3}){0,3}", self.languages):
            raise ValueError("Invalid OCR languages")
        for name, low, high in (("dpi", 100, 300), ("timeout", 1, 60), ("max_words", 1, 2048)):
            if type(getattr(self, name)) is not int or not low <= getattr(self, name) <= high:
                raise ValueError("Invalid OCR profile limit")
        if self.version != "page-v2":
            raise ValueError("Unsupported OCR profile")


def _runtime_hash(path, checkpoint):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        before = path.stat()
        if not 0 < before.st_size <= 67_108_864:
            raise OcrError("RUNTIME_LIMIT")
        total = 0
        while chunk := stream.read(1_048_576):
            checkpoint()
            total += len(chunk)
            if total > 67_108_864:
                raise OcrError("RUNTIME_LIMIT")
            digest.update(chunk)
        after = path.stat()
    if total != before.st_size or (before.st_size, before.st_mtime_ns, before.st_ino) != (
        after.st_size,
        after.st_mtime_ns,
        after.st_ino,
    ):
        raise OcrError("RUNTIME_CHANGED")
    return digest.hexdigest()


class Engine:
    """Trusted local runtime; one selected page/region per bounded invocation.

    Caller owns authorization, durable page scheduling, caching and progress.
    Always OCR the actual selection, even when a partial text layer exists.
    """

    def __init__(self, scratch, executable, tessdata, *, profile=None, checkpoint=lambda: None, runtime_manifest=None):
        self.processor = Processor(scratch, checkpoint=checkpoint)
        self.profile = profile or Profile()
        self.checkpoint = checkpoint
        try:
            self.executable = Path(executable).resolve(strict=True)
            self.tessdata = Path(tessdata).resolve(strict=True)
            runtime = {
                "executable": _runtime_hash(self.executable, checkpoint),
                "pdf": {name: version(name) for name in ("pypdf", "pypdfium2")},
            }
            if runtime_manifest is not None:
                # Installed versions and file checksums bind the native closure.
                runtime["native_packages"] = _runtime_hash(Path(runtime_manifest).resolve(strict=True), checkpoint)
            for language in self.profile.languages.split("+"):
                runtime[language] = _runtime_hash(self.tessdata / f"{language}.traineddata", checkpoint)
        except OSError:
            raise OcrError("RUNTIME_UNAVAILABLE") from None
        self.runtime_key = hashlib.sha256(json.dumps(runtime, sort_keys=True).encode()).hexdigest()

    def cache_key(self, sha256, *, page, bounds, orientation, revision, rules):
        if not re.fullmatch(r"[0-9a-f]{64}", sha256) or not isinstance(rules, str) or not 1 <= len(rules) <= 80:
            raise ValueError("Invalid OCR identity")
        if type(revision) is not int or revision < 1:
            raise ValueError("Invalid region revision")
        payload = {
            "sha256": sha256,
            "page": page,
            "bounds": bounds,
            "orientation": orientation,
            "revision": revision,
            "rules": rules,
            "runtime": self.runtime_key,
            "profile": asdict(self.profile),
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()

    def recognize_page(self, data, *, page, bounds=None, orientation=0, revision=1, rules):
        if not isinstance(data, bytes) or not 0 < len(data) <= self.processor.limits.max_bytes:
            raise OcrError("INPUT_LIMIT")
        if type(page) is not int or not 0 <= page < self.processor.limits.max_pages:
            raise ValueError("Invalid OCR page")
        if bounds is None:
            from core.page_geometry import PageGeometry

            document = self.processor.inspect(data, include_source_geometry=True)
            if page >= len(document.pages):
                raise OcrError("INVALID_PAGE")
            from core.pdf.types import SourcePageGeometry

            geometry = PageGeometry.from_source_page(
                SourcePageGeometry(document.pages[page], document.original_crop_boxes[page])
            )
            bounds = list(geometry.effective_points)
        selection = {"input": 0, "page": page, "bounds": bounds, "orientation": orientation}
        key = self.cache_key(
            hashlib.sha256(data).hexdigest(),
            page=page,
            bounds=bounds,
            orientation=orientation,
            revision=revision,
            rules=rules,
        )
        logical = self.processor.logical_pages([data], [selection])
        text = self.processor.extract_visible_text(logical)[0][:16384]
        image = self.processor.render(logical, 0, dpi=self.profile.dpi)
        with self.processor._workspace() as stage:
            self.processor._write(stage / "input.png", image)
            marker = stage / PARSER_ACTIVE_MARKER
            self.processor._write(marker, b"")
            try:
                run_process(
                    [
                        str(self.executable),
                        str(stage / "input.png"),
                        str(stage / "result"),
                        "--tessdata-dir",
                        str(self.tessdata),
                        "-l",
                        self.profile.languages,
                        "--psm",
                        "11",
                        "--oem",
                        "1",
                        "tsv",
                    ],
                    timeout=self.profile.timeout,
                    checkpoint=self.checkpoint,
                    memory_bytes=402_653_184,
                    cpu_seconds=self.profile.timeout,
                    file_bytes=4_194_304,
                    cwd=stage,
                    env={"OMP_THREAD_LIMIT": "2"},
                )
            except ProcessTimeout:
                raise OcrError("TIMEOUT") from None
            except ProcessFailed:
                raise OcrError("PROCESS_FAILED") from None
            else:
                marker.unlink()
            output = self.processor._read(stage / "result.tsv", 4_194_304)
            words = parse_tsv(output, maximum=self.profile.max_words)
        return {
            "cache_key": key,
            "sha256": hashlib.sha256(data).hexdigest(),
            "page": page,
            "bounds": bounds,
            "orientation": orientation,
            "revision": revision,
            "runtime": self.runtime_key,
            "profile": asdict(self.profile),
            "rules": rules,
            "text_layer": text,
            "words": words,
        }
