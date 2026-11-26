"""Backend ownership checks and archive/export cleanup dispatch; no native writes."""

from types import SimpleNamespace
from unittest.mock import Mock, call
from uuid import UUID

import pytest

from apps.archive import publication as archive
from apps.exports import generation
from apps.jobs.models import OperationIntent
from core import files

IDENTIFIER = UUID("1" * 32)
STAGED = f".staging/{IDENTIFIER.hex}/attempt-1.pdf"


@pytest.mark.parametrize("owner", [41, 42])
def test_posix_stage_owner_check_preserves_exact_uid_comparison(tmp_path, monkeypatch, owner):
    monkeypatch.setattr(files.os, "geteuid", lambda: 41, raising=False)
    root = files.Root(tmp_path)
    info = SimpleNamespace(st_uid=owner)
    if owner == 41:
        assert root.validate_stage_owner(info) is None
    else:
        with pytest.raises(files.FileError, match="UNSAFE_STAGING"):
            root.validate_stage_owner(info)


def test_posix_stage_owner_check_propagates_identity_query_error(tmp_path, monkeypatch):
    error = OSError("Synthetic identity query failure")
    monkeypatch.setattr(files.os, "geteuid", Mock(side_effect=error), raising=False)
    with pytest.raises(OSError) as caught:
        files.Root(tmp_path).validate_stage_owner(SimpleNamespace(st_uid=41))
    assert caught.value is error


@pytest.mark.parametrize("consumer", ["archive", "export", "export-recovery"])
@pytest.mark.parametrize("failure", [None, "owner", "metadata"])
def test_cleanup_checks_backend_ownership_before_discard(monkeypatch, consumer, failure):
    context = Mock(attempt_number=2, using="default", job_id=IDENTIFIER)
    record = Mock(pk=IDENTIFIER)
    root = Mock(writable=True)
    info = SimpleNamespace(st_dev=3, st_ino=7)
    root.metadata.return_value = info  # Deliberately has no POSIX ownership fields.
    error = files.FileError("UNSAFE_STAGING") if failure == "owner" else OSError("Synthetic metadata failure")
    if failure == "owner":
        root.validate_stage_owner.side_effect = error
    elif failure == "metadata":
        root.metadata.side_effect = error

    if consumer == "archive":
        record.job.history.using.return_value.filter.return_value.exists.return_value = True

        def invoke():
            archive._prune_old_stages(context, record, root)
    elif consumer == "export":
        record.run.job.history.filter.return_value.exists.return_value = True

        def invoke():
            generation._cleanup(context, record, root)
    else:
        context.attempt_number = 1
        record.participant_id = None
        monkeypatch.setattr(generation, "_roots", Mock(return_value=(root, Mock())))
        monkeypatch.setattr(generation, "_processor", Mock())
        monkeypatch.setattr(generation, "prune_disposable", Mock())
        monkeypatch.setattr(generation.ExportPublication.objects, "filter", Mock(return_value=[record]))
        monkeypatch.setattr(OperationIntent.objects, "filter", Mock(return_value=Mock(first=Mock(return_value=None))))

        def invoke():
            generation.recover_cleanup(context)

    if failure is not None:
        with pytest.raises(type(error)) as caught:
            invoke()
        assert caught.value is error
        root.discard_stage.assert_not_called()
        context.checkpoint.assert_not_called()
        if failure == "metadata":
            root.validate_stage_owner.assert_not_called()
        else:
            root.validate_stage_owner.assert_called_once_with(info)
    else:
        invoke()
        assert root.mock_calls == [
            call.exists(STAGED),
            call.metadata(STAGED),
            call.validate_stage_owner(info),
            call.discard_stage(STAGED, (3, 7)),
        ]
        if consumer == "archive":
            context.checkpoint.assert_called_once_with()
