#!/usr/bin/env python3
"""One-time (idempotent) setup: backend venv + deps + migrations, frontend deps.

Usage: python3 scripts/setup.py
Safe to re-run — skips steps that are already done.
"""

import subprocess
import sys

from _paths import BACKEND_DIR, FRONTEND_DIR, VENV_DIR, find_system_python, require_npm, venv_python


def run(cmd: list[str], cwd=None, env=None) -> None:
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


def main() -> None:
    if not VENV_DIR.exists():
        print("Creating backend virtual environment...")
        run([find_system_python(), "-m", "venv", str(VENV_DIR)])
    else:
        print("Backend virtual environment already exists, skipping creation.")

    run([str(venv_python()), "-m", "pip", "install", "--quiet", "--upgrade", "pip"])
    run(
        [str(venv_python()), "-m", "pip", "install", "--quiet", "-r", "requirements.txt"],
        cwd=BACKEND_DIR,
    )

    print("Running database migrations...")
    run([str(venv_python()), "-m", "alembic", "upgrade", "head"], cwd=BACKEND_DIR)

    npm = require_npm()
    print("Installing frontend dependencies...")
    run([npm, "install"], cwd=FRONTEND_DIR)

    print("\nSetup complete. Run `python3 scripts/dev.py` to start the app.")


if __name__ == "__main__":
    sys.exit(main())
