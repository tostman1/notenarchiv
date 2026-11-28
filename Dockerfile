# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.13.1@sha256:4a1f3666816dafadd20ceb71eac9a7d56d7ef30279f7d64048519ab901ada336 AS uv
FROM python:3.12.16-alpine3.24@sha256:c5ba3deef00c7758561a0f03c26f44f10589263d40e732b8748e0d1f38f6dd89 AS python-base
# The pinned upstream image predates Alpine's Kerberos security fixes.
RUN apk add --no-cache krb5-libs=1.22.3-r0

FROM python-base AS build
COPY --from=uv /uv /bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
WORKDIR /build
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project --python /usr/local/bin/python
COPY static ./static
COPY scripts/collect_static.py ./collect_static.py
RUN /opt/venv/bin/python collect_static.py

FROM python-base
RUN apk add --no-cache tesseract-ocr=5.5.2-r0 tesseract-ocr-data-deu=5.5.2-r0 tesseract-ocr-data-eng=5.5.2-r0
ARG APP_VERSION=unpublished-ci
ARG VCS_REF=unknown
LABEL org.opencontainers.image.source="https://github.com/tostman1/notenarchiv" \
      org.opencontainers.image.title="Notenarchiv" \
      org.opencontainers.image.version=$APP_VERSION \
      org.opencontainers.image.revision=$VCS_REF
ENV PATH="/opt/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    NOTENARCHIV_PROFILE=nas NOTENARCHIV_RELEASE=$APP_VERSION DJANGO_SETTINGS_MODULE=config.settings
WORKDIR /app
COPY --from=build /opt/venv /opt/venv
COPY --from=build /opt/staticfiles /app/staticfiles
COPY apps ./apps
COPY config ./config
COPY core ./core
COPY templates ./templates
COPY static ./static
COPY manage.py ./manage.py
COPY scripts/container_entrypoint.py scripts/healthcheck.py scripts/gateway.py ./scripts/
COPY docs/LICENSES.md ./THIRD_PARTY_NOTICES.md
RUN mkdir -p /data /archive/raw /archive/clean /archive/processed /archive/status /archive/export /run/secrets
USER 65532:65532
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD ["python", "-m", "scripts.healthcheck"]
ENTRYPOINT ["python", "-m", "scripts.container_entrypoint"]
CMD ["web"]
