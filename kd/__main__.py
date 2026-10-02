"""`python3 -m kd`: the knowledge-dump command line. Run with -h for options."""

import argparse
import os
import sys
import tempfile
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path

from kd.gitsync import Unreachable, VaultClone
from kd.preview import preview
from kd.propose import run_claude
from kd.run import ATTEMPTS, run
from kd.sparks import new_spark_pages
from kd.todos import TodoError, find, mark_done, open_todos
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
    _add_remote(triage.add_argument)
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
    preview_cmd.add_argument(
        "--compare",
        action="store_true",
        help="show each proposal as a diff against the one waiting on the Triage page",
    )
    source = preview_cmd.add_mutually_exclusive_group()
    source.add_argument(
        "--vault",
        type=Path,
        help="read this vault folder as it is, uncommitted edits included, instead of cloning",
    )
    _add_remote(source.add_argument)
    todos_cmd = commands.add_parser(
        "todos",
        help="list the open tasks on topic pages, each with its id",
        description="Print every open task outside the Inbox, Triage and Queue pages, "
        "with the lines under it and an id for `kd done`.",
    )
    _add_remote(todos_cmd.add_argument)
    done_cmd = commands.add_parser(
        "done",
        help="tick an open task and record the work that did it",
        description="Tick the task, add [done: DATE], set its Why, add `Done in:` "
        "and any `Learned:` lines, then push to the host and wait for the merge.",
    )
    done_cmd.add_argument("id", help="the task's id, from `kd todos`")
    done_cmd.add_argument("--done-in", required=True, metavar="REF", help="like repo@4c1e2a9 or repo@a1..b2")
    done_cmd.add_argument("--why", help="the confirmed Why; replaces the task's Why: line, or adds one")
    done_cmd.add_argument(
        "--learned", action="append", default=[], metavar="TEXT", help="add a Learned: line; repeatable"
    )
    done_cmd.add_argument("--date", default=date.today().isoformat(), help="default today, %(default)s")
    _add_remote(done_cmd.add_argument)
    args = parser.parse_args(argv)

    if args.command == "todos":
        return _with_clone(args.remote, _print_todos)
    if args.command == "done":
        return _with_clone(args.remote, lambda clone: _done(clone, args))

    if args.command == "preview" and args.vault:
        return _print_preview(preview(args.vault, run_claude, args.pages, args.compare))
    if args.command == "preview":
        return _preview(args.remote, args.pages, args.compare)
    clone = VaultClone(args.clone, args.remote)
    model = None if args.no_model else run_claude
    sparks = _no_sparks if args.no_sparks else new_spark_pages
    return 0 if run(clone, model, sparks, _log, frozenset(args.repropose)) else 1


def _add_remote(add_argument: Callable[..., object]) -> None:
    add_argument(
        "--remote",
        default=os.environ.get("KD_VAULT_REMOTE", DEFAULT_REMOTE),
        help="git URL of the vault on the host (env KD_VAULT_REMOTE; default %(default)s)",
    )


def _with_clone(remote: str, act: Callable[[VaultClone], int]) -> int:
    """Run `act` on a fresh clone of the vault in a temporary folder."""
    with tempfile.TemporaryDirectory() as tmp:
        clone = VaultClone(Path(tmp) / "vault", remote)
        try:
            clone.ensure()
            return act(clone)
        except (Unreachable, TodoError) as e:
            print(e, file=sys.stderr)
            return 1


def _print_todos(clone: VaultClone) -> int:
    for todo in open_todos(clone.path):
        print(f"{todo.id}  {todo.page}")
        print("\n".join(todo.lines) + "\n")
    return 0


def _done(clone: VaultClone, args: argparse.Namespace) -> int:
    clone.fetch()
    for _ in range(ATTEMPTS):
        clone.reset_to_main()
        todo = find(clone.path, args.id)
        mark_done(clone.path, todo, args.done_in, args.date, args.why, args.learned)
        clone.commit_all(f"Done: {todo.lines[0].strip()}")
        if clone.merged(clone.push()):
            print(f"ticked {args.id} on {todo.page}; merged into main")
            return 0
    print(f"gave up after {ATTEMPTS} attempts; the host keeps refusing the merge", file=sys.stderr)
    return 1


def _preview(remote: str, pages: list[str], compare: bool) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        clone = VaultClone(Path(tmp) / "vault", remote)
        try:
            clone.ensure()
        except Unreachable as e:
            print(e, file=sys.stderr)
            return 1
        lines = preview(clone.path, run_claude, pages, compare)
    return _print_preview(lines)


def _print_preview(lines: list[str]) -> int:
    print("\n".join(lines))
    return 1 if any(line.startswith("problem: ") for line in lines) else 0


if __name__ == "__main__":
    sys.exit(main())
