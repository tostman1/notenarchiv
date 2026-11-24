"""Distribute only a real verified digest; source candidates are fail-closed."""

import argparse
import gzip
import io
import re
import tarfile
from pathlib import Path

FILES = ("compose.yaml", "prepare.sh", "verify-host.sh", "README.de.md", "demo.py")
CANDIDATE = "${VERIFIED_TEST_IMAGE:?Publication pending - use the verified installation bundle}"


def contents(image, source=None):
    if not re.fullmatch(r"ghcr\.io/tostman1/notenarchiv@sha256:[0-9a-f]{64}", image):
        raise ValueError("A verified published immutable digest is mandatory")
    source = source or Path(__file__).resolve().parent.parent / "deploy/synology-test"
    result = {}
    for name in FILES:
        path = source / name
        if not path.is_file() or path.is_symlink():
            raise ValueError("Missing or unsafe installation source")
        result[name] = path.read_bytes()
    template = result["compose.yaml"].decode("utf-8")
    references = re.findall(r"ghcr\.io/tostman1/notenarchiv@sha256:[0-9a-f]{64}", template)
    if template.count(CANDIDATE) == 1 and not references:
        original = CANDIDATE
    elif len(references) == 1 and CANDIDATE not in template:
        original = references[0]
    else:
        raise ValueError("Exactly one source image reference is required")
    result["compose.yaml"] = (
        template.replace(original, image)
        .replace(
            "# NOT INSTALLABLE YET: publication is gated by full-stack CI. Packaging replaces\n"
            "# this fail-closed build input with the verified published digest, never a guessed tag.\n",
            "# Published test-only image pinned by verified immutable digest.\n",
        )
        .encode("utf-8")
    )
    result["release-digest.txt"] = (image + "\n").encode("ascii")
    return result


def build(output, image):
    files = contents(image)
    with (
        Path(output).open("xb") as target,
        gzip.GzipFile(fileobj=target, mode="wb", mtime=0, filename="") as zipped,
        tarfile.open(fileobj=zipped, mode="w") as archive,
    ):
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(data), 0o644, 0
            archive.addfile(info, io.BytesIO(data))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--digest-file", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    build(args.output, args.digest_file.read_text(encoding="ascii").strip())
