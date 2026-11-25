"""Bounded, descriptor-anchored private backup bundles (Linux only)."""

import hashlib
import json
import os
import re
import sqlite3
import stat
import time
from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path

from core.files import CHUNK, FileError, Root, fingerprint, identity
from core.paths import relative_path

GROUPS = {"data", "clean", "processed", "status", "config", "secrets", "export"}
MANIFEST_LIMIT = 32 * 1024 * 1024


class BackupError(ValueError):
    """Safe error codes only; never expose private paths or database contents."""


@dataclass(frozen=True)
class Limits:
    files: int = 100_000
    bytes: int = 50 * 1024**3
    file_bytes: int = 4 * 1024**3
    seconds: int = 7200

    def __post_init__(self):
        if not (1 <= self.files <= 100_000 and 1 <= self.bytes <= 1024**4):
            raise BackupError("INVALID_LIMIT")
        if not (1 <= self.file_bytes <= 16 * 1024**3 and 1 <= self.seconds <= 86400):
            raise BackupError("INVALID_LIMIT")


class Budget:
    def __init__(self, limits):
        self.limits, self.count, self.size = limits, 0, 0
        self.deadline = time.monotonic() + limits.seconds

    def checkpoint(self):
        if time.monotonic() > self.deadline:
            raise BackupError("BACKUP_TIMEOUT")

    def add(self, size):
        self.checkpoint()
        self.count += 1
        self.size += size
        if self.count > self.limits.files or self.size > self.limits.bytes or size > self.limits.file_bytes:
            raise BackupError("BACKUP_LIMIT")


DEFAULT_LIMITS = Limits()


def inventory(root, budget, excluded=()):
    """Never follow links, special files or unbounded directory trees."""

    def walk(path, depth, expected_identity=None):
        if depth > 32:
            raise BackupError("DIRECTORY_DEPTH")
        with root.directory_entries(path) as (directory, entries):
            if expected_identity is not None and identity(directory) != expected_identity:
                raise BackupError("BACKUP_CHANGED")
            for name, info in entries:
                budget.checkpoint()
                child = f"{path}/{name}" if path else name
                if child in excluded:
                    continue
                relative_path(child)
                if stat.S_ISDIR(info.st_mode):
                    budget.add(0)
                    yield from walk(child, depth + 1, identity(info))
                elif stat.S_ISREG(info.st_mode) and 1 <= info.st_nlink <= 2:
                    budget.add(info.st_size)
                    yield child
                else:
                    raise BackupError("UNSAFE_BACKUP_FILE")

    try:
        yield from walk("", 0)
    except FileError:
        raise BackupError("BACKUP_CHANGED") from None


def digest(root, path, budget):
    with root.reader(path, links=2) as (descriptor, info):
        if info.st_size > budget.limits.file_bytes:
            raise BackupError("BACKUP_LIMIT")
        result, size = hashlib.sha256(), 0
        while chunk := os.read(descriptor, CHUNK):
            budget.checkpoint()
            size += len(chunk)
            if size > budget.limits.file_bytes:
                raise BackupError("BACKUP_LIMIT")
            result.update(chunk)
        if size != info.st_size:
            raise BackupError("BACKUP_CHANGED")
        return result.hexdigest(), size


def write(root, path, data):
    with private_parent(root, path) as (parent, name):
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.fsync(parent)


def copy(source, path, target, target_path, budget):
    with source.reader(path, links=2) as (descriptor, info):
        with private_parent(target, target_path) as (parent, name):
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
            expected, size = hashlib.sha256(), 0
            with os.fdopen(fd, "wb") as stream:
                while chunk := os.read(descriptor, CHUNK):
                    budget.checkpoint()
                    size += len(chunk)
                    if size > budget.limits.file_bytes:
                        raise BackupError("BACKUP_LIMIT")
                    expected.update(chunk)
                    stream.write(chunk)
                stream.flush()
                os.fsync(stream.fileno())
            os.fsync(parent)
        if size != info.st_size or fingerprint(info) != fingerprint(os.fstat(descriptor)):
            raise BackupError("BACKUP_CHANGED")
    actual = digest(target, target_path, budget)
    if actual != (expected.hexdigest(), size):
        raise BackupError("BACKUP_COPY_MISMATCH")
    return {"path": target_path, "sha256": actual[0], "size": size}


