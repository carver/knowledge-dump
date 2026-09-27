#!/usr/bin/env python3
"""Host side of the vault: set it up, auto-commit it, and merge what the sandbox pushes.

Runs on the host with the standard library only. The systemd units and git hooks
that install_host.py writes call these subcommands. Run with -h for details.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

MAIN = "main"
AGENT_REF = "refs/heads/agent"
IDENTITY = ("knowledge-dump host", "host@knowledge-dump.invalid")
LOCK_NAME = "kd.lock"

GITIGNORE = """\
# SilverBullet's login secrets and caches stay out of history.
.silverbullet*
"""

INDEX = """\
# Notes

- [[Triage]]: proposals for filing what's in the Inbox. Tick to apply.
- Quick notes land in the Inbox.
"""


def _clean_env() -> dict[str, str]:
    """The environment without git's hook variables, so git commands act on the vault we name."""
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def git(vault: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(vault), *args], capture_output=True, text=True, check=check, env=_clean_env()
    )


@contextlib.contextmanager
def locked(vault: Path) -> Iterator[None]:
    """One git writer at a time: the auto-commit timer and the merge hook can overlap."""
    with open(vault / ".git" / LOCK_NAME, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def commit_all(vault: Path, message: str) -> bool:
    git(vault, "add", "-A")
    if git(vault, "diff", "--cached", "--quiet", check=False).returncode == 0:
        return False
    git(vault, "commit", "-q", "-m", message)
    return True


def _hook(body: str) -> str:
    return f"#!/bin/sh\n# Written by knowledge-dump's host/kd_host.py; re-run init to update.\n{body}\n"


def install_hooks(vault: Path) -> None:
    script = Path(__file__).resolve()
    python = sys.executable
    hooks = vault / ".git" / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    bodies = {
        # Runs per ref before it's updated; a non-zero exit rejects that ref.
        "update": f'exec "{python}" "{script}" check-push "$1"',
        # Runs after every push; its output shows up in the pusher's terminal.
        "post-receive": f'exec "{python}" "{script}" merge-agent "{vault}"',
    }
    for name, body in bodies.items():
        path = hooks / name
        path.write_text(_hook(body))
        path.chmod(0o755)


def init(vault: Path) -> None:
    """Create the vault repo if needed, then (re)install its hooks and settings. Safe to repeat."""
    vault.mkdir(parents=True, exist_ok=True)
    if not (vault / ".git").is_dir():
        git(vault, "init", "-q", "-b", MAIN)
    git(vault, "config", "user.name", IDENTITY[0])
    git(vault, "config", "user.email", IDENTITY[1])
    gitignore = vault / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(GITIGNORE)
    index = vault / "index.md"
    if not index.exists():
        index.write_text(INDEX)
    install_hooks(vault)
    with locked(vault):
        commit_all(vault, "Set up the vault")


def autocommit(vault: Path) -> None:
    with locked(vault):
        commit_all(vault, "Autocommit")


def merge_agent(vault: Path) -> int:
    """Merge the sandbox's agent branch into main. Exit code 1 means it wasn't merged."""
    with locked(vault):
        branch = git(vault, "symbolic-ref", "--short", "HEAD", check=False).stdout.strip()
        if branch != MAIN:
            print(f"knowledge-dump: vault is on {branch or 'a detached HEAD'}, not {MAIN}; not merging")
            return 1
        commit_all(vault, "Autocommit before merging the agent branch")
        result = git(vault, "merge", "-q", "--no-edit", AGENT_REF, check=False)
        if result.returncode == 0:
            print("knowledge-dump: merged into main")
            return 0
        if git(vault, "rev-parse", "-q", "--verify", "MERGE_HEAD", check=False).returncode == 0:
            git(vault, "merge", "--abort", check=False)
        print(f"knowledge-dump: not merged: {(result.stdout + result.stderr).strip()[:500]}")
        return 1


def git_daemon_command(vault: Path, port: int) -> list[str]:
    """git daemon serving only `vault`, on loopback, accepting pushes.

    --interpolated-path without placeholders maps every requested path to the
    vault, so git://host/notes reaches it and nothing else on disk is served.
    Pushes are limited to the agent branch by the update hook.
    """
    return [
        "git",
        "daemon",
        "--reuseaddr",
        "--listen=127.0.0.1",
        f"--port={port}",
        "--export-all",
        "--enable=receive-pack",
        f"--interpolated-path={vault}",
        "--informative-errors",
    ]


def check_push(ref: str) -> int:
    if ref == AGENT_REF:
        return 0
    print(f"knowledge-dump: only {AGENT_REF} accepts pushes, not {ref}")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kd_host.py", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name, text in [
        ("init", "create the vault repo if missing and (re)install its git hooks"),
        ("autocommit", "commit every change in the vault (the timer runs this)"),
        ("merge-agent", "merge the agent branch into main (the post-receive hook runs this)"),
    ]:
        commands.add_parser(name, help=text).add_argument("vault", type=Path)
    commands.add_parser(
        "check-push", help="reject pushes to anything but the agent branch (update hook)"
    ).add_argument("ref")
    args = parser.parse_args(argv)

    if args.command == "check-push":
        return check_push(args.ref)
    vault = args.vault.expanduser().resolve()
    if args.command == "init":
        init(vault)
        return 0
    if args.command == "autocommit":
        autocommit(vault)
        return 0
    return merge_agent(vault)


if __name__ == "__main__":
    sys.exit(main())
