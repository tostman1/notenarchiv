"""Synthetic reproductions of P0 false-green CI evidence."""

import pytest

from scripts.wait_for_ci import CheckRun, WaitConfig, _evaluate_pr, _verified_docs_only, main, poll_once
from tests.test_wait_for_ci import REPO, SHA, FakeClock, config, response, transport_from

FOUNDATION = "Foundation (ruff + pytest)"
CONTAINER = "Container (amd64 + security + synthetic smoke)"


def cfg(**kwargs):
    return WaitConfig(mode="pr", repo=REPO, sha=SHA, pr=42, **kwargs)


def test_foundation_alone_is_not_full_verification():
    checks = [CheckRun(FOUNDATION, "completed", "success", SHA)]
    assert _evaluate_pr(checks, SHA, cfg())["kind"] == "mismatch"


def test_explicit_requirements_cannot_remove_container():
    checks = [CheckRun(FOUNDATION, "completed", "success", SHA)]
    assert _evaluate_pr(checks, SHA, cfg(required_checks=(FOUNDATION,)))["kind"] == "mismatch"


@pytest.mark.parametrize("sha", ["", None, 12, "bad", "b" * 40])
def test_check_sha_must_be_complete_and_bound(sha):
    checks = [CheckRun(name, "completed", "success", sha) for name in (FOUNDATION, CONTAINER)]
    assert _evaluate_pr(checks, SHA, cfg())["kind"] == "mismatch"


@pytest.mark.parametrize("sha", ["", None, 12, "bad", "b" * 40])
def test_pr_sha_must_be_complete_and_bound(sha):
    evidence = [
        response({"head": {"sha": sha}}),
        response(
            {
                "total_count": 2,
                "check_runs": [
                    {"name": name, "status": "completed", "conclusion": "success", "head_sha": SHA}
                    for name in (FOUNDATION, CONTAINER)
                ],
            }
        ),
    ]
    assert poll_once(cfg(), transport_from(evidence, []), 0)["kind"] == "mismatch"


def test_run_aggregate_success_does_not_prove_jobs():
    evidence = [
        response({"status": "completed", "conclusion": "success", "head_sha": SHA}),
        response({"total_count": 0, "jobs": []}),
    ]
    config = WaitConfig(mode="run", repo=REPO, sha=SHA, run_id=7)
    assert poll_once(config, transport_from(evidence, []), 0)["kind"] == "mismatch"


@pytest.mark.parametrize("conclusion", ["skipped", "neutral", "unknown", ""])
def test_required_insufficient_conclusion_is_mismatch(conclusion):
    checks = [CheckRun(FOUNDATION, "completed", "success", SHA), CheckRun(CONTAINER, "completed", conclusion, SHA)]
    assert _evaluate_pr(checks, SHA, cfg())["kind"] == "mismatch"


@pytest.mark.parametrize(
    "paths, expected",
    [
        (b"docs/PROGRESS.md\0tests/TRACEABILITY.md\0", True),
        (b"docs/PROGRESS.md\0scripts/wait_for_ci.py\0", False),
        (b"docs/PROCESS.md\0", False),
        (b"", False),
    ],
)
def test_exact_git_classification_is_cached(monkeypatch, paths, expected):
    calls = []
    base = "b" * 40

    def git(args, **kwargs):
        calls.append(args)
        if args[1] == "rev-parse":
            return args[-1][:40] + "\n"
        assert args[-2:] == [base, SHA]
        return paths

    monkeypatch.setattr("scripts.wait_for_ci.subprocess.check_output", git)
    config = cfg()
    pr = {"base": {"sha": base}, "head": {"sha": SHA}}
    assert _verified_docs_only(pr, config) is expected
    assert _verified_docs_only(pr, config) is expected
    assert len(calls) == 3


def test_unavailable_classification_requires_full_scope(monkeypatch):
    def unavailable(*args, **kwargs):
        raise OSError("missing git")

    monkeypatch.setattr("scripts.wait_for_ci.subprocess.check_output", unavailable)
    assert not _verified_docs_only({"base": {"sha": "b" * 40}, "head": {"sha": SHA}}, cfg())


@pytest.mark.parametrize("container", [None, "skipped", "success"])
def test_verified_docs_exception(container):
    checks = [CheckRun(FOUNDATION, "completed", "success", SHA), CheckRun("changes", "completed", "success", SHA)]
    if container:
        checks.append(CheckRun(CONTAINER, "completed", container, SHA))
    assert _evaluate_pr(checks, SHA, cfg(), docs_exception=True)["kind"] == "success"
    if container != "success":
        assert _evaluate_pr(checks, SHA, cfg())["kind"] == "mismatch"


def test_docs_exception_requires_classification_success():
    checks = [CheckRun(FOUNDATION, "completed", "success", SHA)]
    assert _evaluate_pr(checks, SHA, cfg(), docs_exception=True)["kind"] == "mismatch"


