"""One triage pass over a checked-out vault. No git here; see kd/run.py for that.

A pass:
1. adds new Sparks to the Inbox as pages,
2. reads the Triage page: applies ticked proposals, parks items whose proposal was deleted,
3. asks the model about Inbox items with no proposal yet,
4. rewrites the Triage page and the state file.
"""

import subprocess
from dataclasses import dataclass, field, replace
from datetime import date
from pathlib import Path

from kd import triage_page
from kd.pages import TRIAGE, linkable, page_path
from kd.propose import Model, ModelError, propose
from kd.state import Proposal, State, load, state_path
from kd.vault import (
    InboxItem,
    append_to_page,
    content_pages,
    inbox_items,
    remove_inbox_page,
    write_if_changed,
)


@dataclass(frozen=True)
class NewPage:
    """A page to add to the Inbox, like one made from a Spark."""

    source_id: str
    page: str
    text: str


@dataclass
class Report:
    imported: list[str] = field(default_factory=list)
    applied: list[str] = field(default_factory=list)
    parked: list[str] = field(default_factory=list)
    withdrawn: list[str] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)
    proposed: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    def lines(self) -> list[str]:
        labels = [
            ("imported Spark", self.imported),
            ("applied", self.applied),
            ("parked (proposal deleted)", self.parked),
            ("withdrawn to propose again", self.withdrawn),
            ("dropped (item changed or gone)", self.dropped),
            ("proposed", self.proposed),
            ("problem", self.problems),
        ]
        return [f"{label}: {entry}" for label, entries in labels for entry in entries]


def _import_pages(vault: Path, state: State, new_pages: list[NewPage], report: Report) -> None:
    done = set(state.imported_sparks)
    for new in new_pages:
        if new.source_id in done:
            continue
        name, n = new.page, 1
        while page_path(vault, name).exists():
            n += 1
            name = f"{new.page} ({n})"
        write_if_changed(page_path(vault, name), new.text)
        state.imported_sparks.append(new.source_id)
        done.add(new.source_id)
        report.imported.append(name)


def with_why(content: str, why: str) -> str:
    """`content` with a `Why:` line after its first line, nested under it when that line is a list item."""
    first, _, rest = content.partition("\n")
    indent = "  " if first.lstrip().startswith(("- ", "* ")) else ""
    lead = first[: len(first) - len(first.lstrip())]
    return f"{first}\n{lead}{indent}Why: {why}\n{rest}"


def _apply(vault: Path, proposal: Proposal) -> None:
    if proposal.action == "file" and proposal.page and proposal.content:
        content = proposal.content
        if proposal.why and proposal.keep_why:
            content = with_why(content, proposal.why)
        append_to_page(vault, proposal.page, content)
    remove_inbox_page(vault, proposal.item)


def _withdraw(state: State, targets: set[str], report: Report) -> None:
    """Forget proposals and parking for `targets`, proposal ids or Inbox pages, so they're proposed again."""
    for target in sorted(targets):
        pages = {p.item for p in state.proposals if target in (p.id, p.item)}
        if target in state.parked:
            pages.add(target)
        if not pages:
            report.problems.append(f"nothing to repropose for {target!r}")
        state.proposals = [p for p in state.proposals if p.item not in pages]
        for page in sorted(pages):
            state.parked.pop(page, None)
            report.withdrawn.append(page)


def _review(vault: Path, state: State, page_text: str | None, report: Report) -> None:
    """Act on the user's ticks and deletions on the Triage page for proposals shown last time.

    With no Triage page, nothing is parked. With both boxes of a proposal ticked,
    neither is done; the page is rewritten unticked.
    """
    ticks = triage_page.parse(page_text) if page_text is not None else None
    kept = triage_page.kept_whys(page_text) if page_text is not None else None
    items = {item.page: item for item in inbox_items(vault)}
    waiting = []
    for proposal in state.proposals:
        if kept is not None and proposal.why:
            proposal = replace(proposal, keep_why=proposal.id in kept)
        item = items.get(proposal.item)
        answer = "none" if ticks is None else ticks.get(proposal.id)
        if item is None or item.digest != proposal.digest:
            report.dropped.append(proposal.item)
        elif answer is None:
            state.parked[proposal.item] = proposal.digest
            report.parked.append(proposal.item)
        elif answer in ("apply", "discard"):
            chosen = (
                proposal
                if answer == "apply"
                else replace(proposal, action="discard", page=None, content=None)
            )
            _apply(vault, chosen)
            report.applied.append(f"{chosen.item} -> {chosen.page or 'discarded'}")
        else:
            if answer == "both":
                report.problems.append(f"both boxes ticked for {proposal.item}; unticked them, tick one")
            waiting.append(proposal)
    state.proposals = waiting


def _needing_proposals(state: State, items: list[InboxItem], report: Report) -> list[InboxItem]:
    proposed = {p.item for p in state.proposals}
    todo = [i for i in items if i.page not in proposed and state.parked.get(i.page) != i.digest]
    for item in todo:
        if not linkable(item.page):
            report.problems.append(f"can't link to {item.page!r} from the Triage page; rename it")
    return [i for i in todo if linkable(i.page)]


def _propose_for(vault: Path, state: State, todo: list[InboxItem], model: Model, report: Report) -> None:
    """Add proposals for `todo`. Items the model had nothing usable for get parked.

    If the model call itself fails, nothing is parked, so the next run tries again.
    """
    taken = {p.id for p in state.proposals}
    try:
        new, problems = propose(todo, content_pages(vault), model, taken, date.today())
    except (ModelError, OSError, subprocess.TimeoutExpired, ValueError) as e:
        report.problems.append(f"model call failed, will retry next run: {e}")
        return
    state.proposals.extend(new)
    report.proposed.extend(p.item for p in new)
    report.problems.extend(problems)
    proposed = {p.item for p in new}
    state.parked.update({i.page: i.digest for i in todo if i.page not in proposed})


def triage(
    vault: Path, model: Model | None, new_pages: list[NewPage], repropose: frozenset[str] = frozenset()
) -> Report:
    """Run one pass. With `model` None, nothing new is proposed.

    `repropose` names proposal ids or Inbox pages to drop and propose afresh,
    e.g. after changing the triage prompt.
    """
    state = load(vault)
    report = Report()
    _import_pages(vault, state, new_pages, report)
    _withdraw(state, set(repropose), report)

    triage_file = page_path(vault, TRIAGE)
    page_text = triage_file.read_text(encoding="utf-8") if triage_file.exists() else None
    _review(vault, state, page_text, report)

    items = inbox_items(vault)
    current = {item.page: item.digest for item in items}
    state.parked = {page: d for page, d in state.parked.items() if current.get(page) == d}

    todo = _needing_proposals(state, items, report)
    if todo and model is not None:
        _propose_for(vault, state, todo, model, report)

    write_if_changed(triage_file, triage_page.render(state.proposals))
    write_if_changed(state_path(vault), state.to_json())
    return report
