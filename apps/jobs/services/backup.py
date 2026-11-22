"""Offline maintenance orchestration; no HTTP endpoint or automatic destination."""

import hashlib
import re
import sqlite3
from contextlib import ExitStack, closing
from pathlib import Path

from core import backup as b
from core.files import Root
from core.locking import ProcessLock


def roots(env):
    return {
        "data": env.database_path.parent,
        "clean": env.curated_dir,
        "processed": env.processed_dir,
        "status": env.status_dir,
        "export": env.export_dir,
    }


def check_raw(source, independent, budget):
    """Read-only comparison against an operator-supplied independent RAW copy."""
    left, right = set(b.inventory(source, budget)), set(b.inventory(independent, b.Budget(budget.limits)))
    if left != right:
        raise b.BackupError("RAW_BACKUP_INCOMPLETE")
    for name in sorted(left):
        if (source.metadata(name).st_dev, source.metadata(name).st_ino) == (
            independent.metadata(name).st_dev,
            independent.metadata(name).st_ino,
        ):
            raise b.BackupError("RAW_BACKUP_NOT_INDEPENDENT")
        if b.digest(source, name, budget) != b.digest(independent, name, budget):
            raise b.BackupError("RAW_BACKUP_INTEGRITY")
    return {"verified": True, "files": len(left)}


def create(env, destination, *, config_dir, raw_backup, image, include_exports=False, limits=b.DEFAULT_LIMITS):
    if not re.fullmatch(r"[a-z0-9./:_-]+@sha256:[0-9a-f]{64}", image):
        raise b.BackupError("EXACT_IMAGE_REQUIRED")
    groups = roots(env)
    data = groups["data"]
    for key, other in groups.items():
        if key != "data" and (data.is_relative_to(other) or other.is_relative_to(data)):
            raise b.BackupError("LIVE_ROOT_OVERLAP")
    if data.is_relative_to(env.source_dir) or env.source_dir.is_relative_to(data):
        raise b.BackupError("LIVE_ROOT_OVERLAP")
    config_dir, raw_backup = Path(config_dir), Path(raw_backup)
    protected = [*groups.values(), env.source_dir, env.secret_key_file.parent, config_dir, raw_backup]
    # Open every trusted input before creating a destination or a lock file.
    with ExitStack() as stack:
        opened = {key: stack.enter_context(Root(path)) for key, path in groups.items()}
        config = stack.enter_context(Root(config_dir))
        secret = stack.enter_context(Root(env.secret_key_file.parent))
        raw = stack.enter_context(Root(env.source_dir))
        independent = stack.enter_context(Root(raw_backup))
        for path in protected[:-1]:
            if raw_backup == path or raw_backup.is_relative_to(path) or path.is_relative_to(raw_backup):
                raise b.BackupError("RAW_BACKUP_NOT_INDEPENDENT")
        stack.enter_context(ProcessLock(env.database_path.parent / ".maintenance.lock"))
        stack.enter_context(ProcessLock(env.database_path.parent / "worker.lock"))
        budget = b.Budget(limits)
        # Freeze all DB writers for the entire file capture, not only the Backup API call.
        with opened["data"].reader(env.database_path.name, links=1):
            barrier = stack.enter_context(closing(sqlite3.connect(env.database_path.as_uri() + "?mode=rw", uri=True)))
            barrier.execute("BEGIN IMMEDIATE")
            b.database_state_check(barrier, budget)
        raw_evidence = check_raw(raw, independent, budget)
        path = b.new_directory(destination, protected)
        bundle = stack.enter_context(Root(path, writable=True))
        selected = set(groups) if include_exports else set(groups) - {"export"}
        manifest = {
            "format": 1,
            "release": env.release,
            "image": image,
            "raw": raw_evidence,
            "groups": sorted(selected | {"config", "secrets"}),
            "files": [],
        }
        excluded = {
            env.database_path.name,
            env.database_path.name + "-wal",
            env.database_path.name + "-shm",
            env.database_path.name + "-journal",
            ".maintenance.lock",
            "worker.lock",
            "logs",
            "scratch",
            "thumbnails",
            "cache",
            "download-scratch",
            "direct-download.lock",
        }
        for key in sorted(selected):
            for name in b.inventory(opened[key], budget, excluded if key == "data" else ()):
                manifest["files"].append(b.copy(opened[key], name, bundle, key + "/" + name, budget))
        config_files = list(b.inventory(config, budget))
        if not config_files:
            raise b.BackupError("CONFIG_BACKUP_EMPTY")
        for name in config_files:
            manifest["files"].append(b.copy(config, name, bundle, "config/" + name, budget))
        budget.add(secret.metadata(env.secret_key_file.name).st_size)
        manifest["files"].append(b.copy(secret, env.secret_key_file.name, bundle, "secrets/django.key", budget))
        manifest["files"].append(b.sqlite_backup(opened["data"], env.database_path.name, bundle, budget))
        manifest["files"].sort(key=lambda item: item["path"])
        data = b.manifest_bytes(manifest)
        b.write(bundle, "manifest.json", data)
        seal = hashlib.sha256(data).hexdigest()
        b.write(bundle, "manifest.sha256", seal.encode("ascii"))
        b.private_directories(bundle)
        b.verify_bundle(path, limits=limits, expected_manifest=seal)
        barrier.rollback()
        return seal


def restore(env, source, destination, *, expected_manifest, limits=b.DEFAULT_LIMITS):
    """Restore only into a new root, never write to any live configured path."""
    source = Path(source)
    if not isinstance(expected_manifest, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_manifest):
        raise b.BackupError("TRUSTED_MANIFEST_REQUIRED")
    manifest, seal = b.verify_bundle(source, limits=limits, expected_manifest=expected_manifest)
    protected = [*roots(env).values(), env.source_dir, env.secret_key_file.parent, source]
    path = b.new_directory(destination, protected)
    with Root(source) as bundle, Root(path, writable=True) as target:
        budget = b.Budget(limits)
        for entry in manifest["files"]:
            budget.add(entry["size"])
            copied = b.copy(bundle, entry["path"], target, entry["path"], budget)
            if copied != entry:
                raise b.BackupError("RESTORE_SOURCE_CHANGED")
        for group in manifest["groups"]:
            (path / group).mkdir(mode=0o700, exist_ok=True)
        # RAW intentionally absent. An independent copy must be mounted read-only
        # before starting a deliberately reconfigured isolated installation.
        b.write(target, "manifest.json", b.manifest_bytes(manifest))
        b.write(target, "manifest.sha256", seal.encode("ascii"))
        b.private_directories(target)
    b.verify_bundle(path, limits=limits, expected_manifest=seal)
    return seal
