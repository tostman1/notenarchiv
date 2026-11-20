# Dependency license inventory (WP-01 mechanism, finalization in WP-51)

This file is the working inventory of the direct Python dependencies in
`uv.lock`. It records license metadata from actual package metadata; no
license is assumed or guessed.

## Direct dependencies

Verified against installed package metadata (`importlib.metadata`) of the
locked environment on 2026-11-19 (Windows dev environment, uv 0.12.5,
CPython 3.12.13):

| Package | Pinned version | License (from package metadata) | Status |
| --- | --- | --- | --- |
| Django | 5.2.10 | BSD-3-Clause | Verified from metadata |
| whitenoise | 6.12.0 | MIT | Verified from metadata (WP-02) |
| pytest | 8.4.1 (dev) | MIT | Verified from metadata |
| pytest-django | 4.14.0 (dev) | BSD-3-Clause | Verified from metadata (WP-02) |
| ruff | 0.14.5 (dev) | MIT | Verified from metadata (classifier) |

Transitive dependencies (asgiref, colorama, iniconfig, packaging, pluggy,
pygments, sqlparse, tzdata) are recorded in `uv.lock`; their licenses are
accounted for in WP-51 when the full inventory is finalized.

## Policy

- Every new dependency added by a later work package is added to this table
  with its license taken from `uv.lock` / package metadata, not from memory.
- Transitive dependencies, OS packages, native libraries, bundled fonts and
  vendored JavaScript are inventoried when they ship (WP-51), with notices
  distributed as required by their licenses.
- A `LICENSE` file for this project itself is added only after the owner
  approves license and copyright holder (see DECISIONS.md D-10).
- Private distribution is not an exemption from third-party notice
  obligations (OP-06).

## Regeneration

To re-check metadata for the locked environment:

```sh
uv pip show --format=freeze $(uv pip list | cut -d' ' -f1)
```

or inspect `uv.lock`, which carries `license = ...` fields per resolved
package.
