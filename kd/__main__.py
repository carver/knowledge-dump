"""`python3 -m kd`: the knowledge-dump command line. Run with -h for options."""

import argparse
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from kd.gitsync import Unreachable, VaultClone
from kd.preview import preview
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
    _add_remote(triage)
    triage.add_argument(
        "--no-model", action="store_true", help="don't call the model; only apply ticks and import"
    )
    triage.add_argument("--no-sparks", action="store_true", help="don't import Sparks from tab-squasher")
    triage.add_argument(
        "--repropose",
        action="append",
        default=[],
        metavar="ID_OR_PAGE",
        help="drop this proposal (id like 3f9a1c, or its Inbox page) and propose it afresh; repeatable",
    )
    preview_cmd = commands.add_parser(
        "preview",
        help="print what triage would propose, changing nothing",
        description="Ask the model about Inbox pages in a throwaway clone and print its proposals. "
        "Nothing is written or pushed. For trying a triage prompt change on real notes.",
    )
    preview_cmd.add_argument(
        "pages", nargs="*", help="Inbox pages to ask about, like 'Inbox/Spark x' (default: all)"
    )
    _add_remote(preview_cmd)
    args = parser.parse_args(argv)

    if args.command == "preview":
        return _preview(args.remote, args.pages)
    clone = VaultClone(args.clone, args.remote)
    model = None if args.no_model else run_claude
    sparks = _no_sparks if args.no_sparks else new_spark_pages
    return 0 if run(clone, model, sparks, _log, frozenset(args.repropose)) else 1


def _add_remote(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--remote",
        default=os.environ.get("KD_VAULT_REMOTE", DEFAULT_REMOTE),
        help="git URL of the vault on the host (env KD_VAULT_REMOTE; default %(default)s)",
    )


def _preview(remote: str, pages: list[str]) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        clone = VaultClone(Path(tmp) / "vault", remote)
        try:
            clone.ensure()
        except Unreachable as e:
            print(e, file=sys.stderr)
            return 1
        lines = preview(clone.path, run_claude, pages)
    print("\n".join(lines))
    return 1 if any(line.startswith("problem: ") for line in lines) else 0


if __name__ == "__main__":
    sys.exit(main())
