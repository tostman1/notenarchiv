"""Deterministic, SHA-bound CI waiter contract (mocked GitHub, no real calls)."""

from scripts.wait_for_ci import (
    EXIT_CANCELLED,
    EXIT_FAILED,
    EXIT_MISMATCH,
    EXIT_RATE_LIMITED,
    EXIT_SUCCESS,
    EXIT_TIMEOUT,
    EXIT_UNAVAILABLE,
    Response,
    WaitConfig,
    build_arg_parser,
    run,
)

REPO = "owner/repo"
SHA = "a" * 40


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def sleep(self, seconds):
        self.now += max(0.0, float(seconds))

    def monotonic(self):
        return self.now

    def epoch(self):
        return 1_000_000.0 + self.now


def config(**overrides) -> WaitConfig:
    values = dict(
        mode="pr",
        repo=REPO,
        sha=SHA,
        pr=42,
        initial_delay=5.0,
        interval=10.0,
        long_after=30.0,
        long_interval=20.0,
        max_duration=100.0,
        transient_retries=2,
    )
    values.update(overrides)
    return WaitConfig(**values)


def transport_from(scenarios, log):
    """Replay scripted responses; each item is a Response or a callable(args)->Response."""

    def fake_transport(method, url, headers, body=None):
        log.append((method, url))
        item = scenarios.pop(0)
        if callable(item):
            return item(method, url, headers)
        return item

    return fake_transport


def response(payload=None, status=200, headers=None):
    import json

    body = json.dumps(payload).encode() if payload is not None else b""
    return Response(status, headers or {}, body)


def pr_body(sha=None):
    return {"state": "open", "head": {"sha": sha or SHA, "ref": "feature/x"}}


def check_runs(pr_sha, runs):
    return {"total_count": len(runs), "check_runs": runs}


def run_check(name, status, conclusion, sha=None):
    return {"name": name, "status": status, "conclusion": conclusion, "head_sha": sha or SHA}


def test_pr_success_on_exact_bound_sha():
    clock = FakeClock()
    log = []
    scenarios = [
        response(pr_body()),
        response(
            check_runs(
                SHA,
                [
                    run_check("Foundation (ruff + pytest)", "completed", "success"),
                    run_check("Container (amd64 + security + synthetic smoke)", "completed", "success"),
                ],
            )
        ),
    ]
    payload = run(
        config(), transport_from(scenarios, log), sleep=clock.sleep, monotonic=clock.monotonic, now_epoch=clock.epoch
    )
    assert payload["result"] == "success"
    assert payload["exit_code"] == EXIT_SUCCESS
    assert payload["head_sha"] == SHA
    assert payload["checks"] and all(c["conclusion"] == "success" for c in payload["checks"])
    # One deterministic operation: two transport reads, no redundant polling.
    assert len(log) == 2
    assert log[0][1].endswith("/pulls/42")
    assert log[1][1].endswith(f"/commits/{SHA}/check-runs?per_page=100")


def test_pr_pending_then_success_uses_bounded_intervals():
    clock = FakeClock()
    log = []

    def pending(method, url, headers):
        return response(check_runs(SHA, [run_check("Foundation (ruff + pytest)", "in_progress", "")]))

    done = response(check_runs(SHA, [run_check("Foundation (ruff + pytest)", "completed", "success")]))
    # Poll 1 = [PR fetch, check-runs fetch], Poll 2 = [PR fetch, check-runs fetch].
    scenarios = [response(pr_body()), pending, response(pr_body()), done]
    payload = run(
        config(), transport_from(scenarios, log), sleep=clock.sleep, monotonic=clock.monotonic, now_epoch=clock.epoch
    )
    assert payload["result"] == "success"
    assert payload["attempts"] == 2
    # 5s initial delay + 10s normal interval between polls (under long-after 30s).
    assert clock.now == 5.0 + 10.0


def test_pr_missing_required_check_is_mismatch_not_success():
    clock = FakeClock()
    scenarios = [
        response(pr_body()),
        # Container passed but the required Foundation check is absent.
        response(
            check_runs(SHA, [run_check("Container (amd64 + security + synthetic smoke)", "completed", "success")])
        ),
    ]
    payload = run(
        config(), transport_from(scenarios, list()), sleep=clock.sleep, monotonic=clock.monotonic, now_epoch=clock.epoch
    )
    assert payload["result"] == "mismatch"
    assert payload["exit_code"] == EXIT_MISMATCH
    assert "Foundation (ruff + pytest)" in payload["message"]


def test_pr_foreign_sha_check_is_mismatch():
    clock = FakeClock()
    other = "b" * 40
    scenarios = [
        response(pr_body()),
        response(check_runs(SHA, [run_check("Foundation (ruff + pytest)", "completed", "success", sha=other)])),
    ]
    payload = run(
        config(), transport_from(scenarios, list()), sleep=clock.sleep, monotonic=clock.monotonic, now_epoch=clock.epoch
    )
    assert payload["result"] == "mismatch"
    assert payload["exit_code"] == EXIT_MISMATCH


def test_pr_head_mismatch_when_pr_moved_on():
    clock = FakeClock()
    other = "c" * 40
    scenarios = [response(pr_body(sha=other))]
    payload = run(
        config(), transport_from(scenarios, list()), sleep=clock.sleep, monotonic=clock.monotonic, now_epoch=clock.epoch
    )
    assert payload["result"] == "mismatch"
    assert payload["exit_code"] == EXIT_MISMATCH


