# Dependency license inventory (WP-01 mechanism, finalization in WP-51)

This file is the working inventory of the direct Python dependencies in
`uv.lock`. It records license metadata from actual package metadata; no
license is assumed or guessed.

## Direct dependencies

Verified against installed package metadata (`importlib.metadata`) of the
locked environment (foundation verification 2026-11-19; runtime pins checked
again on 2026-11-20 with uv 0.13.1 and CPython 3.12.14):

| Package | Pinned version | License (from package metadata) | Status |
| --- | --- | --- | --- |
| Django | 5.2.19 | BSD-3-Clause | Verified from SPDX metadata; current 5.2 LTS security patch |
| gunicorn | 27.0.1 | MIT | Verified from SPDX metadata; Linux production server |
| whitenoise | 6.12.0 | MIT | Verified from metadata (WP-02) |
| pypdf | 7.1.1 | BSD-3-Clause | Verified from downloaded/installed wheel metadata and LICENSE (WP-17) |
| pypdfium2 | 5.15.2 | BSD-3-Clause / Apache-2.0 plus native dependency notices | Verified from Windows and musllinux amd64 wheels (WP-17) |
| pytest | 8.4.1 (dev) | MIT | Verified from metadata |
| pytest-django | 4.14.0 (dev) | BSD-3-Clause | Verified from metadata (WP-02) |
| ruff | 0.14.5 (dev) | MIT | Verified from metadata (classifier) |

Transitive dependencies (asgiref, colorama, iniconfig, packaging, pluggy,
pygments, sqlparse, tzdata) are recorded in `uv.lock`; their licenses are
accounted for in WP-51 when the full inventory is finalized.

The preview Linux runtime additionally ships asgiref 3.13.0 (BSD-3-Clause,
package metadata) and sqlparse 0.6.1 (BSD-3-Clause, installed LICENSE including
the non-endorsement clause). tzdata 2026.6 is Windows-only in the Python lock
(Apache-2.0 metadata and bundled data notices); Linux zone data comes from the
pinned base image. Runtime wheel license files remain installed under
`/opt/venv/lib/python3.12/site-packages/*.dist-info/`. The official Python image
retains Python notices and Alpine's installed package/license metadata. CI generates a CycloneDX image SBOM;
release evidence records its exact source revision and registry digest.

Build-only uv 0.13.1 is copied from its digest-pinned official image; it is not
present in the runtime image. Test/security tools (Playwright, pip-audit,
Trivy) are CI-only and do not run on the NAS. Full future native/OCR/printing
dependency and project-license acceptance remains WP-51 / D-10.

The browser smoke uses playwright-core 1.62.1 (Apache-2.0, verified from its
package.json). This test-only Node dependency runs outside the application.

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

## PDF native foundation (WP-17, 2026-11-21)

Official PyPI 5.15.2 wheels were downloaded and their PyPI SHA-256 checked:

- Windows amd64: `74d1bace34fb01c660d0b64344d5a4b7d276942b7c6623c88ab59ea21c5acfbd`.
- musllinux 1.2 amd64: `ef452a7178744196d4ff97029f46b56a13817346fc7ee0473c75643512276b3a`.
- pypdf 7.1.1 universal: `04c5680d4b4cfa04ab505b09393fc949860c34a4dad6565284d11a2f5c3ce8b1`.

The PDFium version JSON records 159.0.8149.0, without V8/XFA flags. The musl
wheel bundles libgcc/libstdc++ with their GCC runtime exception notices, and
retains BUILD_LICENSES for PDFium, Abseil, AGG, Dragonbox, fast_float, FreeType,
HarfBuzz, Highway, ICU, lcms, libjpeg-turbo, OpenJPEG, libpng, libtiff, simdutf
and zlib. Keep the wheel's complete `*.dist-info/licenses/` tree in the image;
this includes the applicable BSD/MIT/Apache/FreeType/ICU/Boost/runtime-exception
texts and platform-specific notices, not just the Python wrapper's license.
The wheel's documentation license (CC-BY-4.0) is also retained. No native source
or bundled notice is modified. References: [official package](https://pypi.org/project/pypdfium2/5.15.2/),
[platform support](https://pypdfium2-team.github.io/pypdfium2/platforms.html).
Actual musl loading/rendering and image vulnerability checks are CI gates;
wheel availability alone is not evidence of runtime success.

PDF fixtures use original synthetic text, paths, pixels and Type3 glyphs.
Base-14 Helvetica references do not distribute a font binary. No real music or
third-party score fixture is copied. Font authoring for later generated covers
still needs its own bundled Unicode font/notice selection (WP-37a/WP-51).
