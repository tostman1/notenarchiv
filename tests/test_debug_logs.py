"""Synthetic debug UI, privacy, bounded pagination and rotation acceptance."""

import json
from datetime import UTC, datetime
from uuid import UUID

import pytest

from apps.jobs.services.diagnostics import MAX_LINE, InvalidCursor, read_page

JOB = str(UUID(int=1))


def record(**changes):
    value = {
        "timestamp": "2026-11-20T12:00:00+00:00",
        "level": "INFO",
        "component": "jobs",
        "service": "web",
        "event": "job_finished",
        "job_id": JOB,
    }
    value.update(changes)
    return value


def write_logs(directory, records, source="web"):
    directory.mkdir(exist_ok=True)
    path = directory / f"{source}.debug.log"
    path.write_text("".join(json.dumps(item) + "\n" for item in records), encoding="utf-8")
    return path


@pytest.fixture()
def debug_client(client, django_user_model, settings, tmp_path, db):
    settings.DEBUG_MODE = True
    settings.DIAGNOSTIC_LOG_DIR = tmp_path / "logs"
    client.force_login(django_user_model.objects.create_user("synthetic-debug"))
    return client


@pytest.mark.django_db
@pytest.mark.parametrize("route", ["/diagnostics/", "/diagnostics/records/", "/diagnostics/download/"])
def test_routes_require_debug_and_authentication(client, django_user_model, settings, tmp_path, route):
    settings.DIAGNOSTIC_LOG_DIR = tmp_path
    write_logs(tmp_path, [record()])
    settings.DEBUG_MODE = False
    assert client.get(route).status_code == 404
    client.force_login(django_user_model.objects.create_user("synthetic"))
    assert client.get(route).status_code == 404  # Old files never enable access in Deploy.
    client.logout()
    settings.DEBUG_MODE = True
    assert client.get(route).status_code == 302
    client.force_login(django_user_model.objects.get(username="synthetic"))
    response = client.get(route)
    assert response.status_code == 200
    assert "no-store" in response["Cache-Control"]


def test_filters_and_download_are_sanitized(debug_client, settings):
    write_logs(
        settings.DIAGNOSTIC_LOG_DIR,
        [
            record(message="<script>synthetic secret</script>", event="<img src=x onerror=alert(1)>"),
            record(level="ERROR", component="archive", timestamp="2026-11-20T13:00:00+00:00", error="synthetic secret"),
            record(level="ERROR", component="archive", job_id=str(UUID(int=2))),
        ],
    )
    params = {
        "source": "web",
        "level": "ERROR",
        "component": "archive",
        "job_id": JOB,
        "since": "2026-11-20T12:30:00Z",
        "until": "2026-11-20T14:00:00Z",
        "history": "on",
    }
    records = debug_client.get("/diagnostics/records/", params).json()["records"]
    assert len(records) == 1
    assert records[0]["level"] == "ERROR"
    download = debug_client.get("/diagnostics/download/", params)
    assert download["Content-Disposition"] == 'attachment; filename="diagnostics-web.jsonl"'
    assert [json.loads(line) for line in download.content.splitlines()] == records
    for route in ("/diagnostics/", "/diagnostics/records/", "/diagnostics/download/"):
        content = debug_client.get(route, {"history": "on"}).content
        assert b"synthetic secret" not in content
        assert b"onerror" not in content
        assert b"<img" not in content


@pytest.mark.parametrize(
    "params",
    [
        {"source": "../raw"},
        {"job_id": "synthetic private path"},
        {"level": "INVALID"},
        {"component": "<script>"},
        {"cursor": "invalid"},
        {"since": "2026-11-21T00:00Z", "until": "2026-11-20T00:00Z"},
    ],
)
def test_bad_filters_and_cursors_are_rejected(debug_client, params):
    assert debug_client.get("/diagnostics/records/", params).status_code == 400


def test_missing_files_and_io_failures_have_safe_responses(debug_client, settings, monkeypatch):
    assert debug_client.get("/diagnostics/records/").json()["records"] == []

    def unavailable(*args, **kwargs):
        raise PermissionError("synthetic private path")

    monkeypatch.setattr("apps.jobs.views.read_page", unavailable)
    response = debug_client.get("/diagnostics/records/")
    assert response.status_code == 503
    assert b"synthetic" not in response.content


