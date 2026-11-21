"""Linux CI only: real non-root containers, synthetic bind mounts and no NAS access."""

import argparse
import hashlib
import http.client
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import closing
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4

UID = GID = 10001
HOST = "notenarchiv.example.invalid"
PASSWORD = "Synthetic-container-acceptance-135"


def docker(*arguments, check=True):
    result = subprocess.run(["docker", *arguments], capture_output=True, text=True, timeout=180)
    if check and result.returncode:
        raise RuntimeError(f"Synthetic Docker check failed: {arguments[0]}\n{result.stdout}\n{result.stderr}")
    return result


def prepare(root):
    root.chmod(0o750)
    os.chown(root, 0, GID)
    paths = {}
    for name in ("raw", "clean", "processed", "status", "export", "data"):
        path = root / name
        path.mkdir()
        os.chown(path, UID if name == "data" else 0, GID)
        path.chmod(0o700 if name == "data" else 0o550)
        paths[name] = path
    note = paths["raw"] / "synthetic.txt"
    note.write_text("Deterministic synthetic fixture; no actual music.")
    os.chown(note, 0, GID)
    note.chmod(0o440)
    secret = root / "secret"
    secret.write_text("synthetic-container-test-key-" + "x" * 64)
    os.chown(secret, 0, GID)
    secret.chmod(0o440)
    paths["secret"] = secret
    return paths


def arguments(paths, network, *, debug=False, raw_readonly=True, service="web"):
    args = [
        "--read-only",
        "--init",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--user",
        f"{UID}:{GID}",
        "--tmpfs",
        "/tmp:rw,nosuid,nodev,size=64m",
        "--network",
        network,
        "--memory",
        "512m",
        "--pids-limit",
        "64",
        "--health-interval",
        "1s",
        "--health-start-period",
        "1s",
    ]
    environment = {
        "NOTENARCHIV_SERVICE": service,
        "APP_BIND": "127.0.0.1",
        "APP_ALLOWED_HOSTS": f"{HOST},localhost,127.0.0.1",
        "APP_CSRF_TRUSTED_ORIGINS": f"https://{HOST}",
        "DJANGO_SECRET_KEY_FILE": "/run/secrets/django_secret_key",
        "DATABASE_PATH": "/data/notenarchiv.sqlite3",
        "SOURCE_DIR": "/archive/raw",
        "CURATED_DIR": "/archive/clean",
        "PROCESSED_DIR": "/archive/processed",
        "STATUS_DIR": "/archive/status",
        "EXPORT_DIR": "/archive/export",
    }
    if debug:
        environment["DEBUG_MODE"] = "TRUE"
    for key, value in environment.items():
        args.extend(["-e", f"{key}={value}"])
    for key, source in paths.items():
        target = "/data" if key == "data" else f"/archive/{key}"
        if key == "secret":
            target = "/run/secrets/django_secret_key"
        readonly = (
            key != "data" and (key != "raw" or raw_readonly) and (service != "worker" or key in {"raw", "secret"})
        )
        args.extend(["--mount", f"type=bind,src={source},dst={target}" + (",readonly" if readonly else "")])
    return args


def request(port, method, path, *, cookies=None, form=None, secure=True, host=HOST):
    headers = {"Host": host}
    if secure:
        headers["X-Forwarded-Proto"] = "https"
    if cookies:
        headers["Cookie"] = "; ".join(f"{key}={value}" for key, value in cookies.items())
    body = urlencode(form) if form is not None else None
    if body is not None:
        headers.update({"Content-Type": "application/x-www-form-urlencoded", "Origin": f"https://{HOST}"})
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        data = response.read()
        received = SimpleCookie()
        for name, value in response.getheaders():
            if name.lower() == "set-cookie":
                received.load(value)
        return response.status, data, response.getheaders(), {key: item.value for key, item in received.items()}
    finally:
        connection.close()


