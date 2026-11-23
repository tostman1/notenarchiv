"""Fail-closed docs classification: deployment/security docs are always full scope."""
# ruff: noqa: T201

import subprocess
import sys

HARMLESS = {"docs/PROGRESS.md", "tests/TRACEABILITY.md"}


def docs_only(paths):
    return bool(paths) and all(path in HARMLESS for path in paths)


if __name__ == "__main__":
    paths = subprocess.check_output(["git", "diff", "--name-only", sys.argv[1], sys.argv[2]], text=True).splitlines()
    print("docs-only=" + str(docs_only(paths)).lower())
