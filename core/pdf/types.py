"""Explicit bounded PDF contracts, independent of Django and archive state."""

from dataclasses import dataclass


class PdfError(ValueError):
    """Fixed codes only: never include document content or parser exception text."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class Limits:
    max_bytes: int = 104_857_600
    max_pages: int = 500
    max_pixels: int = 30_000_000
    max_text_chars: int = 1_000_000
    max_output_bytes: int = 104_857_600
    memory_bytes: int = 402_653_184
    cpu_seconds: int = 30
    timeout_seconds: int = 60

    def __post_init__(self):
        bounds = {
            "max_bytes": (1024, 104_857_600),
            "max_pages": (1, 1000),
            "max_pixels": (1, 30_000_000),
            "max_text_chars": (1, 1_000_000),
            "max_output_bytes": (1024, 104_857_600),
            "memory_bytes": (67_108_864, 536_870_912),
            "cpu_seconds": (1, 120),
            "timeout_seconds": (1, 180),
        }
        for name, (low, high) in bounds.items():
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError("Invalid PDF resource limit")


@dataclass(frozen=True)
class PageInfo:
    media_box: tuple[float, float, float, float]
    crop_box: tuple[float, float, float, float]
    user_unit: float
    rotation: int
    width_points: float
    height_points: float

    @property
    def size_mm(self):
        return self.width_points * 25.4 / 72, self.height_points * 25.4 / 72

    @property
    def paper(self):
        short, long = sorted(self.size_mm)
        for name, width, height in (("A4", 210, 297), ("A3", 297, 420)):
            if abs(short - width) <= 2 and abs(long - height) <= 2:
                return name
        return "CUSTOM"


@dataclass(frozen=True)
class SourcePageGeometry:
    """Opt-in parser geometry; not part of legacy inspection IPC or manifests.

    PageInfo.crop_box remains effective. Original CropBox must come from the
    exact source page, never reconstruction from legacy metadata.
    """

    page_info: PageInfo
    original_crop_box: tuple[float, float, float, float]


@dataclass(frozen=True)
class DocumentInfo:
    sha256: str
    pages: tuple[PageInfo, ...]
    text: tuple[str, ...] | None = None


@dataclass(frozen=True)
class Selection:
    data: bytes
    # Zero-based explicit order; None selects every page. Repetitions are explicit.
    pages: tuple[int, ...] | None = None
