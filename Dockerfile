# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.13.1@sha256:4a1f3666816dafadd20ceb71eac9a7d56d7ef30279f7d64048519ab901ada336 AS uv
FROM python:3.12.16-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df AS build
COPY --from=uv /uv /bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
WORKDIR /build
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project --python /usr/local/bin/python
COPY static ./static
COPY scripts/collect_static.py ./collect_static.py
RUN /opt/venv/bin/python collect_static.py

FROM python:3.12.16-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df
ARG APP_VERSION=0.1.0-preview.1
ARG VCS_REF=unknown
LABEL org.opencontainers.image.source="https://github.com/tostman1/notenarchiv" \
      org.opencontainers.image.title="Notenarchiv technical preview" \
      org.opencontainers.image.version=$APP_VERSION \
      org.opencontainers.image.revision=$VCS_REF
ENV PATH="/opt/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    NOTENARCHIV_PROFILE=nas NOTENARCHIV_RELEASE=$APP_VERSION
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
