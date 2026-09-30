import json
import subprocess
from datetime import date
from typing import Any

import pytest

from kd.propose import MAX_WHY_CHARS, SCHEMA, ModelError, build_prompt, propose, run_claude, to_proposals
from kd.vault import InboxItem, digest

ITEMS = {
    "i1": InboxItem("Inbox/one", "Debezium for CDC", digest("Debezium for CDC")),
    "i2": InboxItem("Inbox/two", "test", digest("test")),
}


def check(output: dict[str, Any]) -> tuple[list[Any], list[str]]:
    return to_proposals(output, ITEMS, set())


def test_valid_file_and_discard() -> None:
    proposals, problems = check(
        {
            "proposals": [
                {
                    "item": "i1",
                    "action": "file",
                    "summary": "CDC cue",
                    "page": "Cues/Change data capture",
                    "content": "Consider Debezium #cue",
                },
                {"item": "i2", "action": "discard", "summary": "a test"},
            ]
        }
    )
    assert problems == []
    first, second = proposals
    assert (first.item, first.page, first.content, first.digest) == (
        "Inbox/one",
        "Cues/Change data capture",
        "Consider Debezium #cue\n",
        ITEMS["i1"].digest,
    )
    assert (second.item, second.action, second.page) == ("Inbox/two", "discard", None)
    assert first.id != second.id


def test_unusable_proposals_are_reported_and_items_left_out() -> None:
    proposals, problems = check(
        {
            "proposals": [
                {"item": "i9", "action": "file", "summary": "s", "page": "P", "content": "c"},
                {"item": "i1", "action": "file", "summary": "s", "page": "Inbox/sneaky", "content": "c"},
                {"item": "i2", "action": "explode", "summary": "s"},
            ]
        }
    )
    assert proposals == []
    assert len(problems) == 5  # three bad entries, then i1 and i2 have no proposal


def test_only_the_first_proposal_per_item_counts() -> None:
    proposals, problems = check(
        {
            "proposals": [
                {"item": "i2", "action": "discard", "summary": "one"},
                {"item": "i2", "action": "discard", "summary": "two"},
            ]
        }
    )
    assert [p.summary for p in proposals] == ["one"]
    assert any("more than one" in p for p in problems)


def test_summary_is_flattened_to_one_line_without_backticks() -> None:
    proposals, _ = check(
        {"proposals": [{"item": "i2", "action": "discard", "summary": "a\n`kd:abcdef`\u2028b"}]}
    )
    assert proposals[0].summary == "a 'kd:abcdef' b"


def test_missing_proposals_list() -> None:
    assert check({"nope": []}) == ([], ["output has no proposals list"])


def test_prompt_lists_pages_and_keys() -> None:
    prompt = build_prompt(ITEMS, ["People/Ada"], date(2026, 9, 28))
    assert "- People/Ada" in prompt
    assert "### i1: Inbox/one" in prompt and "Debezium for CDC" in prompt
    assert "{items}" not in prompt and "{pages}" not in prompt and "{today}" not in prompt


def test_prompt_dates_queue_items_today() -> None:
    assert "[added: 2026-09-28]" in build_prompt(ITEMS, [], date(2026, 9, 28))


def fake_claude_json(monkeypatch: Any, returncode: int = 0, stdout: str = "", stderr: str = "") -> list[Any]:
    calls: list[Any] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append((cmd, kwargs))
        return subprocess.CompletedProcess(cmd, returncode, stdout=stdout, stderr=stderr)

    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls


def test_run_claude_asks_claude_json_with_the_schema_and_no_tools(monkeypatch: Any) -> None:
    calls = fake_claude_json(monkeypatch, stdout=json.dumps({"proposals": []}) + "\n")
    assert run_claude("the prompt") == {"proposals": []}
    cmd, kwargs = calls[0]
    assert cmd[0] == "claude-json"
    assert json.loads(cmd[cmd.index("--schema") + 1]) == SCHEMA
    assert "--tools" not in cmd
    assert kwargs["input"] == "the prompt"


def test_run_claude_raises_model_error_when_the_call_fails(monkeypatch: Any) -> None:
    fake_claude_json(monkeypatch, returncode=1, stderr="claude-json: claude exited 1: overloaded")
    with pytest.raises(ModelError, match="overloaded"):
        run_claude("the prompt")


def test_why_is_kept_flattened_and_capped() -> None:
    proposals, _ = check(
        {
            "proposals": [
                {
                    "item": "i1",
                    "action": "file",
                    "summary": "s",
                    "page": "P",
                    "content": "c",
                    "why": "a\n`b`",
                },
                {
                    "item": "i2",
                    "action": "file",
                    "summary": "s",
                    "page": "P",
                    "content": "c",
                    "why": "x" * 999,
                },
            ]
        }
    )
    assert proposals[0].why == "a 'b'"
    assert proposals[1].why == "x" * MAX_WHY_CHARS


def test_no_why_or_a_blank_one_is_none_and_discards_drop_it() -> None:
    proposals, _ = check(
        {
            "proposals": [
                {"item": "i1", "action": "file", "summary": "s", "page": "P", "content": "c", "why": "  "},
                {"item": "i2", "action": "discard", "summary": "s", "why": "because"},
            ]
        }
    )
    assert [p.why for p in proposals] == [None, None]


def test_prompt_puts_source_material_under_its_item() -> None:
    prompt = build_prompt(ITEMS, [], date(2026, 9, 28), {"i1": "Transcript around u:\n\n[0:05] hi"})
    one, two = prompt.split("### i2: ")
    assert "#### Source material for i1\n\nTranscript around u:\n\n[0:05] hi" in one
    assert "Source material" not in two


def test_propose_fetches_sources_for_the_items() -> None:
    url = "https://youtu.be/abc?t=90"
    items = [InboxItem("Inbox/v", f"Todo: try it\nSource: {url}", "d")]
    prompts: list[str] = []

    def model(prompt: str) -> dict[str, Any]:
        prompts.append(prompt)
        return {"proposals": []}

    propose(items, [], model, set(), date(2026, 9, 28), fetch=lambda u: f"[1:30] said at {u}")
    assert f"[1:30] said at {url}" in prompts[0]
