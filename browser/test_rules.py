"""Real rule editor selects exact versions and resets preference explicitly."""

import subprocess
from pathlib import Path

import pytest
from django.core.management import call_command

from apps.catalog.models import Part
from apps.projects import models as m
from apps.projects import services as p
from tests.test_editions import edition_inputs as _edition_fixture
from tests.test_projects import values

edition_inputs = _edition_fixture


@pytest.mark.django_db(transaction=True)
def test_rule_editor_in_browser(edition_inputs, settings, tmp_path, request):
    actor, arr, parts, first, _second, _make = edition_inputs
    actor.set_password("Synthetic-rules-135")
    actor.save()
    settings.STATIC_ROOT = tmp_path / "static"
    call_command("collectstatic", interactive=False, verbosity=0)
    m.GlobalRuleState.objects.get_or_create(pk=1)
    project = p.save_project(values(), actor=actor)
    target = Part.objects.create(instrument=parts[0].instrument, code="3")
    position = m.ProjectPosition.objects.create(project=project, order=1, arrangement=arr)
    server = request.getfixturevalue("live_server")
    subprocess.run(
        [
            "node",
            str(Path(__file__).with_name("rules.cjs")),
            server.url,
            str(project.pk),
            str(arr.pk),
            str(parts[0].pk),
            str(target.pk),
            str(first.assignments.get().pk),
            str(position.pk),
        ],
        check=True,
        timeout=90,
    )
    assert m.GlobalReplacementRule.objects.get().active
    assert m.ReplacementRule.objects.get(project=project).active
    assert m.ProjectEditionPreference.objects.get(project=project).active is False
