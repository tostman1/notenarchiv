# Published technical previews

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
