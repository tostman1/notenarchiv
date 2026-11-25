"""Deterministic, read-only GitHub CI waiting helper.

Waiting is not reasoning. This script blocks until a GitHub Actions run, or a
pull request's checks, reach a terminal state, bound to an exact commit SHA. It
performs exactly one blocking wait per CI phase and then reports a single
machine-readable result. It never merges, modifies, reruns, cancels or
otherwise changes any GitHub resource.

Run through uv so the interpreter is pinned and no system Python is required::

    uv run python scripts/wait_for_ci.py --mode pr  --pr 42 --sha <HEAD_SHA>
    uv run python scripts/wait_for_ci.py --mode run --run-id 123 --sha <HEAD_SHA>

A single JSON line is written to stdout and (by default) to a result file under
the git-ignored ``.dev/ci-wait/`` directory so a backgrounded invocation can be
re-read after the process exits.

Exit codes:
    0 success      1 failed         2 cancelled
    3 timeout      4 rate_limited   5 unavailable
    6 mismatch     64 usage error
"""

# ruff: noqa: T201
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

try:
    from scripts.ci_changes import docs_only
except ModuleNotFoundError:  # Direct script invocation puts scripts/ on sys.path.
    from ci_changes import docs_only

API_BASE = "https://api.github.com"

EXIT_SUCCESS = 0
EXIT_FAILED = 1
EXIT_CANCELLED = 2
EXIT_TIMEOUT = 3
EXIT_RATE_LIMITED = 4
EXIT_UNAVAILABLE = 5
EXIT_MISMATCH = 6
EXIT_USAGE = 64

HARD_FAIL = {"failure", "timed_out", "startup_failure", "action_required"}
CANCELLED = {"cancelled", "canceled"}
PENDING_STATUS = {"queued", "in_progress", "waiting", "pending", "requested"}
FOUNDATION = "Foundation (ruff + pytest)"
CONTAINER = "Container (amd64 + security + synthetic smoke)"
DEFAULT_REQUIRED = (FOUNDATION, CONTAINER)
RESULT_DIRNAME = ".dev/ci-wait"

_MESSAGES = {
    "success": "verified CI success on the exact bound commit",
    "failed": "CI reported a failed check",
    "cancelled": "CI run/check was cancelled",
    "mismatch": "insufficient verification: SHA mismatch or missing required check",
    "timeout": "max duration reached; CI did not reach a terminal state (not a success)",
    "rate_limited": "GitHub rate limit prevented completion within the wait budget (not a success)",
    "unavailable": "GitHub API/network unavailable after bounded retries (not a success)",
}


@dataclass
class Response:
    """A decoded GitHub REST response. ``status == 0`` is the network-failure sentinel."""

    status: int
    headers: dict = field(default_factory=dict)
    body: bytes = b""

    def json(self):
        return json.loads(self.body.decode("utf-8") or "null")


@dataclass
class CheckRun:
    name: str
    status: str
    conclusion: str
    head_sha: str


@dataclass
class WaitConfig:
    mode: str
    repo: str
    sha: str
    run_id: int | None = None
    pr: int | None = None
    initial_delay: float = 90.0
    interval: float = 60.0
    long_interval: float = 120.0
    long_after: float = 600.0
    max_duration: float = 1800.0
    transient_retries: int = 3
    required_checks: tuple = DEFAULT_REQUIRED
    result_file: str | None = None
    api_base: str = API_BASE
    token: str = ""
    classification_cache: dict = field(default_factory=dict)


def _norm_header(header: dict) -> dict:
    return {k.lower(): v for k, v in header.items()}


def _rate_wait(resp: Response, now_epoch: float) -> float | None:
    """Return deterministic seconds to wait if this response is a GitHub rate limit, else None."""
    if resp.status not in (403, 429):
        return None
    h = _norm_header(resp.headers)
    retry_after = h.get("retry-after")
    remaining = h.get("x-ratelimit-remaining")
    # A 403 that is not rate-limit related (e.g. bad token) must not be waited out.
    if resp.status == 403 and not retry_after and (remaining or "1") != "0":
        return None
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            try:
                dt = parsedate_to_datetime(retry_after)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=datetime.UTC)
                return max(0.0, (dt - datetime.now(datetime.UTC)).total_seconds())
            except Exception:
                return 30.0
    reset = h.get("x-ratelimit-reset")
    if reset:
        try:
            return max(0.0, float(reset) - now_epoch)
        except ValueError:
            return 30.0
    return 30.0


