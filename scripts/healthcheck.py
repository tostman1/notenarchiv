"""Public container liveness check; no settings import, DB or diagnostics writer."""

import json
import urllib.request


def main():
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open("http://127.0.0.1:8000/healthz", timeout=3) as response:
            return 0 if response.status == 200 and json.load(response) == {"status": "ok"} else 1
    except Exception:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
