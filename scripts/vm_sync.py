#!/usr/bin/env python3
"""Sync the local project tree to the Ubuntu verification VM.

Usage: python3 scripts/vm_sync.py
Configurable via env vars: VM_HOST, VM_REMOTE_DIR (see _vm.py).

Always uses the absolute repo root as the rsync source, regardless of the caller's current
directory -- an earlier manual sync accidentally ran from inside backend/ instead of the repo
root (because the shell's cwd had changed from an unrelated prior command) and dumped backend/'s
own contents into the VM's project root. Anchoring on REPO_ROOT makes that class of mistake
impossible here.

Excludes are derived from .gitignore (see gitignore_rsync_excludes in _vm.py), so the venvs,
node_modules, and the local encryption key/database never get copied without a second
hand-maintained list to keep in sync.
"""

import sys

from _vm import REPO_ROOT, VM_HOST, VM_REMOTE_DIR, gitignore_rsync_excludes, run


def main() -> None:
    run(
        [
            "rsync",
            "-az",
            "--checksum",
            *gitignore_rsync_excludes(),
            f"{REPO_ROOT}/",
            f"{VM_HOST}:{VM_REMOTE_DIR}/",
        ],
        check=True,
    )
    print(f"Synced {REPO_ROOT} -> {VM_HOST}:{VM_REMOTE_DIR}")


if __name__ == "__main__":
    sys.exit(main())
