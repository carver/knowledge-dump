# Next steps at the laptop

Slice 1 is built and committed locally in the sandbox. Nothing is pushed or installed on the host yet. Do these in order.

The shared Spark reader lives in `tab-squasher/reader/inbox.py`. `spec/` keeps only the format: schema, rules and fixtures. The same branch also fixes a bug in tab-squasher's pre-commit hook (`9c57132`). The hook resolved git's index path wrong, so it refused every commit touching `spec/`.

## 1. Merge the Destination branches

The tab-squasher and anki-cards working trees are checked out on `knowledge-dump-destination`. anki-cards' hourly cron commits to whichever branch is checked out, so it's writing to that branch until you merge.

1. Review and merge both branches together. Merging only one breaks things:
   - new anki-cards without new tab-squasher can't import the reader.
   - old anki-cards with the new schema would turn knowledge-dump Sparks into Anki cards.
2. Push tab-squasher to GitHub. CI runs there.

## 2. Redeploy the tab-squasher server

```bash
cd ~/code/claudedev/tab-squasher && server/install-host.sh
```

The old server rejects knowledge-dump Sparks with a 400. The extension's settings page should say "Server 0.2.0 is reachable".

## 3. Sign and install the extension

```bash
cd ~/code/claudedev/tab-squasher/extension && ./scripts/sign.sh --no-bump
```

`--no-bump` keeps it at 0.2.0. Install it on desktop and the phone, and check that the popup shows the Anki / Knowledge dump choice.

## 4. Install the knowledge-dump host side

```bash
cd ~/code/claudedev/knowledge-dump && python3 host/install_host.py
```

It asks for a SilverBullet login (12+ characters), creates `~/notes`, starts `kd-silverbullet`, `kd-git-daemon` and the `kd-autocommit` timer, and prints the phone URL. It fails loudly if SilverBullet or git daemon doesn't answer on loopback. Options are in `-h`; `--https-port` if 443 is taken.

## 5. Set up the phone

Open the printed URL in Chrome, log in, then menu > Add to home screen > Install.

## 6. Try the loop

1. On the phone, run Quick Note and write something, e.g. a cue.
2. Wait for the auto-commit (up to 5 minutes), then run triage in the sandbox instead of waiting for :23 past the hour:
   ```bash
   cd ~/code/claudedev/knowledge-dump && python3 -m kd triage
   ```
3. Open the Triage page on the phone and tick the proposal. After the next auto-commit, run triage again. The note should be filed and gone from the Inbox.
4. Send a Spark with the Knowledge dump Destination and check it shows up as an `Inbox/Spark …` page after a run.

## Not verified yet

- **Host installer.** It can't run in the sandbox. The unit files are unit-tested, but systemd, `loginctl enable-linger` and `tailscale serve` on 443 haven't been tried.
- **`git daemon` on Ubuntu.** I expect Ubuntu's `git` package to include it, but I haven't checked. If the installer says git daemon isn't answering, check `journalctl --user -u kd-git-daemon -n 50` and whether `git daemon --help` works.
- **Sandbox → host git.** The sandbox reached the host's loopback over raw TCP (tested against Syncthing's port), but not yet on the git port.
- **SilverBullet offline on your phone.** Whether Chrome keeps the local copy, how offline edits merge, and how quickly it syncs after reopening.
- **SilverBullet Quick Note.** It should create pages under `Inbox/`; the default index page suggests so, but I haven't checked on a real install.
- **Triage page ticking in SilverBullet.** Ticking a box should turn `- [ ]` into `- [x]` in the file. The parser also accepts `[X]`. Any other syntax would go unseen.
- **Host Python.** `host/` uses only the standard library and should run on 3.10+, but it's only been tested on 3.14.

## Later

Open decisions and the later slices are in `docs/slice-1.md` and `uncertainties.md`. Backup is still deferred: the laptop has the only full copy of the vault with history.
