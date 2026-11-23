"""Apply resource limits before target imports; wait for Windows Job assignment."""

import json
import os
import subprocess
import sys

if __name__ == "__main__":
    request = json.loads(sys.stdin.buffer.readline(65537))
    arguments, limits = request["arguments"], request["limits"]
    if sys.platform == "linux":
        import ctypes
        import signal

        # A worker crash must not leave an untrusted PDF child running. Install
        # before target imports/exec and close the parent-death race explicitly.
        libc = ctypes.CDLL(None, use_errno=True)
        if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0:
            raise OSError(ctypes.get_errno(), "Cannot bind child lifetime to its owner")
        if os.getppid() != request["parent_pid"]:
            os._exit(1)
    if os.name != "nt":
        import resource

        for name, kind in (
            ("memory_bytes", resource.RLIMIT_AS),
            ("cpu_seconds", resource.RLIMIT_CPU),
            ("file_bytes", resource.RLIMIT_FSIZE),
        ):
            if limits[name] is not None:
                resource.setrlimit(kind, (limits[name], limits[name]))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
        os.execv(arguments[0], arguments)
    sys.exit(subprocess.call(arguments, stdin=subprocess.DEVNULL))
