#!/usr/bin/env python3
"""Start the backend and frontend dev servers together.

Usage: python3 scripts/dev.py
Configurable via env vars (all optional):
  BACKEND_PORT     (default 8000)
  FRONTEND_PORT    (default 5173)
  DATABASE_PATH    (default backend/data/app.db)
  ENCRYPTION_KEY_PATH (default backend/data/secret.key)

Run `python3 scripts/setup.py` first if this is your first time running the project.

Stops cleanly on Ctrl+C (SIGINT) or on SIGTERM (e.g. from a process manager / systemd on
the Ubuntu deployment target, ADR-0015) — both are handled explicitly rather than relying
on Python's default Ctrl+C behavior, which doesn't fire the same way for background/managed
processes.
"""

import os
import signal
import subprocess
import sys
import time

from _paths import BACKEND_DIR, FRONTEND_DIR, VENV_DIR, require_npm, venv_python

_shutdown_requested = False


def _request_shutdown(signum, frame):
    global _shutdown_requested
    _shutdown_requested = True


def main() -> None:
    if not VENV_DIR.exists():
        sys.exit("Backend virtual environment not found. Run `python3 scripts/setup.py` first.")
    npm = require_npm()

    signal.signal(signal.SIGINT, _request_shutdown)
    signal.signal(signal.SIGTERM, _request_shutdown)

    backend_port = os.environ.get("BACKEND_PORT", "8000")
    frontend_port = os.environ.get("FRONTEND_PORT", "5173")

    backend_env = os.environ.copy()
    backend_env["ALLOWED_ORIGINS"] = (
        f"http://localhost:{frontend_port},http://127.0.0.1:{frontend_port}"
    )

    frontend_env = os.environ.copy()
    frontend_env["VITE_API_BASE_URL"] = f"http://localhost:{backend_port}"

    print(f"Backend:  http://localhost:{backend_port}")
    print(f"Frontend: http://localhost:{frontend_port}")

    backend_proc = subprocess.Popen(
        [
            str(venv_python()),
            "-m",
            "uvicorn",
            "app.presentation.main:app",
            "--port",
            backend_port,
            "--reload",
        ],
        cwd=BACKEND_DIR,
        env=backend_env,
    )
    frontend_proc = subprocess.Popen(
        [npm, "run", "dev", "--", "--port", frontend_port],
        cwd=FRONTEND_DIR,
        env=frontend_env,
    )

    try:
        while not _shutdown_requested:
            time.sleep(0.5)
            if backend_proc.poll() is not None or frontend_proc.poll() is not None:
                break
    finally:
        print("\nShutting down...")
        for proc in (backend_proc, frontend_proc):
            if proc.poll() is None:
                proc.terminate()
        for proc in (backend_proc, frontend_proc):
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)


if __name__ == "__main__":
    sys.exit(main())
