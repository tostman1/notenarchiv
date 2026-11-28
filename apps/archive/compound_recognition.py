"""Conservative compound-heading observations; never segmentation or approval."""

import math
from dataclasses import dataclass
from uuid import UUID

from apps.archive.recognition import WORK_AMBIGUOUS, match_work
from core.recognition import normalize

MAX_WORDS = 2048
MAX_HEADINGS = 128


@dataclass(frozen=True)
class Heading:
    text: str
    work_id: UUID | None
    ambiguous: bool
    page: int
    box: tuple


def headings(evidence, rules):
    """Find exact catalog headings with their rendered-selection pixel locations.

    Locations are NOT source-PDF rectangles: they refer to the OCR selection's
    rendered image, including its rotation. Repeated headings remain distinct.
    No continuation, blank, page-size or musical boundary is inferred here.
    """
    words = evidence.get("words", [])
    if not isinstance(words, list) or len(words) > MAX_WORDS:
        raise ValueError("Invalid compound evidence size")
    page = evidence.get("page")
    if type(page) is not int or not 0 <= page < 500:
        raise ValueError("Invalid compound evidence page")
    lines = []
    for word in words:
        # Immutable OCR evidence can predate native line identities. Do not
        # guess grouping for those rows: the ordinary evidence stays visible.
        if not isinstance(word, dict):
            raise ValueError("Invalid compound word")
        identity = word.get("line")
        if identity is None:
            continue
        box = word.get("box")
        text = word.get("text")
        if (
            not isinstance(identity, list)
            or len(identity) != 4
            or any(type(value) is not int or not 0 <= value <= 100000 for value in identity)
            or not isinstance(text, str)
            or len(text) > 512
            or not isinstance(box, list)
            or len(box) != 4
            or any(
                type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 100000 for value in box
            )
            or box[0] >= box[2]
            or box[1] >= box[3]
        ):
            raise ValueError("Invalid compound word geometry")
        if not lines or lines[-1][0] != identity:
            lines.append([identity, [], []])
        lines[-1][1].append(word["text"])
        lines[-1][2].append(word["box"])
    found = []
    for _, texts, boxes in lines:
        text = " ".join(texts)
        key = normalize(text)
        if key not in rules.works and key not in rules.work_aliases:
            continue
        work_id, exact = match_work(text, rules)
        ambiguous = work_id == WORK_AMBIGUOUS
        if not exact and not ambiguous:
            continue
        box = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
        found.append(Heading(text, None if ambiguous else work_id, ambiguous, page, box))
        if len(found) == MAX_HEADINGS:
            break
    return found
