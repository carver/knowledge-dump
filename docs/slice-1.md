# Long-term shape and slice 1

Decided in a grilling session on 2026-09-26. Background and tool research: [research/pkm-tools-landscape.md](../research/pkm-tools-landscape.md).

## Long term

- **Store.** A markdown vault in its own git repo on the host, outside the `claudedev/` mount (e.g. `~/notes`). No GitHub. This code repo holds the tooling only.
- **Phone.** SilverBullet installed as a web app from Chrome, over Tailscale HTTPS. It keeps every page offline, handles browsing and editing, and merges edits when it reconnects. Markor + Syncthing comes back only if capture in SilverBullet feels clumsy.
- **Agents.** They run in the sandbox. They reach the vault only through a host `git daemon`: they clone outside the mount, push, and a host job merges. The mount is never used for the vault, because the sandbox sees stale files and directory listings there (see the test log in the research doc).
- **Retrieval.**
  - On the phone, offline, through SilverBullet.
  - By asking an agent, which should be quick and easy.
- **Capture.** From two places:
  - an Inbox page in SilverBullet.
  - tab-squasher Sparks with a new `knowledge-dump` Destination. Only Sparks addressed to knowledge-dump; others are ignored.
- **Triage.** A cron job in the sandbox proposes where each inbox item goes. Proposals land on a Triage page in SilverBullet as checkboxes. The next run applies the ticked ones. You can always edit the vault directly and skip the inbox.
- **Cues.** Captured through the inbox and Sparks. They become tagged notes you can search offline. Coding agents look them up on their own while working, without being asked.
- **Location reminders.** Tasks.org on the phone, standalone. It can sync with a Radicale CalDAV server later: its source syncs location as `GEO`, so agents could then create them.
- **Contacts.** Radicale is the master copy for contacts, synced to the phone with DAVx5. Markdown pages only for the few people with more to say.
- **Host services.** systemd user services exposed with `tailscale serve`, the same pattern as tab-squasher's ADR 0001.

## Slice 1: walking skeleton

Every piece, minimal, end to end:

1. Vault repo on the host, outside the mount, with an Inbox page and a Triage page.
2. SilverBullet as a systemd user service behind `tailscale serve` HTTPS, installed on the phone as a web app.
3. Host auto-commit timer for the vault.
4. Host `git daemon` serving the vault, with pushes enabled, plus a host job that merges agent pushes into the working tree.
5. Sandbox clone outside the mount, and a triage cron that:
   - skips the run when there's nothing new.
   - proposes filing for Inbox items and new knowledge-dump Sparks.
   - applies ticked proposals.
6. tab-squasher: add a `knowledge-dump` Destination. knowledge-dump tracks the Spark ids it has handled in its own files, per ADR 0001.

Not in slice 1: cue lookup by coding agents, Anki ideas, Evernote migration, Keep archive, contacts, Radicale, Karakeep, bookmark and repo-TODO indexing.

## Later, roughly in order

1. Try SilverBullet-only capture for a week; add Markor + Syncthing if needed.
2. Cue lookup: a rule or skill so coding agents search cue notes unprompted.
3. Evernote exit: `jimmy` or `evernote2md` into the vault.
4. Contacts: Radicale + DAVx5, page-per-person linking.
5. Keep Takeout archive and search, bookmarks and repo TODO indexing.
6. Anki cards as a source of note ideas.
7. Location reminders synced through Radicale.

## Open risks

- **Backup: deferred.** The laptop holds the only full copy with history. The phone holds pages but not attachments or history. The sandbox clone lives outside the mount, so a sandbox recreate deletes it.
- **Unattended triage.** The cron spends tokens and sends note contents to the model API. It runs only when there's something new.
- **SilverBullet background sync.** It syncs only while the app is open or shortly after. Chrome's storage for installed web apps is untested on your phone.
- **Syncthing exposure.** The host's Syncthing port was reachable from the internet (probably UPnP). If Syncthing stays for other uses, lock it to Tailscale.
