"""Read-only process-token evidence and explicitly uncertified capabilities."""

import ctypes as c
import os
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from core import windows_security as security
from core.files import FileError


def evidence(**changes):
    values = dict(
        user_sid=b"synthetic-private-user",
        owner_sid=b"synthetic-private-owner",
        privileges=(),
        elevated=False,
        elevation_type=1,
        restricted=False,
        administrator_enabled=False,
    )
    values.update(changes)
    return security.TokenEvidence(**values)


@pytest.mark.parametrize("restricted", [False, True])
def test_acceptable_token_never_certifies_raw_or_publication(restricted):
    result = security.capabilities(evidence(restricted=restricted))
    assert result.token_policy_rejections == ()
    assert result.raw_isolation_certified is False and result.writable_publication is False


@pytest.mark.parametrize("name", sorted(security.DANGEROUS_PRIVILEGES))
@pytest.mark.parametrize("enabled", [False, True])
def test_dangerous_privilege_presence_is_rejected_even_when_disabled(name, enabled):
    result = security.capabilities(evidence(privileges=((name, enabled),)))
    assert result.token_policy_rejections == ("DANGEROUS_PRIVILEGE_PRESENT",)
    assert not result.raw_isolation_certified and not result.writable_publication


@pytest.mark.parametrize("changes", [{"elevated": True}, {"elevation_type": 2}, {"administrator_enabled": True}])
def test_administrative_evidence_is_rejected(changes):
    result = security.capabilities(evidence(**changes))
    assert result.token_policy_rejections == ("ADMINISTRATIVE_TOKEN",)
    assert not result.raw_isolation_certified and not result.writable_publication


def test_identity_bytes_are_not_in_default_representation():
    token = evidence()
    assert "synthetic-private" not in repr(token)


def fake_api():
    def open_token(process, access, output):
        assert process == 17 and access == 0x0008
        c.cast(output, c.POINTER(c.c_void_p))[0] = 23
        return 1

    return SimpleNamespace(
        GetCurrentProcess=Mock(return_value=17),
        OpenProcessToken=Mock(side_effect=open_token),
        GetHandleInformation=Mock(return_value=1),
        CloseHandle=Mock(return_value=1),
    )


@pytest.mark.parametrize(
    "failure", [None, "open", "inherit", "flags", "collect", "close", "native", "buffer", "argument"]
)
def test_query_handle_access_cleanup_and_sanitized_errors(monkeypatch, failure):
    api = fake_api()
    monkeypatch.setattr(security.os, "name", "nt")
    monkeypatch.setattr(security, "_api", lambda: api)
    collect = Mock(return_value=evidence())
    monkeypatch.setattr(security, "_collect", collect)
    if failure == "open":
        api.OpenProcessToken.side_effect = None
        api.OpenProcessToken.return_value = 0
    elif failure == "inherit":

        def inherited(token, flags):
            c.cast(flags, c.POINTER(security.DWORD))[0] = 1
            return 1

        api.GetHandleInformation.side_effect = inherited
    elif failure == "flags":
        api.GetHandleInformation.return_value = 0
    elif failure == "collect":
        collect.side_effect = FileError("SECURITY_QUERY_FAILED")
    elif failure == "close":
        api.CloseHandle.return_value = 0
    elif failure == "native":
        collect.side_effect = OSError("Synthetic sensitive error details")
    elif failure == "buffer":
        collect.side_effect = ValueError("Synthetic sensitive buffer details")
    elif failure == "argument":
        collect.side_effect = c.ArgumentError("Synthetic sensitive argument details")
    if failure:
        with pytest.raises(FileError, match="^SECURITY_QUERY_FAILED$") as caught:
            security.current_process_token()
        assert "sensitive" not in str(caught.value)
    else:
        assert security.current_process_token() == evidence()
    if failure == "open":
        api.CloseHandle.assert_not_called()
    else:
        api.CloseHandle.assert_called_once()
        assert api.CloseHandle.call_args.args[0].value == 23
    if failure in {"open", "inherit", "flags"}:
        collect.assert_not_called()


