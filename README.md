# Personal Knowledge Dump

Store a broad array of thoughts.
Includes everything from important information about people I know, to coding ideas for solving problems, to random introspective thoughts.

It may include a mixture of:

- SQL databases
- wiki-style free-form linked thoughts
- knowledge graphs
- Garry Tan's GBrain
- Probably others I haven't thought of yet

The main location that ties it all together is the **vault**: a git repo of markdown pages on the host (`~/notes`), served by [SilverBullet](https://silverbullet.md) to the phone and laptop over Tailscale. This repo holds the tooling only.

Vocabulary is in [CONTEXT.md](CONTEXT.md), decisions in [docs/adr](docs/adr), the plan in [docs/slice-1.md](docs/slice-1.md), and judgment calls in [uncertainties.md](uncertainties.md).

## How it fits together

```
phone / laptop ── HTTPS (tailscale serve) ──> SilverBullet ──> ~/notes (git, host)
                                                                   │  auto-commit every 5 min
tab-squasher Sparks ──┐                                            │
                      v                                            │
sandbox: kd triage (hourly) ── git://host.docker.internal/notes ───┘
         clone, propose, push to `agent`; the host hook merges into main
```

1. **Capture.** Use SilverBullet's Quick Note, which makes a page under `Inbox/`, or send a Spark with the tab-squasher extension and pick the "Knowledge dump" Destination.
2. **Triage.** Every hour the sandbox pulls the vault and turns new Sparks into Inbox pages. Then it asks Claude where each new Inbox page belongs and lists the answers on the **Triage** page as checkboxes.
3. **Approve.** Tick a proposal in SilverBullet and the next run applies it: the content is appended to the chosen page and the Inbox page is removed. To throw the note away instead, tick "Discard the note instead" under it. To turn a proposal down, delete its line; the page stays in the Inbox until you edit it.
4. **Steer.** To change a proposal, open its Inbox page and add a line like `Triage: reference only, not a queue item`. Editing the page withdraws the proposal, and the next run follows the instruction without filing the line.
5. **Queue.** Start a note with `Read:`, `Watch:` or `Research:` and triage files it as a `#queue` task on its topic page, keeping the quote and link. The **Queue** page lists every open one. Tick it there or on the topic page when you're done.
6. You can always edit any page directly. The Inbox is optional.

The sandbox never touches the vault through the shared mount, which serves stale files (see [ADR 0001](docs/adr/0001-vault-on-host-agents-over-git-daemon.md)).

## Setup

**Host** (Ubuntu, with Tailscale HTTPS already set up, e.g. by tab-squasher's `server/tailscale-wizard.sh`):

```bash
python3 host/install_host.py            # -h for options; re-run to upgrade
python3 host/install_host.py --uninstall
```

It downloads SilverBullet, asks once for a login, creates `~/notes` if missing, and starts three systemd user units: `kd-silverbullet`, `kd-git-daemon` and the `kd-autocommit` timer. Then it publishes SilverBullet with `tailscale serve` and prints the phone URL. In Chrome on the phone, open it, log in, and use "Add to home screen" to install it.

**Sandbox:** `python3 install_sandbox.py` installs dependencies, the git hooks and the hourly cron job. sandbox-setup runs it after every recreate.

## Commands

```bash
python3 -m kd triage -h                    # one run; silent when there's nothing to do
python3 -m kd triage --no-model            # apply ticks and import Sparks, don't call Claude
python3 -m kd triage --repropose 3f9a1c     # drop a proposal and ask again, e.g. after a prompt change
python3 -m kd preview 'Inbox/Spark x'       # print what triage would propose; changes nothing
python3 -m kd preview --vault ~/v          # same, on a local vault folder with uncommitted edits
python3 host/kd_host.py -h                 # host side: init, autocommit, merge-agent
```

Triage runs log to `triage.log`. On the host, check `journalctl --user -u kd-silverbullet` and the other units.

## Development

```bash
python3 -m pytest          # includes an end-to-end test against a real git daemon
python3 -m ruff check . && python3 -m ruff format --check . && python3 -m mypy
```

The pre-commit hook in `.githooks` runs these on the staged files in under 5 seconds, skipping the tests marked `slow` (the git daemon end-to-end ones). It uses whatever `python3` is on `PATH`. CI (`.github/workflows/ci.yml`) installs from scratch into a fresh venv and runs everything; it needs a GitHub remote to run. The sandbox has the tools installed system-wide. On the host, make a venv once (`python3 -m venv venv && venv/bin/pip install -e '.[dev]'`) and activate it before committing. `host/` must stay standard-library only, since it runs on the host's system Python.

## Privacy

This is not meant to get published.

Of course the info is not entirely private, since LLMs gain access: triage sends Inbox pages and the list of page names to Claude.
Still, take reasonable precautions to never post or expose this data outside of this local machine. The vault has no remote besides the sandbox's clone, and SilverBullet is reachable only on loopback and the tailnet.
