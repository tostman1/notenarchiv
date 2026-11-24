"""Real targeted one-person and project-free archive-reading crash/replay acceptance."""

import json
import os
from pathlib import Path

import pytest

from tests.test_generation_publication import export_action
from tests.test_generation_publication import export_installation as _installation

export_installation = _installation
pytestmark = pytest.mark.skipif(os.name != "posix", reason="Real export publication requires POSIX")
SCENARIO = Path(__file__).with_name("export_library_scenario.py").read_text(encoding="utf-8")


def action(installation, mode, ids):
    output = installation.run("-c", SCENARIO, mode, json.dumps(ids)).stdout
    return json.loads(
        next(
            line.removeprefix("SCENARIO_RESULT=") for line in output.splitlines() if line.startswith("SCENARIO_RESULT=")
        )
    )


@pytest.mark.parametrize("mode", ["targeted", "archive"])
@pytest.mark.parametrize("crash", [False, True])
def test_targeted_and_archive_reading_publication_preserve_old_files(export_installation, mode, crash):
    installation, ids = export_installation
    installation.worker()
    originals = {str(p): p.read_bytes() for p in (installation.root / "export").rglob("*.pdf")}
    new = action(installation, mode, ids)
    if crash:
        export_action(installation, "crash-after-link", new, 32)
        installation.recover(new)
    else:
        installation.worker()
    assert action(installation, "check", new)["ok"]
    assert all(Path(path).read_bytes() == data for path, data in originals.items())
    assert not list((installation.root / "export/.staging").rglob("*.pdf"))
