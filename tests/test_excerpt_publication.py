"""Real Linux publication and restart for every WP-37c output kind."""

import json
import os
from pathlib import Path

import pytest

from tests.test_generation_publication import export_action
from tests.test_generation_publication import export_installation as _export_fixture

export_installation = _export_fixture

pytestmark = pytest.mark.skipif(os.name != "posix", reason="Real publication requires POSIX")
SCENARIO = Path(__file__).with_name("excerpt_scenario.py").read_text(encoding="utf-8")


def action(installation, name, ids):
    result = installation.run("-c", SCENARIO, name, json.dumps(ids))
    return json.loads(
        next(
            line.removeprefix("SCENARIO_RESULT=")
            for line in result.stdout.splitlines()
            if line.startswith("SCENARIO_RESULT=")
        )
    )


@pytest.mark.parametrize("kind", ["EXCERPT", "CONTENTS", "HISTORICAL"])
@pytest.mark.parametrize("crash", [False, True])
def test_real_excerpt_contents_and_historical_publication_preserve_previous_bytes(export_installation, kind, crash):
    installation, ids = export_installation
    installation.worker()
    old = {str(p): p.read_bytes() for p in (installation.root / "export").rglob("*.pdf")}
    new = action(installation, kind, ids)
    if crash:
        export_action(installation, "crash-after-link", new, 32)
        installation.recover(new)
    else:
        installation.worker()
    result = action(installation, "check", new)
    assert result["artifacts"] == (2 if kind == "EXCERPT" else 1)
    for path, data in old.items():
        assert Path(path).read_bytes() == data
    assert not list((installation.root / "export/.staging").rglob("*.pdf"))


@pytest.mark.parametrize("kind", ["EXCERPT", "CONTENTS", "HISTORICAL"])
def test_selected_output_cancellation_never_exposes_a_completed_run(export_installation, kind):
    installation, ids = export_installation
    installation.worker()
    new = action(installation, kind, ids)
    export_action(installation, "cancel-after-stage", new)
    installation.code(
        "from apps.exports.models import GenerationRun\nfrom apps.exports.generation import is_complete\n"
        "r=GenerationRun.objects.get(pk=data['run'])\n"
        "assert r.job.status=='CANCELLED' and not is_complete(r) and not r.artifacts.exists()",
        new,
    )
    assert not list((installation.root / "export/.staging").rglob("*.pdf"))
