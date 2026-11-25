"""Container startup guards shared by the entrypoint and Gunicorn master."""

import subprocess
import sys
from pathlib import Path


def ensure_database_ready(env):
    if not env.database_path.is_file():
        raise RuntimeError("Initialize the database with the migration service first")
    try:
        subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parents[1] / "manage.py"), "migrate", "--check", "--noinput"],
            check=True,
            timeout=30,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.SubprocessError, OSError):
        raise RuntimeError("Database validation failed; run the migration service before web startup") from None
