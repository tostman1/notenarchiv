# Notenarchiv 0.1.0-preview.1 — technical installation preview

First web-only installation preview for Synology DS224+ / Linux amd64.
This is not the full Notenarchiv application or the personal-folder MVP.

Included: authenticated German responsive shell; clear disabled feature
navigation; health endpoint; Deploy/Debug diagnostics; strict configuration,
non-root and mount validation; persistent SQLite; explicit one-shot migrations
and interactive archivist provisioning; private HTTPS-proxy backend; scoped
container CI, security scans, SBOM and versioned release evidence.

Web and a small mount-free TCP gateway use the same image. Web stays on an
internal network; only the gateway publishes NAS loopback and it has no
data/archive/secret access. No processing worker is deployed.

Not available: archive import/review, catalog/member editing, project workflows,
OCR, PDF generation, scan processing, marchbooks and printing. No worker is
deployed; the existing job framework remains in the common codebase for later
integration. No placeholder action changes archive data.

Use **empty or synthetic roots only**. Do not attach actual music/member data.
Read INSTALL.de.md / INSTALL.md, DEBUG_MODE.md, UPDATE.md and RESTORE.md in the
installation bundle. Real DSM ACL/TLS/hardware validation remains the separate
authorized NAS acceptance step. No release workflow deploys to the NAS.

The proposed source version is not proof of publication. Only a successful
release run supplies `release-digest.txt`, the pulled GHCR reference, SBOM and
installation archive. Use that immutable digest in APP_IMAGE. Do not use
`latest` or overwrite an existing version tag. No stable release is enabled
before full acceptance.
