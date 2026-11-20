"""Startup validation command tests (WP-02 acceptance)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from django.core.management import get_commands

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_LOCAL_ROOT = PROJECT_ROOT / ".dev" / "pytest"

# Business configuration variables that tests must always control
# explicitly; any of them leaking in from the parent environment would make
# the subprocess runs non-deterministic.
_CONTROLLED_VARS = (
    "NOTENARCHIV_PROFILE",
    "NOTENARCHIV_LOCAL_ROOT",
    "DEBUG_MODE",
    "APP_ALLOWED_HOSTS",
    "APP_BIND",
    "APP_PORT",
    "DATABASE_PATH",
    "SOURCE_DIR",
    "CURATED_DIR",
    "PROCESSED_DIR",
    "STATUS_DIR",
    "EXPORT_DIR",
    "DJANGO_SECRET_KEY_FILE",
    "PRINT_ENABLED",
    "OCR_DPI",
    "TZ",
    # pytest-django exports the test settings module; subprocesses must use
    # the real project settings (manage.py default), so it is reset here.
    "DJANGO_SETTINGS_MODULE",
)


def _venv_python() -> str:
    """The interpreter of the current (uv-managed) virtual environment."""
    return sys.executable


def _run_command(*args: str, **overrides: str) -> subprocess.CompletedProcess[str]:
    """Run manage.py in a subprocess with a deterministic test environment.

    The parent environment is kept as the base (the Windows Python runtime
    needs SystemRoot/PATH); all business configuration is reset and then
    overridden explicitly, so results do not depend on the shell.
    """
    env = {key: value for key, value in os.environ.items() if key not in _CONTROLLED_VARS}
    env.update(
        {
            "NOTENARCHIV_PROFILE": "local",
            "NOTENARCHIV_LOCAL_ROOT": str(TEST_LOCAL_ROOT),
            "DEBUG_MODE": "FALSE",
            "APP_ALLOWED_HOSTS": "localhost,127.0.0.1",
            "PYTHONPATH": str(PROJECT_ROOT),
        }
    )
    env.update(overrides)
    return subprocess.run(
        [_venv_python(), "manage.py", *args],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        env=env,
        timeout=60,
    )


class TestValidateConfigCommand:
    def test_web_service_validation_passes_in_local_profile(self) -> None:
        result = _run_command("validate_config", "--service", "web")
        assert result.returncode == 0, result.stderr
        assert "profile: local" in result.stdout
        assert "Django DEBUG is always False" in result.stdout
        assert "configuration OK" in result.stdout

    def test_worker_service_validation_passes_in_local_profile(self) -> None:
        result = _run_command("validate_config", "--service", "worker")
        assert result.returncode == 0, result.stderr
        assert "CURATED (CLEAN) writable" in result.stdout
        assert "PROCESSED writable" in result.stdout
        assert "STATUS writable" in result.stdout
        assert "EXPORT writable" in result.stdout

    def test_nas_profile_missing_configuration_fails_with_clear_error(self) -> None:
        """A misconfigured nas profile (no secret file, no hosts, no roots)
        must fail loudly at startup instead of starting degraded."""
        result = _run_command("validate_config", NOTENARCHIV_PROFILE="nas")
        assert result.returncode != 0
        combined = result.stderr + result.stdout
        assert "DJANGO_SECRET_KEY_FILE" in combined

    def test_debug_mode_true_does_not_enable_django_debug_in_command(self) -> None:
        result = _run_command("validate_config", "--service", "web", DEBUG_MODE="TRUE")
        assert result.returncode == 0, result.stderr
        assert "DEBUG_MODE: TRUE" in result.stdout
        assert "Django DEBUG is always False" in result.stdout


def test_command_exists_in_django_shell() -> None:
    """The command is discoverable by the management framework."""
    assert "validate_config" in get_commands()
