"""Real Linux filesystem, independent SQLite reopen, crash/cancellation acceptance."""

import hashlib
import json
import os
from pathlib import Path

import pytest

from tests.test_archive_publication import Installation

pytestmark = pytest.mark.skipif(os.name != "posix", reason="Actual publication requires POSIX no-follow/dir-fd APIs")
SCENARIO = Path(__file__).with_name("generation_scenario.py").read_text(encoding="utf-8")


@pytest.fixture
def export_installation(tmp_path):
    installation = Installation(tmp_path / "synthetic-export")
    ids = installation.action("setup")
    installation.worker()
    ids = installation.action("review", ids)
    installation.worker()
    ids = export_action(installation, "setup", ids)
    return installation, ids


def export_action(installation, action, ids=None, expected=0):
    result = installation.run("-c", SCENARIO, action, json.dumps(ids), check=False)
    assert result.returncode == expected, result.stdout + result.stderr
    if expected:
        return None
    values = [
        json.loads(line.removeprefix("SCENARIO_RESULT="))
        for line in result.stdout.splitlines()
        if line.startswith("SCENARIO_RESULT=")
    ]
    assert len(values) == 1, result.stdout + result.stderr
    return values[0]


def test_complete_personal_publication_reopen_and_replay_preserve_history(export_installation):
    installation, ids = export_installation
    raw = installation.root / "raw/correct.pdf"
    before = raw.read_bytes(), raw.stat().st_mtime_ns
    installation.worker()
    result = export_action(installation, "check", ids)
    files = [(installation.root / "export" / a["path"]) for a in result["inventory"]]
    original = [(p.read_bytes(), p.stat().st_ino) for p in files]
    installation.worker()
    assert export_action(installation, "check", ids) == result
    assert [(p.read_bytes(), p.stat().st_ino) for p in files] == original
    assert (raw.read_bytes(), raw.stat().st_mtime_ns) == before
    assert not list((installation.root / "export/.staging").rglob("*.pdf"))


@pytest.mark.parametrize(
    "mode,code",
    [
        ("crash-before-composition", 30),
        ("crash-during-stage", 31),
        ("crash-after-link", 32),
        ("crash-after-first-participant", 32),
        ("crash-inside-ack", 33),
        ("crash-after-commit", 34),
        ("crash-after-completion", 35),
        ("crash-after-stage-record", 36),
        ("crash-during-composition", 37),
    ],
)
def test_real_crash_recovery_completes_once_without_duplicate_artifacts(export_installation, mode, code):
    installation, ids = export_installation
    export_action(installation, mode, ids, code)
    installation.recover(ids)
    result = export_action(installation, "check", ids)
    assert result["attempt"] == 2 and len(result["inventory"]) == 2
    assert len([p for p in (installation.root / "export").rglob("*.pdf") if ".staging" not in p.parts]) == 2
    assert not list((installation.root / "export/.staging").rglob("*.pdf"))


@pytest.mark.parametrize("mode", ["queued", "cancel-during-composition", "cancel-during-stage", "cancel-after-stage"])
def test_cancel_never_completes_or_exposes_outputs_and_cleans_private_stages(export_installation, mode):
    installation, ids = export_installation
    if mode == "queued":
        installation.code("from apps.jobs.services.lifecycle import request_cancel\nrequest_cancel(data['job'])", ids)
        installation.worker()
    else:
        export_action(installation, mode, ids)
    installation.code(
        "from apps.exports.models import GenerationRun\nfrom apps.exports.generation import is_complete\n"
        "r=GenerationRun.objects.get(pk=data['run'])\n"
        "assert r.job.status=='CANCELLED',r.job.status\nassert not is_complete(r) and not r.artifacts.exists()",
        ids,
    )
    assert not list((installation.root / "export").rglob("*.pdf"))


@pytest.mark.parametrize("damage", ["missing-stage", "corrupt-stage", "unrelated-same-bytes", "unrelated-bytes"])
def test_uncertain_publication_never_adopts_damaged_or_unrelated_evidence(export_installation, damage):
    installation, ids = export_installation
    export_action(installation, "crash-after-link", ids, 32)
    root = installation.root / "export"
    stage = next((root / ".staging").rglob("*.pdf"))
    final = next(p for p in root.rglob("*.pdf") if ".staging" not in p.parts)
    if damage == "missing-stage":
        stage.unlink()
    elif damage == "corrupt-stage":
        stage.chmod(0o600)
        stage.write_bytes(b"Synthetic corrupt stage")
    else:
        value = final.read_bytes() if damage == "unrelated-same-bytes" else b"Synthetic foreign bytes"
        final.unlink()
        final.write_bytes(value)
    installation.worker()
    installation.code(
        "from apps.exports.models import GenerationRun\nfrom apps.exports.generation import is_complete\n"
        "r=GenerationRun.objects.get(pk=data['run'])\n"
        "assert r.job.status=='REVIEW_REQUIRED',r.job.status\nassert not is_complete(r) and not r.artifacts.exists()",
        ids,
    )


def test_failed_multi_person_run_retains_effect_but_never_exposes_partial_batch(export_installation):
    installation, ids = export_installation
    export_action(installation, "fail-second-participant", ids)
    installation.code(
        "from apps.exports.models import GenerationRun\nfrom apps.exports.generation import is_complete\n"
        "r=GenerationRun.objects.get(pk=data['run'])\n"
        "assert r.job.status=='FAILED' and r.artifacts.count()==1 and not is_complete(r)",
        ids,
    )
    finals = [p for p in (installation.root / "export").rglob("*.pdf") if ".staging" not in p.parts]
    assert len(finals) == 1 and hashlib.sha256(finals[0].read_bytes()).hexdigest()


def test_cancelled_crash_recovers_effect_truth_without_success_or_stage_leaks(export_installation):
    installation, ids = export_installation
    export_action(installation, "crash-after-link", ids, 32)
    installation.code("from apps.jobs.services.lifecycle import request_cancel\nrequest_cancel(data['job'])", ids)
    installation.worker()
    installation.code(
        "from apps.exports.models import GenerationRun\nfrom apps.exports.generation import is_complete\n"
        "r=GenerationRun.objects.get(pk=data['run'])\n"
        "assert r.job.status=='CANCELLED' and r.artifacts.count()==1 and not is_complete(r)",
        ids,
    )
    assert not list((installation.root / "export/.staging").rglob("*.pdf"))