def _conclusion_kind(conclusion: str) -> str:
    if conclusion == "success":
        return "success"
    if conclusion in CANCELLED:
        return "cancelled"
    return "failed"


def _checks_list(checks) -> list:
    return [{"name": c.name, "status": c.status, "conclusion": c.conclusion} for c in checks]


def _valid_sha(value) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{40}", value) is not None


def _verified_docs_only(pr, cfg: WaitConfig) -> bool:
    """Use the workflow's exact direct diff, never caller-asserted classification."""
    base = (pr.get("base") or {}).get("sha")
    head = (pr.get("head") or {}).get("sha")
    if not _valid_sha(base) or head != cfg.sha:
        return False
    key = (base, head)
    if key not in cfg.classification_cache:
        verified = False
        try:
            for sha in key:
                resolved = subprocess.check_output(
                    ["git", "rev-parse", "--verify", f"{sha}^{{commit}}"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=10,
                ).strip()
                if resolved != sha:
                    raise ValueError("unresolved classification commit")
            # -z preserves filenames containing newlines; disable external diff drivers.
            paths = (
                subprocess.check_output(
                    ["git", "diff", "--no-ext-diff", "--name-only", "-z", base, head],
                    stderr=subprocess.DEVNULL,
                    timeout=10,
                )
                .decode("utf-8")
                .split("\0")
            )
            verified = paths[-1] == "" and docs_only(paths[:-1])
        except (OSError, subprocess.SubprocessError, ValueError):
            pass  # Unknown evidence requires full scope.
        cfg.classification_cache[key] = verified
    return cfg.classification_cache[key]


def _evaluate_pr(checks, bound_sha: str, cfg: WaitConfig, *, docs_exception=False) -> dict:
    if not _valid_sha(bound_sha) or bound_sha != cfg.sha:
        return {"kind": "mismatch", "message": "invalid or mismatched bound SHA"}
    if not checks:
        return {"kind": "pending", "head_sha": bound_sha, "note": "no check runs yet"}
    for c in checks:
        if not _valid_sha(c.head_sha) or c.head_sha != bound_sha:
            return {
                "kind": "mismatch",
                "head_sha": bound_sha,
                "checks": _checks_list(checks),
                "message": f"check '{c.name}' has invalid or mismatched SHA evidence",
            }
        if c.status not in PENDING_STATUS | {"completed"}:
            return {"kind": "mismatch", "message": f"check '{c.name}' has invalid status"}
    if any(c.status in PENDING_STATUS for c in checks):
        return {"kind": "pending", "head_sha": bound_sha, "checks": _checks_list(checks)}
    if any(c.conclusion in CANCELLED for c in checks):
        return {"kind": "cancelled", "head_sha": bound_sha, "checks": _checks_list(checks)}
    hard_fail = [c.name for c in checks if c.conclusion in HARD_FAIL]
    if hard_fail:
        return {
            "kind": "failed",
            "head_sha": bound_sha,
            "checks": _checks_list(checks),
            "failed_checks": hard_fail,
        }
    by_name = {c.name: c for c in checks}
    required = tuple(dict.fromkeys((*DEFAULT_REQUIRED, *cfg.required_checks)))
    if docs_exception:
        classification = by_name.get("changes")
        if not classification or classification.status != "completed" or classification.conclusion != "success":
            return {"kind": "mismatch", "message": "docs-only exception lacks successful classification job"}
        required = tuple(n for n in required if n != CONTAINER)
        container = by_name.get(CONTAINER)
        if container and container.conclusion not in ("success", "skipped"):
            return {"kind": "mismatch", "head_sha": bound_sha, "checks": _checks_list(checks)}
    missing = [n for n in required if n not in by_name]
    if missing:
        return {
            "kind": "mismatch",
            "head_sha": bound_sha,
            "checks": _checks_list(checks),
            "message": f"missing required checks: {', '.join(missing)}",
        }
    not_ok = [n for n in required if by_name[n].conclusion != "success" or by_name[n].status != "completed"]
    if not_ok:
        return {
            "kind": "mismatch",
            "head_sha": bound_sha,
            "checks": _checks_list(checks),
            "failed_checks": not_ok,
        }
    return {"kind": "success", "head_sha": bound_sha, "checks": _checks_list(checks)}


def poll_once(cfg: WaitConfig, transport, now_epoch: float) -> dict:
    """Malformed evidence never escapes as a false green or unhandled exception."""
    if not _valid_sha(cfg.sha):
        return {"kind": "mismatch", "message": "invalid expected SHA"}
    try:
        return _poll_once(cfg, transport, now_epoch)
    except (ValueError, TypeError, AttributeError, KeyError):
        return {"kind": "mismatch", "message": "malformed GitHub evidence"}


def _fetch_checks(cfg, transport, headers, now_epoch, url, key):
    resp = transport("GET", url, headers)
    rw = _rate_wait(resp, now_epoch)
    if rw is not None:
        return None, {"kind": "rate_limited", "wait_seconds": rw}
    if resp.status == 404:
        return None, {"kind": "pending", "note": "checks not discoverable yet"}
    if resp.status != 200:
        return None, {"kind": "error", "status": resp.status}
    data = resp.json()
    rows = data[key]
    count = data["total_count"]
    # Reject incomplete pages rather than silently dropping jobs/checks.
    if not isinstance(rows, list) or type(count) is not int or count != len(rows) or count > 100:
        return None, {"kind": "mismatch", "message": "incomplete check/job evidence"}
    checks = []
    for row in rows:
        name, status, conclusion = row["name"], row["status"], row["conclusion"]
        if not isinstance(name, str) or not name or not isinstance(status, str):
            return None, {"kind": "mismatch", "message": "malformed check/job identity"}
        if conclusion is not None and not isinstance(conclusion, str):
            return None, {"kind": "mismatch", "message": "malformed conclusion"}
        checks.append(CheckRun(name, status, (conclusion or "").lower(), row.get("head_sha")))
    if len({c.name for c in checks}) != len(checks):
        return None, {"kind": "mismatch", "message": "ambiguous duplicate check/job names"}
    return checks, None


def _poll_once(cfg: WaitConfig, transport, now_epoch: float) -> dict:
    """Perform a single read-only poll and return a normalized outcome."""
    base = cfg.api_base.rstrip("/")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "notenarchiv-ci-wait/1.0"}
    if cfg.token:
        headers["Authorization"] = f"Bearer {cfg.token}"

    if cfg.mode == "run":
        resp = transport("GET", f"{base}/repos/{cfg.repo}/actions/runs/{cfg.run_id}", headers)
        if resp.status == 0:
            return {"kind": "error"}
        rw = _rate_wait(resp, now_epoch)
        if rw is not None:
            return {"kind": "rate_limited", "wait_seconds": rw}
        if resp.status == 404:
            return {"kind": "pending", "note": "run not discoverable yet"}
        if resp.status != 200:
            return {"kind": "error", "status": resp.status}
        data = resp.json()
        head_sha = data.get("head_sha") or ""
        run_url = data.get("html_url") or ""
        if not _valid_sha(head_sha) or head_sha != cfg.sha:
            return {
                "kind": "mismatch",
                "head_sha": head_sha,
                "run_url": run_url,
                "message": "invalid or mismatched run SHA",
            }
        if data.get("status") != "completed":
            return {"kind": "pending", "head_sha": head_sha, "run_url": run_url}
        conclusion = (data.get("conclusion") or "").lower()
        checks, error = _fetch_checks(
            cfg,
            transport,
            headers,
            now_epoch,
            f"{base}/repos/{cfg.repo}/actions/runs/{cfg.run_id}/jobs?per_page=100",
            "jobs",
        )
        if error:
            return {**error, "head_sha": head_sha, "run_url": run_url}
        outcome = _evaluate_pr(checks, head_sha, cfg)
        if not checks:
            outcome = {"kind": "mismatch", "message": "completed run has no required jobs"}
        if conclusion in HARD_FAIL or conclusion in CANCELLED:
            outcome["kind"] = _conclusion_kind(conclusion)
        elif conclusion != "success" and outcome["kind"] == "success":
            outcome["kind"] = "mismatch"
        return {**outcome, "head_sha": head_sha, "run_url": run_url}

    # mode == "pr"
    resp = transport("GET", f"{base}/repos/{cfg.repo}/pulls/{cfg.pr}", headers)
    if resp.status == 0:
        return {"kind": "error"}
    rw = _rate_wait(resp, now_epoch)
    if rw is not None:
        return {"kind": "rate_limited", "wait_seconds": rw}
    if resp.status != 200:
        return {"kind": "error", "status": resp.status}
    pr = resp.json()
    head_sha = (pr.get("head") or {}).get("sha") or ""
    if not _valid_sha(head_sha) or head_sha != cfg.sha:
        return {
            "kind": "mismatch",
            "head_sha": head_sha,
            "message": "invalid or mismatched PR SHA",
        }
    bound_sha = head_sha
    checks, error = _fetch_checks(
        cfg,
        transport,
        headers,
        now_epoch,
        f"{base}/repos/{cfg.repo}/commits/{bound_sha}/check-runs?per_page=100",
        "check_runs",
    )
    if error:
        return {**error, "head_sha": head_sha}
    return _evaluate_pr(checks, bound_sha, cfg, docs_exception=_verified_docs_only(pr, cfg))


