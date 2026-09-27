# Proposed next work

Written 2026-09-27, after slice 1 was running with real notes: a Quick Note got a proposal, and a Spark was filed into "Bay Area Role Playing Games". Ordered by what I'd do first. The longer list of later slices is in [slice-1.md](slice-1.md).

## 1. Backup (small, first)

The laptop holds the only full copy of the vault with its history. The phone keeps pages but not attachments or history, and a sandbox recreate deletes the sandbox's clone. It's cheap insurance before Evernote adds years of notes.

Options:
- Encrypted offsite copy: restic to a cloud bucket, on a systemd timer next to the auto-commit one. The content leaves the machine, but encrypted.
- A git copy on another machine you own, if one is always on. Nothing leaves your devices, but it only helps if that machine is somewhere else.

To decide: which of these, and how often.

## 2. Leave Evernote (medium)

It irritates you, and it's a one-time job.

- Export `.enex` files per notebook and convert them with `jimmy` or `evernote2md` (both open source; see the research doc).
- Notebooks become folders, and tags become SilverBullet tags.
- Decide what happens to attachments: keep them next to the pages, or leave large ones out.
- Imported notes should go straight to their final pages, not through triage. Otherwise the Triage page gets buried.
- Do a test import into a scratch vault first, then the real one.

To decide: rough note and attachment counts, and whether anything stays behind.

## 3. Cue lookup for coding agents (small to medium)

The payoff of the Debezium example: agents in the sandbox search `#cue` notes before related work, unprompted, and mention hits. It builds only on what exists: the sandbox clone plus a rule or skill in the global agent instructions.

To decide: how noisy is acceptable, e.g. mention only strong matches, at most once per session.

## 4. Contacts (bigger, after Evernote)

Radicale on the host as the master copy, DAVx5 on the phone, and a page per person only when there's more to say. It comes after Evernote because some Evernote notes are probably about people, and those should link to their contact.

## In the background

Keep using SilverBullet alone for capture for a week or so. If Quick Note still feels slow even with the button on the index page, bring back Markor with Syncthing for the Inbox, or build a tiny capture page served by the host.
