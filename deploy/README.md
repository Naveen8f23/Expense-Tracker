# Deployment (Ubuntu VM, ADR-0020)

Runs the backend (which also serves the built dashboard — see `app/presentation/main.py`'s static
mount) as a persistent `systemd --user` service: auto-restarts on failure, survives SSH
disconnects, and (once lingering is enabled) starts on boot without needing an active login
session.

## One-time setup (needs your own sudo password — not run on your behalf)

```
sudo loginctl enable-linger $(whoami)
```

This is the only step that needs root. It lets your user's systemd instance keep running after
you log out, which a user-level service otherwise wouldn't do. Everything below never needs sudo.

## Install / update the service

```
mkdir -p ~/.config/systemd/user
cp deploy/expense-tracker.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now expense-tracker
```

`scripts/deploy_vm.py` (repo root) automates syncing code, rebuilding the frontend, and running
`systemctl --user restart expense-tracker` for future updates — this manual sequence is only
needed for the very first install.

## Useful commands

```
systemctl --user status expense-tracker
systemctl --user restart expense-tracker
journalctl --user -u expense-tracker -f     # follow logs
```
