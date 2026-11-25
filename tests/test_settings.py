"""Settings and environment contract tests (WP-02, OP-01/OP-03/OP-04)."""

from __future__ import annotations

import os

import pytest
from django.conf import settings

from config.env import ConfigError, env, parse_env


def local_env(tmp_path, **overrides: str) -> dict[str, str]:
    """Minimal local-profile environment rooted in a real temp directory."""
    base = {
        "NOTENARCHIV_PROFILE": "local",
        "NOTENARCHIV_LOCAL_ROOT": str(tmp_path),
    }
    base.update(overrides)
    return base


def nas_env(tmp_path, secret_content: str = "k\n", **overrides) -> dict[str, str]:
    """Minimal nas-profile environment with a secret file written to tmp_path."""
    secret_file = tmp_path / "secret.key"
    secret_file.write_text(secret_content, encoding="utf-8")
    base = {
        "DJANGO_SECRET_KEY_FILE": str(secret_file),
        "APP_ALLOWED_HOSTS": "example.invalid",
        "DATABASE_PATH": "/data/db.sqlite3",
        "SOURCE_DIR": "/a",
        "CURATED_DIR": "/b",
        "PROCESSED_DIR": "/c",
        "STATUS_DIR": "/d",
        "EXPORT_DIR": "/e",
    }
    base.update(overrides)
    return base


class TestProfileSelection:
    def test_nas_is_the_default_profile(self, tmp_path) -> None:
        """Deployment stays the default: an absent NOTENARCHIV_PROFILE selects nas."""
        parsed = parse_env(nas_env(tmp_path))
        assert parsed.profile == "nas"

    def test_profile_values_are_case_and_whitespace_insensitive(self, tmp_path) -> None:
        assert parse_env(local_env(tmp_path, NOTENARCHIV_PROFILE=" LOCAL ")).profile == "local"

    def test_invalid_profile_fails_clearly(self) -> None:
        with pytest.raises(ConfigError, match="NOTENARCHIV_PROFILE"):
            parse_env({"NOTENARCHIV_PROFILE": "production"})

    @pytest.mark.parametrize("value", ["TRUE", "true", " False ", "FALSE", None])
    def test_local_profile_selects_loopback_defaults(self, tmp_path, value: str | None) -> None:
        mapping = local_env(tmp_path)
        if value is not None:
            mapping["DEBUG_MODE"] = value
        parsed = parse_env(mapping)
        assert parsed.profile == "local"
        assert parsed.bind == "127.0.0.1"
        assert set(parsed.allowed_hosts) == {"localhost", "127.0.0.1"}


class TestDebugMode:
    def test_debug_mode_true_never_enables_django_debug(self, tmp_path) -> None:
        """GR-13: DEBUG_MODE=TRUE enables application diagnostics only; the
        Django settings DEBUG flag is always False."""
        parsed = parse_env(local_env(tmp_path, DEBUG_MODE="TRUE"))
        assert parsed.debug_mode is True
        assert settings.DEBUG is False

    @pytest.mark.parametrize("raw", ["", "MAYBE", "1", "on", "TRU"])
    def test_invalid_debug_mode_fails_clearly(self, raw: str) -> None:
        from config.env import parse_debug_mode

        with pytest.raises(ConfigError, match="DEBUG_MODE"):
            parse_debug_mode(raw)

    def test_worker_and_local_log_directory(self, tmp_path) -> None:
        parsed = parse_env(local_env(tmp_path, NOTENARCHIV_SERVICE="worker"))
        assert parsed.service == "worker"
        assert parsed.log_dir == tmp_path / "logs"

    def test_invalid_service(self, tmp_path) -> None:
        with pytest.raises(ConfigError, match="NOTENARCHIV_SERVICE"):
            parse_env(local_env(tmp_path, NOTENARCHIV_SERVICE="../raw"))

    def test_debug_log_directory_must_be_separate(self, tmp_path) -> None:
        with pytest.raises(ConfigError, match="separate"):
            parse_env(local_env(tmp_path, DEBUG_MODE="TRUE", SOURCE_DIR=str(tmp_path / "logs")))

    def test_test_session_settings_are_deploy_safe(self) -> None:
        """The running settings module (test session) keeps DEBUG False."""
        assert settings.DEBUG is False


