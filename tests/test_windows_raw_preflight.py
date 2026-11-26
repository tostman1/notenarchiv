"""Bounded RAW evidence traversal with synthetic data and no certification."""

import os
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from core import windows_raw_preflight as preflight
from core.files import FileError
from core.files_windows import WindowsSourceRoot
from core.windows_security import current_process_token

USER = b"synthetic-user"


def metadata(inode=1, *, directory=True, links=1, changed=0):
    return SimpleNamespace(
        st_dev=1,
        st_ino=inode,
        st_mode=0o040700 if directory else 0o100400,
        st_nlink=links,
        st_size=0,
        st_mtime_ns=0,
        st_ctime_ns=changed,
    )


def evidence(**changes):
    values = dict(
        user_sid=USER,
        owner_sid=b"synthetic-owner",
        dangerous_privileges_present=False,
        administrative_token=False,
        granted_access=0,
        mutation_access=0,
    )
    values.update(changes)
    return SimpleNamespace(**values)


def fixture_root(tmp_path, monkeypatch):
    root = WindowsSourceRoot(tmp_path, inspect_security=True)
    root._stack = object()
    values = {"": metadata(), "nested": metadata(2), "nested/score.pdf": metadata(3, directory=False)}
    tree = {"": [("nested", values["nested"])], "nested": [("score.pdf", values["nested/score.pdf"])]}
    root.root_metadata = Mock(side_effect=lambda: values[""])
    root.metadata = Mock(side_effect=lambda path: values[path])
    visited = []

    @contextmanager
    def entries(path):
        yield values[path], iter(tree[path])

    @contextmanager
    def security_entry(path):
        visited.append(path)
        yield path, values[path]

    root.directory_entries = entries
    root.security_entry = security_entry
    monkeypatch.setattr(preflight.access, "root_access_evidence", Mock(return_value=evidence()))
    monkeypatch.setattr(preflight.access, "parent_access_evidence", Mock(return_value=evidence()))
    monkeypatch.setattr(preflight.access, "_handle_access_evidence", Mock(return_value=evidence()))
    return root, values, tree, visited


def test_complete_snapshot_is_aggregate_only_and_never_certified(tmp_path, monkeypatch):
    root, _, _, visited = fixture_root(tmp_path, monkeypatch)
    result = preflight.inspect_raw(root, USER)
    assert result.complete and result.entries_checked == 3 and result.directories_checked == 2
    assert result.rejections == () and visited == ["nested", "nested/score.pdf"]
    assert not result.raw_isolation_certified and not result.writable_publication
    assert "synthetic" not in repr(result) and "score" not in repr(result)


@pytest.mark.parametrize("scope", ["root", "parent", "child"])
@pytest.mark.parametrize(
    "risk,code",
    [
        ({"user_sid": b"foreign-user"}, "IDENTITY_MISMATCH"),
        ({"owner_sid": USER}, "RAW_OWNED_BY_APPLICATION"),
        ({"mutation_access": 2, "granted_access": 0x40}, "RAW_MUTATION_ACCESS"),
        ({"dangerous_privileges_present": True}, "DANGEROUS_TOKEN"),
        ({"administrative_token": True}, "ADMINISTRATIVE_TOKEN"),
    ],
)
def test_rejection_evidence_does_not_make_complete_inventory_incomplete(tmp_path, monkeypatch, scope, risk, code):
    root, _, _, _ = fixture_root(tmp_path, monkeypatch)
    name = {"root": "root_access_evidence", "parent": "parent_access_evidence", "child": "_handle_access_evidence"}[
        scope
    ]
    monkeypatch.setattr(preflight.access, name, Mock(return_value=evidence(**risk)))
    result = preflight.inspect_raw(root, USER)
    assert result.complete
    if scope == "parent" and code == "RAW_OWNED_BY_APPLICATION":
        assert code not in result.rejections
    else:
        expected = "PARENT_MUTATION_ACCESS" if scope == "parent" and code == "RAW_MUTATION_ACCESS" else code
        assert expected in result.rejections
    assert not result.raw_isolation_certified and not result.writable_publication


@pytest.mark.parametrize("right", [0x40, 0x40000, 0x80000])
def test_parent_entry_mutation_rights_are_rejections(tmp_path, monkeypatch, right):
    root, _, _, _ = fixture_root(tmp_path, monkeypatch)
    monkeypatch.setattr(preflight.access, "parent_access_evidence", Mock(return_value=evidence(granted_access=right)))
    assert "PARENT_MUTATION_ACCESS" in preflight.inspect_raw(root, USER).rejections


@pytest.mark.parametrize(
    "failure,code",
    [
        (FileError("SECURITY_QUERY_FAILED"), "SECURITY_QUERY_FAILED"),
        (FileError("UNSAFE_ROOT"), "MISSING_PARENT"),
        (FileError("SOURCE_CHANGED"), "INVENTORY_CHANGED"),
    ],
)
def test_parent_query_failure_is_incomplete(tmp_path, monkeypatch, failure, code):
    root, _, _, visited = fixture_root(tmp_path, monkeypatch)
    monkeypatch.setattr(preflight.access, "parent_access_evidence", Mock(side_effect=failure))
    result = preflight.inspect_raw(root, USER)
    assert not result.complete and code in result.rejections and not visited


