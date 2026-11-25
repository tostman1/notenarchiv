"""Central parsing and validation of deployment environment variables.

Implements the deployment variable contract of ARCHITECTURE.md section 9.1.
This module is the single place that reads the environment: settings, the
startup validation command and tests all consume :func:`parse_env`, and no
other code may call ``os.environ`` directly for business configuration.

Rules:

- ``NOTENARCHIV_PROFILE`` selects ``local`` (explicit dev profile) or
  ``nas`` (deployment default, also the default when the variable is absent).
- ``DEBUG_MODE`` follows the OP-04 contract: absent or ``FALSE`` (trimmed,
  case-insensitive) means Deploy; ``TRUE`` means application diagnostics;
  any other value (including explicitly empty) fails clearly.
- ``DEBUG_MODE`` never affects Django ``DEBUG``, which is always False.
- Invalid or missing values raise :class:`ConfigError` with an actionable
  message; the process must fail at startup, not silently degrade.
"""

from __future__ import annotations

import os
import re
import secrets
import stat
from dataclasses import dataclass
from pathlib import Path

from core.naming import RESERVED

PROFILES = ("nas", "local")

DEFAULT_TZ = "Europe/Vienna"
DEFAULT_PORT = 8085

# Initial limits (OP-02 / OP-04): bounded PDF handling and OCR resources.
DEFAULT_PDF_MAX_BYTES = 104_857_600
DEFAULT_PDF_MAX_RENDER_PIXELS = 30_000_000
DEFAULT_OCR_LANGUAGES = "deu+eng"
DEFAULT_OCR_DPI = 300
DEFAULT_OCR_TIMEOUT_SECONDS = 60
DEFAULT_OCR_WORKERS = 1
DEFAULT_OMP_THREAD_LIMIT = 2

# Local dev profile root; relative to the project root, git-ignored.
LOCAL_DEV_ROOT = Path(".dev")


class ConfigError(ValueError):
    """Raised for missing or invalid deployment configuration."""


@dataclass(frozen=True, slots=True)
class EnvSettings:
    """Validated, typed view of the deployment environment."""

    profile: str
    dev_login_token: str
    debug_mode: bool
    release: str
    service: str
    log_dir: Path
    # Core Django contract
    secret_key: str
    allowed_hosts: list[str]
    csrf_trusted_origins: list[str]
    # Time zone
    tz: str
    # Network binding
    bind: str
    port: int
    # Secret file (NAS profile)
    secret_key_file: Path
    # Roots
    source_dir: Path
    curated_dir: Path
    processed_dir: Path
    status_dir: Path
    export_dir: Path
    database_path: Path
    # Limits and processing defaults
    pdf_max_bytes: int
    pdf_max_render_pixels: int
    ocr_languages: str
    ocr_dpi: int
    ocr_timeout_seconds: int
    ocr_workers: int
    omp_thread_limit: int
    # Feature flags
    print_enabled: bool
    # The deployment (nas) profile is always served over the private HTTPS
    # reverse proxy, so secure-cookie and SSL-redirect flags are forced on.
    # The local profile is plain HTTP on loopback. This is a data-transport
    # property of the profile, not a security weakening in production.
    secure_transport_required: bool


def parse_debug_mode(raw: str | None) -> bool:
    """Parse ``DEBUG_MODE`` per the OP-04 contract.

    ``None`` (absent) or ``FALSE`` => Deploy (False); ``TRUE`` => application
    diagnostics (True). Comparison is case-insensitive and whitespace-trimmed.
    Any other value, including an explicitly empty string, raises
    :class:`ConfigError` so misconfiguration fails clearly.
    """
    if raw is None:
        return False
    normalized = raw.strip().upper()
    if normalized not in {"TRUE", "FALSE"}:
        raise ConfigError("DEBUG_MODE must be TRUE or FALSE")
    return normalized == "TRUE"


