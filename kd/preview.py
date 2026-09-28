"""What triage would propose for Inbox pages, without changing anything.

For trying a change to the triage prompt on real Items before it goes live.
"""

from datetime import date
from pathlib import Path

from kd.propose import Model, propose
from kd.vault import content_pages, inbox_items


def preview(vault: Path, model: Model, names: list[str]) -> list[str]:
    """Output lines for the named Inbox pages, or for all of them when `names` is empty."""
    items = inbox_items(vault)
    known = {item.page for item in items}
    if unknown := [name for name in names if name not in known]:
        return [f"problem: no Inbox page {name!r}" for name in unknown]
    chosen = [item for item in items if not names or item.page in names]
    if not chosen:
        return ["the Inbox is empty"]
    proposals, problems = propose(chosen, content_pages(vault), model, set(), date.today())
    lines: list[str] = []
    for p in proposals:
        target = p.page if p.action == "file" else "discard"
        lines.append(f"{p.item} -> {target} ({p.summary})")
        if p.content:
            lines.extend(p.content.rstrip("\n").splitlines())
        lines.append("")
    return lines + [f"problem: {problem}" for problem in problems]
