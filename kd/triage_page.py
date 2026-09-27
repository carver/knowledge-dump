"""The Triage page: proposals shown as checkboxes, ticked by the user in SilverBullet.

Each proposal is one top-level task line ending in its id, like `kd:3f9a1c`.
The triage agent rewrites the page. The user only ticks boxes or deletes lines.
"""

import re

from kd.state import Proposal

PREVIEW_LINES = 6
_TASK = re.compile(r"^- \[([ xX])\] .*`kd:([0-9a-f]{6})`\s*$")

HEADER = """# Triage

Proposals from the triage agent for pages in the Inbox. Tick one and the next run applies it. \
Delete a proposal to turn it down; its page stays in the Inbox.
"""


def _line(proposal: Proposal) -> str:
    what = f"File into [[{proposal.page}]]" if proposal.action == "file" else "Discard"
    return f"- [ ] {what}: {proposal.summary} ([[{proposal.item}]]) `kd:{proposal.id}`"


def _preview(content: str) -> list[str]:
    lines = content.strip("\n").splitlines()
    shown = lines[:PREVIEW_LINES]
    if len(lines) > PREVIEW_LINES:
        shown.append("…")
    return ["  > " + line if line.strip() else "  >" for line in shown]


def render(proposals: list[Proposal]) -> str:
    body: list[str] = []
    for proposal in proposals:
        body.append(_line(proposal))
        if proposal.content:
            body.extend(_preview(proposal.content))
    return HEADER + "\n" + ("\n".join(body) if body else "_Nothing to triage._") + "\n"


def parse(text: str) -> dict[str, bool]:
    """Proposal id -> whether it's ticked, for every proposal still on the page."""
    found = {}
    for line in text.splitlines():
        match = _TASK.match(line)
        if match:
            found[match.group(2)] = match.group(1) != " "
    return found
