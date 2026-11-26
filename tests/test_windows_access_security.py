"""Read-only root AccessCheck evidence, not mutation attempts or RAW certification."""

import ctypes as c
import os
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from core import windows_access_security as security
from core.files import FileError
from core.files_windows import WindowsSourceRoot


def output(pointer, kind, value):
    c.cast(pointer, c.POINTER(kind))[0] = value


@pytest.mark.parametrize("allowed,granted", [(False, 0), (True, 0x120089), (True, 0x1F01FF)])
def test_accesscheck_distinguishes_denial_from_api_failure(allowed, granted):
    def check(descriptor, token, desired, mapping, privileges, size, access, status):
        assert descriptor == 100 and token == 24 and desired == 0x02000000
        values = c.cast(mapping, c.POINTER(security.GenericMapping)).contents
        assert (values.read, values.write, values.execute, values.all) == (0x120089, 0x120116, 0x1200A0, 0x1F01FF)
        output(access, security.DWORD, granted)
        output(status, c.c_int, int(allowed))
        return 1  # API success even when access is denied.

    api = SimpleNamespace(AccessCheck=Mock(side_effect=check))
    assert security._check(api, 100, 24) == (allowed, granted)
    api.AccessCheck.assert_called_once()


@pytest.mark.parametrize("required,error", [(65537, 122), (256, 122), (512, 5)])
def test_privilege_buffer_failures_are_bounded(monkeypatch, required, error):
    def check(descriptor, token, desired, mapping, privileges, size, access, status):
        output(size, security.DWORD, required)
        return 0

    monkeypatch.setattr(c, "get_last_error", lambda: error, raising=False)
    api = SimpleNamespace(AccessCheck=Mock(side_effect=check))
    with pytest.raises(FileError, match="SECURITY_QUERY_FAILED"):
        security._check(api, 100, 24)
    api.AccessCheck.assert_called_once()


@pytest.mark.parametrize("succeed", [False, True])
def test_privilege_buffer_retry_limit_and_success(monkeypatch, succeed):
    calls = []

    def check(descriptor, token, desired, mapping, privileges, size, access, status):
        calls.append(len(privileges))
        output(size, security.DWORD, len(privileges) * 2)
        if succeed and len(calls) == 2:
            output(size, security.DWORD, len(privileges))
            output(status, c.c_int, 1)
            return 1
        return 0

    monkeypatch.setattr(c, "get_last_error", lambda: 122, raising=False)
    api = SimpleNamespace(AccessCheck=Mock(side_effect=check))
    if succeed:
        assert security._check(api, 100, 24) == (True, 0)
        assert calls == [256, 512]
    else:
        with pytest.raises(FileError, match="SECURITY_QUERY_FAILED"):
            security._check(api, 100, 24)
        assert calls == [256, 512, 1024]


@pytest.mark.parametrize("status,granted", [(2, 0), (0, 2)])
def test_inconsistent_access_outputs_fail_closed(status, granted):
    def check(descriptor, token, desired, mapping, privileges, size, access, allowed):
        output(access, security.DWORD, granted)
        output(allowed, c.c_int, status)
        return 1

    with pytest.raises(FileError, match="SECURITY_QUERY_FAILED"):
        security._check(SimpleNamespace(AccessCheck=check), 100, 24)


