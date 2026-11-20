"""Bounded, private-output process execution with owned process-tree cleanup."""

import json
import math
import os
import shutil
import signal
import subprocess
import sys
import time
from contextlib import suppress
from pathlib import Path


class ProcessTimeout(RuntimeError):
    pass


class ProcessFailed(RuntimeError):
    pass


class ProcessCleanupError(RuntimeError):
    """The caller must not mark a running job CANCELLED if stop is unproven."""


def _live_group(group):
    for entry in Path("/proc").iterdir():
        if entry.name.isdigit():
            try:
                fields = (entry / "stat").read_text().rsplit(") ", 1)[1].split()
                if int(fields[2]) == group and fields[0] != "Z":
                    return True
            except (FileNotFoundError, ProcessLookupError, PermissionError):
                continue
    return False


def _stop_posix(process):
    with suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGTERM)
    with suppress(subprocess.TimeoutExpired):
        process.wait(timeout=1)
    with suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGKILL)
    process.wait(timeout=5)
    deadline = time.monotonic() + 5
    while _live_group(process.pid):
        if time.monotonic() >= deadline:
            raise OSError("Process tree did not stop")
        time.sleep(0.01)


def run_process(arguments, *, timeout, checkpoint=lambda: None):
    """No shell, no inherited stdin, no logged/captured free-text output.

    Processes may stage results; only the worker's fenced publication callback
    may publish them. Windows starts a waiting launcher before job assignment.
    """
    if not isinstance(arguments, (list, tuple)) or not arguments or not all(isinstance(arg, str) for arg in arguments):
        raise ValueError("Expected explicit process arguments")
    if not math.isfinite(timeout) or not 0 < timeout <= 3600:
        raise ValueError("Process timeout must be bounded")
    arguments = list(arguments)
    arguments[0] = shutil.which(arguments[0]) or str(Path(arguments[0]).resolve(strict=True))
    if len(json.dumps(arguments).encode("utf-8")) > 32768:
        raise ValueError("Process arguments exceed their limit")
    checkpoint()
    job = None
    if os.name == "nt":
        from core.windows_job import WindowsJob

        job = WindowsJob()
        command = [sys.executable, str(Path(__file__).with_name("_process_child.py"))]
    else:
        command = arguments
    process = None
    assigned = False
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE if job else subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=job is None,
        )
        if job:
            job.assign(process)
            assigned = True
            process.stdin.write(json.dumps(arguments).encode("utf-8") + b"\n")
            process.stdin.close()
        deadline = time.monotonic() + timeout
        while process.poll() is None:
            checkpoint()
            if time.monotonic() >= deadline:
                raise ProcessTimeout("Process exceeded its deadline")
            time.sleep(0.05)
        checkpoint()
        if process.returncode:
            raise ProcessFailed("Process did not complete successfully")
    finally:
        try:
            if job:
                if process and process.stdin and not process.stdin.closed:
                    process.stdin.close()
                if process and not assigned and process.poll() is None:
                    process.kill()
                job.stop()
                if process:
                    process.wait(timeout=5)
            elif process:
                _stop_posix(process)
        except (OSError, subprocess.TimeoutExpired):
            raise ProcessCleanupError("Process-tree termination could not be verified") from None