def _interval(elapsed: float, cfg: WaitConfig) -> float:
    return cfg.long_interval if elapsed >= cfg.long_after else cfg.interval


def _exit_for(kind: str) -> int:
    return {
        "success": EXIT_SUCCESS,
        "failed": EXIT_FAILED,
        "cancelled": EXIT_CANCELLED,
        "mismatch": EXIT_MISMATCH,
        "timeout": EXIT_TIMEOUT,
        "rate_limited": EXIT_RATE_LIMITED,
        "unavailable": EXIT_UNAVAILABLE,
    }[kind]


def _terminal(kind, cfg, outcome, attempts, rate_waits) -> dict:
    outcome = outcome or {}
    payload = {
        "result": kind,
        "exit_code": _exit_for(kind),
        "mode": cfg.mode,
        "repo": cfg.repo,
        "sha": cfg.sha,
        "run_id": cfg.run_id,
        "pr": cfg.pr,
        "head_sha": outcome.get("head_sha"),
        "run_url": outcome.get("run_url"),
        "attempts": attempts,
        "rate_waits": rate_waits,
        "checks": outcome.get("checks") or [],
        "failed_checks": outcome.get("failed_checks", []),
        "message": outcome.get("message") or _MESSAGES[kind],
    }
    if cfg.result_file:
        payload["result_file"] = cfg.result_file
    return payload