class TestSecretHandling:
    def test_nas_profile_requires_secret_file(self, tmp_path) -> None:
        with pytest.raises(ConfigError, match="DJANGO_SECRET_KEY_FILE"):
            parse_env(
                {
                    "APP_ALLOWED_HOSTS": "example.invalid",
                    "DATABASE_PATH": str(tmp_path / "db.sqlite3"),
                    "SOURCE_DIR": "/a",
                    "CURATED_DIR": "/b",
                    "PROCESSED_DIR": "/c",
                    "STATUS_DIR": "/d",
                    "EXPORT_DIR": "/e",
                }
            )

    def test_nas_profile_reads_secret_from_protected_file(self, tmp_path) -> None:
        parsed = parse_env(nas_env(tmp_path))
        assert parsed.profile == "nas"
        assert parsed.secret_key == "k"

    def test_missing_secret_file_fails_clearly(self, tmp_path) -> None:
        with pytest.raises(ConfigError, match="cannot read secret key file"):
            parse_env(nas_env(tmp_path, DJANGO_SECRET_KEY_FILE=str(tmp_path / "absent")))

    def test_empty_secret_file_fails_clearly(self, tmp_path) -> None:
        with pytest.raises(ConfigError, match="empty"):
            parse_env(nas_env(tmp_path, secret_content="   \n"))