def test_non_windows_call_fails_before_loading_native_api(monkeypatch):
    monkeypatch.setattr(security.os, "name", "posix")
    api = Mock()
    monkeypatch.setattr(security, "_api", api)
    with pytest.raises(FileError, match="UNSUPPORTED_SECURITY_API"):
        security.current_process_token()
    api.assert_not_called()


def test_domain_file_error_preserved_with_token_handle_cleanup(monkeypatch):
    api = fake_api()
    monkeypatch.setattr(security.os, "name", "nt")
    monkeypatch.setattr(security, "_api", lambda: api)
    error = FileError("UNSAFE_ROOT")
    monkeypatch.setattr(security, "_collect", Mock(side_effect=error))
    with pytest.raises(FileError, match="^UNSAFE_ROOT$") as caught:
        security.current_process_token()
    assert caught.value is error
    api.CloseHandle.assert_called_once()


@pytest.mark.parametrize("size", [0, security.MAX_TOKEN_BYTES + 1])
def test_token_query_rejects_unbounded_buffer_requests(monkeypatch, size):
    def query(token, kind, buffer, length, needed):
        c.cast(needed, c.POINTER(security.DWORD))[0] = size
        return 0

    monkeypatch.setattr(c, "get_last_error", lambda: 122, raising=False)
    api = SimpleNamespace(GetTokenInformation=Mock(side_effect=query))
    with pytest.raises(FileError, match="SECURITY_QUERY_FAILED"):
        security._query(api, 23, 1)
    api.GetTokenInformation.assert_called_once()


def test_sid_parser_rejects_out_of_buffer_pointer():
    buffer = c.create_string_buffer(16)
    with pytest.raises(FileError, match="SECURITY_QUERY_FAILED"):
        security._sid(buffer, c.addressof(buffer) + 12)


def token_buffers(attributes=4, *, admin=True, privilege=False):
    """Build synthetic native layouts, retaining every embedded SID in its buffer."""
    sid = b"\x01\x02\x00\x00\x00\x00\x00\x05" + (32).to_bytes(4, "little")
    sid += (544 if admin else 545).to_bytes(4, "little")
    user = c.create_string_buffer(c.sizeof(security.SidAttributes) + len(sid))
    user_offset = c.sizeof(security.SidAttributes)
    c.memmove(c.addressof(user) + user_offset, sid, len(sid))
    security.SidAttributes.from_buffer(user).sid = c.addressof(user) + user_offset
    owner = c.create_string_buffer(c.sizeof(c.c_void_p) + len(sid))
    c.memmove(c.addressof(owner) + c.sizeof(c.c_void_p), sid, len(sid))
    c.c_void_p.from_buffer(owner).value = c.addressof(owner) + c.sizeof(c.c_void_p)

    class Groups(c.Structure):
        _fields_ = [("count", security.DWORD), ("entries", security.SidAttributes * 1)]

    groups = c.create_string_buffer(c.sizeof(Groups) + len(sid))
    value = Groups.from_buffer(groups)
    value.count = 1
    value.entries[0].sid = c.addressof(groups) + c.sizeof(Groups)
    value.entries[0].attributes = attributes
    c.memmove(value.entries[0].sid, sid, len(sid))
    privileges = c.create_string_buffer(4 + (c.sizeof(security.Privilege) if privilege else 0))
    security.DWORD.from_buffer(privileges).value = int(privilege)
    elevation_type, elevation = c.create_string_buffer(4), c.create_string_buffer(4)
    security.DWORD.from_buffer(elevation_type).value = 1
    return {1: user, 4: owner, 2: groups, 3: privileges, 18: elevation_type, 20: elevation}


