# knowledge-dump: notes for agents

Read [GLOSSARY.md](GLOSSARY.md) for the vocabulary (Vault, Item, Triage, Proposal, Queue item). [README.md](README.md) explains how the pieces connect.

## The live vault

The vault lives on the host. The sandbox reaches it only through `git://host.docker.internal/notes`, never through the mount.

- **Read it:** `git clone -q git://host.docker.internal/notes <scratchpad>/v`, and `git fetch && git reset --hard origin/main` to refresh it.
- **Change it:** commit in that clone and run `git push --force origin HEAD:refs/heads/agent`. The host merges the branch and prints "merged into main". Don't edit `.kd/state.json` by hand; use the commands below.
- **Try a triage prompt change on real Items:** `python3 -m kd preview --compare ['Inbox/…']`. It writes nothing, and `--compare` diffs each proposal against the one waiting on the Triage page, so check every changed line, not only the one you meant to change. To try it on an edited or made-up Item, change your clone and run `python3 -m kd preview --vault <scratchpad>/v`, no commit needed.
- **Redo proposals after a prompt change:** `python3 -m kd triage --repropose <id or Inbox page>`.
- `triage.log`, at this repo's root rather than in the vault, has one line per action from every run.

## SilverBullet

The syntax for tasks, attributes and queries is in [docs/silverbullet.md](docs/silverbullet.md). Check there before grepping SilverBullet's source.

## Checks

Fix what ruff can first with `python3 -m ruff check --fix . && python3 -m ruff format .`, then run `python3 -m pytest && python3 -m ruff check . && python3 -m ruff format --check . && python3 -m mypy`. `host/` is standard library only.
