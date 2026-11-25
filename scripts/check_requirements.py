"""Bounded structural traceability checks; semantic coverage remains review work."""

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENT = r"(?:GR|UI|AR|CAT|PR|AS|EX|SC|PT|OP)-[0-9]{2}"
EXPECTED_ALIASES = {
    f"{family}-{number:02}"
    for family, count in (("EXT", 18), ("FUT", 7), ("REF", 36))
    for number in range(1, count + 1)
}


def validate(requirements, plan, architecture, crosswalk, *, root=ROOT):
    errors = []
    definitions = re.findall(rf"^\| ({REQUIREMENT}) \|", requirements, re.M)
    definitions += re.findall(rf"^- \*\*({REQUIREMENT}):\*\*", requirements, re.M)
    counts = Counter(definitions)
    for identifier, count in sorted(counts.items()):
        if count != 1:
            errors.append(f"Duplicate requirement definition: {identifier}")
    aliases = re.findall(r"^\| ((?:EXT|FUT|REF)-[0-9]{2})\b", crosswalk, re.M)
    for row in re.findall(r"^\| (?:EXT|FUT|REF)-[0-9]{2}\b.*$", crosswalk, re.M):
        if not re.search(REQUIREMENT, row) or not re.search(r"WP-[0-9]{2}", row):
            errors.append(f"Incomplete alias mapping: {row.split('|')[1].strip()}")
    alias_counts = Counter(aliases)
    for alias in sorted(EXPECTED_ALIASES | set(aliases)):
        if alias_counts[alias] != 1 or alias not in EXPECTED_ALIASES:
            errors.append(f"Missing, duplicate or unexpected source alias: {alias}")
    for identifier in sorted(set(re.findall(REQUIREMENT, crosswalk)) - counts.keys()):
        errors.append(f"Undefined canonical requirement: {identifier}")
    work_packages = set(re.findall(r"^### (WP-[0-9]{2}[a-z]?)\b", plan, re.M))
    work_packages.update(re.findall(r"^\| (WP-[0-9]{2}[a-z]?) \|", plan, re.M))
    families = {re.match(r"WP-[0-9]{2}", item).group() for item in work_packages}
    for identifier in sorted(set(re.findall(r"WP-[0-9]{2}[a-z]?", crosswalk))):
        if identifier not in work_packages and identifier not in families:
            errors.append(f"Undefined work package: {identifier}")
    for name, document in (("requirements", requirements), ("plan", plan), ("architecture", architecture)):
        headings = Counter(re.findall(r"^##? .+$", document, re.M))
        for heading, count in headings.items():
            if count > 1:
                errors.append(f"Duplicate {name} heading: {heading}")
    for path in sorted(set(re.findall(r"tests/[a-zA-Z0-9_]+\.py", crosswalk))):
        if not (root / path).is_file():
            errors.append(f"Missing evidence file: {path}")
    return {
        "result": "mismatch" if errors else "success",
        "requirement_definitions": len(definitions),
        "source_aliases": len(aliases),
        "error_count": len(errors),
        "errors": [error[:240] for error in errors[:100]],
    }


def main():
    try:
        documents = []
        for name in ("REQUIREMENTS.md", "IMPLEMENTATION_PLAN.md", "ARCHITECTURE.md", "docs/REQUIREMENTS_CROSSWALK.md"):
            path = ROOT / name
            if path.stat().st_size > 2_097_152:
                raise ValueError("Traceability input exceeds limit")
            documents.append(path.read_text(encoding="utf-8"))
        result = validate(*documents)
    except (OSError, ValueError):
        result = {"result": "mismatch", "errors": ["Traceability inputs unavailable or invalid"]}
    print(json.dumps(result, separators=(",", ":")))  # noqa: T201
    return 0 if result["result"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