def adapters(monkeypatch, failure=None):
    events = []

    def open_token(process, access, pointer):
        assert access == 0xA
        if failure == "open":
            return 0
        output(pointer, c.c_void_p, 23)
        return 1

    def duplicate(token, access, attributes, level, kind, pointer):
        assert token.value == 23 and (access, attributes, level, kind) == (8, None, 2, 2)
        if failure == "duplicate":
            return 0
        output(pointer, c.c_void_p, 24)
        return 1

    def descriptor(handle, kind, mask, owner, group, dacl, sacl, pointer):
        assert handle == 25 and kind == 1 and mask == 7
        assert owner is group is dacl is sacl is None
        if failure != "descriptor":
            output(pointer, c.c_void_p, 100)
        return 5 if failure == "descriptor" else 0

    def close(handle):
        events.append(("close", handle.value))
        return failure != "close"

    def free(pointer):
        events.append(("free", pointer.value))
        return 100 if failure == "free" else None

    token_api = SimpleNamespace(
        GetCurrentProcess=Mock(return_value=17),
        OpenProcessToken=Mock(side_effect=open_token),
        GetHandleInformation=Mock(return_value=0 if failure == "flags" else 1),
        CloseHandle=Mock(side_effect=close),
    )
    api = SimpleNamespace(DuplicateTokenEx=Mock(side_effect=duplicate))
    descriptor_api = SimpleNamespace(GetSecurityInfo=Mock(side_effect=descriptor), LocalFree=Mock(side_effect=free))
    monkeypatch.setattr(security.os, "name", "nt")
    monkeypatch.setattr(security, "_api", lambda: api)
    monkeypatch.setattr(security.tokens, "_api", lambda: token_api)
    monkeypatch.setattr(security.descriptors, "_api", lambda: descriptor_api)
    token = SimpleNamespace(
        user_sid=b"private-user", privileges=(), elevated=False, elevation_type=1, administrator_enabled=False
    )
    monkeypatch.setattr(security.tokens, "_collect", Mock(return_value=token))
    monkeypatch.setattr(
        security.descriptors, "_collect", Mock(return_value=SimpleNamespace(owner_sid=b"private-owner"))
    )
    check = Mock(return_value=(True, 0x1F01FF))
    if failure == "check":
        check.side_effect = OSError("sensitive native text")
    monkeypatch.setattr(security, "_check", check)
    return events, token


@pytest.mark.parametrize("granted", [0, 2, 4, 0x10, 0x100, 0x10000, 0x40000, 0x80000, 0x40])
@pytest.mark.parametrize("owner", [False, True])
def test_root_owner_and_precise_mutation_evidence_remain_uncertified(tmp_path, monkeypatch, granted, owner):
    events, token = adapters(monkeypatch)
    if owner:
        token.user_sid = b"private-owner"
    monkeypatch.setattr(security, "_check", Mock(return_value=(bool(granted), granted)))
    root = WindowsSourceRoot(tmp_path, inspect_security=True)
    root._stack, root._handle = object(), 25
    root.root_metadata = Mock(return_value=SimpleNamespace(st_mode=0o040700))
    result = security.root_access_evidence(root)
    assert result.owner_is_process_user is owner
    assert result.mutation_access == granted
    assert result.directory and not result.raw_isolation_certified and not result.writable_publication
    assert "private" not in repr(result)
    assert events == [("free", 100), ("close", 24), ("close", 23)]
    assert root._handle == 25


@pytest.mark.parametrize("failure", ["open", "flags", "duplicate", "descriptor", "check", "free", "close"])
def test_resource_failures_close_all_acquired_resources(tmp_path, monkeypatch, failure):
    events, _ = adapters(monkeypatch, failure)
    root = WindowsSourceRoot(tmp_path)
    root._stack, root._handle = object(), 25
    root.root_metadata = Mock(return_value=SimpleNamespace(st_mode=0o040700))
    with pytest.raises(FileError, match="^SECURITY_QUERY_FAILED$"):
        security.root_access_evidence(root)
    expected = {
        "open": [],
        "flags": [("close", 23)],
        "duplicate": [("close", 23)],
        "descriptor": [("close", 24), ("close", 23)],
    }.get(failure, [("free", 100), ("close", 24), ("close", 23)])
    assert events == expected


@pytest.mark.parametrize("dangerous,administrative", [(True, False), (False, True)])
def test_token_risk_evidence_survives_acl_denial(tmp_path, monkeypatch, dangerous, administrative):
    _, token = adapters(monkeypatch)
    token.privileges = (("SeRestorePrivilege", False),) if dangerous else ()
    token.administrator_enabled = administrative
    monkeypatch.setattr(security, "_check", Mock(return_value=(False, 0)))
    root = WindowsSourceRoot(tmp_path)
    root._stack, root._handle = object(), 25
    root.root_metadata = Mock(return_value=SimpleNamespace(st_mode=0o040700))
    result = security.root_access_evidence(root)
    assert result.dangerous_privileges_present is dangerous
    assert result.administrative_token is administrative
    assert result.mutation_access == 0
    assert not result.raw_isolation_certified and not result.writable_publication


def test_mutation_masks_contain_only_intended_precise_write_rights():
    intended = sum([0x2, 0x4, 0x10, 0x100, 0x10000, 0x40000, 0x80000])
    assert security.FILE_MUTATION_MASK == intended == 0x000D0116
    directory_intended = intended | 0x40
    assert directory_intended == security.DIRECTORY_MUTATION_MASK
    assert security.DIRECTORY_MUTATION_MASK ^ security.FILE_MUTATION_MASK == 0x40


