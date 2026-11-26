"""Pinned-handle descriptor evidence; no ACL provisioning or certification."""

import ctypes as c
import os
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from core import windows_root_security as security
from core.files import FileError
from core.files_windows import WindowsSourceRoot


def pinned_root(tmp_path):
    root = WindowsSourceRoot(tmp_path)
    root._stack, root._handle = object(), 23
    root.root_metadata = Mock(return_value=SimpleNamespace(st_mode=0o040700))
    return root


def set_output(pointer, kind, value):
    c.cast(pointer, c.POINTER(kind))[0] = value


def descriptor_api(*, present=True, null=False, protected=False, count=2):
    buffer = c.create_string_buffer(128)
    base = c.addressof(buffer)

    def control(descriptor, flags, revision):
        set_output(flags, c.c_uint16, 0x8000 | (0x1000 if protected else 0))
        set_output(revision, security.DWORD, 1)
        return 1

    def owner(descriptor, output, defaulted):
        set_output(output, c.c_void_p, base + 20)
        return 1

    def dacl(descriptor, exists, output, defaulted):
        set_output(exists, c.c_int, int(present))
        set_output(output, c.c_void_p, None if null else base + 40)
        return 1

    def acl_information(acl, output, length, kind):
        assert length == c.sizeof(security.AclSize) and kind == 2
        value = c.cast(output, c.POINTER(security.AclSize)).contents
        value.count, value.used, value.free = count, 16, 0
        return 1

    api = SimpleNamespace(
        IsValidSecurityDescriptor=Mock(return_value=1),
        GetSecurityDescriptorLength=Mock(return_value=128),
        GetSecurityDescriptorControl=Mock(side_effect=control),
        GetSecurityDescriptorOwner=Mock(side_effect=owner),
        IsValidSid=Mock(return_value=1),
        GetLengthSid=Mock(return_value=12),
        CopySid=Mock(side_effect=lambda length, target, source: c.memmove(target, b"privateowner", length) or 1),
        GetSecurityDescriptorDacl=Mock(side_effect=dacl),
        IsValidAcl=Mock(return_value=1),
        GetAclInformation=Mock(side_effect=acl_information),
    )
    return api, buffer


@pytest.mark.parametrize(
    "present,null,protected,count",
    [(True, False, True, 2), (True, True, False, 0), (False, False, False, 0), (True, False, False, 0)],
)
def test_descriptor_evidence_distinguishes_null_absent_empty_and_protected(present, null, protected, count):
    api, buffer = descriptor_api(present=present, null=null, protected=protected, count=count)
    result = security._collect(api, c.c_void_p(c.addressof(buffer)))
    assert result.owner_sid == b"privateowner"
    assert "privateowner" not in repr(result)
    assert (result.dacl_present, result.dacl_null, result.dacl_protected, result.ace_count) == (
        present,
        present and null,
        protected,
        count,
    )
    assert not result.raw_isolation_certified and not result.writable_publication
    if not present or null:
        api.GetAclInformation.assert_not_called()


@pytest.mark.parametrize(
    "method",
    [
        "IsValidSecurityDescriptor",
        "GetSecurityDescriptorControl",
        "GetSecurityDescriptorOwner",
        "IsValidSid",
        "CopySid",
        "GetSecurityDescriptorDacl",
        "IsValidAcl",
        "GetAclInformation",
    ],
)
def test_descriptor_api_failure_is_rejected(method):
    api, buffer = descriptor_api()
    getattr(api, method).side_effect = None
    getattr(api, method).return_value = 0
    with pytest.raises(FileError, match="SECURITY_QUERY_FAILED"):
        security._collect(api, c.c_void_p(c.addressof(buffer)))


@pytest.mark.parametrize("invalid", ["length", "sid-length", "owner-pointer", "ace-count", "acl-size", "absolute"])
def test_descriptor_bounds_fail_closed(invalid):
    api, buffer = descriptor_api(count=security.MAX_ACES + 1 if invalid == "ace-count" else 2)
    if invalid == "length":
        api.GetSecurityDescriptorLength.return_value = security.MAX_DESCRIPTOR_BYTES + 1
    elif invalid == "sid-length":
        api.GetLengthSid.return_value = 69
    elif invalid == "owner-pointer":
        api.GetSecurityDescriptorOwner.side_effect = (
            lambda descriptor, output, defaulted: set_output(output, c.c_void_p, c.addressof(buffer) + 127) or 1
        )
    elif invalid == "acl-size":

        def excessive(acl, output, length, kind):
            value = c.cast(output, c.POINTER(security.AclSize)).contents
            value.used = 256
            return 1

        api.GetAclInformation.side_effect = excessive
    elif invalid == "absolute":
        api.GetSecurityDescriptorControl.side_effect = (
            lambda descriptor, flags, revision: set_output(flags, c.c_uint16, 0) or 1
        )
    with pytest.raises(FileError, match="SECURITY_QUERY_FAILED"):
        security._collect(api, c.c_void_p(c.addressof(buffer)))


