#!/usr/bin/env python3
"""Run the app on the Ubuntu verification VM and tunnel it to this machine for a live look.

Usage:
  python3 scripts/vm_dev.py         # sync, (re)start backend+frontend on the VM, open the tunnel
  python3 scripts/vm_dev.py stop    # stop the VM's dev servers and close the tunnel

Once started, open http://localhost:<FRONTEND_PORT> in your own browser -- the app is genuinely
running on the VM; your machine only carries the SSH tunnel (see docs/ARCHITECTURE.md #7).

Uses `setsid ... < /dev/null` (not just `nohup ... &`) to fully detach the remote process group
from the SSH session -- plain `nohup foo & disown` left the frontend's node/vite child process
attached closely enough that stopping it required hunting down a second PID by hand.
"""

import sys
import time

import vm_sync
import vm_tunnel
from _vm import VM_REMOTE_DIR, check_backend_health, ssh_run

# The bracket-class space (`[ ]` instead of a literal space) keeps this pattern from matching
# its own invoking shell command -- since the whole remote command string (this pattern
# included) shows up in that shell's own argv, a literal-space pattern intermittently pkills the
# script's own shell mid-run before its later commands execute.
_STOP_REMOTE_SERVERS = (
    "pkill -9 -f 'uvicorn[ ]app.presentation.main' 2>/dev/null; "
    "pkill -9 -f 'vite[ ]--port' 2>/dev/null; "
    "true"
)


def start() -> None:
    vm_sync.main()
    ssh_run(_STOP_REMOTE_SERVERS)
    ssh_run(
        f"cd {VM_REMOTE_DIR} && "
        "setsid nohup python3 scripts/dev.py > /tmp/dev.log 2>&1 < /dev/null & disown"
    )
    print("Waiting for the VM's dev servers to come up...")
    time.sleep(4)
    vm_tunnel.start()
    if not check_backend_health():
        sys.exit(
            "Backend did not come up as expected -- check /tmp/dev.log on the VM "
            f"(`ssh $VM_HOST cat /tmp/dev.log`)."
        )


def stop() -> None:
    ssh_run(_STOP_REMOTE_SERVERS)
    vm_tunnel.stop()
    print("VM dev servers stopped and tunnel closed.")


def main() -> None:
    action = sys.argv[1] if len(sys.argv) > 1 else "start"
    if action == "start":
        start()
    elif action == "stop":
        stop()
    else:
        sys.exit(f"Unknown action {action!r}. Use 'start' (default) or 'stop'.")


if __name__ == "__main__":
    sys.exit(main())
