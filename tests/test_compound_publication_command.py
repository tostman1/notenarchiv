"""The compound entry point queues existing durable publication, never approval."""

from io import StringIO
from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError


def test_command_passes_exact_version_and_explicit_title(monkeypatch):
    version_id, job_id = uuid4(), uuid4()
    calls = []

    def enqueue(version, *, title):
        calls.append((version, title))
        return SimpleNamespace(pk=job_id)

    monkeypatch.setattr("apps.archive.management.commands.publish_compound_source.queue_compound_copy", enqueue)
    output = StringIO()
    call_command("publish_compound_source", str(version_id), title="Synthetic booklet", stdout=output)
    assert calls == [(version_id, "Synthetic booklet")]
    assert output.getvalue().strip() == str(job_id)


@pytest.mark.parametrize("error", [ValidationError("private source context"), OSError("private path")])
def test_command_errors_do_not_disclose_source_context(monkeypatch, error):
    def enqueue(*args, **kwargs):
        raise error

    monkeypatch.setattr("apps.archive.management.commands.publish_compound_source.queue_compound_copy", enqueue)
    with pytest.raises(CommandError) as raised:
        call_command("publish_compound_source", str(uuid4()), title="Synthetic booklet")
    assert "private" not in str(raised.value)