def run(cfg: WaitConfig, transport, *, sleep, monotonic, now_epoch) -> dict:
    """Block until a terminal CI state, returning the final machine-readable payload."""
    t0 = monotonic()
    deadline = t0 + cfg.max_duration
    next_poll = t0 + cfg.initial_delay
    transient = 0
    rate_waits = 0
    attempts = 0
    last: dict = {}
    while True:
        now = monotonic()
        if now >= deadline:
            return _terminal("timeout", cfg, last, attempts, rate_waits)
        if now < next_poll:
            sleep(min(next_poll, deadline) - now)
            continue
        attempts += 1
        outcome = poll_once(cfg, transport, now_epoch())
        kind = outcome["kind"]
        if kind == "rate_limited":
            wait = outcome.get("wait_seconds", cfg.interval)
            if monotonic() + wait > deadline:
                return _terminal("rate_limited", cfg, outcome, attempts, rate_waits + 1)
            rate_waits += 1
            last = outcome
            sleep(wait)
            next_poll = monotonic()  # retry exactly at the permitted time
            continue
        if kind == "error":
            transient += 1
            if transient > cfg.transient_retries:
                return _terminal("unavailable", cfg, outcome, attempts, rate_waits)
            backoff = cfg.interval * (2 ** (transient - 1))
            next_poll = min(deadline, monotonic() + backoff)
            continue
        last = outcome
        if kind == "pending":
            next_poll = monotonic() + _interval(now - t0, cfg)
            continue
        return _terminal(kind, cfg, outcome, attempts, rate_waits)