def start(image, paths, network, name, *, debug=False):
    backend, gateway = name + "-backend", name + "-gateway"
    docker("network", "create", "--internal", backend)
    docker("run", "-d", "--name", name, *arguments(paths, backend, debug=debug), "--network-alias", "web", image)
    docker(
        "run",
        "-d",
        "--name",
        gateway,
        "--read-only",
        "--init",
        "--user",
        f"{UID}:{GID}",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--memory",
        "64m",
        "--pids-limit",
        "64",
        "--network",
        network + "-front",
        "-p",
        "127.0.0.1::8000",
        image,
        "gateway",
    )
    docker("network", "connect", backend, gateway)
    gateway_info = json.loads(docker("inspect", gateway).stdout)[0]
    assert not any(mount["Type"] == "bind" for mount in gateway_info["Mounts"])
    assert gateway_info["HostConfig"]["ReadonlyRootfs"]
    docker(
        "exec",
        name,
        "python",
        "-c",
        "from pathlib import Path; rows=Path('/proc/net/route').read_text().splitlines()[1:]; "
        "assert not any(row.split()[1]=='00000000' for row in rows)",
    )
    binding = docker("port", gateway, "8000/tcp", check=False)
    if binding.returncode:
        state = docker("inspect", "--format", "{{json .State}}", name, check=False)
        logs = docker("logs", name, check=False)
        raise RuntimeError(f"Synthetic web port unavailable\n{state.stdout}\n{logs.stdout}\n{logs.stderr}")
    port = int(binding.stdout.strip().rsplit(":", 1)[1])
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        try:
            if request(port, "GET", "/healthz", secure=False, host="127.0.0.1")[0] == 200:
                return port
        except (OSError, http.client.HTTPException):
            pass
        time.sleep(0.2)
    raise RuntimeError("Container did not become healthy\n" + docker("logs", name).stdout)


def authentication(port):
    assert request(port, "GET", "/login/", secure=False)[0] == 301
    assert request(port, "GET", "/", host="untrusted.invalid")[0] == 400
    assert request(port, "GET", "/")[0] == 302
    status, body, headers, cookies = request(port, "GET", "/login/")
    assert status == 200 and b"Benutzername" in body
    token = re.search(rb'name="csrfmiddlewaretoken" value="([^"]+)"', body).group(1).decode()
    form = {"username": "synthetic-archivist", "password": PASSWORD}
    assert request(port, "POST", "/login/", form=form, cookies=cookies)[0] == 403
    form["csrfmiddlewaretoken"] = token
    status, _body, headers, updated = request(port, "POST", "/login/", form=form, cookies=cookies)
    assert status == 302
    session_header = next(value for name, value in headers if name.lower() == "set-cookie" and "sessionid" in value)
    assert "Secure" in session_header and "HttpOnly" in session_header
    cookies.update(updated)
    status, body, _headers, _updated = request(port, "GET", "/", cookies=cookies)
    assert status == 200 and "Noch nicht verfügbar".encode() in body
    assert b"synthetische Testdaten" in body
    assert request(port, "GET", "/static/css/base.css")[0] == 200
    assert request(port, "GET", "/static/js/diagnostics.js")[0] == 200
    return cookies


