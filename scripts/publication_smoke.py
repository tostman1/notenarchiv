"""Real non-root image publication against new synthetic mounts only (Linux CI)."""

import argparse
import base64
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from scripts.container_smoke import GID, UID, arguments, docker, prepare, raw_negatives


def smoke(image, root):
    paths = prepare(root)
    # Only this newly created disposable fixture. Never change existing installs.
    for name in ("clean", "processed", "status", "export"):
        os.chown(paths[name], UID, GID)
        paths[name].chmod(0o750)
    scenario = Path("tests/publication_scenario.py").read_text(encoding="utf-8")

    def action(name, identities=None):
        args = ["run", "--rm", *arguments(paths, "none"), "--entrypoint", "python", image, "-c", scenario, name]
        if identities is not None:
            args.append(json.dumps(identities))
        output = docker(*args).stdout
        if name == "pdf":
            return output
        responses = [
            line.removeprefix("SCENARIO_RESULT=") for line in output.splitlines() if line.startswith("SCENARIO_RESULT=")
        ]
        assert len(responses) == 1, "Synthetic scenario did not return exactly one result"
        return responses[0]

    data = base64.b64decode(action("pdf"))
    source = paths["raw"] / "correct.pdf"
    source.write_bytes(data)
    os.chown(source, 0, GID)
    source.chmod(0o440)
    raw_negatives(image, paths, "none")
    before = {
        path.name: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
        for path in paths["raw"].iterdir()
    }
    docker("run", "--rm", *arguments(paths, "none"), image, "migrate")
    identities = json.loads(action("setup"))
    unsafe = docker(
        "run",
        "--rm",
        *arguments(paths, "none", service="worker", raw_readonly=False),
        "--entrypoint",
        "python",
        image,
        "manage.py",
        "run_worker",
        "--once",
        check=False,
    )
    assert unsafe.returncode != 0, "Worker accepted writable RAW"

    def worker():
        result = docker(
            "run",
            "--rm",
            *arguments(paths, "none", service="worker"),
            "--entrypoint",
            "python",
            image,
            "manage.py",
            "run_worker",
            "--once",
        )
        assert "synthetic-publication-reviewer" not in result.stdout + result.stderr

    worker()
    copied = json.loads(action("check-copy", identities))
    identities = json.loads(action("review", identities))
    worker()
    approved = json.loads(action("check-approved", identities))
    assert copied["path"] != approved["path"] and approved["operations"] == 2
    assert (paths["clean"] / copied["path"]).read_bytes() == data
    assert (paths["clean"] / approved["path"]).read_bytes() == data
    after = {
        path.name: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
        for path in paths["raw"].iterdir()
    }
    assert before == after
    assert not list(paths["status"].iterdir())  # STATUS publication belongs to WP-15.
    assert not list((paths["clean"] / ".staging").rglob("*.pdf"))
    assert (paths["clean"] / approved["path"]).stat().st_uid == UID
    preference_code = """
import django,json,sys
django.setup()
from apps.archive import models as m,edition_services as e
from apps.catalog.models import Arrangement
data=json.loads(sys.argv[1])
assignment=m.ArchiveAssignment.objects.usable().filter(archive_file_id=data['file']).first()
arrangement=Arrangement.objects.get(pk=data['arrangement'])
e.set_preference(arrangement.pk,assignment.part_id,assignment.pk,actor=data['actor'],expected_revision=arrangement.revision)
result=e.resolve(arrangement.pk,assignment.part_id)
assert result.origin=='ARCHIVE' and result.assignment.pk==assignment.pk
"""
    docker(
        "run",
        "--rm",
        *arguments(paths, "none"),
        "-e",
        "DJANGO_SETTINGS_MODULE=config.settings",
        "--entrypoint",
        "python",
        image,
        "-c",
        preference_code,
        json.dumps(identities),
    )
    download_code = """
import django,json,sys,zipfile,hashlib
django.setup()
from apps.archive import download_services as s
data=json.loads(sys.argv[1])
selected=s.files([data['file']])
for zipped in (False,True):
    stream=s.stage(selected,zipped=zipped)
    try:
        if zipped:
            with zipfile.ZipFile(stream) as archive:
                assert len(archive.namelist())==1
                content=archive.read(archive.namelist()[0])
        else:
            content=stream.read()
        assert hashlib.sha256(content).hexdigest()==selected[0].sha256
    finally:
        stream.close()
"""
    docker(
        "run",
        "--rm",
        *arguments(paths, "none"),
        "-e",
        "DJANGO_SETTINGS_MODULE=config.settings",
        "--entrypoint",
        "python",
        image,
        "-c",
        download_code,
        json.dumps(identities),
    )
    # Full WP-47a: real copied/confirmed files and SQLite restored together in
    # hardened network-disabled containers. Only these new synthetic roots.
    private_config, independent, output = root / "config", root / "independent", root / "backup-output"
    for directory in (private_config, output):
        directory.mkdir(mode=0o700)
        os.chown(directory, UID, GID)
    (private_config / "configuration.yaml").write_text("# Synthetic private deployment configuration\n")
    os.chown(private_config / "configuration.yaml", UID, GID)
    (private_config / "configuration.yaml").chmod(0o600)
    shutil.copytree(paths["raw"], independent)
    os.chown(independent, 0, GID)
    independent.chmod(0o550)
    # copytree preserves modes but not ownership. Give the non-root verifier
    # read-only group access to this newly created synthetic independent copy.
    for note in independent.iterdir():
        os.chown(note, 0, GID)
        note.chmod(0o440)
    mounts = [
        "--mount",
        f"type=bind,src={private_config},dst=/private-config,readonly",
        "--mount",
        f"type=bind,src={independent},dst=/independent-raw,readonly",
        "--mount",
        f"type=bind,src={output},dst=/backup-output",
    ]
    backup_result = docker(
        "run",
        "--rm",
        *arguments(paths, "none"),
        *mounts,
        image,
        "backup",
        "/backup-output/bundle",
        "--config-dir",
        "/private-config",
        "--raw-backup",
        "/independent-raw",
        "--image",
        "ghcr.io/tostman1/notenarchiv@sha256:" + "a" * 64,
    )
    seal = (output / "bundle" / "manifest.sha256").read_text()
    assert seal in backup_result.stdout
    docker(
        "run",
        "--rm",
        *arguments(paths, "none"),
        *mounts,
        image,
        "restore",
        "/backup-output/bundle",
        "/backup-output/restored",
        "--manifest-sha256",
        seal,
    )
    assert (output / "restored" / "clean" / approved["path"]).read_bytes() == data
    assert (output / "restored" / "secrets" / "django.key").read_bytes() == paths["secret"].read_bytes()
    assert not (output / "restored" / "raw").exists()
    # Outputs are deliberately excluded by default. Rehearsal explicitly creates
    # a new empty isolated export root, never binds the live EXPORT location.
    (output / "restored" / "export").mkdir(mode=0o700)
    os.chown(output / "restored" / "export", UID, GID)
    restored_paths = {
        name: output / "restored" / name
        if name not in {"raw", "secret"}
        else independent
        if name == "raw"
        else output / "restored" / "secrets" / "django.key"
        for name in paths
    }
    # Reopen the restored actual ORM state and preview bytes in the image with
    # explicitly isolated mounts; never start captured production configuration.
    checked = docker(
        "run",
        "--rm",
        *arguments(restored_paths, "none"),
        "-e",
        "DATABASE_PATH=/data/database.sqlite3",
        "-e",
        "DJANGO_SETTINGS_MODULE=config.settings",
        "--entrypoint",
        "python",
        image,
        "-c",
        scenario,
        "check-approved",
        json.dumps(identities),
    )
    assert "SCENARIO_RESULT=" in checked.stdout
    project_code = """
import django
django.setup()
from django.contrib.auth import get_user_model
from apps.projects import models as m,services as s
from apps.projects import list_services as pieces
from apps.projects import participant_services as people
from apps.projects import ensemble_services as ensemble
from apps.projects import rule_services as rules
from apps.projects import resolution_services as resolution
from apps.members.models import Member
from apps.catalog.models import Part
actor=get_user_model().objects.get(username='synthetic-publication-reviewer')
values=dict(name='Synthetic project',layout='REGULAR',width_mm=170,height_mm=120,cover_enabled=True,cover_title='')
project=s.save_project(values,actor=actor)
slot=m.ProjectPosition.objects.create(project=project,order=1)
inserted=pieces.insert(project.pk,actor=actor,expected_revision=1)
pieces.move(project.pk,inserted.pk,1,actor=actor,expected_revision=2)
project.refresh_from_db()
clone=s.duplicate_project(project.pk,name=project.name,actor=actor,expected_revision=3)
assert project.revision==3
assert clone.positions.count()==2 and clone.positions.first().pk!=inserted.pk
part=Part.objects.filter(active=True).first()
member=Member.objects.create(name='Synthetic container member',regular_part=part)
people.member_subset(project.pk,[member.pk],scope_ids=[member.pk],actor=actor,expected_revision=3)
participant=project.participants.get()
assert participant.default_part_id==part.pk and participant.member_revision==member.revision
people.add_guest(project.pk,name='Synthetic container guest',part_id=part.pk,actor=actor,expected_revision=4)
assert project.participants.count()==2 and Member.objects.count()==1
role=ensemble.save_role(project.pk,code='3',label='Synthetic ensemble role',actor=actor,expected_revision=5)
ensemble.assign_role(project.pk,participant.pk,role.pk,actor=actor,expected_revision=6)
mapping=ensemble.save_mapping(project.pk,role_id=role.pk,instrument_id=part.instrument_id,
    part_id=part.pk,actor=actor,expected_revision=7)
choice=ensemble.mapping_choice(project.pk,role.pk,part.instrument_id)
assert choice.status=='MAPPED' and choice.mapping.pk==mapping.pk
target=Part.objects.filter(instrument_id=part.instrument_id,active=True).exclude(pk=part.pk).first()
rule=rules.save_replacement(project_id=project.pk,desired_part_id=part.pk,replacement_part_id=target.pk,
    actor=actor,expected_revision=8)
assert rules.replacement_choice(project.pk,None,part.pk).rule.pk==rule.pk
rules.save_replacement(desired_part_id=part.pk,replacement_part_id=target.pk,actor=actor,expected_revision=1)
arrangement=m.ProjectEditionPreference._meta.get_field('arrangement').related_model.objects.get()
pieces.replace(project.pk,slot.pk,arrangement.pk,actor=actor,expected_revision=9)
result=resolution.resolve_cell(project.pk,slot.pk,participant.pk)
assert result.usable and result.desired_part_id==part.pk and result.edition_origin=='ARCHIVE'
s.archive_project(clone.pk,actor=actor,expected_revision=1)
assert m.Project.objects.get(pk=clone.pk).status=='ARCHIVED'
"""
    docker(
        "run",
        "--rm",
        *arguments(restored_paths, "none"),
        "-e",
        "DATABASE_PATH=/data/database.sqlite3",
        "-e",
        "DJANGO_SETTINGS_MODULE=config.settings",
        "--entrypoint",
        "python",
        image,
        "-c",
        project_code,
    )
    docker(
        "run",
        "--rm",
        *arguments(restored_paths, "none"),
        "-e",
        "DATABASE_PATH=/data/database.sqlite3",
        "-e",
        "DJANGO_SETTINGS_MODULE=config.settings",
        "--entrypoint",
        "python",
        image,
        "-c",
        "import django; django.setup(); from apps.archive import models as m,edition_services as e; "
        "p=m.PreferredEdition.objects.get(); r=e.resolve(p.arrangement_id,p.part_id); "
        "assert r.origin=='ARCHIVE' and r.assignment.pk==p.assignment_id; assert p.changes.count()==1",
    )
    assert before == {
        path.name: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
        for path in paths["raw"].iterdir()
    }
    sys.stdout.write(
        "PASS: actual non-root worker, read-only RAW/host permissions, verified independent copy, "
        "explicit multi-part approval, canonical publication, retained history, complete backup/restore, no network\n"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    args = parser.parse_args()
    if os.name != "posix" or os.geteuid() != 0:
        parser.error("Run only as root on isolated Linux Docker CI with new synthetic fixtures")
    with tempfile.TemporaryDirectory(prefix="notenarchiv-publication-") as directory:
        smoke(args.image, Path(directory))


if __name__ == "__main__":
    main()
