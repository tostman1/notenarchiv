"""Actual Linux no-clobber print publication, cancellation, restart and history."""

import json
import os
from pathlib import Path

import pytest

from tests.test_excerpt_publication import action as excerpt_action
from tests.test_generation_publication import export_action
from tests.test_generation_publication import export_installation as _installation

export_installation = _installation
pytestmark = pytest.mark.skipif(os.name != "posix", reason="Actual print publication requires POSIX")
SCENARIO = Path(__file__).with_name("print_scenario.py").read_text(encoding="utf-8")


def action(installation, mode, ids):
    output = installation.run("-c", SCENARIO, mode, json.dumps(ids)).stdout
    return json.loads(
        next(
            line.removeprefix("SCENARIO_RESULT=") for line in output.splitlines() if line.startswith("SCENARIO_RESULT=")
        )
    )


@pytest.mark.parametrize("kind", ["FULL", "EXCERPT", "CONTENTS", "ARCHIVE"])
@pytest.mark.parametrize("interrupt", ["none", "crash-after-link", "cancel-after-stage"])
def test_print_real_publication_and_recovery_preserve_reading_history(export_installation, kind, interrupt):
    installation, ids = export_installation
    installation.worker()
    if kind in {"EXCERPT", "CONTENTS"}:
        ids = excerpt_action(installation, kind, ids)
        installation.worker()
    old = {str(p): p.read_bytes() for p in (installation.root / "export").rglob("*.pdf")}
    new = action(installation, kind, ids)
    if interrupt == "crash-after-link":
        export_action(installation, interrupt, new, 32)
        installation.recover(new)
    elif interrupt == "cancel-after-stage":
        export_action(installation, interrupt, new)
        installation.code(
            "from apps.exports.models import GenerationRun\n"
            "r=GenerationRun.objects.get(pk=data['run']); assert r.job.status=='CANCELLED'",
            new,
        )
    else:
        installation.worker()
    if interrupt != "cancel-after-stage":
        assert action(installation, "check", new)["artifacts"] >= 1
    assert all(Path(path).read_bytes() == data for path, data in old.items())
    assert not list((installation.root / "export/.staging").rglob("*.pdf"))
