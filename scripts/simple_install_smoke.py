"""Linux CI: execute the documented simple install with the published image."""

import argparse
import hashlib
import json
import os
import pty
import pwd
import re
import select
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import closing
from pathlib import Path
from uuid import uuid4

from scripts.container_smoke import PASSWORD, authentication, request

REPOSITORY = Path(__file__).resolve().parent.parent


def execute(arguments, *, success=True, cwd=None, timeout=180):
    result = subprocess.run(arguments, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if success:
        assert result.returncode == 0, (
            f"Synthetic install command failed: {arguments[:2]}\n{result.stdout}\n{result.stderr}"
        )
    else:
        assert result.returncode != 0, "Unsafe synthetic preparation unexpectedly succeeded"
    return result


def provision(command, *, service="admin"):
    master, slave = pty.openpty()
    process = subprocess.Popen(
        [*command, "--profile", "tools", "run", "--rm", service], stdin=slave, stdout=slave, stderr=slave
    )
    os.close(slave)
    transcript, stage = b"", 0
    deadline = time.monotonic() + 60
    try:
        while process.poll() is None:
            if time.monotonic() > deadline:
                raise RuntimeError("Interactive synthetic provisioning timed out")
            if select.select([master], [], [], 0.2)[0]:
                try:
                    transcript += os.read(master, 16384)
                except OSError:
                    break
            if stage == 0 and b"Benutzername:" in transcript:
                os.write(master, b"synthetic-archivist\n")
                stage = 1
            if stage == 1 and b"Passwort:" in transcript:
                os.write(master, PASSWORD.encode() + b"\n")
                stage = 2
        assert process.wait(timeout=10) == 0 and stage == 2
        while select.select([master], [], [], 0.1)[0]:
            try:
                transcript += os.read(master, 16384)
            except OSError:
                break
        assert PASSWORD.encode() not in transcript, "Interactive password was echoed"
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        os.close(master)


def preparation_negatives(parent, uid, gid):
    helper = REPOSITORY / "scripts/prepare-install.sh"
    bad = parent / "bad-mode"
    bad.mkdir(mode=0o750)
    root = bad / "notenarchiv"
    root.mkdir(mode=0o777)
    os.chown(root, 0, gid)
    root.chmod(0o777)
    execute(["sh", str(helper), str(uid), str(gid), str(root)], success=False)
    assert root.stat().st_mode & 0o777 == 0o777 and not list(root.iterdir())
    root.chmod(0o750)
    data = root / "data"
    data.mkdir(mode=0o700)
    os.chown(data, uid, gid)
    sentinel = data / "synthetic-existing.sqlite3"
    sentinel.write_bytes(b"synthetic-existing-state")
    execute(["sh", str(helper), str(uid), str(gid), str(root)], success=False)
    assert sentinel.read_bytes() == b"synthetic-existing-state"
    assert not (root / "secrets/django_secret_key").exists()
    linked_parent = parent / "symlink-case"
    linked_parent.mkdir()
    alias = linked_parent / "notenarchiv"
    alias.symlink_to(root, target_is_directory=True)
    execute(["sh", str(helper), str(uid), str(gid), str(alias)], success=False)
    execute(["sh", str(helper), "0", str(gid), str(root)], success=False)
    execute(["sh", str(helper), str(uid), "100", str(root)], success=False)
    secret = root / "secrets/django_secret_key"
    secret.write_text("Synthetic-existing-short-key")
    os.chown(secret, 0, gid)
    secret.chmod(0o440)
    execute(["sh", str(helper), str(uid), str(gid), str(root)], success=False)
    assert secret.read_text() == "Synthetic-existing-short-key" and secret.stat().st_mode & 0o777 == 0o440


def raw_boundaries(root, command, uid, gid):
    note = root / "raw/synthetic.txt"
    note.write_text("Original synthetic RAW sentinel")
    os.chown(note, 0, gid)
    note.chmod(0o440)
    code = """
from pathlib import Path
raw = Path(RAW_PATH)
note = raw / 'synthetic.txt'
assert note.read_text() == 'Original synthetic RAW sentinel'
actions = [lambda: note.write_text('changed'), lambda: note.unlink(),
           lambda: note.rename(raw / 'renamed'), lambda: (raw / 'new').write_text('new'),
           lambda: raw.rename(raw.parent / 'moved-raw')]
for action in actions:
    try: action()
    except OSError: pass
    else: raise AssertionError('RAW protection failed')
"""
    subprocess.run(
        ["python3", "-c", code.replace("RAW_PATH", repr(str(root / "raw")))],
        user=uid,
        group=gid,
        extra_groups=[],
        check=True,
        timeout=10,
    )
    execute([*command, "exec", "-T", "web", "python", "-c", code.replace("RAW_PATH", repr("/archive/raw"))])
    assert note.read_text() == "Original synthetic RAW sentinel"


def smoke(parent, uid, gid, candidate=None):
    root = parent / "notenarchiv"
    helper = ["sh", str(REPOSITORY / "scripts/prepare-install.sh"), str(uid), str(gid), str(root)]
    execute(helper)
    secret = root / "secrets/django_secret_key"
    secret_hash = hashlib.sha256(secret.read_bytes()).hexdigest()
    execute(helper)
    assert hashlib.sha256(secret.read_bytes()).hexdigest() == secret_hash
    template = (REPOSITORY / "configuration.yaml").read_text()
    if candidate:
        template = re.sub(r"ghcr\.io/tostman1/notenarchiv@sha256:[0-9a-f]{64}", candidate, template)
    project_file = root / "config/docker-compose.yml"
    project_file.write_text(
        template.replace("CHANGE_UID:CHANGE_GID", f"{uid}:{gid}").replace("/volume1/docker/notenarchiv", str(root))
    )
    project_file.chmod(0o640)
    os.chown(project_file, 0, gid)
    command = [
        "docker",
        "compose",
        "--env-file",
        "/dev/null",
        "--project-name",
        "simple-" + uuid4().hex[:12],
        "-f",
        str(project_file),
    ]
    try:
        execute([*command, "config", "--quiet"])
        config = json.loads(execute([*command, "--profile", "tools", "config", "--format", "json"]).stdout)
        image = config["services"]["web"]["image"]
        metadata = json.loads(execute(["docker", "image", "inspect", image]).stdout)[0]
        assert metadata["Architecture"] == "amd64"
        if not candidate:
            assert image in metadata["RepoDigests"]
        execute([*command, "run", "--rm", "web"], success=False)
        execute([*command, "--profile", "tools", "run", "--rm", "migrate"])
        database = root / "data/notenarchiv.sqlite3"
        assert database.is_file() and database.stat().st_uid == uid
        before = database.read_bytes()
        execute([*command, "--profile", "tools", "run", "--rm", "migrate"])
        assert database.read_bytes() == before
        provision(command)
        execute([*command, "up", "-d", "web", "gateway"])
        web_id = execute([*command, "ps", "-q", "web"]).stdout.strip()
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            try:
                state = json.loads(execute(["docker", "inspect", web_id]).stdout)[0]["State"]
                if (
                    state["Health"]["Status"] == "healthy"
                    and request(8085, "GET", "/healthz", secure=False, host="127.0.0.1")[0] == 200
                ):
                    break
            except OSError:
                pass
            time.sleep(0.5)
        else:
            raise RuntimeError("Simple installation did not become healthy")
        services = execute([*command, "ps", "--services", "--status", "running"]).stdout.split()
        assert set(services) == {"web", "gateway"}
        for service in services:
            identifier = execute([*command, "ps", "-q", service]).stdout.strip()
            info = json.loads(execute(["docker", "inspect", identifier]).stdout)[0]
            assert info["Config"]["User"] == f"{uid}:{gid}" and info["HostConfig"]["ReadonlyRootfs"]
            assert info["HostConfig"]["CapDrop"] == ["ALL"]
            assert any(value.startswith("no-new-privileges") for value in info["HostConfig"]["SecurityOpt"])
            networks = [
                json.loads(execute(["docker", "network", "inspect", name]).stdout)[0]
                for name in info["NetworkSettings"]["Networks"]
            ]
            if service == "gateway":
                assert not any(mount["Type"] in {"bind", "volume"} for mount in info["Mounts"])
                assert info["HostConfig"]["PortBindings"]["8000/tcp"][0]["HostIp"] == "127.0.0.1"
                assert sorted(network["Internal"] for network in networks) == [False, True]
            else:
                binds = {mount["Destination"]: mount for mount in info["Mounts"] if mount["Type"] == "bind"}
                expected = {f"/archive/{name}": name for name in ("raw", "clean", "processed", "status", "export")}
                expected.update({"/data": "data", "/run/secrets/django_secret_key": "secrets/django_secret_key"})
                assert set(binds) == set(expected)
                for destination, source in expected.items():
                    assert binds[destination]["RW"] == (destination == "/data")
                    assert binds[destination]["Source"] == str(root / source)
                assert len(networks) == 1 and networks[0]["Internal"]
                assert not info["HostConfig"]["PortBindings"]
                assert info["State"]["Health"]["Status"] == "healthy"
        cookies = authentication(8085)
        raw_boundaries(root, command, uid, gid)
        execute(helper)  # A live installation is preserved; only new paths/key would be created.
        assert hashlib.sha256(secret.read_bytes()).hexdigest() == secret_hash
        execute([*command, "restart", "web", "gateway"])
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            try:
                if request(8085, "GET", "/", cookies=cookies)[0] == 200:
                    break
            except OSError:
                pass
            time.sleep(0.5)
        else:
            raise RuntimeError("Saved authentication did not survive restart")
        with closing(sqlite3.connect(f"file:{database}?mode=ro", uri=True)) as connection:
            assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        logs = execute([*command, "logs", "--no-color"]).stdout
        assert PASSWORD not in logs and secret.read_text().strip() not in logs
        parent.chmod(0o770)
        try:
            refused = execute(helper, success=False)
            assert "RAW ancestor" in refused.stderr
            assert hashlib.sha256(secret.read_bytes()).hexdigest() == secret_hash
        finally:
            parent.chmod(0o750)
        preparation_negatives(parent, uid, gid)
    finally:
        execute([*command, "down", "--remove-orphans", "--timeout", "10"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-image", help="Also check a local CI candidate without publishing it")
    arguments = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("Run only as root on an isolated Linux CI Docker host")
    account = pwd.getpwnam("nobody")
    for candidate in [None, arguments.candidate_image] if arguments.candidate_image else [None]:
        with tempfile.TemporaryDirectory(prefix="notenarchiv-simple-") as directory:
            parent = Path(directory)
            os.chown(parent, 0, account.pw_gid)
            parent.chmod(0o750)
            smoke(parent, account.pw_uid, account.pw_gid, candidate)
        label = "local candidate" if candidate else "published immutable digest"
        sys.stdout.write(
            f"PASS: simple installation ({label}), interactive account, RAW denial, persistence and preservation\n"
        )


if __name__ == "__main__":
    main()