@pytest.mark.parametrize("unsafe", ["reparse", "hardlink"])
def test_unsafe_entries_not_inspected_or_followed(tmp_path, monkeypatch, unsafe):
    root, values, tree, visited = fixture_root(tmp_path, monkeypatch)
    info = metadata(4, directory=False, links=2 if unsafe == "hardlink" else 1)
    if unsafe == "reparse":
        info.st_mode = 0o120700
    tree[""] = [("unsafe", info)]
    result = preflight.inspect_raw(root, USER)
    assert not result.complete and "UNSAFE_ENTRY" in result.rejections and not visited


@pytest.mark.parametrize("limits,code", [({"maximum": 1}, "ENTRY_LIMIT"), ({"max_depth": 1}, "DEPTH_LIMIT")])
def test_entry_and_depth_limits_are_incomplete(tmp_path, monkeypatch, limits, code):
    root, _, _, _ = fixture_root(tmp_path, monkeypatch)
    result = preflight.inspect_raw(root, USER, **limits)
    assert not result.complete and code in result.rejections


def test_cancellation_and_deadline_are_incomplete(tmp_path, monkeypatch):
    root, _, _, _ = fixture_root(tmp_path, monkeypatch)
    cancel = Mock(side_effect=RuntimeError("private cancellation text"))
    assert preflight.inspect_raw(root, USER, checkpoint=cancel).rejections == ("CANCELLED",)
    monkeypatch.setattr(preflight.time, "monotonic", Mock(side_effect=[0, 121]))
    assert preflight.inspect_raw(root, USER).rejections == ("TIME_LIMIT",)


@pytest.mark.parametrize("where", ["child-query", "disappear", "directory-exit", "after-children"])
def test_query_failure_or_changed_inventory_is_incomplete(tmp_path, monkeypatch, where):
    root, values, tree, _ = fixture_root(tmp_path, monkeypatch)
    if where == "child-query":
        monkeypatch.setattr(
            preflight.access, "_handle_access_evidence", Mock(side_effect=FileError("SECURITY_QUERY_FAILED"))
        )
    elif where == "disappear":
        root.metadata.side_effect = FileNotFoundError("private path")
    elif where == "directory-exit":

        @contextmanager
        def entries(path):
            yield values[path], iter(tree[path])
            raise FileError("SOURCE_CHANGED")

        root.directory_entries = entries
    else:
        original = root.security_entry

        @contextmanager
        def mutate(path):
            with original(path) as entry:
                yield entry
            if path.endswith(".pdf"):
                values[""] = metadata(changed=1)

        root.security_entry = mutate
    result = preflight.inspect_raw(root, USER)
    assert not result.complete
    assert ("SECURITY_QUERY_FAILED" if where == "child-query" else "INVENTORY_CHANGED") in result.rejections


def test_explicit_inspection_and_input_validation(tmp_path):
    root = WindowsSourceRoot(tmp_path)
    assert preflight.inspect_raw(root, USER).rejections == ("SECURITY_MODE_REQUIRED",)
    for sid in ("not-bytes", b"short"):
        with pytest.raises(FileError, match="INVALID_IDENTITY"):
            preflight.inspect_raw(root, sid)
    with pytest.raises(FileError, match="INVALID_LIMIT"):
        preflight.inspect_raw(root, USER, maximum=True)


def test_repeated_directory_identity_invalidates_inventory(tmp_path, monkeypatch):
    root, values, tree, _ = fixture_root(tmp_path, monkeypatch)
    values["nested"] = values[""]
    tree[""] = [("nested", values["nested"])]
    result = preflight.inspect_raw(root, USER)
    assert not result.complete and "INVENTORY_CHANGED" in result.rejections


def test_replaced_entry_between_enumeration_and_pin_is_incomplete(tmp_path, monkeypatch):
    root, _, _, _ = fixture_root(tmp_path, monkeypatch)

    @contextmanager
    def replacement(path):
        yield path, metadata(99)

    root.security_entry = replacement
    result = preflight.inspect_raw(root, USER)
    assert not result.complete and "INVENTORY_CHANGED" in result.rejections
    preflight.access._handle_access_evidence.assert_not_called()


@pytest.mark.skipif(os.name != "nt", reason="Native Windows RAW snapshot")
def test_native_nested_synthetic_raw_is_complete_but_not_isolated(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "nested").mkdir()
    (raw / "nested" / "score.pdf").write_bytes(b"synthetic")
    user = current_process_token().user_sid
    with WindowsSourceRoot(raw, inspect_security=True) as root:
        result = preflight.inspect_raw(root, user)
    assert result.complete and result.entries_checked == 3 and result.directories_checked == 2
    assert "RAW_MUTATION_ACCESS" in result.rejections
    assert not result.raw_isolation_certified and not result.writable_publication