def _profile(env: dict[str, str], errors: list[str]) -> str:
    raw = env.get("NOTENARCHIV_PROFILE")
    if raw is None:
        return "nas"
    normalized = raw.strip().lower()
    if normalized not in PROFILES:
        errors.append(f"NOTENARCHIV_PROFILE must be one of {', '.join(PROFILES)}, got {raw!r}")
        return "nas"
    return normalized


def _string(env: dict[str, str], name: str, default: str | None = None, required: bool = False) -> str:
    raw = env.get(name)
    if raw is None:
        if required:
            raise ConfigError(f"{name} is required and not set")
        if default is None:
            raise ConfigError(f"{name} is required but no default exists")
        return default
    if required and raw.strip() == "":
        raise ConfigError(f"{name} is set but empty")
    return raw.strip()


def _list(env: dict[str, str], name: str) -> list[str]:
    raw = env.get(name)
    if raw is None:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _int(env: dict[str, str], name: str, default: int, minimum: int = 1) -> int:
    raw = env.get(name)
    if raw is None:
        return default
    try:
        value = int(raw.strip())
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc
    if value < minimum:
        raise ConfigError(f"{name} must be >= {minimum}, got {value}")
    return value


def _bool_flag(env: dict[str, str], name: str, default: bool) -> bool:
    raw = env.get(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"0", "false", "no", "off"}:
        return False
    if normalized in {"1", "true", "yes", "on"}:
        return True
    raise ConfigError(f"{name} must be a boolean (0/1, true/false), got {raw!r}")