@pytest.mark.parametrize(
    ("attributes", "admin", "enabled"),
    [(4, True, True), (2, True, False), (1, True, False), (16, True, False), (4 | 16, True, False), (4, False, False)],
    ids=["enabled", "enabled-by-default", "mandatory", "deny-only", "deny-overrides-enabled", "absent-admin"],
)
def test_collect_uses_enabled_group_bit_not_default_or_mandatory(monkeypatch, attributes, admin, enabled):
    buffers = token_buffers(attributes, admin=admin)
    query = Mock(side_effect=lambda api, token, kind: buffers[kind])
    monkeypatch.setattr(security, "_query", query)
    api = SimpleNamespace(IsTokenRestricted=Mock(return_value=0), LookupPrivilegeNameW=Mock())
    token = security._collect(api, 23)
    assert token.administrator_enabled is enabled
    assert token.user_sid and token.owner_sid
    assert token.privileges == ()
    api.LookupPrivilegeNameW.assert_not_called()
    result = security.capabilities(token)
    assert not result.raw_isolation_certified and not result.writable_publication


@pytest.mark.parametrize("entry", [security.SidAttributes, security.Privilege])
@pytest.mark.parametrize("case", ["short-count", "missing-entry", "huge-count"])
def test_array_rejects_truncated_or_excessive_counts(entry, case):
    buffer = c.create_string_buffer(3 if case == "short-count" else 4)
    if case != "short-count":
        security.DWORD.from_buffer(buffer).value = 1 if case == "missing-entry" else 0xFFFFFFFF
    with pytest.raises(FileError, match="SECURITY_QUERY_FAILED"):
        security._array(buffer, entry)


@pytest.mark.parametrize("entry", [security.SidAttributes, security.Privilege])
def test_array_accepts_exact_entry_boundary(entry):
    class Array(c.Structure):
        _fields_ = [("count", security.DWORD), ("entries", entry * 1)]

    buffer = c.create_string_buffer(c.sizeof(Array))
    security.DWORD.from_buffer(buffer).value = 1
    assert len(security._array(buffer, entry)) == 1
    security.DWORD.from_buffer(buffer).value = 2
    with pytest.raises(FileError, match="SECURITY_QUERY_FAILED"):
        security._array(buffer, entry)


def test_collect_privilege_lookup_failure_is_sanitized(monkeypatch):
    buffers = token_buffers(privilege=True)
    monkeypatch.setattr(security, "_query", lambda api, token, kind: buffers[kind])
    api = SimpleNamespace(IsTokenRestricted=Mock(), LookupPrivilegeNameW=Mock(return_value=0))
    with pytest.raises(FileError, match="^SECURITY_QUERY_FAILED$"):
        security._collect(api, 23)
    api.LookupPrivilegeNameW.assert_called_once()
    api.IsTokenRestricted.assert_not_called()


@pytest.mark.parametrize("kind", [18, 20])
@pytest.mark.parametrize("failure", [False, True])
def test_fixed_token_information_uses_exact_dword_buffer(kind, failure):
    def query(token, information, buffer, length, needed):
        assert information == kind and length == 4 and buffer is not None
        c.cast(needed, c.POINTER(security.DWORD))[0] = 4
        if not failure:
            c.cast(buffer, c.POINTER(security.DWORD))[0] = 1
        return not failure

    api = SimpleNamespace(GetTokenInformation=Mock(side_effect=query))
    if failure:
        with pytest.raises(FileError, match="SECURITY_QUERY_FAILED"):
            security._query(api, 23, kind)
    else:
        assert security._scalar(security._query(api, 23, kind)) == 1
    api.GetTokenInformation.assert_called_once()


@pytest.mark.skipif(os.name != "nt", reason="Native Windows process token query")
def test_native_current_process_token_readonly_smoke():
    token = security.current_process_token()
    # Compare private identities only in memory; never log their exact values.
    assert token.user_sid and token.owner_sid
    assert token.elevation_type in {1, 2, 3}
    assert type(token.elevated) is bool and type(token.restricted) is bool
    assert all(isinstance(name, str) and type(enabled) is bool for name, enabled in token.privileges)
    result = security.capabilities(token)
    assert not result.raw_isolation_certified and not result.writable_publication
