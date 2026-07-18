"""Shared helpers for scripts/vm_sync.py, vm_tunnel.py, vm_test.py, vm_dev.py.

These talk to the Ubuntu verification VM (the actual deployment target, ADR-0015) over SSH and
rsync. Kept dependency-free (stdlib only), matching _paths.py.

Configurable via env vars:
  VM_HOST         (default "naveen@turnny-vm")
  VM_REMOTE_DIR   (default "~/expense_tracker")
  BACKEND_PORT    (default 8000, must match scripts/dev.py's default)
  FRONTEND_PORT   (default 5173, must match scripts/dev.py's default)
"""

import os
import socket
import subprocess
import urllib.error
import urllib.request

from _paths import REPO_ROOT

VM_HOST = os.environ.get("VM_HOST", "naveen@turnny-vm")
VM_REMOTE_DIR = os.environ.get("VM_REMOTE_DIR", "~/expense_tracker")
BACKEND_PORT = os.environ.get("BACKEND_PORT", "8000")
FRONTEND_PORT = os.environ.get("FRONTEND_PORT", "5173")


def run(cmd: list[str], check: bool = False, **kwargs) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, **kwargs)


def ssh_run(remote_command: str, check: bool = False, **kwargs) -> subprocess.CompletedProcess:
    return run(["ssh", VM_HOST, remote_command], check=check, **kwargs)


def gitignore_rsync_excludes() -> list[str]:
    """Build rsync --exclude args from .gitignore.

    One source of truth for what's local-only (venvs, node_modules, the encryption key and
    local database) instead of a second hand-maintained exclude list that can silently drift
    from .gitignore, as nearly happened during the first manual VM sync.
    """
    excludes = ["--exclude=.git/"]
    gitignore = REPO_ROOT / ".gitignore"
    for line in gitignore.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            excludes.append(f"--exclude={line}")
    return excludes


def is_local_port_listening(port: str) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", int(port))) == 0


def check_backend_health() -> bool:
    url = f"http://localhost:{BACKEND_PORT}/health"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            body = resp.read().decode()
            print(f"Backend health check ({url}): {resp.status} {body}")
            return resp.status == 200
    except (urllib.error.URLError, OSError) as exc:
        print(f"Backend health check ({url}) failed: {exc}")
        return False