def default_transport(method, url, headers, body=None) -> Response:
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return Response(resp.status, dict(resp.headers), resp.read())
    except urllib.error.HTTPError as exc:
        return Response(exc.code, dict(exc.headers or {}), exc.read())
    except urllib.error.URLError:
        return Response(0, {}, b"")


def _repo_from_url(url: str) -> str | None:
    """Extract owner/name from a git remote URL (https, ssh, scp-like, .git suffix)."""
    # Match the final owner/repo path segment without matching the URL scheme colon.
    match = re.search(r"[:/]([^/]+?)/([^/]+?)(?:\.git)?/?$", url)
    return f"{match.group(1)}/{match.group(2)}" if match else None


def _repo_from_git() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "remote", "get-url", "origin"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, OSError):
        return None
    return _repo_from_url(out)


def _resolve_token() -> str:
    for var in ("GH_TOKEN", "GITHUB_TOKEN"):
        if os.environ.get(var):
            return os.environ[var]
    try:
        out = subprocess.check_output(["gh", "auth", "token"], text=True, stderr=subprocess.DEVNULL).strip()
        if out:
            return out
    except (subprocess.CalledProcessError, OSError):
        pass
    return ""


def _deliver(payload: dict) -> None:
    if payload.get("result_file"):
        path = Path(payload["result_file"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, separators=(",", ":")))


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Deterministic, read-only GitHub CI waiter bound to an exact commit SHA.",
    )
    p.add_argument("--mode", choices=["run", "pr"], required=True)
    p.add_argument("--repo", help="owner/name; defaults to the origin git remote")
    p.add_argument("--sha", required=True, help="exact commit SHA the wait is bound to")
    p.add_argument("--run-id", type=int, help="Actions run id (mode=run)")
    p.add_argument("--pr", type=int, help="pull request number (mode=pr)")
    p.add_argument("--initial-delay", type=float, default=90.0)
    p.add_argument("--interval", type=float, default=60.0)
    p.add_argument("--long-interval", type=float, default=120.0)
    p.add_argument("--long-after", type=float, default=600.0)
    p.add_argument("--max-duration", type=float, default=1800.0)
    p.add_argument("--transient-retries", type=int, default=3)
    p.add_argument("--required", action="append", default=None, help="required check name (repeatable)")
    p.add_argument("--result-file", default=None, help="path for the JSON result (default under .dev/ci-wait/)")
    p.add_argument("--no-result-file", action="store_true")
    p.add_argument("--api-base", default=API_BASE)
    return p


def main(argv=None) -> int:
    args = build_arg_parser().parse_args(argv)
    if not _valid_sha(args.sha):
        print("error: --sha must be a full 40-hex commit SHA", file=sys.stderr)
        return EXIT_USAGE
    repo = args.repo or _repo_from_git()
    if not repo:
        print("error: no --repo given and no origin remote found", file=sys.stderr)
        return EXIT_USAGE
    if args.mode == "run" and args.run_id is None:
        print("error: --run-id is required for mode=run", file=sys.stderr)
        return EXIT_USAGE
    if args.mode == "pr" and args.pr is None:
        print("error: --pr is required for mode=pr", file=sys.stderr)
        return EXIT_USAGE

    result_file = None
    if not args.no_result_file:
        suffix = args.run_id if args.mode == "run" else args.pr
        result_file = args.result_file or str(Path(RESULT_DIRNAME) / f"{args.mode}-{suffix}.json")

    cfg = WaitConfig(
        mode=args.mode,
        repo=repo,
        sha=args.sha,
        run_id=args.run_id,
        pr=args.pr,
        initial_delay=args.initial_delay,
        interval=args.interval,
        long_interval=args.long_interval,
        long_after=args.long_after,
        max_duration=args.max_duration,
        transient_retries=args.transient_retries,
        required_checks=tuple(args.required) if args.required else DEFAULT_REQUIRED,
        result_file=result_file,
        api_base=args.api_base,
        token=_resolve_token(),
    )
    payload = run(cfg, default_transport, sleep=time.sleep, monotonic=time.monotonic, now_epoch=time.time)
    _deliver(payload)
    return payload["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
