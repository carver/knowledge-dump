"""`python3 -m kd`: the knowledge-dump command line. Run with -h for options."""

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from kd.gitsync import VaultClone
from kd.propose import run_claude
from kd.run import run
from kd.sparks import new_spark_pages
from kd.triage import NewPage

DEFAULT_CLONE = Path.home() / ".local" / "share" / "knowledge-dump" / "vault"
DEFAULT_REMOTE = "git://host.docker.internal/notes"


def _no_sparks(done: set[str]) -> tuple[list[NewPage], list[str]]:
    return [], []


def _log(line: str) -> None:
    print(f"{datetime.now(UTC).isoformat(timespec='seconds')} {line}", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kd", description="knowledge-dump tools for the sandbox side.")
    commands = parser.add_subparsers(dest="command", required=True)
    triage = commands.add_parser(
        "triage",
        help="import Sparks, apply ticked proposals, propose filing for new Inbox pages, push to the host",
        description="One triage run against the vault on the host. Silent when there's nothing to do.",
    )
    triage.add_argument(
        "--clone",
        type=Path,
        default=Path(os.environ.get("KD_VAULT_CLONE", DEFAULT_CLONE)),
        help="where the sandbox keeps its clone of the vault (env KD_VAULT_CLONE; default %(default)s)",
    )
    triage.add_argument(
        "--remote",
        default=os.environ.get("KD_VAULT_REMOTE", DEFAULT_REMOTE),
        help="git URL of the vault on the host (env KD_VAULT_REMOTE; default %(default)s)",
    )
    triage.add_argument(
        "--no-model", action="store_true", help="don't call the model; only apply ticks and import"
    )
    triage.add_argument("--no-sparks", action="store_true", help="don't import Sparks from tab-squasher")
    args = parser.parse_args(argv)

    clone = VaultClone(args.clone, args.remote)
    model = None if args.no_model else run_claude
    sparks = _no_sparks if args.no_sparks else new_spark_pages
    return 0 if run(clone, model, sparks, _log) else 1


if __name__ == "__main__":
    sys.exit(main())
