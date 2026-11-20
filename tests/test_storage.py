"""Synthetic mount/permission negatives; no actual NAS or RAW write probes."""

import os
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.jobs.services import storage
from core.mounts import Mount, parse_mountinfo


@pytest.fixture()
def topology(tmp_path, monkeypatch):
    paths = [tmp_path / name for name in ("raw", "clean", "processed", "status", "export", "data")]
    mounts = {Path("/"): Mount(Path("/"), "0:1", "/", True)}
    for index, path in enumerate(paths):
        path.mkdir()
        mounts[path] = Mount(path, "8:1", f"/synthetic/{path.name}", index < 5)
    secret = tmp_path / "key"
    secret.write_text("synthetic-only-key", encoding="utf-8")
    secret.chmod(0o440)
    if os.name == "nt":
        # Windows chmod exposes a read-only attribute, not POSIX group/world bits.
        # Linux CI and the real container smoke verify the actual file mode.
        monkeypatch.setattr(storage, "_secret_mode", lambda path: 0o440)
    mounts[secret] = Mount(secret, "8:1", "/private/key", True)
    env = SimpleNamespace(
        source_dir=paths[0],
        curated_dir=paths[1],
        processed_dir=paths[2],
        status_dir=paths[3],
        export_dir=paths[4],
        database_path=paths[5] / "test.sqlite3",
        secret_key_file=secret,
    )
    return env, mounts


def test_mountinfo_escapes_and_flags():
    mounts = parse_mountinfo("25 22 8:1 /example\\040path /archive/raw ro,relatime - ext4 /dev/sda rw\n")
    assert mounts[Path("/archive/raw")].root == "/example path"
    assert mounts[Path("/archive/raw")].readonly
    assert mounts[Path("/archive/raw")].filesystem == "ext4"
    with pytest.raises(ValueError):
        parse_mountinfo("invalid")


def test_web_only_probes_data_and_worker_never_probes_raw(topology, monkeypatch):
    env, mounts = topology
    probes = []
    monkeypatch.setattr(storage, "_writable", probes.append)
    storage.validate_storage(env, "web", mounts=mounts)
    assert probes == [env.database_path.parent]
    probes.clear()
    for path in (env.curated_dir, env.processed_dir, env.status_dir, env.export_dir):
        mounts[path] = replace(mounts[path], readonly=False)
    storage.validate_storage(env, "worker", mounts=mounts)
    assert env.source_dir not in probes and len(probes) == 5


@pytest.mark.parametrize(
    "failure", ["raw_rw", "web_clean_rw", "data_ro", "root_rw", "missing", "same_host", "nested_host"]
)
def test_unsafe_mounts_fail_before_any_write_probe(topology, monkeypatch, failure):
    env, mounts = topology
    if failure == "raw_rw":
        mounts[env.source_dir] = replace(mounts[env.source_dir], readonly=False)
    elif failure == "web_clean_rw":
        mounts[env.curated_dir] = replace(mounts[env.curated_dir], readonly=False)
    elif failure == "data_ro":
        path = env.database_path.parent
        mounts[path] = replace(mounts[path], readonly=True)
    elif failure == "root_rw":
        mounts[Path("/")] = replace(mounts[Path("/")], readonly=False)
    elif failure == "missing":
        del mounts[env.source_dir]
    else:
        root = "/synthetic/raw" if failure == "same_host" else "/synthetic/raw/nested"
        mounts[env.curated_dir] = replace(mounts[env.curated_dir], root=root)
    probes = []
    monkeypatch.setattr(storage, "_writable", probes.append)
    with pytest.raises(storage.StorageError):
        storage.validate_storage(env, "web", mounts=mounts)
    assert probes == []


def test_secret_cannot_be_in_data_or_writable(topology):
    env, mounts = topology
    mounts[env.secret_key_file] = replace(mounts[env.secret_key_file], root="/synthetic/data/key")
    with pytest.raises(storage.StorageError, match="overlaps"):
        storage.validate_storage(env, "web", mounts=mounts)
    mounts[env.secret_key_file] = replace(mounts[env.secret_key_file], root="/private/key", readonly=False)
    with pytest.raises(storage.StorageError, match="read-only"):
        storage.validate_storage(env, "web", mounts=mounts)


def test_database_symlink_is_rejected(topology, tmp_path):
    env, mounts = topology
    target = tmp_path / "synthetic-db"
    target.touch()
    try:
        env.database_path.symlink_to(target)
    except OSError:
        pytest.skip("Local symlink creation is unavailable; Linux CI exercises this negative")
    with pytest.raises(storage.StorageError, match="symlink"):
        storage.validate_storage(env, "web", mounts=mounts)


@pytest.mark.parametrize("mode", [0o644, 0o666, 0o777, 0o660])
def test_unsafe_secret_modes_are_rejected(topology, monkeypatch, mode):
    env, mounts = topology
    monkeypatch.setattr(storage, "_secret_mode", lambda path: mode)
    with pytest.raises(storage.StorageError, match="private"):
        storage.validate_storage(env, "web", mounts=mounts)


@pytest.mark.parametrize("filesystem", ["cifs", "nfs", "nfs4", "fuse.sshfs"])
def test_network_database_storage_is_rejected_without_probe(topology, monkeypatch, filesystem):
    env, mounts = topology
    path = env.database_path.parent
    mounts[path] = replace(mounts[path], filesystem=filesystem)
    probes = []
    monkeypatch.setattr(storage, "_writable", probes.append)
    with pytest.raises(storage.StorageError, match="local filesystem"):
        storage.validate_storage(env, "web", mounts=mounts)
    assert not probes
