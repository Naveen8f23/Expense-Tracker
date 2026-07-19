#!/usr/bin/env python3
"""Deploy the current code to the Ubuntu VM's persistent production service (ADR-0020).

Usage: python3 scripts/deploy_vm.py

Syncs the source tree, installs backend deps, runs pending Alembic migrations, rebuilds the
frontend's production bundle, and restarts the systemd --user service -- everything needed to
push a code change live, in one command. Unlike scripts/vm_dev.py (ephemeral dev-mode servers
for interactive testing), this targets the always-on service set up per deploy/README.md and
never needs sudo: `systemctl --user` and `loginctl enable-linger` (a one-time, separate manual
step -- see deploy/README.md) are enough for a non-root user to manage it.

Run scripts/vm_test.py first and don't deploy on a red build -- this script does not run tests
itself, matching vm_dev.py's separation of concerns (testing vs. running).
"""

import sys
import time

import vm_sync
from _vm import VM_REMOTE_DIR, check_backend_health, ssh_run


def main() -> None:
    vm_sync.main()

    ssh_run(
        f"cd {VM_REMOTE_DIR}/backend && .venv/bin/python -m pip install --quiet -r requirements.txt",
        check=True,
    )
    ssh_run(f"cd {VM_REMOTE_DIR}/backend && .venv/bin/alembic upgrade head", check=True)
    ssh_run(f"cd {VM_REMOTE_DIR}/frontend && npm install --silent", check=True)
    ssh_run(f"cd {VM_REMOTE_DIR}/frontend && npm run build", check=True)

    ssh_run("systemctl --user restart expense-tracker", check=True)
    print("Restarted expense-tracker.service; waiting for it to come back up...")
    time.sleep(2)
    if not check_backend_health():
        sys.exit(
            "Service did not come back up as expected -- check "
            "`ssh $VM_HOST journalctl --user -u expense-tracker -n 50`."
        )
    print("Deployed and healthy.")


if __name__ == "__main__":
    sys.exit(main())
