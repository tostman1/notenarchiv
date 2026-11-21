"""Build future install bundles without changing existing releases or source files."""

import argparse
import gzip
import io
import re
import tarfile
from pathlib import Path

FILES = (
    "configuration.yaml",
    "compose.yaml",
    "compose.debug.yaml",
    ".env.example",
    "scripts/prepare-install.sh",
    "scripts/preflight-host.sh",
    "docs/INSTALL.de.md",
    "docs/INSTALL.md",
    "docs/UPDATE.md",
    "docs/RESTORE.md",
    "docs/DEBUG_MODE.md",
    "docs/archivist-diagnostics.de.md",
    "docs/LICENSES.md",
)
_PINNED_FILES = {"configuration.yaml", "scripts/prepare-install.sh", "scripts/preflight-host.sh"}
_REFERENCE = re.compile(r"ghcr\.io/tostman1/notenarchiv@sha256:[0-9a-f]{64}")


def build_bundle(output, image, *, source=None):
    if not _REFERENCE.fullmatch(image):
        raise ValueError("An immutable Notenarchiv image digest is required")
    source = source or Path(__file__).resolve().parent.parent
    for name in FILES:
        path = source / name
        if not path.is_file() or path.is_symlink():
            raise ValueError("Installation source must be a regular file")
    pins = set()
    for name in _PINNED_FILES:
        matches = _REFERENCE.findall((source / name).read_text(encoding="utf-8"))
        if len(matches) != 1:
            raise ValueError("Expected exactly one example image reference")
        pins.add(matches[0])
    if len(pins) != 1:
        raise ValueError("Installation example image references disagree")
    original = pins.pop()
    # Exclusive creation: never overwrite even a local installation archive.
    with (
        Path(output).open("xb") as target,
        gzip.GzipFile(fileobj=target, mode="wb", mtime=0, filename="") as zipped,
        tarfile.open(fileobj=zipped, mode="w") as archive,
    ):
        for name in (*FILES, "release-digest.txt"):
            if name == "release-digest.txt":
                data = (image + "\n").encode("ascii")
            else:
                path = source / name
                data = path.read_bytes()
                if name in _PINNED_FILES:
                    if data.count(original.encode()) != 1:
                        raise ValueError("Expected exactly one example image reference")
                    data = data.replace(original.encode(), image.encode())
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(data), 0o644, 0
            archive.addfile(info, io.BytesIO(data))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--digest-file", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    build_bundle(arguments.output, arguments.digest_file.read_text(encoding="ascii").strip())


if __name__ == "__main__":
    main()
