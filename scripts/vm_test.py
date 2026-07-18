#!/usr/bin/env python3
"""Run the backend automated test suite on the Ubuntu verification VM.

Usage: python3 scripts/vm_test.py

Syncs the current source tree to the VM, installs any requirements.txt changes into its venv
(quick and idempotent if nothing changed), then runs pytest there. Per docs/DECISIONS.md
ADR-0017, the Ubuntu VM is the authoritative verification environment -- passing on macOS is
necessary but not sufficient, since real divergence (ADR-0016, a Python 3.14/SQLAlchemy
incompatibility that only exists on the VM's stock Python) has already been found there once.

Assumes `python3 scripts/setup.py` has already been run at least once *on the VM* (via
`ssh $VM_HOST` or scripts/vm_dev.py) so its backend venv exists -- this script doesn't create it.
"""

import sys

import vm_sync
from _vm import VM_REMOTE_DIR, ssh_run


def main() -> int:
    vm_sync.main()
    ssh_run(
        f"cd {VM_REMOTE_DIR}/backend && .venv/bin/python -m pip install --quiet -r requirements.txt",
        check=True,
    )
    result = ssh_run(f"cd {VM_REMOTE_DIR}/backend && .venv/bin/python -m pytest -v")
    if result.returncode == 0:
        print("\nAll backend tests passed on the Ubuntu VM.")
    else:
        print("\nBackend tests FAILED on the Ubuntu VM.")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