@pytest.mark.parametrize(
    "conclusion, kind",
    [("skipped", "mismatch"), ("failure", "failed"), ("cancelled", "cancelled"), ("neutral", "mismatch")],
)
def test_run_checks_individual_jobs(conclusion, kind):
    jobs = [
        {"name": name, "status": "completed", "conclusion": result, "head_sha": SHA}
        for name, result in ((FOUNDATION, "success"), (CONTAINER, conclusion))
    ]
    evidence = [
        response({"status": "completed", "conclusion": "success", "head_sha": SHA}),
        response({"total_count": 2, "jobs": jobs}),
    ]
    assert (
        poll_once(WaitConfig(mode="run", repo=REPO, sha=SHA, run_id=7), transport_from(evidence, []), 0)["kind"] == kind
    )


@pytest.mark.parametrize("level", ["run", "job"])
@pytest.mark.parametrize("sha", [None, "", 12, "bad", "b" * 40])
def test_run_sha_evidence(level, sha):
    evidence = [
        response({"status": "completed", "conclusion": "success", "head_sha": sha if level == "run" else SHA}),
        response(
            {
                "total_count": 1,
                "jobs": [{"name": FOUNDATION, "status": "completed", "conclusion": "success", "head_sha": sha}],
            }
        ),
    ]
    assert (
        poll_once(WaitConfig(mode="run", repo=REPO, sha=SHA, run_id=7), transport_from(evidence, []), 0)["kind"]
        == "mismatch"
    )


@pytest.mark.parametrize("count", [None, "2", -1, 3, 101])
def test_incomplete_check_response(count):
    evidence = [response({"head": {"sha": SHA}}), response({"total_count": count, "check_runs": []})]
    assert poll_once(cfg(), transport_from(evidence, []), 0)["kind"] == "mismatch"


def test_invalid_cli_sha_is_usage_error():
    assert main(["--mode", "pr", "--pr", "42", "--sha", "bad", "--repo", REPO]) == 64


@pytest.mark.parametrize(
    "status, kind", [("in_progress", "pending"), ("requested", "pending"), ("garbage", "mismatch"), ("", "mismatch")]
)
def test_required_status_is_not_inferred_from_conclusion(status, kind):
    checks = [CheckRun(FOUNDATION, status, "success", SHA), CheckRun(CONTAINER, "completed", "success", SHA)]
    assert _evaluate_pr(checks, SHA, cfg())["kind"] == kind


def test_foreign_sha_is_rejected_while_run_pending():
    evidence = [response({"status": "in_progress", "head_sha": "b" * 40})]
    assert (
        poll_once(WaitConfig(mode="run", repo=REPO, sha=SHA, run_id=7), transport_from(evidence, []), 0)["kind"]
        == "mismatch"
    )


@pytest.mark.parametrize("kind", ["failure", "cancelled"])
def test_optional_classification_failure_is_observed(kind):
    checks = [CheckRun(name, "completed", "success", SHA) for name in (FOUNDATION, CONTAINER)]
    checks.append(CheckRun("changes", "completed", kind, SHA))
    assert _evaluate_pr(checks, SHA, cfg())["kind"] == ("failed" if kind == "failure" else "cancelled")


@pytest.mark.parametrize("body", [b"invalid json", b"null", b"[]", b'{"check_runs": {}, "total_count": 0}'])
def test_malformed_response_fails_closed(body):
    from scripts.wait_for_ci import Response

    evidence = [response({"head": {"sha": SHA}}), Response(200, {}, body)]
    assert poll_once(cfg(), transport_from(evidence, []), 0)["kind"] == "mismatch"


def test_duplicate_names_are_ambiguous():
    rows = [{"name": FOUNDATION, "status": "completed", "conclusion": "success", "head_sha": SHA}] * 2
    evidence = [response({"head": {"sha": SHA}}), response({"total_count": 2, "check_runs": rows})]
    assert poll_once(cfg(), transport_from(evidence, []), 0)["kind"] == "mismatch"


def test_initial_delay_is_capped_by_deadline():
    from scripts.wait_for_ci import run

    clock = FakeClock()
    payload = run(
        config(initial_delay=200, max_duration=10),
        transport_from([], []),
        sleep=clock.sleep,
        monotonic=clock.monotonic,
        now_epoch=clock.epoch,
    )
    assert payload["exit_code"] == 3
    assert payload["attempts"] == 0
    assert clock.now == 10


def test_transient_backoff_is_applied_once():
    from scripts.wait_for_ci import Response, run

    clock = FakeClock()
    evidence = [Response(0, {}, b""), response({"head": {"sha": "b" * 40}})]
    payload = run(
        config(initial_delay=0),
        transport_from(evidence, []),
        sleep=clock.sleep,
        monotonic=clock.monotonic,
        now_epoch=clock.epoch,
    )
    assert payload["exit_code"] == 6
    assert payload["attempts"] == 2
    assert clock.now == 10
