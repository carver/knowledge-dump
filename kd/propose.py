"""Asking the model for proposals, and checking what it sends back."""

import json
import secrets
import subprocess
from collections.abc import Callable, Iterable
from datetime import date
from pathlib import Path
from typing import Any

from kd.pages import name_problem
from kd.state import Proposal
from kd.vault import InboxItem

PROMPT_TEMPLATE = Path(__file__).with_name("triage-prompt.md")
MAX_ITEM_CHARS = 6000
MAX_PAGES_LISTED = 1000
MAX_SUMMARY_CHARS = 160
MAX_CONTENT_CHARS = 20_000
TIMEOUT_SECONDS = 600

SCHEMA = {
    "type": "object",
    "properties": {
        "proposals": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item": {"type": "string"},
                    "action": {"enum": ["file", "discard"]},
                    "summary": {"type": "string"},
                    "page": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["item", "action", "summary"],
            },
        }
    },
    "required": ["proposals"],
}

CLAUDE_CMD = [
    "claude-json",
    "--model",
    "sonnet",
    "--timeout",
    str(TIMEOUT_SECONDS),
    "--schema",
    json.dumps(SCHEMA),
]

# Takes the prompt, returns the model's structured output.
Model = Callable[[str], dict[str, Any]]


class ModelError(RuntimeError):
    """The model call failed or returned something that isn't structured output."""


def build_prompt(items: dict[str, InboxItem], pages: list[str], today: date) -> str:
    listed = pages[:MAX_PAGES_LISTED]
    page_lines = "\n".join(f"- {p}" for p in listed) or "(none yet)"
    if len(pages) > len(listed):
        page_lines += f"\n- … and {len(pages) - len(listed)} more"
    item_blocks = []
    for key, item in items.items():
        text = item.text
        if len(text) > MAX_ITEM_CHARS:
            text = text[:MAX_ITEM_CHARS] + "\n[… cut]"
        item_blocks.append(f"### {key}: {item.page}\n\n{text.strip() or '(empty page)'}")
    template = PROMPT_TEMPLATE.read_text(encoding="utf-8")
    filled = template.replace("{today}", today.isoformat()).replace("{pages}", page_lines)
    return filled.replace("{items}", "\n\n".join(item_blocks))


def run_claude(prompt: str) -> dict[str, Any]:
    """Ask Claude through llm-toolbox's claude-json, which bills the claude.ai subscription."""
    try:
        result = subprocess.run(
            CLAUDE_CMD, input=prompt, capture_output=True, text=True, timeout=TIMEOUT_SECONDS + 60
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ModelError(f"claude-json did not run: {error}") from error
    if result.returncode != 0:
        raise ModelError(result.stderr.strip()[:500] or f"claude-json exited {result.returncode}")
    output: dict[str, Any] = json.loads(result.stdout)
    return output


def _one_line(text: str) -> str:
    flat = " ".join(text.replace("`", "'").split())
    return flat[:MAX_SUMMARY_CHARS]


def _check(raw: Any, items: dict[str, InboxItem], seen: set[str]) -> tuple[str, dict[str, Any]] | str:
    """The item key and cleaned fields of one raw proposal, or why it's unusable."""
    if not isinstance(raw, dict):
        return "proposal is not an object"
    key = raw.get("item")
    if key not in items:
        return f"unknown item {key!r}"
    if key in seen:
        return f"more than one proposal for {key}"
    summary = _one_line(str(raw.get("summary", "")))
    if not summary:
        return f"{key}: empty summary"
    action = raw.get("action")
    if action == "discard":
        return key, {"action": "discard", "summary": summary}
    if action != "file":
        return f"{key}: unknown action {action!r}"
    page = raw.get("page")
    content = raw.get("content")
    if not isinstance(page, str) or (problem := name_problem(page)):
        return f"{key}: bad page {page!r}: {problem if isinstance(page, str) else 'missing'}"
    if not isinstance(content, str) or not content.strip() or len(content) > MAX_CONTENT_CHARS:
        return f"{key}: content must be 1 to {MAX_CONTENT_CHARS} characters"
    return key, {"action": "file", "summary": summary, "page": page, "content": content.strip("\n") + "\n"}


def new_id(taken: Iterable[str]) -> str:
    taken = set(taken)
    while (candidate := secrets.token_hex(3)) in taken:
        pass
    return candidate


def to_proposals(
    output: dict[str, Any], items: dict[str, InboxItem], taken_ids: set[str]
) -> tuple[list[Proposal], list[str]]:
    """Proposals from the model's output, and a problem for each one that was unusable."""
    proposals: list[Proposal] = []
    problems: list[str] = []
    raw_list = output.get("proposals")
    if not isinstance(raw_list, list):
        return [], ["output has no proposals list"]
    seen: set[str] = set()
    for raw in raw_list:
        checked = _check(raw, items, seen)
        if isinstance(checked, str):
            problems.append(checked)
            continue
        key, fields = checked
        seen.add(key)
        item = items[key]
        proposal_id = new_id(taken_ids)
        taken_ids.add(proposal_id)
        proposals.append(Proposal(id=proposal_id, item=item.page, digest=item.digest, **fields))
    problems.extend(f"{key}: no proposal" for key in items if key not in seen)
    return proposals, problems


def propose(
    items: list[InboxItem], pages: list[str], model: Model, taken_ids: set[str], today: date
) -> tuple[list[Proposal], list[str]]:
    keyed = {f"i{n}": item for n, item in enumerate(items, start=1)}
    return to_proposals(model(build_prompt(keyed, pages, today)), keyed, taken_ids)
