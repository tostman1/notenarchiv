# PDF.js local distribution

Upstream: https://github.com/mozilla/pdf.js/tree/v6.5.438
Version: 6.5.438 (unmodified build/worker, CMaps and standard fonts).
Registry artifact: https://registry.npmjs.org/pdfjs-dist/-/pdfjs-dist-6.5.438.tgz
Verified registry SHA-512 (base64):
`vg8Pw1x+AFKy4AMDvhuWl5cOYV8d698UoEANoFFhc79hqXDnZQqnOXoxw3HG907WHOg1JYOvLhP756boddFxpA==`

PDF.js/CMaps: Apache-2.0; retain LICENSE and original file notices.
Foxit PFB standard fonts: BSD-3-Clause; retain standard_fonts/LICENSE_FOXIT.
Liberation Sans fonts: unmodified upstream 1.07.4, GPL-2.0 with Liberation font
exception; retain standard_fonts/LICENSE_LIBERATION (including full GPL text).
See upstream external/standard_fonts/README.md and the corresponding font
source distribution at https://github.com/liberationfonts/liberation-fonts.
This font license is not the license of the application or rendered documents.

The application uses its own canvas-only viewer in static/archive/preview.mjs.
It does not vendor upstream viewer UI, sandbox scripting bundle or optional
WASM assets. All bundled dependency assets/notices remain locally accessible.
