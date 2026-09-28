"""The Triage page: proposals shown as checkboxes, ticked by the user in SilverBullet.

Each proposal is one top-level task line ending in its id, like `kd:3f9a1c`.
A proposal to file has a nested task under it ending in `kd:3f9a1c:discard`,
for throwing the note away instead. The triage agent rewrites the page. The
user only ticks boxes or deletes lines.
"""

import re
from typing import Literal

from kd.state import Proposal

# What the user ticked for one proposal still on the page.
Answer = Literal["none", "apply", "discard", "both"]
_ANSWERS: dict[tuple[bool, bool], Answer] = {
    (False, False): "none",
    (True, False): "apply",
    (False, True): "discard",
    (True, True): "both",
}

PREVIEW_LINES = 6
_TASK = re.compile(r"^- \[([ xX])\] .*`kd:([0-9a-f]{6})`\s*$")
_DISCARD = re.compile(r"^  - \[([ xX])\] .*`kd:([0-9a-f]{6}):discard`\s*$")

HEADER = """# Triage

Proposals from the triage agent for pages in the Inbox. Tick one and the next run applies it, \
or tick "Discard the note instead" to delete its Inbox page. \
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
        if proposal.action == "file":
            body.append(f"  - [ ] Discard the note instead `kd:{proposal.id}:discard`")
        if proposal.content:
            body.extend(_preview(proposal.content))
    return HEADER + "\n" + ("\n".join(body) if body else "_Nothing to triage._") + "\n"


def _ticked(pattern: re.Pattern[str], text: str) -> dict[str, bool]:
    return {m.group(2): m.group(1) != " " for m in map(pattern.match, text.splitlines()) if m}


def parse(text: str) -> dict[str, Answer]:
    """Proposal id -> what's ticked, for every proposal whose main line is still on the page."""
    discard = _ticked(_DISCARD, text)
    return {pid: _ANSWERS[apply, discard.get(pid, False)] for pid, apply in _ticked(_TASK, text).items()}
