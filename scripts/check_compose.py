"""Check the rendered deployment contract using the real Docker Compose parser."""

import json
import os
import subprocess
from pathlib import Path

environment = os.environ.copy()
environment.update(
    {
        "APP_IMAGE": "ghcr.io/tostman1/notenarchiv@sha256:" + "0" * 64,
        "APP_UID": "10001",
        "APP_GID": "10001",
        "APP_ALLOWED_HOSTS": "example.invalid,127.0.0.1,localhost",
        "APP_CSRF_TRUSTED_ORIGINS": "https://example.invalid",
        **{
            name: "/synthetic/" + name.lower()
            for name in (
                "SOURCE_HOST",
                "CURATED_HOST",
                "PROCESSED_HOST",
                "STATUS_HOST",
                "EXPORT_HOST",
                "DATA_HOST",
                "SECRET_HOST",
            )
        },
    }
)
for debug in (False, True):
    command = ["docker", "compose", "--env-file", "/dev/null", "-f", "compose.yaml"]
    if debug:
        command.extend(["-f", "compose.debug.yaml"])
    default = subprocess.run(
        [*command, "config", "--format", "json"],
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert set(json.loads(default.stdout)["services"]) == {"web", "gateway"}
    result = subprocess.run(
        [*command, "--profile", "tools", "config", "--format", "json"],
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    config = json.loads(result.stdout)
    assert set(config["services"]) == {"web", "gateway", "migrate", "admin"}
    assert config["networks"]["backend"]["internal"]
    for name, service in config["services"].items():
        assert service["read_only"] and service["user"] == "10001:10001"
        if name == "gateway":
            assert not service.get("volumes")
            assert set(service["networks"]) == {"backend", "frontend"}
            assert service["ports"][0]["host_ip"] == "127.0.0.1"
            assert service["depends_on"]["web"]["condition"] == "service_healthy"
            continue
        assert service["environment"].get("DEBUG_MODE") == ("TRUE" if debug else None)
        assert service["environment"]["PRINT_ENABLED"] == "0"
        for mount in service["volumes"]:
            assert mount["bind"]["create_host_path"] is False
            assert mount.get("read_only", False) == (mount["target"] != "/data")
        if name != "web":
            assert service["profiles"] == ["tools"] and not service.get("ports")
    assert not config["services"]["web"].get("ports")

# The simple file is self-contained, even if unrelated environment values exist.
simple = subprocess.run(
    [
        "docker",
        "compose",
        "--env-file",
        "/dev/null",
        "-f",
        "configuration.yaml",
        "--profile",
        "tools",
        "config",
        "--format",
        "json",
    ],
    env=environment,
    check=True,
    capture_output=True,
    text=True,
    timeout=30,
)
config = json.loads(simple.stdout)
reference = config["services"]["web"]["image"]
assert "${" not in Path("configuration.yaml").read_text()
assert reference.startswith("ghcr.io/tostman1/notenarchiv@sha256:") and len(reference.rsplit(":", 1)[1]) == 64
assert config["networks"]["backend"]["internal"]
for name, service in config["services"].items():
    assert service["image"] == reference and service["user"] == "CHANGE_UID:CHANGE_GID"
    assert service["read_only"] and service["cap_drop"] == ["ALL"]
    assert service["security_opt"] == ["no-new-privileges:true"]
    if name == "gateway":
        assert not service.get("volumes")
        assert service["ports"][0]["host_ip"] == "127.0.0.1"
        continue
    assert service["environment"]["PRINT_ENABLED"] == "0" and "DEBUG_MODE" not in service["environment"]
    assert not service.get("ports")
    for mount in service["volumes"]:
        assert mount["bind"]["create_host_path"] is False
        assert mount["source"].startswith("/volume1/docker/notenarchiv/")
        assert mount.get("read_only", False) == (mount["target"] != "/data")
    if name in {"migrate", "admin"}:
        assert service["profiles"] == ["tools"]
assert config["services"]["admin"]["logging"]["driver"] == "none"
