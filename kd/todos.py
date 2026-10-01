"""Open to-dos on the vault's pages, and ticking one off once its work is done.

A to-do is an open task on a topic page, with its context (Why, Source) on the
indented lines under it. /todone in llm-toolbox does the work and records it here.
"""

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from kd.pages import QUEUE, TRIAGE, page_path
from kd.vault import content_pages

_OPEN_TASK = re.compile(r"^(\s*)- \[ \] ")


class TodoError(ValueError):
    pass


@dataclass(frozen=True)
class Todo:
    id: str
    page: str
    line: int
    lines: list[str]

    @property
    def indent(self) -> str:
        match = _OPEN_TASK.match(self.lines[0])
        assert match
        return match.group(1)


def _todo_id(page: str, task_line: str) -> str:
    return hashlib.sha256(f"{page}\n{task_line.strip()}".encode()).hexdigest()[:6]


def _nested_end(lines: list[str], start: int, indent: str) -> int:
    """The index just past the indented lines under the task at `start`."""
    end = start + 1
    while end < len(lines) and lines[end].strip() and _indent(lines[end]) > len(indent):
        end += 1
    return end


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _page_todos(vault: Path, page: str) -> list[Todo]:
    lines = page_path(vault, page).read_text(encoding="utf-8").splitlines()
    todos = []
    for i, line in enumerate(lines):
        match = _OPEN_TASK.match(line)
        if match:
            end = _nested_end(lines, i, match.group(1))
            todos.append(Todo(_todo_id(page, line), page, i, lines[i:end]))
    return todos


def open_todos(vault: Path) -> list[Todo]:
    pages = [p for p in content_pages(vault) if p not in (TRIAGE, QUEUE)]
    return [todo for page in pages for todo in _page_todos(vault, page)]


def find(vault: Path, todo_id: str) -> Todo:
    matches = [t for t in open_todos(vault) if t.id == todo_id]
    if not matches:
        raise TodoError(f"no open task with id {todo_id}; `kd todos` lists them")
    if len(matches) > 1:
        raise TodoError(f"{len(matches)} open tasks share id {todo_id}; make their lines differ")
    return matches[0]


def mark_done(
    vault: Path, todo: Todo, done_in: str, today: str, why: str | None = None, learned: Sequence[str] = ()
) -> None:
    """Tick the task and add `[done: today]`, a Why if given, `Done in:` and any `Learned:` lines."""
    for value in (done_in, why or "", *learned):
        if "\n" in value or "\r" in value:
            raise TodoError(f"each value must be one line: {value!r}")
    if why and any(line.strip().startswith("Why:") for line in todo.lines[1:]):
        raise TodoError(f"the task already has a Why: {todo.lines[0].strip()}")

    path = page_path(vault, todo.page)
    lines = path.read_text(encoding="utf-8").splitlines()
    end = todo.line + len(todo.lines)
    if lines[todo.line : end] != todo.lines:
        raise TodoError(f"{todo.page} changed since the task was read")
    nested = todo.indent + "  "
    ticked = lines[todo.line].replace("- [ ] ", "- [x] ", 1).rstrip() + f" [done: {today}]"
    added_why = [f"{nested}Why: {why}"] if why else []
    record = [f"{nested}Done in: {done_in}"]
    if learned:
        record += [f"{nested}Learned:", *(f"{nested}  - {item}" for item in learned)]
    block = [ticked, *added_why, *todo.lines[1:], *record]
    lines[todo.line : end] = block
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