def test_pr_failed_check_is_failed():
    clock = FakeClock()
    scenarios = [
        response(pr_body()),
        response(
            check_runs(
                SHA,
                [
                    run_check("Foundation (ruff + pytest)", "completed", "failure"),
                    run_check("Container (amd64 + security + synthetic smoke)", "completed", "success"),
                ],
            )
        ),
    ]
    payload = run(
        config(), transport_from(scenarios, list()), sleep=clock.sleep, monotonic=clock.monotonic, now_epoch=clock.epoch
    )
    assert payload["result"] == "failed"
    assert payload["exit_code"] == EXIT_FAILED
    assert payload["failed_checks"] == ["Foundation (ruff + pytest)"]


def test_pr_cancelled_is_cancelled():
    clock = FakeClock()
    scenarios = [
        response(pr_body()),
        response(check_runs(SHA, [run_check("Foundation (ruff + pytest)", "completed", "cancelled")])),
    ]
    payload = run(
        config(), transport_from(scenarios, list()), sleep=clock.sleep, monotonic=clock.monotonic, now_epoch=clock.epoch
    )
    assert payload["result"] == "cancelled"
    assert payload["exit_code"] == EXIT_CANCELLED


def test_timeout_is_not_success():
    clock = FakeClock()

    def pending(method, url, headers):
        return response(check_runs(SHA, [run_check("Foundation (ruff + pytest)", "in_progress", "")]))

    # Each poll = one PR fetch (pr_body) plus one check-runs fetch (pending).
    scenarios = []
    for _ in range(6):
        scenarios.append(response(pr_body()))
        scenarios.append(pending)

    payload = run(
        config(max_duration=20.0),
        transport_from(scenarios, list()),
        sleep=clock.sleep,
        monotonic=clock.monotonic,
        now_epoch=clock.epoch,
    )
    assert payload["result"] == "timeout"
    assert payload["exit_code"] == EXIT_TIMEOUT


def test_rate_limit_honors_retry_after_within_budget():
    clock = FakeClock()
    log = []
    rl = Response(429, {"Retry-After": "7", "X-RateLimit-Remaining": "0"}, b"")
    scenarios = [
        response(pr_body()),
        rl,
        response(pr_body()),
        response(check_runs(SHA, [run_check("Foundation (ruff + pytest)", "completed", "success")])),
    ]
    payload = run(
        config(), transport_from(scenarios, log), sleep=clock.sleep, monotonic=clock.monotonic, now_epoch=clock.epoch
    )
    assert payload["result"] == "success"
    assert payload["rate_waits"] == 1
    # 5s initial delay, 7s rate-limit wait, then success on the next poll.
    assert clock.now == 5.0 + 7.0


def test_rate_limit_beyond_budget_is_rate_limited():
    clock = FakeClock()
    rl = Response(429, {"Retry-After": "900", "X-RateLimit-Remaining": "0"}, b"")
    scenarios = [response(pr_body()), rl]
    payload = run(
        config(max_duration=30.0),
        transport_from(scenarios, list()),
        sleep=clock.sleep,
        monotonic=clock.monotonic,
        now_epoch=clock.epoch,
    )
    assert payload["result"] == "rate_limited"
    assert payload["exit_code"] == EXIT_RATE_LIMITED


def test_unavailable_after_bounded_transient_retries():
    clock = FakeClock()
    net_down = Response(0, {}, b"")
    # 1 initial attempt + 2 bounded retries, then unavailable.
    scenarios = [net_down, net_down, net_down]
    payload = run(
        config(initial_delay=0.0, transient_retries=2),
        transport_from(scenarios, list()),
        sleep=clock.sleep,
        monotonic=clock.monotonic,
        now_epoch=clock.epoch,
    )
    assert payload["result"] == "unavailable"
    assert payload["exit_code"] == EXIT_UNAVAILABLE


def test_run_mode_success_bound_to_sha():
    clock = FakeClock()
    run_body = {
        "status": "completed",
        "conclusion": "success",
        "head_sha": SHA,
        "name": "CI",
        "html_url": f"https://github.com/{REPO}/actions/runs/777",
    }
    scenarios = [response(run_body)]
    payload = run(
        config(mode="run", run_id=777, pr=None),
        transport_from(scenarios, list()),
        sleep=clock.sleep,
        monotonic=clock.monotonic,
        now_epoch=clock.epoch,
    )
    assert payload["result"] == "success"
    assert payload["exit_code"] == EXIT_SUCCESS
    assert payload["run_url"].endswith("/actions/runs/777")


def test_run_mode_not_discoverable_yet_is_pending_then_success():
    clock = FakeClock()
    run_body = {"status": "completed", "conclusion": "success", "head_sha": SHA, "name": "CI", "html_url": "u"}
    scenarios = [Response(404, {}, b"{}"), lambda m, u, h: response(run_body)]
    payload = run(
        config(mode="run", run_id=778, pr=None, initial_delay=0.0),
        transport_from(scenarios, list()),
        sleep=clock.sleep,
        monotonic=clock.monotonic,
        now_epoch=clock.epoch,
    )
    assert payload["result"] == "success"
    assert payload["attempts"] == 2


def test_run_mode_sha_mismatch():
    clock = FakeClock()
    run_body = {"status": "completed", "conclusion": "success", "head_sha": "d" * 40, "name": "CI", "html_url": "u"}
    scenarios = [response(run_body)]
    payload = run(
        config(mode="run", run_id=779, pr=None),
        transport_from(scenarios, list()),
        sleep=clock.sleep,
        monotonic=clock.monotonic,
        now_epoch=clock.epoch,
    )
    assert payload["result"] == "mismatch"
    assert payload["exit_code"] == EXIT_MISMATCH


def test_cli_argument_parsing_defaults():
    args = build_arg_parser().parse_args(["--mode", "pr", "--pr", "42", "--sha", SHA])
    assert args.mode == "pr"
    assert args.initial_delay == 90.0
    assert args.interval == 60.0
    assert args.long_interval == 120.0
    assert args.max_duration == 1800.0
    assert args.transient_retries == 3
