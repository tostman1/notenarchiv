"""Real non-root image publication against new synthetic mounts only (Linux CI)."""

import argparse
import base64
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

from scripts.container_smoke import GID, UID, arguments, docker, prepare, raw_negatives


def smoke(image, root):
    paths = prepare(root)
    # Only this newly created disposable fixture. Never change existing installs.
    for name in ("clean", "processed", "status", "export"):
        os.chown(paths[name], UID, GID)
        paths[name].chmod(0o750)
    scenario = Path("tests/publication_scenario.py").read_text(encoding="utf-8")

    def action(name, identities=None):
        args = ["run", "--rm", *arguments(paths, "none"), "--entrypoint", "python", image, "-c", scenario, name]
        if identities is not None:
            args.append(json.dumps(identities))
        output = docker(*args).stdout
        if name == "pdf":
            return output
        responses = [
            line.removeprefix("SCENARIO_RESULT=") for line in output.splitlines() if line.startswith("SCENARIO_RESULT=")
        ]
        assert len(responses) == 1, "Synthetic scenario did not return exactly one result"
        return responses[0]

    data = base64.b64decode(action("pdf"))
    source = paths["raw"] / "correct.pdf"
    source.write_bytes(data)
    os.chown(source, 0, GID)
    source.chmod(0o440)
    raw_negatives(image, paths, "none")
    before = {
        path.name: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
        for path in paths["raw"].iterdir()
    }
    docker("run", "--rm", *arguments(paths, "none"), image, "migrate")
    identities = json.loads(action("setup"))
    unsafe = docker(
        "run",
        "--rm",
        *arguments(paths, "none", service="worker", raw_readonly=False),
        "--entrypoint",
        "python",
        image,
        "manage.py",
        "run_worker",
        "--once",
        check=False,
    )
    assert unsafe.returncode != 0, "Worker accepted writable RAW"

    def worker():
        result = docker(
            "run",
            "--rm",
            *arguments(paths, "none", service="worker"),
            "--entrypoint",
            "python",
            image,
            "manage.py",
            "run_worker",
            "--once",
        )
        assert "synthetic-publication-reviewer" not in result.stdout + result.stderr

    worker()
    copied = json.loads(action("check-copy", identities))
    identities = json.loads(action("review", identities))
    worker()
    approved = json.loads(action("check-approved", identities))
    assert copied["path"] != approved["path"] and approved["operations"] == 2
    assert (paths["clean"] / copied["path"]).read_bytes() == data
    assert (paths["clean"] / approved["path"]).read_bytes() == data
    after = {
        path.name: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
        for path in paths["raw"].iterdir()
    }
    assert before == after
    assert not list(paths["status"].iterdir())  # STATUS publication belongs to WP-15.
    assert not list((paths["clean"] / ".staging").rglob("*.pdf"))
    assert (paths["clean"] / approved["path"]).stat().st_uid == UID
    sys.stdout.write(
        "PASS: actual non-root worker, read-only RAW/host permissions, verified independent copy, "
        "explicit multi-part approval, canonical publication, retained history, no network\n"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    args = parser.parse_args()
    if os.name != "posix" or os.geteuid() != 0:
        parser.error("Run only as root on isolated Linux Docker CI with new synthetic fixtures")
    with tempfile.TemporaryDirectory(prefix="notenarchiv-publication-") as directory:
        smoke(args.image, Path(directory))


if __name__ == "__main__":
    main()
