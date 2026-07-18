"""Shared path/helper logic for scripts/setup.py and scripts/dev.py.

Kept dependency-free (stdlib only) so it works before the backend venv or frontend
node_modules even exist yet.
"""

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"
VENV_DIR = BACKEND_DIR / ".venv"

_CANDIDATE_PYTHONS = ["python3.12", "python3.11", "python3.10", "python3"]


def find_system_python() -> str:
    """Find a Python 3.10+ interpreter to create the backend venv with.

    Checked in preference order; falls back to whatever `python3` resolves to. Works the
    same way on macOS and Ubuntu (ADR-0015) since it only relies on PATH lookup, not any
    OS-specific package manager.
    """
    for candidate in _CANDIDATE_PYTHONS:
        found = shutil.which(candidate)
        if found:
            return found
    sys.exit(
        "No python3 interpreter found on PATH. Install Python 3.10+ "
        "(e.g. `brew install python@3.12` on macOS, `apt install python3.12` on Ubuntu)."
    )


def venv_python() -> Path:
    # Layout differs between POSIX (bin/) and Windows (Scripts/) — not a concern here since
    # only macOS/Ubuntu are targets (ADR-0015), but kept explicit rather than assumed.
    return VENV_DIR / "bin" / "python"


def require_npm() -> str:
    found = shutil.which("npm")
    if not found:
        sys.exit(
            "npm not found on PATH. Install Node.js "
            "(e.g. `brew install node` on macOS, `apt install nodejs npm` on Ubuntu)."
        )
    return found
