# Actions runtime maintenance — 2026-11-27

The CI and preview-release workflows now pin supported Node.js 24 actions.
Upstream release tags and their resolved commits were checked through GitHub's
release/ref API and `action.yml` at each pinned commit (not inferred from tag names).

| Upstream | Release | Pinned commit |
| --- | --- | --- |
| [actions/checkout](https://github.com/actions/checkout/releases/tag/v7.0.1) | v7.0.1 | `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| [actions/cache](https://github.com/actions/cache/releases/tag/v6.1.0) | v6.1.0 | `55cc8345863c7cc4c66a329aec7e433d2d1c52a9` |
| [astral-sh/setup-uv](https://github.com/astral-sh/setup-uv/releases/tag/v10.4.0) | v10.4.0 | `1db35dd8eee11c5894872e0b383ae6c406cf738d` |
| [docker/setup-buildx-action](https://github.com/docker/setup-buildx-action/releases/tag/v4.4.1) | v4.4.1 | `f87e5991a6d7451dcb8d9637bfbc97413f497069` |
| [actions/upload-artifact](https://github.com/actions/upload-artifact/releases/tag/v7.0.2) | v7.0.2 | `cf430e030ddbb5b0abf93d22962f4752f3646cd9` |
| [actions/download-artifact](https://github.com/actions/download-artifact/releases/tag/v8.0.2) | v8.0.2 | `9000827ccba6bdab643e8b6fd33ac0654aef8333` |
| [docker/login-action](https://github.com/docker/login-action/releases/tag/v4.8.0) | v4.8.0 | `8aa5831fb8d48d8f76594c7ddde61ae58019f550` |
| [actions/attest](https://github.com/actions/attest/releases/tag/v4.2.2) | v4.2.2 (unchanged) | `1e69f48acb82d1966a394da916b4c1698aa569d6` |

Compatibility review: hosted Ubuntu/Windows runners satisfy the Node 24 runner
minimum (2.327.1); authenticated container actions would require 2.329.0, but
these workflows do not run such git operations. Checkout's new fork protection
does not require an unsafe override: neither privileged trigger is used.
Existing uv 0.13.1, Python 3.12, cache inputs and SHA verification behavior remain.
Artifact ZIP mode is explicit; multi-file names, retention, immutable uploads,
the recovery ZIP's mandatory digest and exact member-set validation remain.
Download now fails on digest mismatch by default. Registry authentication,
permissions, synthetic data, scanners and all required checks are unchanged.
No release, registry publication or deployment is performed by this maintenance.

Local environment: `uv` and `gh` are available; `node` and `npm` are not on PATH.
This is separate from hosted Actions runtime deprecation. No system installation
or external-directory permission is needed; actual browser execution remains a
mandatory exact-SHA CI gate, not a locally passed claim.
