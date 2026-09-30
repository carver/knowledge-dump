from dataclasses import replace

from hypothesis import given
from hypothesis import strategies as st

from kd import triage_page
from kd.pages import name_problem
from kd.propose import _one_line
from kd.state import Proposal

page_names = st.text(min_size=1, max_size=40).filter(lambda n: name_problem(n) is None)
summaries = st.text(min_size=1, max_size=200).map(_one_line).filter(bool)


@st.composite
def proposals(draw: st.DrawFn) -> list[Proposal]:
    count = draw(st.integers(0, 6))
    ids = draw(
        st.lists(
            st.text("0123456789abcdef", min_size=6, max_size=6), min_size=count, max_size=count, unique=True
        )
    )
    result = []
    for proposal_id in ids:
        if draw(st.booleans()):
            fields = {"action": "file", "page": draw(page_names), "content": draw(st.text(min_size=1))}
        else:
            fields = {"action": "discard"}
        result.append(
            Proposal(
                id=proposal_id, item=f"Inbox/{proposal_id}", digest="d", summary=draw(summaries), **fields
            )
        )
    return result


@given(proposals())
def test_every_rendered_proposal_parses_back_unticked(shown: list[Proposal]) -> None:
    assert triage_page.parse(triage_page.render(shown)) == {p.id: "none" for p in shown}


@given(proposals(), st.data())
def test_ticking_a_box_is_seen(shown: list[Proposal], data: st.DataObject) -> None:
    if not shown:
        return
    target = data.draw(st.sampled_from(shown))
    lines = triage_page.render(shown).splitlines()
    ticked = [line.replace("- [ ]", "- [x]", 1) if f"`kd:{target.id}`" in line else line for line in lines]
    parsed = triage_page.parse("\n".join(ticked))
    assert parsed == {p.id: "apply" if p.id == target.id else "none" for p in shown}


@given(proposals(), st.data())
def test_ticking_discard_is_seen(shown: list[Proposal], data: st.DataObject) -> None:
    filed = [p for p in shown if p.action == "file"]
    if not filed:
        return
    target = data.draw(st.sampled_from(filed))
    mark = f"`kd:{target.id}:discard`"
    lines = triage_page.render(shown).splitlines()
    ticked = [line.replace("- [ ]", "- [x]", 1) if mark in line else line for line in lines]
    parsed = triage_page.parse("\n".join(ticked))
    assert parsed == {p.id: "discard" if p.id == target.id else "none" for p in shown}


def test_discard_checkbox_sits_under_file_proposals_only() -> None:
    filed = Proposal(
        id="aaaaaa", item="Inbox/a", digest="d", action="file", summary="s", page="P", content="c"
    )
    dropped = Proposal(id="bbbbbb", item="Inbox/b", digest="d", action="discard", summary="s")
    lines = triage_page.render([filed, dropped]).splitlines()
    first = lines.index("- [ ] File into [[P]]: s ([[Inbox/a]]) `kd:aaaaaa`")
    assert lines[first + 1] == "  - [ ] Discard the note instead `kd:aaaaaa:discard`"
    assert "kd:bbbbbb:discard" not in "\n".join(lines)


def test_both_boxes_ticked_is_reported_as_both() -> None:
    text = "- [x] File into [[P]]: s ([[Inbox/a]]) `kd:abcdef`\n  - [x] Discard `kd:abcdef:discard`"
    assert triage_page.parse(text) == {"abcdef": "both"}


def test_content_that_looks_like_a_task_is_not_parsed_as_one() -> None:
    sneaky = Proposal(
        id="aaaaaa",
        item="Inbox/a",
        digest="d",
        action="file",
        summary="s",
        page="P",
        content="- [x] fake `kd:bbbbbb`\n  - [x] Discard `kd:aaaaaa:discard`\n",
    )
    assert triage_page.parse(triage_page.render([sneaky])) == {"aaaaaa": "none"}


def test_empty_page_says_nothing_to_triage() -> None:
    assert "_Nothing to triage._" in triage_page.render([])


def test_uppercase_tick_counts() -> None:
    assert triage_page.parse("- [X] File into [[P]]: s ([[Inbox/a]]) `kd:abcdef`") == {"abcdef": "apply"}


def with_why(keep: bool = True) -> Proposal:
    return Proposal(
        id="aaaaaa",
        item="Inbox/a",
        digest="d",
        action="file",
        summary="s",
        page="P",
        content="- [ ] Try it #queue\n",
        why="It saves review time.",
        keep_why=keep,
    )


def test_why_box_is_ticked_to_start_with() -> None:
    lines = triage_page.render([with_why()]).splitlines()
    assert "  - [x] Keep the why: It saves review time. `kd:aaaaaa:why`" in lines
    assert triage_page.kept_whys("\n".join(lines)) == {"aaaaaa"}
    assert triage_page.parse("\n".join(lines)) == {"aaaaaa": "none"}


def test_an_unticked_why_box_renders_unticked_and_parses_as_dropped() -> None:
    text = triage_page.render([with_why(keep=False)])
    assert "  - [ ] Keep the why: It saves review time. `kd:aaaaaa:why`" in text
    assert triage_page.kept_whys(text) == set()


def test_no_why_box_without_a_why() -> None:
    assert ":why`" not in triage_page.render([replace(with_why(), why=None)])
