# Published technical previews

## 0.1.0-test.1 — current-feature synthetic distribution, 2026-11-24

Test-only image through integrated WP-39. PR #51 merged as
`4ccd2698204a1e69ec7c1c4f128acf8e6c65d809`; final PR CI `45407719536` and main CI
`45411431365` passed 956 Linux tests/26 browsers and complete hardened Compose,
private TLS/browser, indexing/review/publication/matrix/PDF/download/recovery/RAW
acceptance plus dependency/image/secret scans. No NAS deployment or real data.

Published image, independently verified anonymous GHCR tag/digest manifests:

```text
ghcr.io/tostman1/notenarchiv:0.1.0-test.1
ghcr.io/tostman1/notenarchiv@sha256:f628501dbc3fbe65c4e53bb2ab6c4723bd4014bca582656383ffd528df543e5a
```

Exact application source: `4ccd2698204a1e69ec7c1c4f128acf8e6c65d809`.
Original release/check/publish run: `45415635235`; promotion loaded the verified
candidate artifact without rebuilding, checked identity/version/source, pushed
and pulled the registry digest. The published digest passed the complete
synthetic Compose stack again. Source and CycloneDX SBOM attestations were signed
and stored in GHCR. Local `gh attestation verify` cryptographically verified both
`https://slsa.dev/provenance/v1` and `https://cyclonedx.org/bom` against this exact
digest, repository, original source SHA and signer `.github/workflows/release.yml`.

Original verified-container artifact `14932487454`, archive digest
`sha256:a6379515a170ac09badf649f7d3175672b2e379ac59e629db5954d5eaf6d33b5`.
Published-evidence artifact `14933417646`, archive digest
`sha256:f5856cacdbb1b66fa4c86b64ec2b14483ee50edd8f90bb5bda408de68a7812d7`.
**Packaging completion pending:** only the original announcement shell failed
on an indented heredoc after checks, publication, pulled-stack and attestations
had succeeded. PR #52 fixes the shell and pins source install Compose to the
real digest. Recovery must reuse the original hash-verified candidate, preserve
image/tag and publish the final installation assets; no completion claimed yet.

Final source Compose: `deploy/synology-test/compose.yaml`; German guide:
`deploy/synology-test/README.de.md`. The separately published installation bundle
is `notenarchiv-synology-test.tar.gz`. Hardware DSM/ACL/TLS/firewall, local
SQLite/WAL, RAM/recovery/scratch and complete NAS restore acceptance remain.
Existing `v0.1.0-preview.1` artifacts are unchanged.

## 0.1.0-preview.1 — 2026-11-20

Owner-approved web-only, empty/synthetic-data preview. No live NAS deployment
or real archive attachment was performed. Unavailable business features remain
disabled; see the German installation guide and the release notes.

- [GitHub prerelease and assets](https://github.com/tostman1/notenarchiv/releases/tag/v0.1.0-preview.1)
- [Installation bundle](https://github.com/tostman1/notenarchiv/releases/download/v0.1.0-preview.1/notenarchiv-preview-install.tar.gz)
- [Exact image reference](https://github.com/tostman1/notenarchiv/releases/download/v0.1.0-preview.1/release-digest.txt)
- [Original build/checks](https://github.com/tostman1/notenarchiv/actions/runs/44815669883)
- [Successful publication completion](https://github.com/tostman1/notenarchiv/actions/runs/44817372155)

Use this immutable APP_IMAGE value:

```text
ghcr.io/tostman1/notenarchiv@sha256:e6e01416737702598458af8c9167f2353e09074c445281d640eaa34f10658f4d
```

The version tag is `ghcr.io/tostman1/notenarchiv:0.1.0-preview.1`.
Anonymous registry manifest retrieval succeeded; no registry visibility or other
repository administration was changed. CI also pulled the actual image and
verified it against the original checked candidate. Docker is unavailable on
the Windows development host, so no local Docker pull is claimed.

Application source/tag commit: `62d85b36189293a59df2ef39729a538f5c53ad3b`.
Release recovery workflow commit: `24c3c8ea175b5c9d39df0813182cdbd39f55075b`.
The first tag run passed all required checks and pushed/pulled the image, then
failed while selecting a digest from multiple repositories. PR #9 fixed that
selection. Completion reused the original SHA-256-verified candidate without
rebuilding, moving the tag or overwriting the image version.

The recovery signs an explicit original-build/promotion predicate, rather than
claiming that the recovery commit built the application. Both it and the
CycloneDX SBOM are signed with Sigstore and uploaded to GitHub and GHCR:

- [Verified-release origin attestation](https://github.com/tostman1/notenarchiv/attestations/70331839)
- [SBOM attestation](https://github.com/tostman1/notenarchiv/attestations/70331881)
- [Signed origin claim as JSON](https://github.com/tostman1/notenarchiv/releases/download/v0.1.0-preview.1/release-origin.json)

Local `gh attestation verify` (2.105.0) cryptographically verified both predicate
types against `tostman1/notenarchiv`, signer workflow
`tostman1/notenarchiv/.github/workflows/release.yml`, and exact signer commit
`24c3c8ea175b5c9d39df0813182cdbd39f55075b`. The signed origin identifies the
original source and retained artifact; the signed SBOM matches the release file.

All five downloaded assets matched GitHub's SHA-256 metadata. Installation
bundle SHA-256:
`6b916074cb644ba729b25605955598617a26bfdfc18fbf5f8b4bd37bf1860e5c`.
All 12 bundled files matched the original tag source or the verified digest file.
Published metadata identifies Linux/amd64, non-root default UID/GID 65532, source
commit and version; the CycloneDX SBOM contains 45 components.

The application image passed 170 tests, two Playwright tests, actual container
mount/startup/auth/restart/mode/isolated-restore acceptance and vulnerability/
secret scans. The pipeline fix additionally passed its full CI. NAS/DSM ACL,
TLS, resources and actual backup destination acceptance remain separate WP-22
work and require explicit deployment authorization.


## Future simplified installation bundles (unpublished source improvement)

The original v0.1.0-preview.1 tag, image and release assets remain immutable.
Source now includes standalone `configuration.yaml` and guarded
`scripts/prepare-install.sh`. They use the existing published digest as their
starting example. Users can obtain these new installation files from the source
ZIP; they are not retroactively added to the original release archive.

For a future separately authorized release, `scripts/package_install.py` packages
the simple YAML/helper, advanced Compose/env example, primary German guide and
technical operating runbooks. It pins all simple-install image references to the
actual verified `release-digest.txt`, without modifying checked-out source files.
The resulting archive needs no generation/preprocessing by the installer. Bundle
creation is reproducible and refuses output overwrite or source/helper digest
drift. Historical source recovery retains its original packaging layout. None of
this publishes a new release or changes an existing asset; release notes and
image/schema compatibility must still be reviewed for the actual future release.
