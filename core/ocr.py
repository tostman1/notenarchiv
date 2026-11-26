"""Local bounded OCR evidence over immutable PDF bytes."""

import hashlib
import json
import re
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from core.pdf import Processor


class OcrError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class Profile:
    languages: str = "deu+eng"
    dpi: int = 300
    max_pages: int = 3
    region_timeout: int = 60
    document_timeout: int = 240
    max_words: int = 512
    version: str = "heading-v1"

    def __post_init__(self):
        if not re.fullmatch(r"[a-z]{3}(?:\+[a-z]{3}){0,3}", self.languages):
            raise ValueError("Invalid OCR languages")
        for name, low, high in (
            ("dpi", 150, 300), ("max_pages", 1, 3), ("region_timeout", 1, 60),
            ("document_timeout", 1, 300), ("max_words", 1, 512),
        ):
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError("Invalid OCR profile limit")
        if self.version != "heading-v1":
            raise ValueError("Unsupported OCR profile")


def _file_hash(path, checkpoint):
    digest, total = hashlib.sha256(), 0
    with path.open("rb") as stream:
        before = path.stat()
        while chunk := stream.read(1_048_576):
            checkpoint()
            total += len(chunk)
            if total > 67_108_864:
                raise OcrError("RUNTIME_LIMIT")
            digest.update(chunk)
        after = path.stat()
    if total == 0 or (before.st_size, before.st_mtime_ns, before.st_ino) != (
        after.st_size, after.st_mtime_ns, after.st_ino
    ):
        raise OcrError("RUNTIME_CHANGED")
    return digest.hexdigest()


class Engine:
    """Caller supplies trusted executable, language data and private scratch."""

    def __init__(self, scratch, executable, tessdata, *, profile=None, checkpoint=lambda: None):
        self.processor = Processor(scratch, checkpoint=checkpoint)
        self.profile = profile or Profile()
        self.checkpoint = checkpoint
        try:
            self.executable = Path(executable).resolve(strict=True)
            self.tessdata = Path(tessdata).resolve(strict=True)
            runtime = {"executable": _file_hash(self.executable, checkpoint)}
            for language in self.profile.languages.split("+"):
                runtime[language] = _file_hash(self.tessdata / f"{language}.traineddata", checkpoint)
        except OSError:
            raise OcrError("RUNTIME_UNAVAILABLE") from None
        self.profile_key = hashlib.sha256(
            json.dumps({"profile": asdict(self.profile), "runtime": runtime}, sort_keys=True).encode()
        ).hexdigest()

    def cache_key(self, sha256, rule_version):
        if not re.fullmatch("[0-9a-f]{64}", sha256) or not isinstance(rule_version, str) or len(rule_version) > 80:
            raise ValueError("Invalid OCR cache identity")
        return hashlib.sha256(f"{sha256}/{self.profile_key}/{rule_version}".encode()).hexdigest()

    def analyze(self, data, *, rule_version):
        if not isinstance(data, bytes) or not 0 < len(data) <= self.processor.limits.max_bytes:
            raise OcrError("INPUT_LIMIT")
        deadline = time.monotonic() + self.profile.document_timeout

        def checkpoint():
            self.checkpoint()
            if time.monotonic() >= deadline:
                raise OcrError("TIMEOUT")

        processor = Processor(self.processor.root, limits=self.processor.limits, checkpoint=checkpoint)
        document = processor.inspect(data)
        key = self.cache_key(document.sha256, rule_version)
        regions = []
        with tempfile.TemporaryDirectory(prefix="ocr-", dir=processor.root) as directory:
            stage = Path(directory)
            for page in range(min(len(document.pages), self.profile.max_pages)):
                checkpoint()
                image = processor.render(data, page, dpi=self.profile.dpi)
                (stage / "input.png").write_bytes(image)
                evidence = self._region(stage, page, 0.3, checkpoint)
                regions.append(evidence)
                if len(evidence["words"]) < 3:
                    regions.append(self._region(stage, page, 0.7, checkpoint))
        return {"cache_key": key, "sha256": document.sha256, "profile": self.profile_key, "regions": regions}
