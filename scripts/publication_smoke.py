"""Real non-root image publication against new synthetic mounts only (Linux CI)."""

import argparse
import base64
import hashlib
import json
import os
import shutil
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
    # Full WP-47a: real copied/confirmed files and SQLite restored together in
    # hardened network-disabled containers. Only these new synthetic roots.
    private_config, independent, output = root / "config", root / "independent", root / "backup-output"
    for directory in (private_config, output):
        directory.mkdir(mode=0o700)
        os.chown(directory, UID, GID)
    (private_config / "configuration.yaml").write_text("# Synthetic private deployment configuration\n")
    os.chown(private_config / "configuration.yaml", UID, GID)
    (private_config / "configuration.yaml").chmod(0o600)
    shutil.copytree(paths["raw"], independent)
    os.chown(independent, 0, GID)
    independent.chmod(0o550)
    mounts = [
        "--mount",
        f"type=bind,src={private_config},dst=/private-config,readonly",
        "--mount",
        f"type=bind,src={independent},dst=/independent-raw,readonly",
        "--mount",
        f"type=bind,src={output},dst=/backup-output",
    ]
    backup_result = docker(
        "run",
        "--rm",
        *arguments(paths, "none"),
        *mounts,
        image,
        "backup",
        "/backup-output/bundle",
        "--config-dir",
        "/private-config",
        "--raw-backup",
        "/independent-raw",
        "--image",
        "ghcr.io/tostman1/notenarchiv@sha256:" + "a" * 64,
    )
    seal = (output / "bundle" / "manifest.sha256").read_text()
    assert seal in backup_result.stdout
    docker(
        "run",
        "--rm",
        *arguments(paths, "none"),
        *mounts,
        image,
        "restore",
        "/backup-output/bundle",
        "/backup-output/restored",
        "--manifest-sha256",
        seal,
    )
    assert (output / "restored" / "clean" / approved["path"]).read_bytes() == data
    assert (output / "restored" / "secrets" / "django.key").read_bytes() == paths["secret"].read_bytes()
    assert not (output / "restored" / "raw").exists()
    # Outputs are deliberately excluded by default. Rehearsal explicitly creates
    # a new empty isolated export root, never binds the live EXPORT location.
    (output / "restored" / "export").mkdir(mode=0o700)
    os.chown(output / "restored" / "export", UID, GID)
    restored_paths = {
        name: output / "restored" / name
        if name not in {"raw", "secret"}
        else independent
        if name == "raw"
        else output / "restored" / "secrets" / "django.key"
        for name in paths
    }
    # Reopen the restored actual ORM state and preview bytes in the image with
    # explicitly isolated mounts; never start captured production configuration.
    checked = docker(
        "run",
        "--rm",
        *arguments(restored_paths, "none"),
        "-e",
        "DATABASE_PATH=/data/database.sqlite3",
        "--entrypoint",
        "python",
        image,
        "-c",
        scenario,
        "check-approved",
        json.dumps(identities),
    )
    assert "SCENARIO_RESULT=" in checked.stdout
    assert before == {
        path.name: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
        for path in paths["raw"].iterdir()
    }
    sys.stdout.write(
        "PASS: actual non-root worker, read-only RAW/host permissions, verified independent copy, "
        "explicit multi-part approval, canonical publication, retained history, complete backup/restore, no network\n"
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
