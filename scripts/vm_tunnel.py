#!/usr/bin/env python3
"""Open (or close) the SSH tunnel to the Ubuntu verification VM's dev servers.

Usage:
  python3 scripts/vm_tunnel.py          # open the tunnel (safe to re-run -- no-ops if already up)
  python3 scripts/vm_tunnel.py stop     # close it

Once open, the VM's dev servers (started via scripts/vm_dev.py) are reachable at
http://localhost:<FRONTEND_PORT> and http://localhost:<BACKEND_PORT> exactly as if they were
running locally.

A tunnel is used rather than exposing the VM's ports directly on the network: direct connections
to the VM's app ports (5173/8000) time out even though `ssh` and `ping` both work fine and the
VM's own firewall (ufw) is inactive -- the Tailscale network this VM is on appears to only permit
SSH between nodes via its ACLs. See docs/ARCHITECTURE.md #7 and docs/DECISIONS.md ADR-0017.
"""

import sys

from _vm import BACKEND_PORT, FRONTEND_PORT, VM_HOST, is_local_port_listening, run

# Must not start with "-" -- macOS's pkill misparses a pattern beginning with a dash as an
# option flag rather than the search pattern.
_TUNNEL_MARKER = f"ssh -f -N -L {FRONTEND_PORT}:localhost:{FRONTEND_PORT}"


def start() -> None:
    if is_local_port_listening(FRONTEND_PORT) or is_local_port_listening(BACKEND_PORT):
        print(
            f"localhost:{FRONTEND_PORT} or localhost:{BACKEND_PORT} is already in use -- "
            "assuming the tunnel (or the app itself) is already up. Run "
            "`python3 scripts/vm_tunnel.py stop` first if that's not the case."
        )
        return
    run(
        [
            "ssh",
            "-f",
            "-N",
            "-L",
            f"{FRONTEND_PORT}:localhost:{FRONTEND_PORT}",
            "-L",
            f"{BACKEND_PORT}:localhost:{BACKEND_PORT}",
            VM_HOST,
        ],
        check=True,
    )
    print(
        f"Tunnel up. Frontend: http://localhost:{FRONTEND_PORT}  "
        f"Backend: http://localhost:{BACKEND_PORT}/health"
    )


def stop() -> None:
    result = run(["pkill", "-f", _TUNNEL_MARKER])
    print("Tunnel closed." if result.returncode == 0 else "No matching tunnel process found.")


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
