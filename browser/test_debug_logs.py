"""Real-browser debug filtering, live polling, sanitized download and auth."""

import json
import subprocess
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command


@pytest.mark.django_db(transaction=True)
def test_debug_logs_in_browser(settings, tmp_path, request):
    settings.DEBUG_MODE = True
    settings.DIAGNOSTIC_LOG_DIR = tmp_path / "logs"
    settings.DIAGNOSTIC_LOG_DIR.mkdir()
    settings.STATIC_ROOT = tmp_path / "staticfiles"
    call_command("collectstatic", interactive=False, verbosity=0)
    log = settings.DIAGNOSTIC_LOG_DIR / "web.debug.log"
    log.write_text(
        json.dumps(
            {
                "timestamp": "2026-11-20T12:00:00+00:00",
                "level": "INFO",
                "component": "jobs",
                "service": "web",
                "event": "job_finished",
                "message": "<script>synthetic secret</script>",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    get_user_model().objects.create_user("synthetic-debug", password="Synthetic-browser-135")
    server = request.getfixturevalue("live_server")
    subprocess.run(
        ["node", str(Path(__file__).with_name("debug_logs.cjs")), server.url, str(log)],
        check=True,
        timeout=60,
    )