@pytest.mark.parametrize(
    "granted",
    [0x1, 0x8, 0x80, 0x20000, 0x100000, 0x120089],
    ids=["read-data", "read-ea", "read-attributes", "read-control", "synchronize", "file-generic-read"],
)
def test_readonly_grants_have_no_mutation_access(tmp_path, monkeypatch, granted):
    events, _ = adapters(monkeypatch)
    monkeypatch.setattr(security, "_check", Mock(return_value=(True, granted)))
    root = WindowsSourceRoot(tmp_path, inspect_security=True)
    root._stack, root._handle = object(), 25
    root.root_metadata = Mock(return_value=SimpleNamespace(st_mode=0o040700))
    result = security.root_access_evidence(root)
    assert result.access_allowed and result.granted_access == granted
    assert result.mutation_access == 0
    assert not result.raw_isolation_certified and not result.writable_publication
    assert events == [("free", 100), ("close", 24), ("close", 23)]


def test_platform_and_unpinned_root_guard(monkeypatch, tmp_path):
    api = Mock()
    monkeypatch.setattr(security, "_api", api)
    monkeypatch.setattr(security.os, "name", "posix")
    with pytest.raises(FileError, match="UNSUPPORTED_SECURITY_API"):
        security.root_access_evidence(WindowsSourceRoot(tmp_path))
    monkeypatch.setattr(security.os, "name", "nt")
    with pytest.raises(FileError, match="UNSAFE_ROOT"):
        security.root_access_evidence(WindowsSourceRoot(tmp_path))
    api.assert_not_called()


@pytest.mark.skipif(os.name != "nt", reason="Native Windows AccessCheck")
def test_native_readonly_tmp_root_access_evidence(tmp_path):
    with WindowsSourceRoot(tmp_path, inspect_security=True) as root:
        result = security.root_access_evidence(root)
        assert result.directory and result.owner_sid and result.user_sid
        assert result.mutation_access == result.granted_access & security.DIRECTORY_MUTATION_MASK
        assert not result.raw_isolation_certified and not result.writable_publication


@pytest.mark.parametrize("directory", [False, True])
def test_borrowed_handle_uses_file_or_directory_mutation_mask(monkeypatch, directory):
    adapters(monkeypatch)
    monkeypatch.setattr(security, "_check", Mock(return_value=(True, 0x40 | 0x40000 | 0x80000)))
    result = security._handle_access_evidence(25, directory=directory)
    assert result.directory is directory
    assert result.mutation_access == (0x40 | 0x40000 | 0x80000 if directory else 0x40000 | 0x80000)
    assert not result.raw_isolation_certified and not result.writable_publication


@pytest.mark.skipif(os.name != "nt", reason="Native Windows descendant/parent AccessCheck")
def test_native_file_directory_and_parent_access_evidence(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "nested").mkdir()
    (raw / "nested" / "score.pdf").write_bytes(b"synthetic")
    with WindowsSourceRoot(raw, inspect_security=True) as root:
        for path, directory in (("nested", True), ("nested/score.pdf", False)):
            result = security.relative_entry_access_evidence(root, path)
            assert result.directory is directory
            mask = security.DIRECTORY_MUTATION_MASK if directory else security.FILE_MUTATION_MASK
            assert result.mutation_access == result.granted_access & mask
            assert not result.raw_isolation_certified and not result.writable_publication
        parent = security.parent_access_evidence(root)
        assert parent.directory
        assert parent.mutation_access == parent.granted_access & security.DIRECTORY_MUTATION_MASK
        assert not parent.raw_isolation_certified and not parent.writable_publication


@pytest.mark.skipif(os.name != "nt", reason="Native Windows security mode guard")
def test_access_entry_and_parent_disabled_without_explicit_mode(tmp_path, monkeypatch):
    with WindowsSourceRoot(tmp_path) as root:
        monkeypatch.setattr(security, "_handle_access_evidence", lambda *_, **__: pytest.fail("No disabled query"))
        with pytest.raises(FileError, match="UNSAFE_ROOT"):
            security.relative_entry_access_evidence(root, "score.pdf")
        with pytest.raises(FileError, match="UNSAFE_ROOT"):
            security.parent_access_evidence(root)
