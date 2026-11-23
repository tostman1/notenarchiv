"""Local hash-pinned HTMX asset and safe matrix config, no runtime CDN."""

import hashlib
from pathlib import Path


def test_htmx_release_bytes_and_safe_config():
    root = Path(__file__).resolve().parent.parent
    assert (
        hashlib.sha256((root / "static/vendor/htmx/htmx.min.js").read_bytes()).hexdigest()
        == "d6fdc75f204e6bdefa99b69bf1e6d4ac69b8a364f77929f45c13476b4000f717"
    )
    assert "Zero-Clause BSD" in (root / "static/vendor/htmx/LICENSE").read_text(encoding="utf-8")
    template = (root / "templates/projects/matrix.html").read_text(encoding="utf-8")
    assert '"allowEval":false' in template and '"allowScriptTags":false' in template
    assert '"selfRequestsOnly":true' in template and '"historyCacheSize":0' in template
    assert "https://" not in template
