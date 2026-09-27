# Vault on the host, agents sync over git daemon

The vault has to be editable from the phone while the sandbox is closed, so it lives on the host, served by SilverBullet as a systemd user service. Agents run in the sandbox. We tested the shared virtiofs mount with Syncthing on 2026-09-26 (log in `research/pkm-tools-landscape.md`). The sandbox saw files the host had replaced by rename late, and new files never showed up in directory listings, even after dropping caches. An agent reading the vault there would miss Items and could overwrite newer text.

So the vault sits outside the mount (`~/notes`), and the sandbox reaches it only through `git daemon` on the host's loopback (`git://host.docker.internal/notes`). The sandbox keeps its own clone, commits there, and force-pushes to the `agent` branch. A `post-receive` hook on the host merges `agent` into the checked-out `main`: it auto-commits the working tree, then merges, and aborts cleanly on a conflict. The sandbox checks whether its commit reached `main`. If it didn't, it starts over from the newer `main`, up to three times. An `update` hook rejects pushes to any other ref.

## Considered Options

- Vault on the mount, agents read files directly. Rejected: stale reads and invisible new files, seen in testing.
- The same, with `refresh-mount` before each read. Rejected: dropping caches fixed file contents but not directory listings.
- Agents read and write through SilverBullet's HTTP API. Rejected: agents lose plain `rg`/`git` over the files and history, and every tool has to learn the API.
- Clone from the mounted `.git`. Rejected for the same stale-listing reasons; git reads object and ref files the host just wrote.
- Pushing to a GitHub remote. Rejected: the data stays private and local.

## Consequences

- Anything that can reach the host's loopback can push to `agent` and get it merged: the host itself and any sandbox. Git history keeps every earlier version, so damage is reversible. The daemon serves only the vault (`--interpolated-path`), and nothing on the LAN can reach it.
- Items typed in SilverBullet reach the sandbox after the next auto-commit (every 5 minutes). A tick made during a run is merged in and applied by the following run.
- The sandbox clone is a cache. A sandbox recreate deletes it, and the next run clones again.