@pytest.mark.parametrize("failure", [None, "access", "collect", "buffer", "argument", "free"])
def test_borrowed_handle_not_reopened_and_allocation_released(tmp_path, monkeypatch, failure):
    root = pinned_root(tmp_path)

    def get_security(handle, kind, mask, owner, group, dacl, sacl, output):
        assert handle == 23 and kind == 1 and mask == 5
        assert owner is group is dacl is sacl is None
        if failure != "access":
            set_output(output, c.c_void_p, 100)
        return 5 if failure == "access" else 0

    api = SimpleNamespace(
        GetSecurityInfo=Mock(side_effect=get_security), LocalFree=Mock(return_value=100 if failure == "free" else None)
    )
    monkeypatch.setattr(security.os, "name", "nt")
    monkeypatch.setattr(security, "_api", lambda: api)
    result = security.RootSecurityEvidence(b"private", True, False, False, 1)
    collect = Mock(return_value=result)
    monkeypatch.setattr(security, "_collect", collect)
    if failure in {"collect", "buffer", "argument"}:
        collect.side_effect = {"collect": OSError, "buffer": ValueError, "argument": c.ArgumentError}[failure](
            "sensitive private text"
        )
    if failure:
        with pytest.raises(FileError, match="^SECURITY_QUERY_FAILED$"):
            security.root_security_evidence(root)
    else:
        assert security.root_security_evidence(root) == result
    assert root._handle == 23
    if failure == "access":
        api.LocalFree.assert_not_called()
        collect.assert_not_called()
    else:
        api.LocalFree.assert_called_once()
        assert api.LocalFree.call_args.args[0].value == 100


def test_domain_file_error_preserved_with_descriptor_cleanup(tmp_path, monkeypatch):
    root = pinned_root(tmp_path)

    def get_security(handle, kind, mask, owner, group, dacl, sacl, output):
        set_output(output, c.c_void_p, 100)
        return 0

    api = SimpleNamespace(GetSecurityInfo=Mock(side_effect=get_security), LocalFree=Mock(return_value=None))
    monkeypatch.setattr(security.os, "name", "nt")
    monkeypatch.setattr(security, "_api", lambda: api)
    error = FileError("UNSAFE_ROOT")
    monkeypatch.setattr(security, "_collect", Mock(side_effect=error))
    with pytest.raises(FileError, match="^UNSAFE_ROOT$") as caught:
        security.root_security_evidence(root)
    assert caught.value is error
    api.LocalFree.assert_called_once()


def test_non_directory_metadata_preserves_unsafe_root_before_api(tmp_path, monkeypatch):
    root = pinned_root(tmp_path)
    root.root_metadata.return_value = SimpleNamespace(st_mode=0o100600)
    monkeypatch.setattr(security.os, "name", "nt")
    api = Mock()
    monkeypatch.setattr(security, "_api", api)
    with pytest.raises(FileError, match="^UNSAFE_ROOT$"):
        security.root_security_evidence(root)
    api.assert_not_called()


def test_platform_and_unpinned_root_fail_before_api(monkeypatch, tmp_path):
    api = Mock()
    monkeypatch.setattr(security, "_api", api)
    monkeypatch.setattr(security.os, "name", "posix")
    with pytest.raises(FileError, match="UNSUPPORTED_SECURITY_API"):
        security.root_security_evidence(WindowsSourceRoot(tmp_path))
    monkeypatch.setattr(security.os, "name", "nt")
    with pytest.raises(FileError, match="UNSAFE_ROOT"):
        security.root_security_evidence(WindowsSourceRoot(tmp_path))
    api.assert_not_called()


@pytest.mark.skipif(os.name != "nt", reason="Native Windows descriptor query")
def test_native_readonly_synthetic_root_descriptor(tmp_path):
    # Existing reader pins intentionally lack READ_CONTROL; no fallback reopen.
    with WindowsSourceRoot(tmp_path) as root, pytest.raises(FileError, match="SECURITY_QUERY_FAILED"):
        security.root_security_evidence(root)
    with WindowsSourceRoot(tmp_path, inspect_security=True) as root:
        result = security.root_security_evidence(root)
        assert result.owner_sid and result.ace_count <= security.MAX_ACES
        assert not result.raw_isolation_certified and not result.writable_publication
