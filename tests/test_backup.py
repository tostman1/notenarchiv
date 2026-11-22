"""Real SQLite and physical synthetic file backups; never production/NAS data."""

import json
import os
import shutil
import sqlite3
from contextlib import closing

import pytest

from apps.jobs.services import backup
from config.env import parse_env
from core import backup as b
from core.files import FileError, Root
from core.locking import ProcessLock
from tests.test_archive_publication import Installation

IMAGE = "ghcr.io/tostman1/notenarchiv@sha256:" + "a" * 64
posix = pytest.mark.skipif(os.name != "posix", reason="Backup requires Linux no-follow/dir-fd APIs")


@pytest.fixture
def backup_install(tmp_path):
    install = Installation(tmp_path / "installation")
    identities = install.action("setup")
    install.worker()
    identities = install.action("review", identities)
    install.worker()
    approved = install.action("check-approved", identities)
    (install.root / "processed" / "synthetic-copy.pdf").write_bytes((install.root / "raw" / "correct.pdf").read_bytes())
    (install.root / "status" / "state.json").write_text('{"synthetic":true}')
    (install.root / "data" / "non-regenerable.dat").write_bytes(b"synthetic durable state")
    config = tmp_path / "config"
    config.mkdir()
    (config / "configuration.yaml").write_text("# Synthetic private config\nimage: " + IMAGE)
    raw_backup = tmp_path / "independent-raw"
    shutil.copytree(install.root / "raw", raw_backup)
    env = parse_env(install.environment)
    return install, env, config, raw_backup, identities, approved


def capture(fixture, path, **options):
    _install, env, config, raw, _identities, _approved = fixture
    return backup.create(env, path, config_dir=config, raw_backup=raw, image=IMAGE, **options)


@posix
@pytest.mark.parametrize("wal", [False, True])
def test_actual_files_and_confirmed_assignments_restore_together(backup_install, tmp_path, wal):
    install, env, _config, _raw, identities, approved = backup_install
    with closing(sqlite3.connect(env.database_path)) as database:
        if wal:
            assert database.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        destination = tmp_path / "backup"
        seal = capture(backup_install, destination)
        restored = tmp_path / "restored"
        assert backup.restore(env, destination, restored, expected_manifest=seal) == seal
    manifest, _seal = b.verify_bundle(restored, expected_manifest=seal)
    assert manifest["raw"] == {"verified": True, "files": 1}
    assert not (restored / "raw").exists()
    assert (restored / "clean" / approved["path"]).read_bytes() == (install.root / "raw" / "correct.pdf").read_bytes()
    assert (restored / "processed" / "synthetic-copy.pdf").exists()
    assert (restored / "status" / "state.json").exists()
    assert (restored / "data" / "non-regenerable.dat").exists()
    assert (restored / "secrets" / "django.key").read_bytes() == env.secret_key_file.read_bytes()
    with closing(sqlite3.connect(restored / "data" / "database.sqlite3")) as db:
        assert db.execute(
            "SELECT review_state FROM archive_archivefile WHERE id=?", (identities["file"].replace("-", ""),)
        ).fetchone() == ("CONFIRMED",)
        assert db.execute("SELECT COUNT(*) FROM archive_archiveassignment WHERE state='CONFIRMED'").fetchone()[0] == 2
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    for path in restored.rglob("*"):
        assert path.stat().st_mode & 0o077 == 0


@posix
@pytest.mark.parametrize("lock", [".maintenance.lock", "worker.lock"])
def test_active_service_blocks_backup_without_destination(backup_install, tmp_path, lock):
    _install, env, *_other = backup_install
    with ProcessLock(env.database_path.parent / lock), pytest.raises(OSError):
        capture(backup_install, tmp_path / "blocked")
    assert not (tmp_path / "blocked").exists()


@posix
@pytest.mark.parametrize("target", ["raw", "clean", "data"])
def test_never_overwrites_live_roots(backup_install, tmp_path, target):
    install, env, *_other = backup_install
    seal = capture(backup_install, tmp_path / "backup")
    with pytest.raises((b.BackupError, FileError, FileExistsError)):
        backup.restore(env, tmp_path / "backup", install.root / target / "restore", expected_manifest=seal)
    assert not (install.root / target / "restore").exists()


