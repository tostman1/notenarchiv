"""Linux-only actual Compose stack, TLS browser, recovery and RAW acceptance."""

import argparse
import hashlib
import http.client
import importlib.util
import json
import os
import pwd
import ssl
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4

from scripts.container_smoke import HOST, PASSWORD, request
from scripts.simple_install_smoke import execute, provision

ROOT = Path(__file__).resolve().parent.parent
WEB, WORKER, GATEWAY = ("notenarchiv-test-" + name for name in ("web", "worker", "gateway"))


class Proxy(BaseHTTPRequestHandler):
    """Synthetic CI TLS terminator; strip incoming proxy headers, fixed private target."""

    def do_GET(self):
        self.forward()

    def do_POST(self):
        self.forward()

    def forward(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        headers = {
            k: v for k, v in self.headers.items() if k.lower() not in {"host", "x-forwarded-proto", "connection"}
        }
        headers.update({"Host": "127.0.0.1:9443", "X-Forwarded-Proto": "https", "Connection": "close"})
        connection = http.client.HTTPConnection("127.0.0.1", 8090, timeout=30)
        try:
            connection.request(self.command, self.path, body, headers)
            response = connection.getresponse()
            data = response.read()
            self.send_response(response.status)
            for k, v in response.getheaders():
                if k.lower() not in {"transfer-encoding", "connection", "content-length"}:
                    self.send_header(k, v)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        finally:
            connection.close()

    def log_message(self, *_args):
        pass


def wait_until(check, message, seconds=120):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if check():
            return
        time.sleep(0.5)
    raise AssertionError(message)


def smoke(parent, image):
    other_containers = execute(["docker", "ps", "-aq"]).stdout.split()
    other_volumes = execute(["docker", "volume", "ls", "-q"]).stdout.split()
    account = pwd.getpwnam("nobody")
    uid, gid = account.pw_uid, account.pw_gid
    os.chown(parent, 0, gid)
    parent.chmod(0o750)
    root = parent / "notenarchiv-test"
    prepare = ["sh", str(ROOT / "deploy/synology-test/prepare.sh"), str(uid), str(gid), str(root)]
    execute(prepare)
    secret = root / "secrets/django_secret_key"
    secret_hash = hashlib.sha256(secret.read_bytes()).hexdigest()
    execute(prepare)
    assert hashlib.sha256(secret.read_bytes()).hexdigest() == secret_hash
    template = (ROOT / "deploy/synology-test/compose.yaml").read_text()
    from scripts.package_synology_test import CANDIDATE, contents

    if "@sha256:" in image:
        template = contents(image)["compose.yaml"].decode()
        execute(["docker", "pull", image])
    else:
        template = template.replace(CANDIDATE, image)
    suffix = uuid4().hex[:12]
    for service in (WEB, WORKER, GATEWAY):
        template = template.replace(f"container_name: {service}", f"container_name: {service}-{suffix}")
    template = template.replace("https://notenarchiv-test.example.invalid", "https://127.0.0.1:9443")
    template = template.replace("notenarchiv-test.example.invalid", HOST)
    compose_file = root / "config/compose.yaml"
    compose_file.write_text(
        template.replace("CHANGE_UID:CHANGE_GID", f"{uid}:{gid}").replace("/volume1/docker/notenarchiv-test", str(root))
    )
    command = [
        "docker",
        "compose",
        "--env-file",
        "/dev/null",
        "-p",
        f"notenarchiv-stack-{suffix}",
        "-f",
        str(compose_file),
    ]

    def compose(*args, success=True):
        return execute([*command, *args], success=success)

    def action(mode, ids=None):
        code = (ROOT / "tests/synology_scenario.py").read_text()
        args = ["exec", "-T", "-e", "DJANGO_SETTINGS_MODULE=config.settings", WEB, "python", "-c", code, mode]
        if ids is not None:
            args.append(json.dumps(ids))
        output = compose(*args).stdout
        return json.loads(
            next(
                line.removeprefix("SCENARIO_RESULT=")
                for line in output.splitlines()
                if line.startswith("SCENARIO_RESULT=")
            )
        )

    def health():
        result = compose("ps", "--format", "json").stdout
        rows = [json.loads(line) for line in result.splitlines() if line.strip()]
        return len(rows) == 3 and all(row.get("Health") == "healthy" for row in rows)

    spec = importlib.util.spec_from_file_location("demo", ROOT / "deploy/synology-test/demo.py")
    demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(demo)
    demo.create(root / "raw/demo")
    for path in (root / "raw/demo").rglob("*"):
        os.chown(path, 0, gid)
        path.chmod(0o550 if path.is_dir() else 0o440)
    os.chown(root / "raw/demo", 0, gid)
    (root / "raw/demo").chmod(0o550)
    before = {
        str(p.relative_to(root / "raw")): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (root / "raw").rglob("*.pdf")
    }
    try:
        compose("config", "--quiet")
        compose("run", "--rm", "--no-deps", WEB, success=False)
        compose("--profile", "tools", "run", "--rm", "initialize")
        provision(command, service="archivist")
        compose("up", "-d", WEB, WORKER, GATEWAY)
        wait_until(health, "Full stack did not become healthy")
        identities = action("setup")
        for service in (WEB, WORKER, GATEWAY):
            identifier = compose("ps", "-q", service).stdout.strip()
            info = json.loads(execute(["docker", "inspect", identifier]).stdout)[0]
            assert info["Config"]["User"] == f"{uid}:{gid}"
            assert info["HostConfig"]["ReadonlyRootfs"] and info["HostConfig"]["CapDrop"] == ["ALL"]
            assert "no-new-privileges:true" in info["HostConfig"]["SecurityOpt"]
            binds = {m["Destination"]: m for m in info["Mounts"] if m["Type"] == "bind"}
            if service == GATEWAY:
                assert not binds and not any(m["Type"] == "volume" for m in info["Mounts"])
                assert info["HostConfig"]["PortBindings"]["8000/tcp"][0]["HostIp"] == "127.0.0.1"
            else:
                assert len(binds) == 7 and not info["HostConfig"]["PortBindings"]
                for destination, mount in binds.items():
                    assert mount["Source"].startswith(str(root) + "/")
                    assert mount["RW"] is (
                        destination == "/data"
                        or (
                            service == WORKER
                            and destination
                            in {"/archive/clean", "/archive/processed", "/archive/status", "/archive/export"}
                        )
                    )
                networks = info["NetworkSettings"]["Networks"]
                assert len(networks) == 1
                assert json.loads(execute(["docker", "network", "inspect", next(iter(networks))]).stdout)[0]["Internal"]
        # Maintenance and a duplicate worker must be rejected, not steal ownership.
        compose("--profile", "tools", "run", "--rm", "initialize", success=False)
        compose("run", "--rm", "--no-deps", WORKER, success=False)
        assert request(8090, "GET", "/login/", secure=False)[0] == 301
        assert request(8090, "GET", "/", host="untrusted.invalid")[0] == 400
        assert request(8090, "POST", "/login/", form={"username": "synthetic"})[0] == 403
        cert, key = parent / "cert.pem", parent / "key.pem"
        execute(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-days",
                "1",
                "-subj",
                "/CN=localhost",
                "-keyout",
                str(key),
                "-out",
                str(cert),
            ]
        )
        server = ThreadingHTTPServer(("127.0.0.1", 9443), Proxy)
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(cert, key)
        server.socket = tls.wrap_socket(server.socket, server_side=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        input_file = parent / "browser-input.json"
        input_file.write_text(json.dumps({**identities, "password": PASSWORD}))
        try:
            execute(
                [
                    "node",
                    str(ROOT / "browser/synology_stack.cjs"),
                    f"https://127.0.0.1:{server.server_port}",
                    str(input_file),
                ],
                timeout=600,
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=10)
        assert len(action("files")) == 6 and all(f["review"] == "CONFIRMED" for f in action("files"))
        assert list((root / "status").rglob("*.json")), "Index status was not independently published"
        # Actual worker crash after filesystem publication; regular service recovers.
        compose("stop", WORKER)
        recovery = action("authorize", identities)
        code = (ROOT / "tests/generation_scenario.py").read_text()
        compose(
            "run", "--rm", "--no-deps", "--entrypoint", "python", WORKER, "-c", code, "crash-after-link", success=False
        )
        assert action("state", recovery)["status"] == "RUNNING"
        compose("up", "-d", WORKER)
        wait_until(lambda: action("state", recovery)["status"] == "SUCCEEDED", "Crash recovery failed")
        assert action("state", recovery)["attempt"] >= 2
        assert action("pins", recovery)["protected"]
        # Cancellation and partial-failure paths run real composition/publication.
        for fault, expected in (("cancel-after-stage", "CANCELLED"), ("fail-second-participant", "FAILED")):
            compose("stop", WORKER)
            ids = action("authorize", identities)
            compose("run", "--rm", "--no-deps", "--entrypoint", "python", WORKER, "-c", code, fault)
            assert action("state", ids)["status"] == expected
            for artifact in action("state", ids)["artifacts"]:
                denied_code = (
                    "import django; django.setup(); from django.test import Client; "
                    "from django.contrib.auth import get_user_model; "
                    "c=Client(); c.force_login(get_user_model().objects.get(username='synthetic-archivist')); "
                    f"assert c.get('/exports/artifacts/{artifact}/download/', "
                    "HTTP_HOST='127.0.0.1', HTTP_X_FORWARDED_PROTO='https').status_code == 404"
                )
                compose("exec", "-T", WEB, "python", "-c", denied_code)
            compose("up", "-d", WORKER)
            wait_until(health, "Worker did not restart after negative path")
        # RAW create/write/rename/delete denied in both services and host identity.
        raw_code = """
from pathlib import Path
raw=Path(RAW_PATH); note=next(raw.rglob('*.pdf'))
for operation in (lambda:note.write_bytes(b'changed'),lambda:note.unlink(),
                  lambda:note.rename(note.with_name('renamed')),
                  lambda:(raw/'new').write_text('new'),lambda:raw.rename(raw.parent/'moved-raw')):
    try: operation()
    except OSError: pass
    else: raise AssertionError('RAW boundary failed')
"""
        for service in (WEB, WORKER):
            compose("exec", "-T", service, "python", "-c", raw_code.replace("RAW_PATH", repr("/archive/raw")))
        subprocess.run(
            ["python3", "-c", raw_code.replace("RAW_PATH", repr(str(root / "raw")))],
            user=uid,
            group=gid,
            extra_groups=[],
            check=True,
            timeout=10,
        )
        compose("restart", WEB, WORKER, GATEWAY)
        wait_until(health, "Stack did not recover after restart")
        assert len(action("files")) == 6
        assert action("state", recovery)["status"] == "SUCCEEDED"
        assert action("outputs")["verified"]
        assert before == {
            str(p.relative_to(root / "raw")): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (root / "raw").rglob("*.pdf")
        }
        logs = compose("logs", "--no-color").stdout
        assert PASSWORD not in logs and secret.read_text().strip() not in logs
        assert hashlib.sha256(secret.read_bytes()).hexdigest() == secret_hash
        sys.stdout.write(
            "PASS: actual Compose/TLS browser/index/manual approval/matrix/all PDFs/downloads/"
            "recovery/cancel/failure/pins/RAW/persistence\n"
        )
    except Exception:
        sys.stderr.write(compose("logs", "--no-color").stdout)
        diagnosis = """
import django,json,traceback
django.setup()
from django.test import Client
from django.contrib.auth import get_user_model
from apps.archive.models import ArchiveFile
from apps.jobs.models import Job
c=Client(); c.force_login(get_user_model().objects.get(username='synthetic-archivist'))
for file in ArchiveFile.objects.all():
    print('SYNTHETIC_FILE',file.pk,file.review_state,file.revision,file.current_proposal_id)
    try:
        response=c.get('/archive/review/'+str(file.pk)+'/',HTTP_HOST='127.0.0.1',HTTP_X_FORWARDED_PROTO='https')
        print('SYNTHETIC_REVIEW_STATUS',response.status_code)
    except Exception:
        traceback.print_exc()
print('SYNTHETIC_JOBS',list(Job.objects.values('id','status','error_code')))
"""
        diagnostic = subprocess.run(
            [*command, "exec", "-T", WEB, "python", "-c", diagnosis],
            capture_output=True,
            text=True,
            timeout=30,
        )
        sys.stderr.write(diagnostic.stdout + diagnostic.stderr)
        raise
    finally:
        compose("down", "--timeout", "10")
        assert other_containers == execute(["docker", "ps", "-aq"]).stdout.split()
        assert other_volumes == execute(["docker", "volume", "ls", "-q"]).stdout.split()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    args = parser.parse_args()
    if os.name != "posix" or os.geteuid() != 0:
        parser.error("Use isolated root Linux CI only; never on a NAS")
    with tempfile.TemporaryDirectory(prefix="notenarchiv-stack-") as directory:
        smoke(Path(directory), args.image)
