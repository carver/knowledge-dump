# Next steps at the laptop

Slice 1 is built and committed locally in the sandbox. Nothing is pushed or installed on the host yet. Do these in order.

## Not verified yet

- **Reboot, without logging in** verify that:
    - SilverBullet loads on the phone, and connects to the laptop server
    - `systemctl --user status kd-silverbullet kd-git-daemon kd-autocommit.timer` should show active times from boot, and before login

## Later

Open decisions and the later slices are in `docs/slice-1.md` and `uncertainties.md`. Backup is still deferred: the laptop has the only full copy of the vault with history.
