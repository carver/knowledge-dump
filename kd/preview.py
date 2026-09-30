"""What triage would propose for Inbox pages, without changing anything.

For trying a change to the triage prompt on real Items before it goes live.
With `compare`, each proposal is shown as a diff against the one waiting on
the Triage page, so a prompt change's side effects stand out.
"""

import difflib
from datetime import date
from pathlib import Path

from kd import state
from kd.propose import Model, propose
from kd.state import Proposal
from kd.vault import content_pages, inbox_items


def _body(p: Proposal) -> list[str]:
    """What gets filed: the target, the Why and the content. The summary is left out; it varies run to run."""
    lines = [f"-> {p.page if p.action == 'file' else 'discard'}"]
    if p.why:
        lines.append(f"Why: {p.why}")
    if p.content:
        lines.extend(p.content.rstrip("\n").splitlines())
    return lines


def _compared(p: Proposal, current: Proposal | None) -> list[str]:
    if current is None:
        return ["(no current proposal)", *_body(p)]
    diff = list(difflib.unified_diff(_body(current), _body(p), "current", "preview", lineterm=""))
    return diff or ["(same as the current proposal)"]


def preview(vault: Path, model: Model, names: list[str], compare: bool = False) -> list[str]:
    """Output lines for the named Inbox pages, or for all of them when `names` is empty."""
    items = inbox_items(vault)
    known = {item.page for item in items}
    if unknown := [name for name in names if name not in known]:
        return [f"problem: no Inbox page {name!r}" for name in unknown]
    chosen = [item for item in items if not names or item.page in names]
    if not chosen:
        return ["the Inbox is empty"]
    proposals, problems = propose(chosen, content_pages(vault), model, set(), date.today())
    waiting = {p.item: p for p in state.load(vault).proposals}
    lines: list[str] = []
    for p in proposals:
        target = p.page if p.action == "file" else "discard"
        lines.append(f"{p.item} -> {target} ({p.summary})")
        if compare:
            lines.extend(_compared(p, waiting.get(p.item)))
        else:
            lines.extend(_body(p)[1:])
        lines.append("")
    return lines + [f"problem: {problem}" for problem in problems]
