from typing import Any

from kd.propose import build_prompt, to_proposals
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
    prompt = build_prompt(ITEMS, ["People/Ada"])
    assert "- People/Ada" in prompt
    assert "### i1: Inbox/one" in prompt and "Debezium for CDC" in prompt
    assert "{items}" not in prompt and "{pages}" not in prompt
