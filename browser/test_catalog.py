"""German master-data workflow, copied expectations and protected references."""

import subprocess
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.catalog.models import Arrangement, Part, TemplatePart, Work
from apps.members.models import Member


@pytest.mark.django_db(transaction=True)
def test_master_data_in_real_browser(settings, tmp_path, request):
    settings.DEBUG_MODE = False
    settings.STATIC_ROOT = tmp_path / "staticfiles"
    call_command("collectstatic", interactive=False, verbosity=0)
    get_user_model().objects.create_user("synthetic-catalog", password="Synthetic-browser-135")
    server = request.getfixturevalue("live_server")
    subprocess.run(["node", str(Path(__file__).with_name("catalog.cjs")), server.url], check=True, timeout=90)
    assert Work.objects.filter(title="Synthetischer Marsch").count() == 2
    members = Member.objects.filter(name="Synthetische Person")
    assert members.count() == 2 and members.filter(active=True).count() == 1
    assert Part.objects.filter(code="1", active=True).count() == 1
    assert Arrangement.objects.get().expectations_defined
    assert Arrangement.objects.get().expected_parts.get().required
    assert not TemplatePart.objects.get().required