@posix
@pytest.mark.parametrize("change", ["missing", "corrupt", "extra", "manifest", "manifest-only", "symlink"])
def test_incomplete_or_tampered_bundle_is_rejected(backup_install, tmp_path, change):
    destination = tmp_path / "backup"
    seal = capture(backup_install, destination)
    manifest = json.loads((destination / "manifest.json").read_bytes())
    file = destination / next(entry["path"] for entry in manifest["files"] if entry["path"].startswith("clean/"))
    if change == "missing":
        file.unlink()
    elif change == "corrupt":
        file.write_bytes(b"different")
    elif change == "extra":
        (destination / "clean" / "extra.pdf").write_bytes(b"unlisted")
    elif change == "manifest":
        (destination / "manifest.json").write_bytes(b"{}")
    elif change == "manifest-only":
        for entry in manifest["files"]:
            (destination / entry["path"]).unlink()
    else:
        file.unlink()
        file.symlink_to(backup_install[0].root / "raw" / "correct.pdf")
    with pytest.raises((b.BackupError, FileError, OSError)):
        backup.restore(backup_install[1], destination, tmp_path / "bad-restore", expected_manifest=seal)
    assert not (tmp_path / "bad-restore").exists()


@posix
@pytest.mark.parametrize("raw_change", ["missing", "corrupt", "not-independent"])
def test_independent_raw_backup_required(backup_install, tmp_path, raw_change):
    _install, env, config, independent, *_other = backup_install
    if raw_change == "not-independent":
        independent = env.source_dir
    elif raw_change == "missing":
        (independent / "correct.pdf").unlink()
    else:
        (independent / "correct.pdf").write_bytes(b"corrupt")
    with pytest.raises(b.BackupError):
        backup.create(env, tmp_path / "backup", config_dir=config, raw_backup=independent, image=IMAGE)
    assert not (tmp_path / "backup").exists()


@posix
def test_sqlite_barrier_blocks_concurrent_writer_during_file_capture(backup_install, tmp_path, monkeypatch):
    _install, env, *_other = backup_install
    original = b.copy
    attempts = []

    def checked_copy(*args, **kwargs):
        with (
            closing(sqlite3.connect(env.database_path, timeout=0.01)) as writer,
            pytest.raises(sqlite3.OperationalError, match="locked"),
        ):
            writer.execute("UPDATE catalog_work SET title='unexpected'")
        attempts.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(b, "copy", checked_copy)
    capture(backup_install, tmp_path / "backup")
    assert attempts


@posix
def test_retained_historical_copy_must_match_publication_receipt(backup_install, tmp_path):
    install, env, *_other = backup_install
    with closing(sqlite3.connect(env.database_path)) as db:
        old_path = db.execute(
            "SELECT target_path FROM archive_fileoperation WHERE kind='COPY' AND state='APPLIED'"
        ).fetchone()[0]
    (install.root / "clean" / old_path).write_bytes(b"corrupt retained history")
    with pytest.raises(b.BackupError, match="ARCHIVE_INTEGRITY"):
        capture(backup_install, tmp_path / "backup")


@posix
@pytest.mark.parametrize("status", ["RUNNING", "PENDING", "REVIEW_REQUIRED"])
def test_unsettled_operations_require_recovery(backup_install, tmp_path, status):
    _install, env, *_other = backup_install
    with closing(sqlite3.connect(env.database_path)) as db:
        if status == "RUNNING":
            db.execute("UPDATE jobs_job SET status='RUNNING' WHERE id=(SELECT id FROM jobs_job LIMIT 1)")
        else:
            db.execute("UPDATE jobs_operationintent SET state=?", (status,))
        db.commit()
    with pytest.raises(b.BackupError, match="RECOVERY_REQUIRED"):
        capture(backup_install, tmp_path / "backup")
    assert not (tmp_path / "backup").exists()


@posix
def test_bounds_exports_and_immutable_destinations(backup_install, tmp_path):
    export = backup_install[1].export_dir / "synthetic.pdf"
    export.write_bytes(b"synthetic optional artifact")
    with pytest.raises(b.BackupError, match="LIMIT"):
        capture(backup_install, tmp_path / "limited", limits=b.Limits(bytes=1))
    seal = capture(backup_install, tmp_path / "backup", include_exports=True)
    manifest, _ = b.verify_bundle(tmp_path / "backup", expected_manifest=seal)
    assert any(entry["path"] == "export/synthetic.pdf" for entry in manifest["files"])
    with pytest.raises(FileExistsError):
        capture(backup_install, tmp_path / "backup")


def test_limits_validate_and_unsupported_platform_fails_closed(tmp_path):
    with pytest.raises(b.BackupError):
        b.Limits(files=0)
    if os.name != "posix":
        with pytest.raises(FileError, match="UNSUPPORTED_FILESYSTEM_API"), Root(tmp_path):
            pass