class TestHostAndBinding:
    def test_nas_profile_requires_non_empty_hosts(self, tmp_path) -> None:
        with pytest.raises(ConfigError, match="APP_ALLOWED_HOSTS"):
            parse_env(nas_env(tmp_path, APP_ALLOWED_HOSTS="  , "))

    def test_local_profile_rejects_non_loopback_binding(self, tmp_path) -> None:
        with pytest.raises(ConfigError, match="loopback"):
            parse_env(local_env(tmp_path, APP_BIND="0.0.0.0"))

    def test_local_profile_rejects_duplicate_roots(self, tmp_path) -> None:
        with pytest.raises(ConfigError, match="distinct paths"):
            parse_env(
                local_env(
                    tmp_path,
                    SOURCE_DIR=str(tmp_path / "same"),
                    CURATED_DIR=str(tmp_path / "same"),
                )
            )

    def test_port_and_integer_validation(self, tmp_path) -> None:
        parsed = parse_env(local_env(tmp_path, APP_PORT="9090"))
        assert parsed.port == 9090
        with pytest.raises(ConfigError, match="APP_PORT must be an integer"):
            parse_env(local_env(tmp_path, APP_PORT="abc"))
        with pytest.raises(ConfigError, match="OCR_DPI"):
            parse_env(local_env(tmp_path, OCR_DPI="0"))

    @pytest.mark.parametrize(
        "overrides",
        [
            {"SOURCE_DIR": "raw", "CURATED_DIR": "raw/clean"},
            {"SOURCE_DIR": "raw/nested", "CURATED_DIR": "raw"},
            {"SOURCE_DIR": ""},
            {"DATABASE_PATH": "raw/data.sqlite3"},
            {"DATABASE_PATH": "secret.key"},
            {"DATABASE_PATH": "logs/data.sqlite3"},
            {"SOURCE_DIR": "logs/raw"},
        ],
    )
    def test_conflicting_local_paths_fail_before_initialization(self, tmp_path, overrides):
        root = tmp_path / "uninitialized"
        configured = {name: str(root / value) for name, value in overrides.items()}
        with pytest.raises(ConfigError):
            parse_env(local_env(root, **configured))
        assert not root.exists()

    @pytest.mark.parametrize("target", ["database", "secret"])
    def test_local_runtime_rejects_hardlinked_files_without_modification(self, tmp_path, target):
        root = tmp_path / "runtime"
        root.mkdir()
        original = tmp_path / "original"
        original.write_bytes(b"Synthetic retained bytes")
        linked = root / ("data.sqlite3" if target == "database" else "secret.key")
        linked.hardlink_to(original)
        overrides = {"DATABASE_PATH": str(linked)} if target == "database" else {}
        with pytest.raises(ConfigError, match="single-link regular files"):
            parse_env(local_env(root, **overrides))
        assert original.read_bytes() == b"Synthetic retained bytes"
        assert not (root / "raw").exists()

    def test_linked_local_root_is_rejected_before_secret_creation(self, tmp_path):
        outside = tmp_path / "outside"
        outside.mkdir()
        linked = tmp_path / "linked"
        try:
            linked.symlink_to(outside, target_is_directory=True)
        except OSError:
            pytest.skip("Creating synthetic symlinks requires platform permission")
        with pytest.raises(ConfigError, match="links and reparse points"):
            parse_env(local_env(linked))
        assert list(outside.iterdir()) == []

    def test_local_path_metadata_errors_use_fixed_configuration_message(self, tmp_path, monkeypatch):
        def denied(*args, **kwargs):
            raise PermissionError("Synthetic private path")

        monkeypatch.setattr("config.env.Path.lstat", denied)
        with pytest.raises(ConfigError, match="Local runtime path metadata is unavailable") as error:
            parse_env(local_env(tmp_path))
        assert "Synthetic private path" not in str(error.value)

    @pytest.mark.skipif(os.name != "nt", reason="Windows namespace normalization")
    @pytest.mark.parametrize("source", ["raw.", "raw /nested", "CON", "COM1.txt", "raw:stream", "raw?"])
    def test_windows_namespace_aliases_fail_before_initialization(self, tmp_path, source):
        root = tmp_path / "uninitialized"
        with pytest.raises(ConfigError, match="unsupported Windows name"):
            parse_env(local_env(root, SOURCE_DIR=str(root / source), CURATED_DIR=str(root / "raw")))
        assert not root.exists()

    def test_boolean_flag_validation(self, tmp_path) -> None:
        assert parse_env(local_env(tmp_path)).print_enabled is False
        parsed = parse_env(local_env(tmp_path, PRINT_ENABLED="1"))
        assert parsed.print_enabled is True
        with pytest.raises(ConfigError, match="PRINT_ENABLED"):
            parse_env(local_env(tmp_path, PRINT_ENABLED="yes-please"))

    def test_defaults_match_architecture_contract(self, tmp_path) -> None:
        parsed = parse_env(local_env(tmp_path))
        assert parsed.tz == "Europe/Vienna"
        assert parsed.port == 8085
        assert parsed.pdf_max_bytes == 104_857_600
        assert parsed.pdf_max_render_pixels == 30_000_000
        assert parsed.ocr_languages == "deu+eng"
        assert parsed.ocr_dpi == 300
        assert parsed.ocr_timeout_seconds == 60
        assert parsed.ocr_workers == 1
        assert parsed.omp_thread_limit == 2
        assert parsed.print_enabled is False


class TestSessionSettings:
    def test_app_boundaries_registered(self) -> None:
        from django.apps import apps

        labels = {app_config.label for app_config in apps.get_app_configs()}
        for app in ("accounts", "catalog", "members", "archive", "projects", "exports", "printing", "jobs"):
            assert app in labels

    def test_database_points_into_test_local_root(self) -> None:
        # The Django test runner swaps in a temporary database, so verify the
        # configured (env-derived) path instead of the live DATABASES dict.
        db_path = str(env.database_path)
        assert ".dev" in db_path
        assert "pytest" in db_path

    def test_static_and_i18n_configuration(self) -> None:
        assert settings.STATIC_URL == "/static/"
        assert settings.LANGUAGE_CODE == "de"
        assert "whitenoise.middleware.WhiteNoiseMiddleware" in settings.MIDDLEWARE
