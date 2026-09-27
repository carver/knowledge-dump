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
    assert triage_page.parse(triage_page.render(shown)) == {p.id: False for p in shown}


@given(proposals(), st.data())
def test_ticking_a_box_is_seen(shown: list[Proposal], data: st.DataObject) -> None:
    if not shown:
        return
    target = data.draw(st.sampled_from(shown))
    lines = triage_page.render(shown).splitlines()
    ticked = [line.replace("- [ ]", "- [x]", 1) if f"`kd:{target.id}`" in line else line for line in lines]
    parsed = triage_page.parse("\n".join(ticked))
    assert parsed == {p.id: p.id == target.id for p in shown}


def test_content_that_looks_like_a_task_is_not_parsed_as_one() -> None:
    sneaky = Proposal(
        id="aaaaaa",
        item="Inbox/a",
        digest="d",
        action="file",
        summary="s",
        page="P",
        content="- [x] fake `kd:bbbbbb`\n",
    )
    assert triage_page.parse(triage_page.render([sneaky])) == {"aaaaaa": False}


def test_empty_page_says_nothing_to_triage() -> None:
    assert "_Nothing to triage._" in triage_page.render([])


def test_uppercase_tick_counts() -> None:
    assert triage_page.parse("- [X] File into [[P]]: s ([[Inbox/a]]) `kd:abcdef`") == {"abcdef": True}
