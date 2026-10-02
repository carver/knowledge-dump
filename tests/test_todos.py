from pathlib import Path

import pytest
from test_triage import write

from kd.todos import TodoError, find, mark_done, open_todos

TODAY = "2026-10-01"

WORKFLOW = """- [ ] Install retro skill #queue [added: 2026-09-30]
  Why: never write the same comment twice.
  Source: [Video](https://example.com) at 20:38

- [x] Already done
  Done in: repo@abc1234

- [ ] Rename my skill #queue [added: 2026-09-30]
  Source: [Video](https://example.com)
Some prose after it.
"""


def test_lists_open_tasks_with_their_nested_lines(tmp_path: Path) -> None:
    write(tmp_path, "AI coding workflow", WORKFLOW)
    todos = open_todos(tmp_path)
    assert [t.lines[0] for t in todos] == [
        "- [ ] Install retro skill #queue [added: 2026-09-30]",
        "- [ ] Rename my skill #queue [added: 2026-09-30]",
    ]
    assert todos[0].lines[1:] == [
        "  Why: never write the same comment twice.",
        "  Source: [Video](https://example.com) at 20:38",
    ]
    assert todos[1].lines[1:] == ["  Source: [Video](https://example.com)"]
    assert {t.page for t in todos} == {"AI coding workflow"}


def test_skips_inbox_triage_queue_and_library(tmp_path: Path) -> None:
    for page in ("Inbox/x", "Triage", "Queue", "Library/Std/y"):
        write(tmp_path, page, "- [ ] not a to-do\n")
    write(tmp_path, "Topic/Sub", "- [ ] a to-do\n")
    assert [t.page for t in open_todos(tmp_path)] == ["Topic/Sub"]


def test_ids_are_stable_and_distinct(tmp_path: Path) -> None:
    write(tmp_path, "A", "- [ ] one\n- [ ] two\n")
    write(tmp_path, "B", "- [ ] one\n")
    ids = [t.id for t in open_todos(tmp_path)]
    assert len(set(ids)) == 3
    write(tmp_path, "A", "intro\n\n- [ ] one\n- [ ] two\n")
    assert [t.id for t in open_todos(tmp_path)] == ids


def test_find_rejects_unknown_and_ambiguous_ids(tmp_path: Path) -> None:
    write(tmp_path, "A", "- [ ] same\n- [ ] same\n")
    same = open_todos(tmp_path)[0].id
    with pytest.raises(TodoError, match="2 open tasks"):
        find(tmp_path, same)
    with pytest.raises(TodoError, match="no open task"):
        find(tmp_path, "ffffff")


def test_mark_done_ticks_and_records_the_commit(tmp_path: Path) -> None:
    write(tmp_path, "W", WORKFLOW)
    mark_done(tmp_path, find(tmp_path, open_todos(tmp_path)[0].id), "repo@1234567", TODAY)
    text = (tmp_path / "W.md").read_text()
    assert text.startswith(
        "- [x] Install retro skill #queue [added: 2026-09-30] [done: 2026-10-01]\n"
        "  Why: never write the same comment twice.\n"
        "  Source: [Video](https://example.com) at 20:38\n"
        "  Done in: repo@1234567\n"
        "\n- [x] Already done\n"
    )
    assert len(open_todos(tmp_path)) == 1


def test_mark_done_adds_a_missing_why_first_and_learned_last(tmp_path: Path) -> None:
    write(tmp_path, "W", WORKFLOW)
    todo = open_todos(tmp_path)[1]
    mark_done(tmp_path, todo, "repo@a..b", TODAY, why="it clashes", learned=["one thing", "another"])
    assert (
        (tmp_path / "W.md")
        .read_text()
        .endswith(
            "- [x] Rename my skill #queue [added: 2026-09-30] [done: 2026-10-01]\n"
            "  Why: it clashes\n"
            "  Source: [Video](https://example.com)\n"
            "  Done in: repo@a..b\n"
            "  Learned:\n"
            "    - one thing\n"
            "    - another\n"
            "Some prose after it.\n"
        )
    )


def test_mark_done_keeps_a_nested_task_indented(tmp_path: Path) -> None:
    write(tmp_path, "N", "- [ ] parent\n  - [ ] child\n    Source: s\n")
    child = next(t for t in open_todos(tmp_path) if "child" in t.lines[0])
    mark_done(tmp_path, child, "r@1", TODAY)
    assert (tmp_path / "N.md").read_text() == (
        "- [ ] parent\n  - [x] child [done: 2026-10-01]\n    Source: s\n    Done in: r@1\n"
    )


def test_mark_done_replaces_an_existing_why_in_place(tmp_path: Path) -> None:
    write(tmp_path, "W", WORKFLOW)
    todo = open_todos(tmp_path)[0]
    mark_done(tmp_path, todo, "r@1", TODAY, why="the confirmed reason")
    text = (tmp_path / "W.md").read_text()
    assert "  Why: the confirmed reason\n" in text
    assert "never write the same comment twice" not in text
    assert text.count("Why:") == 1
    assert text.index("Why:") < text.index("Done in:")


def test_mark_done_refuses_multiline_values(tmp_path: Path) -> None:
    write(tmp_path, "W", WORKFLOW)
    todo = open_todos(tmp_path)[0]
    with pytest.raises(TodoError, match="one line"):
        mark_done(tmp_path, todo, "r@1", TODAY, learned=["two\nlines"])
    assert (tmp_path / "W.md").read_text() == WORKFLOW