def parse_env(env: dict[str, str] | None = None) -> EnvSettings:
    """Parse and validate the deployment environment.

    ``env`` defaults to ``os.environ``; tests pass an explicit mapping so
    they are isolated from the surrounding environment.
    """
    if env is None:
        env = dict(os.environ)

    errors: list[str] = []
    profile = _profile(env, errors)
    if errors:
        raise ConfigError("; ".join(errors))

    debug_mode = parse_debug_mode(env.get("DEBUG_MODE"))
    release = _string(env, "NOTENARCHIV_RELEASE", default="0.1.0-preview.1")
    if not re.fullmatch(r"[A-Za-z0-9.+-]{1,64}", release):
        raise ConfigError("NOTENARCHIV_RELEASE is invalid")

    service = _string(env, "NOTENARCHIV_SERVICE", default="web")
    if service not in {"web", "worker"}:
        raise ConfigError("NOTENARCHIV_SERVICE must be web or worker")

    if profile == "nas":
        log_dir = Path("/data/logs")
        secret_key_file = Path(_string(env, "DJANGO_SECRET_KEY_FILE", required=True))
        secret_key = _read_secret_key(secret_key_file)
        allowed_hosts = _list(env, "APP_ALLOWED_HOSTS")
        if not allowed_hosts:
            raise ConfigError("APP_ALLOWED_HOSTS is required in the nas profile and must not be empty")
        bind = _string(env, "APP_BIND", default="127.0.0.1")
        port = _int(env, "APP_PORT", default=DEFAULT_PORT, minimum=1)
        database_path = Path(_string(env, "DATABASE_PATH", required=True))
        secure_transport_required = True
        source_dir = Path(_string(env, "SOURCE_DIR", required=True))
        curated_dir = Path(_string(env, "CURATED_DIR", required=True))
        processed_dir = Path(_string(env, "PROCESSED_DIR", required=True))
        status_dir = Path(_string(env, "STATUS_DIR", required=True))
        export_dir = Path(_string(env, "EXPORT_DIR", required=True))
    else:  # local
        local_root = Path(_string(env, "NOTENARCHIV_LOCAL_ROOT", default=str(LOCAL_DEV_ROOT)))
        log_dir = local_root / "logs"
        secret_file = local_root / "secret.key"
        allowed_hosts = _list(env, "APP_ALLOWED_HOSTS") or ["localhost", "127.0.0.1"]
        bind = _string(env, "APP_BIND", default="127.0.0.1")
        port = _int(env, "APP_PORT", default=DEFAULT_PORT, minimum=1)
        if bind not in {"127.0.0.1", "localhost", "::1"}:
            raise ConfigError(f"local profile may only bind to loopback, got APP_BIND={bind!r}")
        secret_key_file = secret_file
        secure_transport_required = False
        database_path = Path(_string(env, "DATABASE_PATH", default=str(local_root / "datenarchiv.sqlite3")))
        source_dir = Path(_string(env, "SOURCE_DIR", default=str(local_root / "raw")))
        curated_dir = Path(_string(env, "CURATED_DIR", default=str(local_root / "clean")))
        processed_dir = Path(_string(env, "PROCESSED_DIR", default=str(local_root / "processed")))
        status_dir = Path(_string(env, "STATUS_DIR", default=str(local_root / "status")))
        export_dir = Path(_string(env, "EXPORT_DIR", default=str(local_root / "export")))
        # Local dev uses synthetic, mutually distinct roots (GR-01 analog).
        roots = {
            "SOURCE_DIR": source_dir,
            "CURATED_DIR": curated_dir,
            "PROCESSED_DIR": processed_dir,
            "STATUS_DIR": status_dir,
            "EXPORT_DIR": export_dir,
        }
        _validate_local_paths(roots, database_path, secret_file, log_dir)
        roots = {name: path.absolute() for name, path in roots.items()}
        source_dir = roots["SOURCE_DIR"]
        curated_dir = roots["CURATED_DIR"]
        processed_dir = roots["PROCESSED_DIR"]
        status_dir = roots["STATUS_DIR"]
        export_dir = roots["EXPORT_DIR"]
        database_path = database_path.absolute()
        secret_file = secret_file.absolute()
        secret_key_file = secret_file
        log_dir = log_dir.absolute()
        secret_key = _read_local_secret(secret_file)
        # The local profile is explicitly selected for development; its
        # synthetic roots and the database directory are created on first
        # use. The nas profile never auto-creates anything (WP-07 contract).
        for path in (*roots.values(), database_path.parent):
            path.mkdir(parents=True, exist_ok=True)

    if debug_mode:
        target = log_dir.resolve()
        for root in (source_dir, curated_dir, processed_dir, status_dir, export_dir):
            archive = root.resolve()
            if target.is_relative_to(archive) or archive.is_relative_to(target):
                raise ConfigError("Debug log directory must be separate from archive roots")

    return EnvSettings(
        profile=profile,
        dev_login_token=_dev_login_token(env, profile, bind),
        debug_mode=debug_mode,
        release=release,
        service=service,
        log_dir=log_dir,
        secret_key=secret_key,
        allowed_hosts=allowed_hosts,
        csrf_trusted_origins=_list(env, "APP_CSRF_TRUSTED_ORIGINS"),
        tz=_string(env, "TZ", default=DEFAULT_TZ),
        bind=bind,
        port=port,
        secret_key_file=secret_key_file,
        source_dir=source_dir,
        curated_dir=curated_dir,
        processed_dir=processed_dir,
        status_dir=status_dir,
        export_dir=export_dir,
        database_path=database_path,
        pdf_max_bytes=_int(env, "PDF_MAX_BYTES", default=DEFAULT_PDF_MAX_BYTES),
        pdf_max_render_pixels=_int(env, "PDF_MAX_RENDER_PIXELS", default=DEFAULT_PDF_MAX_RENDER_PIXELS),
        ocr_languages=_string(env, "OCR_LANGUAGES", default=DEFAULT_OCR_LANGUAGES),
        ocr_dpi=_int(env, "OCR_DPI", default=DEFAULT_OCR_DPI),
        ocr_timeout_seconds=_int(env, "OCR_TIMEOUT_SECONDS", default=DEFAULT_OCR_TIMEOUT_SECONDS),
        ocr_workers=_int(env, "OCR_WORKERS", default=DEFAULT_OCR_WORKERS),
        omp_thread_limit=_int(env, "OMP_THREAD_LIMIT", default=DEFAULT_OMP_THREAD_LIMIT),
        print_enabled=_bool_flag(env, "PRINT_ENABLED", default=False),
        secure_transport_required=secure_transport_required,
    )