def test_cursor_pages_survive_rotation_and_preserve_budget_boundary(tmp_path):
    entries = [record(duration_ms=number) for number in range(4)]
    path = write_logs(tmp_path, entries[:3])
    filters = {"source": "web", "history": True}
    first = read_page(tmp_path, filters, budget=len((json.dumps(entries[0]) + "\n").encode()) + 10)
    assert [row["duration_ms"] for row in first["records"]] == [0]
    path.rename(tmp_path / "web.debug.log.1")
    write_logs(tmp_path, entries[3:])
    rest = read_page(tmp_path, filters, first["cursor"])
    assert [row["duration_ms"] for row in rest["records"]] == [1, 2, 3]
    assert rest["more"] is False
    with pytest.raises(InvalidCursor):
        read_page(tmp_path, {"source": "worker"}, first["cursor"])


def test_lost_cursor_resets_and_partial_line_is_retried(tmp_path):
    path = write_logs(tmp_path, [record()])
    first = read_page(tmp_path, {"source": "web"})
    path.rename(tmp_path / "retired")  # Keep inode allocated, but no longer a retained log.
    path.write_text(json.dumps(record(level="ERROR")), encoding="utf-8")
    reset = read_page(tmp_path, {"source": "web"}, first["cursor"])
    assert reset["reset"] is True
    assert reset["records"] == []
    with path.open("a", encoding="utf-8") as stream:
        stream.write("\n")
    result = read_page(tmp_path, {"source": "web"}, reset["cursor"])
    assert [row["level"] for row in result["records"]] == ["ERROR"]


def test_malformed_oversized_and_untrusted_fields_never_escape(tmp_path):
    path = write_logs(tmp_path, [])
    path.write_bytes(
        b"not json\n"
        + b"x" * (MAX_LINE * 2)
        + b"\n"
        + b"\xff\n"
        + (json.dumps(record(component=["unsafe"])) + "\n").encode()
        + (json.dumps(record(timestamp="invalid")) + "\n").encode()
        + (json.dumps(record(message="synthetic secret", file_id="private path", duration_ms=True)) + "\n").encode()
    )
    result = read_page(tmp_path, {"source": "web", "history": True})
    assert result["records"] == [record()]


def test_download_and_json_page_have_fixed_record_limits(debug_client, settings):
    write_logs(settings.DIAGNOSTIC_LOG_DIR, [record() for _ in range(1100)])
    page = debug_client.get("/diagnostics/records/", {"history": "on"}).json()
    assert len(page["records"]) == 100
    assert page["more"] is True
    download = debug_client.get("/diagnostics/download/", {"history": "on"})
    assert len(download.content.splitlines()) == 1000
    assert download["X-Log-More"] == "true"


def test_naive_and_typed_cursor_validation(tmp_path):
    from django.core import signing

    from apps.jobs.services.diagnostics import SALT

    write_logs(tmp_path, [record(timestamp="2026-11-20T12:00:00")])
    assert read_page(tmp_path, {"source": "web"})["records"] == []
    cursor = signing.dumps({"source": "web", "offset": -1, "discard": False, "identity": [0, 0]}, salt=SALT)
    with pytest.raises(InvalidCursor):
        read_page(tmp_path, {"source": "web"}, cursor)


def test_time_filters_are_timezone_aware(tmp_path):
    write_logs(tmp_path, [record()])
    filters = {"source": "web", "since": datetime(2026, 11, 20, 12, 0, tzinfo=UTC)}
    assert len(read_page(tmp_path, filters)["records"]) == 1


def test_invalid_form_values_are_escaped(debug_client):
    response = debug_client.get("/diagnostics/", {"job_id": '<script>alert("synthetic")</script>'})
    assert response.status_code == 400
    assert b"&lt;script&gt;" in response.content
    assert b"<script>alert(" not in response.content


def test_expired_cursor_is_rejected(tmp_path, monkeypatch):
    from django.core import signing

    write_logs(tmp_path, [record()])
    page = read_page(tmp_path, {"source": "web"})

    def expired(*args, **kwargs):
        raise signing.SignatureExpired

    monkeypatch.setattr(signing, "loads", expired)
    with pytest.raises(InvalidCursor):
        read_page(tmp_path, {"source": "web"}, page["cursor"])


def test_symlink_source_is_never_read(tmp_path):
    target = tmp_path / "synthetic-target"
    target.write_text(json.dumps(record()) + "\n", encoding="utf-8")
    link = tmp_path / "web.debug.log"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("Creating symlinks requires a supported local permission; Linux CI exercises this case")
    assert read_page(tmp_path, {"source": "web"})["records"] == []
