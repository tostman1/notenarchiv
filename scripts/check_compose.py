"""Check the rendered deployment contract using the real Docker Compose parser."""

import json
import os
import subprocess

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
    result = subprocess.run(
        [*command, "config", "--format", "json"],
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    config = json.loads(result.stdout)
    assert set(config["services"]) == {"web", "migrate", "admin"}
    assert config["networks"]["backend"]["internal"]
    for name, service in config["services"].items():
        assert service["read_only"] and service["user"] == "10001:10001"
        assert service["environment"].get("DEBUG_MODE") == ("TRUE" if debug else None)
        assert service["environment"]["PRINT_ENABLED"] == "0"
        for mount in service["volumes"]:
            assert mount["bind"]["create_host_path"] is False
            assert mount.get("read_only", False) == (mount["target"] != "/data")
        if name != "web":
            assert service["profiles"] == ["tools"] and not service.get("ports")
    assert config["services"]["web"]["ports"][0]["host_ip"] == "127.0.0.1"
