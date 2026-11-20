"""Django settings for the Notenarchiv application (WP-02 skeleton).

Security contract (OP-03, GR-13):

- ``DEBUG`` is **always False**, in every profile and mode.
- ``DEBUG_MODE`` (OP-04) only enables application diagnostics; it never
  relaxes authentication, CSRF, host validation or any other safeguard.
- All environment input is parsed centrally by :mod:`config.env` and
  validated at import time; invalid configuration fails the process at
  startup.

Profiles:

- ``nas`` (default): deployment profile; explicit, validated environment
  contract per ARCHITECTURE.md section 9.1, secret from a protected file.
- ``local``: explicitly selected development profile; loopback-only,
  synthetic roots, generated dev secret. It does not weaken any security
  setting used in production; it only chooses different data locations.
"""

from __future__ import annotations

from pathlib import Path

from config.db import _apply_sqlite_pragmas  # noqa: F401 - registers the connection_created signal
from config.env import env

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Security -------------------------------------------------------------

DEBUG = False  # GR-13: Django DEBUG is always False.

SECRET_KEY = env.secret_key
ALLOWED_HOSTS = env.allowed_hosts
CSRF_TRUSTED_ORIGINS = env.csrf_trusted_origins

# OP-04: application diagnostics flag, independent of Django DEBUG.
DEBUG_MODE = env.debug_mode

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_NAME = "notenarchiv_sessionid"
CSRF_COOKIE_NAME = "notenarchiv_csrftoken"
SECURE_HSTS_SECONDS = 0  # HSTS requires HTTPS at the proxy; configured there, not here.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")  # honored behind the reverse proxy.
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# --- Application ----------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Domain apps (WP-02 boundaries; models/views land in later packages).
    "apps.accounts.apps.AccountsConfig",
    "apps.catalog.apps.CatalogConfig",
    "apps.members.apps.MembersConfig",
    "apps.archive.apps.ArchiveConfig",
    "apps.projects.apps.ProjectsConfig",
    "apps.exports.apps.ExportsConfig",
    "apps.printing.apps.PrintingConfig",
    "apps.jobs.apps.JobsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# --- Database -------------------------------------------------------------

# SQLite on local NAS storage; foreign keys and busy timeout are enforced in
# config.db via Django's SQLite backend options and the connection signal.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": env.database_path,
        "OPTIONS": {
            "timeout": 5.0,
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Internationalization (UI is German) ----------------------------------

LANGUAGE_CODE = "de"
TIME_ZONE = env.tz
USE_I18N = True
USE_TZ = True
LOCALE_PATHS = [BASE_DIR / "locale"]

# --- Static files (local assets only, OP-06) ------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
WHITENOISE_ROOT = BASE_DIR / "static"

# --- Domain roots (business configuration) --------------------------------

SOURCE_DIR = env.source_dir
CURATED_DIR = env.curated_dir
PROCESSED_DIR = env.processed_dir
STATUS_DIR = env.status_dir
EXPORT_DIR = env.export_dir

# --- Processing limits (OP-02) --------------------------------------------

PDF_MAX_BYTES = env.pdf_max_bytes
PDF_MAX_RENDER_PIXELS = env.pdf_max_render_pixels
OCR_LANGUAGES = env.ocr_languages
OCR_DPI = env.ocr_dpi
OCR_TIMEOUT_SECONDS = env.ocr_timeout_seconds
OCR_WORKERS = env.ocr_workers
OMP_THREAD_LIMIT = env.omp_thread_limit

# --- Feature flags ---------------------------------------------------------

PRINT_ENABLED = env.print_enabled

# --- Logging (WP-04a replaces this with the full contract) ----------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
