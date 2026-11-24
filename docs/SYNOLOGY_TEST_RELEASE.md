# Current-feature Synology test distribution

Owner-authorized **test-only** distribution of the current integrated application
through WP-39. Not a stable production release, full product acceptance or actual
NAS deployment. Synthetic data only; never attach association music or members.

Web, the durable singleton worker and a mount-free private gateway use identical
Linux/amd64 image bytes. Read-only roots, least privilege, separate storage,
protected secrets, authentication, CSRF and HTTPS remain enforced. Migrations and
interactive account provisioning are one-shot operations.

Available: catalog/members, indexing, explicit visual review and publication,
library/downloads, project numbering/reserves/participants/ensemble/matrix,
preflight/missing decisions/immutable snapshots, personal reading PDFs, excerpts,
contents, regular A4/A3 print PDFs, export history/staleness/targeted generation.
Disabled: OCR, enhancement, marchbook-specific print rendering and physical
printing. Marchbook configuration exists but does not constitute a usable print
layout. Production NAS acceptance remains outstanding.

Download **notenarchiv-synology-test.tar.gz**, follow **README.de.md**, edit only
UID:GID and private HTTPS host/origin. The released **compose.yaml** pins the
actually published digest, uses project `notenarchiv-test`, loopback port 8090 and
isolated `/volume1/docker/notenarchiv-test` binds. No .env or NAS build required.

The mandatory publication workflow tests the candidate stack and then pulls and
tests the published digest without rebuilding the verified candidate. SBOM,
metadata and source provenance accompany the image. Actual DSM/ACL/firewall/TLS,
SQLite filesystem, memory and recovery acceptance remain private hardware gates.
Existing `v0.1.0-preview.1` image and release assets are unchanged.
