"""Service-aware NAS startup validation; RAW is never write-probed."""

import os
import stat
import tempfile
from pathlib import Path

from core.mounts import overlapping, parse_mountinfo


class StorageError(ValueError):
    """Fixed technical messages only; never include private paths or values."""


def _secret_mode(path):
    return stat.S_IMODE(path.stat().st_mode)


def _canonical(path, *, directory=True):
    if not path.is_absolute() or any(parent.is_symlink() for parent in (path, *path.parents)):
        raise StorageError("Storage paths must be absolute and free of symlinks")
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        raise StorageError("A required storage path is missing") from None
    expected = stat.S_ISDIR if directory else stat.S_ISREG
    if not expected(resolved.stat().st_mode):
        raise StorageError("A required storage path has the wrong type")
    return resolved


def _writable(path):
    try:
        with tempfile.TemporaryFile(prefix=".notenarchiv-probe-", dir=path) as stream:
            stream.write(b"synthetic startup probe")
            stream.flush()
    except OSError:
        raise StorageError("A required managed storage root is not writable") from None


def validate_storage(env, service, *, mounts=None):
    """Require dedicated distinct mounts, read-only web roots and protected RAW.

    Host ACL protection is checked by the separate host preflight. Container
    mount flags cannot prove host ACLs. Neither check writes into RAW.
    """
    if service not in {"web", "worker"}:
        raise StorageError("Unknown service")
    if mounts is None:
        try:
            mounts = parse_mountinfo(Path("/proc/self/mountinfo").read_text())
        except (OSError, ValueError):
            raise StorageError("Linux mount metadata is unavailable") from None
    paths = [
        env.source_dir,
        env.curated_dir,
        env.processed_dir,
        env.status_dir,
        env.export_dir,
        env.database_path.parent,
    ]
    roots = [_canonical(path) for path in paths]
    selected = []
    for index, path in enumerate(roots):
        mount = mounts.get(path)
        if mount is None:
            raise StorageError("Each storage root needs an explicit bind mount")
        for previous in selected:
            if path.is_relative_to(previous.target) or previous.target.is_relative_to(path):
                raise StorageError("Storage roots overlap")
            if mount.device == previous.device and overlapping(mount.root, previous.root):
                raise StorageError("Host bind sources overlap")
        should_be_readonly = index == 0 or (service == "web" and index < 5)
        if mount.readonly != should_be_readonly:
            raise StorageError("Storage mount permissions do not match the service")
        if not os.access(path, os.R_OK | os.X_OK):
            raise StorageError("A required storage root is not readable")
        selected.append(mount)
    secret = _canonical(env.secret_key_file, directory=False)
    secret_mount = mounts.get(secret)
    if secret_mount is None or not secret_mount.readonly:
        raise StorageError("The secret must be a separate read-only file mount")
    if _secret_mode(secret) & 0o027:
        raise StorageError("The secret must be private and not group writable")
    if any(secret.is_relative_to(root) for root in roots):
        raise StorageError("The secret must be separate from storage roots")
    if any(secret_mount.device == mount.device and overlapping(secret_mount.root, mount.root) for mount in selected):
        raise StorageError("The secret host source overlaps a storage root")
    root_mount = mounts.get(Path("/"))
    if root_mount is None or not root_mount.readonly:
        raise StorageError("The container root filesystem must be read-only")
    if env.database_path.is_symlink():
        raise StorageError("The database must not be a symlink")
    if env.database_path.exists() and not env.database_path.is_file():
        raise StorageError("The database must be a regular file")
    for path in roots[1:] if service == "worker" else roots[-1:]:
        _writable(path)