@contextmanager
def private_parent(root, path):
    parts = relative_path(path).split("/")
    descriptor = os.dup(root.fd)
    try:
        for name in parts[:-1]:
            try:
                os.mkdir(name, 0o700, dir_fd=descriptor)
                os.fsync(descriptor)
            except FileExistsError:
                pass
            following = os.open(name, root._directory_flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = following
            if os.fstat(descriptor).st_mode & 0o077:
                raise BackupError("UNSAFE_BACKUP_PERMISSIONS")
        yield descriptor, parts[-1]
    finally:
        os.close(descriptor)


def new_directory(path, protected):
    path = Path(path)
    # Validate existing parents with the same no-follow policy before any write.
    with Root(path.parent) as parent:
        if path.name in {"", ".", ".."}:
            raise BackupError("UNSAFE_DESTINATION")
        for other in protected:
            other = Path(other)
            if path == other or path.is_relative_to(other) or other.is_relative_to(path):
                raise BackupError("DESTINATION_OVERLAP")
        os.mkdir(path.name, mode=0o700, dir_fd=parent.fd)
        os.fsync(parent.fd)
    return path


def private_directories(root):
    """Bundle directories contain private state, never shareable archive modes."""
    for directory, _children, _files in os.walk(root.path, followlinks=False):
        Path(directory).chmod(0o700)


def database_state_check(database, budget=None):
    if budget is not None:

        def progress():
            return int(time.monotonic() > budget.deadline)

        database.set_progress_handler(progress, 10_000)
    if database.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise BackupError("DATABASE_INTEGRITY")
    if database.execute("PRAGMA foreign_key_check").fetchone():
        raise BackupError("DATABASE_REFERENCES")
    if database.execute("SELECT 1 FROM jobs_job WHERE status='RUNNING' LIMIT 1").fetchone():
        raise BackupError("WORKER_RECOVERY_REQUIRED")
    if (
        database.execute(
            "SELECT 1 FROM jobs_operationintent WHERE state IN ('PENDING','REVIEW_REQUIRED') LIMIT 1"
        ).fetchone()
        or database.execute(
            "SELECT 1 FROM archive_fileoperation WHERE state IN ('STAGED','REVIEW_REQUIRED') LIMIT 1"
        ).fetchone()
    ):
        raise BackupError("FILE_RECOVERY_REQUIRED")


def database_check(database, bundle, budget):
    database_state_check(database, budget)
    for root, path, sha256, size in database.execute(
        "SELECT root_kind, relative_path, sha256, byte_size FROM archive_archivefile "
        "WHERE publication_state='AVAILABLE' OR review_state IN ('CONFIRMED','WITHDRAWN') "
        "UNION SELECT target_root, target_path, expected_sha256, expected_size "
        "FROM archive_fileoperation WHERE state='APPLIED'"
    ):
        if root not in {"CLEAN", "PROCESSED"}:
            raise BackupError("INVALID_ARCHIVE_ROOT")
        if digest(bundle, root.lower() + "/" + relative_path(path), budget) != (sha256, size):
            raise BackupError("ARCHIVE_INTEGRITY")


def sqlite_backup(source, filename, bundle, budget):
    with source.reader(filename, links=1):
        uri = (source.path / filename).as_uri() + "?mode=ro"
        with closing(sqlite3.connect(uri, uri=True, timeout=5)) as reader:
            target = bundle.path / "data" / "database.sqlite3"
            write(bundle, "data/database.sqlite3", b"")
            with closing(sqlite3.connect(target)) as database:
                page_size = reader.execute("PRAGMA page_size").fetchone()[0]

                def progress(_status, _remaining, total):
                    budget.checkpoint()
                    if total * page_size > budget.limits.file_bytes:
                        raise BackupError("DATABASE_LIMIT")

                reader.backup(database, pages=256, progress=progress)
                # A portable offline DB must not need writable WAL sidecars on
                # its read-only backup mount during verification.
                database.execute("PRAGMA journal_mode=DELETE")
                database_check(database, bundle, budget)
            target.chmod(0o600)
            with target.open("rb") as stream:
                os.fsync(stream.fileno())
            os.fsync(bundle.fd)
            sha256, size = digest(bundle, "data/database.sqlite3", budget)
            budget.add(size)
            return {"path": "data/database.sqlite3", "sha256": sha256, "size": size}


def manifest_bytes(manifest):
    data = json.dumps(manifest, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()
    if len(data) > MANIFEST_LIMIT:
        raise BackupError("MANIFEST_LIMIT")
    return data


def verify_bundle(path, *, limits=DEFAULT_LIMITS, expected_manifest=None):
    budget = Budget(limits)
    with Root(path) as bundle:
        data, _info = bundle.read("manifest.json", maximum=MANIFEST_LIMIT)
        seal, _info = bundle.read("manifest.sha256", maximum=64)
        actual = hashlib.sha256(data).hexdigest()
        if seal.decode("ascii") != actual or (expected_manifest is not None and expected_manifest != actual):
            raise BackupError("MANIFEST_INTEGRITY")
        manifest = json.loads(data)
        if (
            not isinstance(manifest, dict)
            or set(manifest) != {"format", "release", "image", "raw", "groups", "files"}
            or manifest["format"] != 1
            or not isinstance(manifest["groups"], list)
            or any(not isinstance(group, str) for group in manifest["groups"])
            or len(set(manifest["groups"])) != len(manifest["groups"])
            or set(manifest["groups"]) not in (GROUPS - {"export"}, GROUPS)
            or not isinstance(manifest["files"], list)
            or len(manifest["files"]) > limits.files
        ):
            raise BackupError("INVALID_MANIFEST")
        if not isinstance(manifest["raw"], dict) or manifest["raw"].get("verified") is not True:
            raise BackupError("RAW_BACKUP_UNVERIFIED")
        if not isinstance(manifest["image"], str) or not re.fullmatch(
            r"[a-z0-9./:_-]+@sha256:[0-9a-f]{64}", manifest["image"]
        ):
            raise BackupError("EXACT_IMAGE_REQUIRED")
        seen = set()
        for entry in manifest["files"]:
            if not isinstance(entry, dict) or set(entry) != {"path", "sha256", "size"}:
                raise BackupError("INVALID_MANIFEST")
            name = relative_path(entry["path"])
            if name.split("/")[0] not in manifest["groups"] or name in seen:
                raise BackupError("INVALID_MANIFEST")
            seen.add(name)
            if type(entry["size"]) is not int or entry["size"] < 0:
                raise BackupError("INVALID_MANIFEST")
            if not isinstance(entry["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]):
                raise BackupError("INVALID_MANIFEST")
            budget.add(entry["size"])
            if digest(bundle, name, budget) != (entry["sha256"], entry["size"]):
                raise BackupError("BACKUP_INTEGRITY")
        actual_files = set(inventory(bundle, Budget(limits), {"manifest.json", "manifest.sha256"}))
        if actual_files != seen or "data/database.sqlite3" not in seen or "secrets/django.key" not in seen:
            raise BackupError("INCOMPLETE_BACKUP")
        if not any(name.startswith("config/") for name in seen):
            raise BackupError("CONFIG_BACKUP_EMPTY")
        with closing(sqlite3.connect((Path(path) / "data/database.sqlite3").as_uri() + "?mode=ro", uri=True)) as db:
            database_check(db, bundle, budget)
        return manifest, actual
