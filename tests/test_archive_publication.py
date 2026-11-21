"""Actual independent Linux workers: durable copy, approval and crash recovery."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.publication_scenario import synthetic_pdf

pytestmark = pytest.mark.skipif(os.name != "posix", reason="Actual publication requires POSIX dir-fd/no-follow APIs")
SCENARIO = Path(__file__).with_name("publication_scenario.py").read_text(encoding="utf-8")


class Installation:
    def __init__(self, root):
        self.root = root
        self.environment = os.environ.copy()
        self.environment.update(
            DJANGO_SETTINGS_MODULE="config.settings",
            NOTENARCHIV_PROFILE="local",
            NOTENARCHIV_SERVICE="worker",
            DEBUG_MODE="FALSE",
            NOTENARCHIV_LOCAL_ROOT=str(root),
            DATABASE_PATH=str(root / "data" / "archive.sqlite3"),
            SOURCE_DIR=str(root / "raw"),
            CURATED_DIR=str(root / "clean"),
            PROCESSED_DIR=str(root / "processed"),
            STATUS_DIR=str(root / "status"),
            EXPORT_DIR=str(root / "export"),
        )
        self.run("manage.py", "migrate", "--noinput")
        (root / "raw" / "correct.pdf").write_bytes(synthetic_pdf())

    def run(self, *arguments, check=True):
        return subprocess.run(
            [sys.executable, *arguments], env=self.environment, check=check, capture_output=True, text=True, timeout=45
        )

    def action(self, action, identities=None, *, expected=0):
        arguments = ["-c", SCENARIO, action]
        if identities is not None:
            arguments.append(json.dumps(identities) if isinstance(identities, dict) else identities)
        result = self.run(*arguments, check=False)
        assert result.returncode == expected, result.stdout + result.stderr
        if expected:
            return None  # A real process death cannot emit a fixture return value.
        responses = [
            line.removeprefix("SCENARIO_RESULT=")
            for line in result.stdout.splitlines()
            if line.startswith("SCENARIO_RESULT=")
        ]
        assert len(responses) == 1, result.stdout + result.stderr
        return json.loads(responses[0])

    def worker(self):
        return self.run("manage.py", "run_worker", "--once")

    def code(self, code, identities):
        result = self.run(
            "-c",
            "import django,json,sys; django.setup(); data=json.loads(sys.argv[1]);\n" + code,
            json.dumps(identities),
        )
        return result.stdout

    def recover(self, identities):
        self.worker()
        self.code(
            "from apps.jobs.models import Job\nfrom django.utils import timezone\n"
            "job=Job.objects.get(pk=data['job']); assert job.status=='QUEUED',job.status\n"
            "assert job.history.count()==1 and job.history.get().status=='FAILED'\n"
            "Job.objects.filter(pk=job.pk).update(available_at=timezone.now())",
            identities,
        )
        self.worker()


@pytest.fixture
def installation(tmp_path):
    return Installation(tmp_path / "synthetic-installation")


def test_worker_copies_then_canonicalizes_only_after_explicit_review(installation):
    identities = installation.action("setup")
    raw = installation.root / "raw" / "correct.pdf"
    before = hashlib.sha256(raw.read_bytes()).hexdigest(), raw.stat().st_mtime_ns
    installation.worker()
    copied = installation.action("check-copy", identities)
    identities = installation.action("review", identities)
    installation.worker()
    approved = installation.action("check-approved", identities)
    assert copied["path"] != approved["path"] and approved["operations"] == 2
    assert (installation.root / "clean" / copied["path"]).read_bytes() == raw.read_bytes()
    assert before == (hashlib.sha256(raw.read_bytes()).hexdigest(), raw.stat().st_mtime_ns)
    installation.code(
        "from apps.archive.publication import queue_copy\n"
        "file,job=queue_copy(data['version']); assert str(file.pk)==data['file']\n"
        "assert file.operations.count()==2",
        identities,
    )


@pytest.mark.parametrize("collision", ["same", "different", "case"])
def test_preexisting_content_is_retained_and_new_identity_gets_safe_suffix(installation, collision):
    identities = installation.action("setup", collision)
    existing = list((installation.root / "clean").rglob("*.PDF" if collision == "case" else "*.pdf"))
    assert len(existing) == 1
    before = existing[0].read_bytes()
    installation.worker()
    copied = installation.action("check-copy", identities)
    assert "--" in Path(copied["path"]).stem and existing[0].read_bytes() == before
    assert existing[0] != installation.root / "clean" / copied["path"]


@pytest.mark.parametrize(
    "action,exit_code",
    [("crash-during-copy", 24), ("crash-after-link", 23), ("crash-inside-ack", 25), ("crash-after-commit", 26)],
)
def test_actual_process_death_recovers_without_duplicate_effects(installation, action, exit_code):
    identities = installation.action("setup")
    installation.action(action, expected=exit_code)
    installation.recover(identities)
    result = installation.action("check-copy", identities)
    assert result["operations"] == 1
    installation.code(
        "from apps.jobs.models import Job\njob=Job.objects.get(pk=data['job'])\n"
        "assert job.attempt==2 and job.history.count()==2\n"
        "assert job.operations.count()==1 and job.operations.get().state=='APPLIED'",
        identities,
    )
    assert not list((installation.root / "clean" / ".staging").rglob("*.pdf"))


@pytest.mark.parametrize("same_bytes", [False, True])
def test_recovery_never_adopts_an_unrelated_replacement_even_with_the_same_hash(installation, same_bytes):
    identities = installation.action("setup")
    installation.action("crash-after-link", expected=23)
    finals = [path for path in (installation.root / "clean").rglob("*.pdf") if ".staging" not in path.parts]
    assert len(finals) == 1
    # Synthetic external owner replaces the name while the worker is dead.
    finals[0].unlink()
    replacement = synthetic_pdf() if same_bytes else b"Synthetic unrelated replacement"
    finals[0].write_bytes(replacement)
    installation.worker()
    installation.code(
        "from apps.jobs.models import Job\nfrom apps.archive.models import ArchiveFile\n"
        "job=Job.objects.get(pk=data['job']); file=ArchiveFile.objects.get(pk=data['file'])\n"
        "assert job.status=='REVIEW_REQUIRED' and job.operations.get().state=='REVIEW_REQUIRED'\n"
        "assert file.publication_state=='UNPUBLISHED' and not ArchiveFile.objects.usable().exists()",
        identities,
    )
    assert finals[0].read_bytes() == replacement


def test_cancel_before_publication_removes_only_private_partial_work(installation):
    identities = installation.action("setup")
    installation.action("cancel-before-publish")
    installation.code(
        "from apps.jobs.models import Job\nfrom apps.archive.models import ArchiveFile\n"
        "assert Job.objects.get(pk=data['job']).status=='CANCELLED'\n"
        "assert ArchiveFile.objects.get(pk=data['file']).publication_state=='UNPUBLISHED'",
        identities,
    )
    assert not list((installation.root / "clean").rglob("*.pdf"))


def test_cancel_after_effect_still_recovers_truth_without_republishing(installation):
    identities = installation.action("setup")
    installation.action("crash-after-link", expected=23)
    installation.code(
        "from apps.jobs.services.lifecycle import request_cancel\nrequest_cancel(data['job'])", identities
    )
    installation.worker()
    installation.code(
        "from apps.jobs.models import Job\nfrom apps.archive import publication as p\n"
        "from apps.archive.models import ArchiveFile\njob=Job.objects.get(pk=data['job'])\n"
        "assert job.status=='CANCELLED' and job.attempt==1\n"
        "assert ArchiveFile.objects.get(pk=data['file']).publication_state=='AVAILABLE'\n"
        "assert p.verified_bytes(data['file'])",
        identities,
    )


def test_stale_attempt_cannot_publish_a_verified_stage(installation):
    identities = installation.action("setup")
    result = installation.run("-c", SCENARIO, "fence-before-publish", check=False)
    assert result.returncode != 0
    installation.code(
        "from apps.archive.models import ArchiveFile\n"
        "assert ArchiveFile.objects.get(pk=data['file']).publication_state=='UNPUBLISHED'",
        identities,
    )
    assert not list((installation.root / "clean").rglob("*.pdf"))
    installation.recover(identities)
    installation.action("check-copy", identities)


def test_missing_raw_does_not_prevent_review_of_the_verified_clean_copy(installation):
    identities = installation.action("setup")
    installation.worker()
    raw = installation.root / "raw" / "correct.pdf"
    raw.unlink()  # Synthetic source owner action, never performed by application code.
    installation.code(
        "from apps.archive.models import ArchiveFile\nfrom apps.archive.services import mark_source_missing\n"
        "file=ArchiveFile.objects.get(pk=data['file']); source=file.source_version.source_file\n"
        "mark_source_missing(source.pk,expected_revision=source.revision)",
        identities,
    )
    identities = installation.action("review", identities)
    installation.worker()
    installation.action("check-approved", identities)


def test_withdrawal_during_crash_retains_effect_history_without_restoring_approval(installation):
    identities = installation.action("setup")
    installation.worker()
    identities = installation.action("review", identities)
    installation.worker()
    approved = installation.action("check-approved", identities)
    identities = installation.action("correct", identities)
    installation.action("crash-after-link", expected=23)
    installation.code(
        "from apps.archive.models import ArchiveFile\nfrom apps.archive.services import withdraw\n"
        "file=ArchiveFile.objects.get(pk=data['file'])\n"
        "withdraw(file.pk,actor=data['actor'],expected_revision=file.revision)",
        identities,
    )
    installation.recover(identities)
    installation.code(
        "from apps.jobs.models import Job\nfrom apps.archive.models import ArchiveFile\n"
        "file=ArchiveFile.objects.get(pk=data['file']); job=Job.objects.get(pk=data['job'])\n"
        "assert job.status=='REVIEW_REQUIRED'\n"
        "assert file.review_state=='WITHDRAWN' and not ArchiveFile.objects.usable().exists()\n"
        "assert file.operations.filter(state='APPLIED').count()==3\n"
        "assert file.proposals.get(pk=data['proposal']).state=='REJECTED'",
        identities,
    )
    assert (installation.root / "clean" / approved["path"]).read_bytes() == synthetic_pdf()