def host_preflight(paths, root):
    environment = {
        "APP_UID": UID,
        "APP_GID": GID,
        "APP_BIND": "127.0.0.1",
        "PREVIEW_DATA_ONLY": "TRUE",
        "APP_IMAGE": "ghcr.io/tostman1/notenarchiv@sha256:" + "0" * 64,
    }
    for key, name in (
        ("SOURCE_HOST", "raw"),
        ("CURATED_HOST", "clean"),
        ("PROCESSED_HOST", "processed"),
        ("STATUS_HOST", "status"),
        ("EXPORT_HOST", "export"),
        ("DATA_HOST", "data"),
        ("SECRET_HOST", "secret"),
    ):
        environment[key] = paths[name]
    config = root / "synthetic.env"
    config.write_text("".join(f"{key}={value}\n" for key, value in environment.items()))
    os.chown(config, 0, GID)
    config.chmod(0o440)
    script = root / "preflight.sh"
    shutil.copyfile("scripts/preflight-host.sh", script)
    os.chown(script, 0, GID)
    script.chmod(0o550)
    command = ["sh", str(script), str(config)]
    result = subprocess.run(command, user=UID, group=GID, extra_groups=[], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    paths["raw"].chmod(0o770)  # Dedicated synthetic permission negative, never a real archive.
    denied = subprocess.run(command, user=UID, group=GID, extra_groups=[], capture_output=True, timeout=10)
    paths["raw"].chmod(0o550)
    assert denied.returncode != 0


def raw_negatives(image, paths, network):
    note = paths["raw"] / "synthetic.txt"
    original = hashlib.sha256(note.read_bytes()).hexdigest()
    code = """
from pathlib import Path
root=Path('/archive/raw')
actions=[lambda:(root/'new').write_text('synthetic'),lambda:(root/'synthetic.txt').write_text('changed'),
         lambda:(root/'synthetic.txt').rename(root/'renamed'),lambda:(root/'synthetic.txt').unlink()]
for action in actions:
    try: action()
    except OSError: pass
    else: raise AssertionError('RAW protection failed')
"""
    # Mount protection must hold even when this synthetic host fixture allows writes.
    paths["raw"].chmod(0o770)
    note.chmod(0o660)
    docker("run", "--rm", *arguments(paths, network), "--entrypoint", "python", image, "-c", code)
    paths["raw"].chmod(0o550)
    note.chmod(0o440)
    # Separately verify the host permission layer with no container mount involved.
    host_code = code.replace("'/archive/raw'", repr(str(paths["raw"])))
    subprocess.run(["python3", "-c", host_code], user=UID, group=GID, extra_groups=[], check=True, timeout=10)
    assert hashlib.sha256(note.read_bytes()).hexdigest() == original


def pdf_primitives(name):
    # Actual musllinux PDFium loading/rendering in the hardened image, not merely
    # wheel resolution or host tests. No archive file is opened or written.
    code = """
from io import BytesIO
from pathlib import Path
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject
from core.pdf import Processor, Selection
scratch = Path('/data/pdf-smoke')
scratch.mkdir(mode=0o700)
try:
    writer = PdfWriter()
    page = writer.add_blank_page(595.2756, 841.8898)
    content = DecodedStreamObject()
    content.set_data(b'0 0 0 RG 4 w 30 30 m 200 100 l S')
    page[NameObject('/Contents')] = writer._add_object(content)
    stream = BytesIO()
    writer.write(stream)
    data = stream.getvalue()
    processor = Processor(scratch)
    assert processor.inspect(data).pages[0].paper == 'A4'
    assert processor.extract_text(data) == ('',)
    assert processor.thumbnail(data).startswith(b'\\x89PNG')
    merged = processor.merge((Selection(data), Selection(data)))
    assert len(processor.inspect(merged).pages) == 2
    assert not list(scratch.iterdir())
finally:
    scratch.rmdir()
"""
    docker("exec", name, "python", "-c", code)


def backup_restore(paths, root):
    snapshot = root / "backup"
    snapshot.mkdir(mode=0o700)
    with (
        closing(sqlite3.connect(f"file:{paths['data'] / 'notenarchiv.sqlite3'}?mode=ro", uri=True)) as source,
        closing(sqlite3.connect(snapshot / "database.sqlite3")) as destination,
    ):
        source.backup(destination)
        assert destination.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    shutil.copyfile(paths["secret"], snapshot / "secret")
    shutil.copyfile(root / "synthetic.env", snapshot / "config.env")
    restored = root / "restored-data"
    restored.mkdir(mode=0o700)
    target = restored / "notenarchiv.sqlite3"
    shutil.copyfile(snapshot / "database.sqlite3", target)
    os.chown(restored, UID, GID)
    os.chown(target, UID, GID)
    target.chmod(0o600)
    assert target.read_bytes() == (snapshot / "database.sqlite3").read_bytes()
    return {**paths, "data": restored}


def smoke(image, root):
    suffix = uuid4().hex[:12]
    network = f"notenarchiv-test-{suffix}"
    names = [f"{network}-{label}" for label in ("deploy", "debug", "final", "restore")]
    paths = prepare(root)
    metadata = json.loads(docker("image", "inspect", image).stdout)[0]
    assert metadata["Architecture"] == "amd64" and metadata["Os"] == "linux"
    assert metadata["Config"]["User"] not in ("", "root", "0", "0:0")
    docker("network", "create", "--internal", network)
    docker("network", "create", network + "-front")
    try:
        host_preflight(paths, root)
        raw_negatives(image, paths, network)
        for unsafe in (
            arguments(paths, network, raw_readonly=False),
            arguments({**paths, "clean": paths["raw"]}, network),
        ):
            assert docker("run", "--rm", *unsafe, image, "check", check=False).returncode != 0
        missing = root / "missing-raw"
        assert (
            docker(
                "run", "--rm", *arguments({**paths, "raw": missing}, network), image, "check", check=False
            ).returncode
            != 0
        )
        assert not missing.exists()
        assert docker("run", "--rm", *arguments(paths, network), image, "web", check=False).returncode != 0
        docker("run", "--rm", *arguments(paths, network), image, "migrate")
        assert not (paths["data"] / "logs" / "web.debug.log").exists()
        fixture = (
            "from config import runtime; runtime.management_command='synthetic_fixture'; "
            "import os; os.environ['DJANGO_SETTINGS_MODULE']='config.settings'; "
            "import django; django.setup(); from django.contrib.auth import get_user_model; "
            f"get_user_model().objects.create_user('synthetic-archivist',password={PASSWORD!r})"
        )
        docker("run", "--rm", *arguments(paths, network), "--entrypoint", "python", image, "-c", fixture)
        port = start(image, paths, network, names[0])
        pdf_primitives(names[0])
        cookies = authentication(port)
        assert request(port, "GET", "/diagnostics/", cookies=cookies)[0] == 404
        assert docker("run", "--rm", *arguments(paths, network), image, "migrate", check=False).returncode != 0
        docker("stop", "--time", "35", names[0])
        restored = backup_restore(paths, root)
        debug_port = start(image, paths, network, names[1], debug=True)
        assert request(debug_port, "GET", "/", cookies=cookies)[0] == 200
        assert request(debug_port, "GET", "/diagnostics/", cookies=cookies)[0] == 200
        assert (
            request(debug_port, "POST", "/logout/", cookies=cookies, form={"message": "synthetic-private-OCR"})[0]
            == 403
        )
        debug_file = paths["data"] / "logs" / "web.debug.log"
        persisted = debug_file.read_bytes()
        assert persisted and b"synthetic-private-OCR" not in persisted
        docker("exec", names[1], "python", "-m", "scripts.healthcheck")
        docker("stop", "--time", "35", names[1])
        final_port = start(image, paths, network, names[2])
        assert request(final_port, "GET", "/", cookies=cookies)[0] == 200
        assert request(final_port, "GET", "/diagnostics/", cookies=cookies)[0] == 404
        assert debug_file.read_bytes() == persisted
        restore_port = start(image, restored, network, names[3])
        assert request(restore_port, "GET", "/", cookies=cookies)[0] == 200
        token = re.search(
            rb'name="csrfmiddlewaretoken" value="([^"]+)"', request(final_port, "GET", "/", cookies=cookies)[1]
        )
        assert token is not None
        assert (
            request(
                final_port, "POST", "/logout/", cookies=cookies, form={"csrfmiddlewaretoken": token.group(1).decode()}
            )[0]
            == 302
        )
        assert request(final_port, "GET", "/", cookies=cookies)[0] == 302
        for name in names:
            output = docker("logs", name).stdout
            assert PASSWORD not in output and "synthetic-private-OCR" not in output
        sys.stdout.write(
            "PASS: amd64/non-root/read-only mounts, independent RAW rights, startup negatives, "
            "migrations, login/CSRF/logout, persistence, Debug switch, backup/isolated restore, "
            "isolated PDF primitives\n"
        )
    except Exception:
        # These containers contain deterministic synthetic fixtures only.
        for name in names + [name + "-gateway" for name in names]:
            logs = docker("logs", name, check=False)
            if logs.returncode == 0:
                sys.stderr.write(f"Synthetic container {name}:\n{logs.stdout}\n{logs.stderr}\n")
        raise
    finally:
        for name in [name + "-gateway" for name in names] + names:
            docker("rm", "--force", name, check=False)
        for name in names:
            docker("network", "rm", name + "-backend", check=False)
        docker("network", "rm", network + "-front", check=False)
        docker("network", "rm", network, check=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    args = parser.parse_args()
    if os.name != "posix" or os.geteuid() != 0:
        parser.error("Run as root on an isolated Linux Docker CI host with synthetic data only")
    with tempfile.TemporaryDirectory(prefix="notenarchiv-smoke-") as directory:
        smoke(args.image, Path(directory))


if __name__ == "__main__":
    main()
