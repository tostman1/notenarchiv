"""Settings and environment contract tests (WP-02, OP-01/OP-03/OP-04)."""

from __future__ import annotations

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
