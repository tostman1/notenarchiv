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

import os
from pathlib import Path

from config.db import _apply_sqlite_pragmas  # noqa: F401 - registers the connection_created signal
from config.diagnostics import logging_config
from config.env import env
from config.runtime import file_logging_enabled

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Security -------------------------------------------------------------

DEBUG = False  # GR-13: Django DEBUG is always False.

SECRET_KEY = env.secret_key
ALLOWED_HOSTS = env.allowed_hosts
CSRF_TRUSTED_ORIGINS = env.csrf_trusted_origins

# OP-04: application diagnostics flag, independent of Django DEBUG.
DEBUG_MODE = env.debug_mode
RELEASE_VERSION = env.release
DEV_LOGIN_TOKEN = env.dev_login_token
DEVELOPMENT_PROFILE = env.profile == "local"

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_NAME = "notenarchiv_sessionid"
CSRF_COOKIE_NAME = "notenarchiv_csrftoken"
# Secure-cookie/redirect enforcement is part of the deployment contract: in
# the nas profile the app is always behind the private HTTPS reverse proxy
# (OP-03). The local development profile is plain HTTP on loopback, so the
# flags are only applied there if the explicit APP_BIND/APP_CSRF settings
# say otherwise; this is a data-location difference, not a weakening of
# production settings (they are exactly what the nas profile ships).
SECURE_SSL_REDIRECT = env.secure_transport_required
# Public liveness reveals no data and must work directly inside the private backend.
SECURE_REDIRECT_EXEMPT = [r"^healthz$"]
SESSION_COOKIE_SECURE = env.secure_transport_required
CSRF_COOKIE_SECURE = env.secure_transport_required
SECURE_HSTS_SECONDS = 0  # HSTS requires HTTPS at the proxy; configured there, not here.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")  # honored behind the reverse proxy.
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
LOGIN_URL = "login"

# Explicit password policy (OP-03; do not rely on framework defaults for a
# security-sensitive deployment). Applied by create_archivist and Django's
# auth forms alike.
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

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
                "config.context_processors.diagnostics",
                "config.features.availability",
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
STATICFILES_DIRS = [BASE_DIR / "static"]
WHITENOISE_USE_FINDERS = env.profile == "local"

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

LOGGING = logging_config(env.debug_mode, env.service, env.log_dir, file_logging=file_logging_enabled())
DIAGNOSTIC_LOG_DIR = env.log_dir
TEST_DISTRIBUTION = os.environ.get("NOTENARCHIV_TEST_DISTRIBUTION", "FALSE").strip().upper() == "TRUE"
