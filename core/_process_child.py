"""Windows launcher: do not spawn the target before assignment to its job object."""

import json
import subprocess
import sys

if __name__ == "__main__":
    arguments = json.loads(sys.stdin.buffer.readline(65537))
    sys.exit(subprocess.call(arguments, stdin=subprocess.DEVNULL))