def _dev_login_token(env, profile, bind):
    token = env.get("DEV_LOGIN_TOKEN", "")
    if token and (profile != "local" or bind != "127.0.0.1" or len(token) < 32):
        raise ConfigError("Development login requires an explicit loopback local launcher token")
    return token


def _read_secret_key(path: Path) -> str:
    """Read a protected secret file (NAS profile)."""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"cannot read secret key file {path}: {exc.strerror or exc}") from exc
    key = content.strip()
    if not key:
        raise ConfigError(f"secret key file {path} is empty")
    return key


def _validate_local_paths(roots, database, secret, logs):
    """Reject conflicting configured write targets before local initialization."""
    for path in (*roots.values(), database, secret, logs):
        if ".." in path.parts:
            raise ConfigError("Local runtime paths must not contain parent traversal")
        if os.name == "nt":
            for component in path.parts:
                if component == path.anchor:
                    continue
                if (
                    component.endswith((" ", "."))
                    or RESERVED.match(component)
                    or any(char in '<>:"|?*' or ord(char) < 32 for char in component)
                ):
                    raise ConfigError("Local runtime paths contain an unsupported Windows name")
        absolute = path.absolute()
        for component in (absolute, *absolute.parents):
            try:
                info = component.lstat()
            except FileNotFoundError:
                continue
            except OSError:
                raise ConfigError("Local runtime path metadata is unavailable") from None
            reparse_point = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & reparse_point:
                raise ConfigError("Local runtime paths must be free of links and reparse points")
    for path in (database, secret):
        try:
            info = path.lstat()
        except FileNotFoundError:
            continue
        except OSError:
            raise ConfigError("Local runtime file metadata is unavailable") from None
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ConfigError("Local runtime database and secret must be single-link regular files")
    resolved = [(name, path.resolve()) for name, path in roots.items()]
    for index, (name, path) in enumerate(resolved):
        for other_name, other in resolved[index + 1 :]:
            if path.is_relative_to(other) or other.is_relative_to(path):
                raise ConfigError(f"local profile roots {name} and {other_name} must be distinct paths without nesting")
        for target in (database.resolve(), secret.resolve(), logs.resolve()):
            if target.is_relative_to(path) or path.is_relative_to(target):
                raise ConfigError("Local runtime files and logs must be separate from archive roots")
    if database.resolve() == secret.resolve():
        raise ConfigError("Local database and secret must be distinct files")
    for target in (database.resolve(), secret.resolve()):
        if target.is_relative_to(logs.resolve()) or logs.resolve().is_relative_to(target):
            raise ConfigError("Local runtime files must be separate from logs")


def _read_local_secret(path: Path) -> str:
    """Read or create the dev-only secret file of the local profile.

    The local profile is explicitly selected and is safe for development:
    it binds to loopback only and uses synthetic roots. The generated dev
    secret is a development convenience, never used in the nas profile.
    """
    if path.exists():
        key = path.read_text(encoding="utf-8").strip()
        if key:
            return key
        raise ConfigError(f"local dev secret file {path} is empty")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        key = _generate_secret()
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(key + "\n")
    except OSError as exc:
        raise ConfigError(f"cannot create local dev secret file {path}: {exc.strerror or exc}") from exc
    return key


def _generate_secret() -> str:
    return secrets.token_urlsafe(48)


#: Validated environment for this process. Imported by settings and the
#: ``validate_config`` management command; tests call :func:`parse_env`
#: directly with explicit mappings instead.
env = parse_env()
