import re
from pathlib import Path
from typing import Any

import pytest

from kd import state as kd_state
from kd.propose import ModelError
from kd.triage import NewPage, triage, with_why


class FakeModel:
    """Files every item it's shown into `page`, and counts calls."""

    def __init__(self, page: str = "Cues/Change data capture") -> None:
        self.page = page
        self.calls = 0

    def __call__(self, prompt: str) -> dict[str, Any]:
        self.calls += 1
        keys = re.findall(r"^### (i\d+): ", prompt, flags=re.MULTILINE)
        return {
            "proposals": [
                {
                    "item": k,
                    "action": "file",
                    "summary": f"about {k}",
                    "page": self.page,
                    "content": f"from {k}",
                }
                for k in keys
            ]
        }


def write(vault: Path, name: str, text: str) -> None:
    path = vault / (name + ".md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def triage_text(vault: Path) -> str:
    return (vault / "Triage.md").read_text()


def tick(vault: Path, mark: str) -> None:
    """Tick the box whose line ends in `mark`, a proposal id or `<id>:discard`."""
    text = triage_text(vault)
    lines = [
        line.replace("- [ ]", "- [x]") if line.endswith(f"`kd:{mark}`") else line
        for line in text.splitlines()
    ]
    (vault / "Triage.md").write_text("\n".join(lines) + "\n")


def delete_line(vault: Path, proposal_id: str) -> None:
    lines = [line for line in triage_text(vault).splitlines() if f"kd:{proposal_id}" not in line]
    (vault / "Triage.md").write_text("\n".join(lines) + "\n")


def only_proposal(vault: Path) -> kd_state.Proposal:
    (proposal,) = kd_state.load(vault).proposals
    return proposal


def test_new_item_gets_a_proposal_on_the_triage_page(tmp_path: Path) -> None:
    write(tmp_path, "Inbox/2026-09-26/one", "Debezium for CDC")
    model = FakeModel()
    report = triage(tmp_path, model, [])
    proposal = only_proposal(tmp_path)
    assert report.proposed == ["Inbox/2026-09-26/one"]
    target, item = "[[Cues/Change data capture]]", "[[Inbox/2026-09-26/one]]"
    line = f"- [ ] File into {target}: about i1 ({item}) `kd:{proposal.id}`"
    assert line in triage_text(tmp_path)


def test_ticked_proposal_is_applied_and_the_item_removed(tmp_path: Path) -> None:
    write(tmp_path, "Inbox/2026-09-26/one", "Debezium for CDC")
    write(tmp_path, "Cues/Change data capture", "# CDC\n")
    triage(tmp_path, FakeModel(), [])
    tick(tmp_path, only_proposal(tmp_path).id)
    model = FakeModel()
    report = triage(tmp_path, model, [])
    assert report.applied == ["Inbox/2026-09-26/one -> Cues/Change data capture"]
    assert (tmp_path / "Cues/Change data capture.md").read_text() == "# CDC\n\nfrom i1\n"
    assert list((tmp_path / "Inbox").iterdir()) == []  # the emptied day folder goes too
    assert model.calls == 0
    assert "_Nothing to triage._" in triage_text(tmp_path)


def test_untouched_proposal_waits_without_calling_the_model_again(tmp_path: Path) -> None:
    write(tmp_path, "Inbox/one", "x")
    triage(tmp_path, FakeModel(), [])
    before = triage_text(tmp_path)
    model = FakeModel()
    triage(tmp_path, model, [])
    assert model.calls == 0
    assert triage_text(tmp_path) == before


def test_deleted_proposal_parks_the_item_until_it_changes(tmp_path: Path) -> None:
    write(tmp_path, "Inbox/one", "x")
    triage(tmp_path, FakeModel(), [])
    delete_line(tmp_path, only_proposal(tmp_path).id)
    model = FakeModel()
    report = triage(tmp_path, model, [])
    assert report.parked == ["Inbox/one"]
    assert model.calls == 0
    assert (tmp_path / "Inbox/one.md").exists()

    write(tmp_path, "Inbox/one", "x, edited")
    triage(tmp_path, model, [])
    assert model.calls == 1
    assert only_proposal(tmp_path).item == "Inbox/one"


def test_edited_item_is_proposed_again_even_if_ticked(tmp_path: Path) -> None:
    write(tmp_path, "Inbox/one", "x")
    triage(tmp_path, FakeModel(), [])
    first = only_proposal(tmp_path)
    tick(tmp_path, first.id)
    write(tmp_path, "Inbox/one", "x, edited")
    report = triage(tmp_path, FakeModel(), [])
    assert report.dropped == ["Inbox/one"] and report.applied == []
    assert only_proposal(tmp_path).id != first.id


def test_missing_triage_page_keeps_proposals(tmp_path: Path) -> None:
    write(tmp_path, "Inbox/one", "x")
    triage(tmp_path, FakeModel(), [])
    (tmp_path / "Triage.md").unlink()
    report = triage(tmp_path, FakeModel(), [])
    assert report.parked == []
    assert len(kd_state.load(tmp_path).proposals) == 1


def test_discard_removes_the_item(tmp_path: Path) -> None:
    write(tmp_path, "Inbox/junk", "test")

    def discard(prompt: str) -> dict[str, Any]:
        return {"proposals": [{"item": "i1", "action": "discard", "summary": "a test"}]}

    triage(tmp_path, discard, [])
    tick(tmp_path, only_proposal(tmp_path).id)
    triage(tmp_path, None, [])
    assert not (tmp_path / "Inbox/junk.md").exists()


def test_discard_tick_removes_the_item_without_filing_it(tmp_path: Path) -> None:
    write(tmp_path, "Inbox/one", "x")
    triage(tmp_path, FakeModel(), [])
    tick(tmp_path, f"{only_proposal(tmp_path).id}:discard")
    report = triage(tmp_path, None, [])
    assert report.applied == ["Inbox/one -> discarded"]
    assert not (tmp_path / "Inbox/one.md").exists()
    assert not (tmp_path / "Cues/Change data capture.md").exists()


def test_both_boxes_ticked_does_neither_and_asks_again(tmp_path: Path) -> None:
    write(tmp_path, "Inbox/one", "x")
    triage(tmp_path, FakeModel(), [])
    proposal = only_proposal(tmp_path)
    tick(tmp_path, proposal.id)
    tick(tmp_path, f"{proposal.id}:discard")
    report = triage(tmp_path, None, [])
    assert report.applied == [] and report.problems
    assert (tmp_path / "Inbox/one.md").exists()
    assert only_proposal(tmp_path) == proposal
    assert "- [x]" not in triage_text(tmp_path)


def test_model_failure_is_retried_next_run(tmp_path: Path) -> None:
    write(tmp_path, "Inbox/one", "x")

    def broken(prompt: str) -> dict[str, Any]:
        raise ModelError("offline")

    report = triage(tmp_path, broken, [])
    assert report.problems and kd_state.load(tmp_path).parked == {}
    model = FakeModel()
    triage(tmp_path, model, [])
    assert model.calls == 1


def test_items_the_model_skips_are_parked(tmp_path: Path) -> None:
    write(tmp_path, "Inbox/one", "x")
    triage(tmp_path, lambda prompt: {"proposals": []}, [])
    model = FakeModel()
    triage(tmp_path, model, [])
    assert model.calls == 0


def test_spark_pages_are_imported_once(tmp_path: Path) -> None:
    spark = NewPage(source_id="s1", page="Inbox/Spark 2026-09-24 3f0c1d9e", text="Debezium\n")
    report = triage(tmp_path, None, [spark])
    assert report.imported == ["Inbox/Spark 2026-09-24 3f0c1d9e"]
    (tmp_path / "Inbox/Spark 2026-09-24 3f0c1d9e.md").unlink()
    assert triage(tmp_path, None, [spark]).imported == []
    assert kd_state.load(tmp_path).imported_sparks == ["s1"]


def test_imported_page_never_overwrites(tmp_path: Path) -> None:
    write(tmp_path, "Inbox/Spark x", "mine")
    triage(tmp_path, None, [NewPage("s1", "Inbox/Spark x", "spark")])
    assert (tmp_path / "Inbox/Spark x.md").read_text() == "mine"
    assert (tmp_path / "Inbox/Spark x (2).md").read_text() == "spark"


@pytest.mark.parametrize("hidden", [".kd/notes", "Inbox/.trash/x"])
def test_hidden_files_are_not_items(tmp_path: Path, hidden: str) -> None:
    write(tmp_path, hidden, "x")
    model = FakeModel()
    triage(tmp_path, model, [])
    assert model.calls == 0


def test_repropose_by_id_replaces_the_proposal(tmp_path: Path) -> None:
    write(tmp_path, "Inbox/one", "x")
    triage(tmp_path, FakeModel(), [])
    old = only_proposal(tmp_path)
    report = triage(tmp_path, FakeModel("Better/page"), [], repropose=frozenset({old.id}))
    new = only_proposal(tmp_path)
    assert report.withdrawn == ["Inbox/one"]
    assert new.id != old.id and new.page == "Better/page"
    assert f"kd:{old.id}" not in triage_text(tmp_path)


def test_repropose_by_name_unparks_the_item(tmp_path: Path) -> None:
    write(tmp_path, "Inbox/one", "x")
    triage(tmp_path, lambda prompt: {"proposals": []}, [])
    model = FakeModel()
    report = triage(tmp_path, model, [], repropose=frozenset({"Inbox/one"}))
    assert report.withdrawn == ["Inbox/one"]
    assert model.calls == 1 and only_proposal(tmp_path).item == "Inbox/one"


def test_repropose_of_something_unknown_is_a_problem(tmp_path: Path) -> None:
    report = triage(tmp_path, FakeModel(), [], repropose=frozenset({"abc123"}))
    assert report.problems == ["nothing to repropose for 'abc123'"]


class WhyModel:
    """Files every item as a to-do with a Why."""

    def __call__(self, prompt: str) -> dict[str, Any]:
        keys = re.findall(r"^### (i\d+): ", prompt, flags=re.MULTILINE)
        return {
            "proposals": [
                {
                    "item": k,
                    "action": "file",
                    "summary": "a to-do",
                    "page": "AI coding workflow",
                    "content": "- [ ] Install retro #queue\n  Source: [v](https://youtu.be/x)\n",
                    "why": "A comment written twice means the process is wrong.",
                }
                for k in keys
            ]
        }


def untick(vault: Path, mark: str) -> None:
    text = triage_text(vault)
    lines = [
        line.replace("- [x]", "- [ ]") if line.endswith(f"`kd:{mark}`") else line
        for line in text.splitlines()
    ]
    (vault / "Triage.md").write_text("\n".join(lines) + "\n")


def filed_page(vault: Path) -> str:
    return (vault / "AI coding workflow.md").read_text()


def test_with_why_nests_under_a_task_and_follows_a_plain_line() -> None:
    assert with_why("- [ ] Do it #queue\n  Source: s\n", "Because.") == (
        "- [ ] Do it #queue\n  Why: Because.\n  Source: s\n"
    )
    assert with_why("Plain note\n", "Because.") == "Plain note\nWhy: Because.\n"


def test_a_kept_why_is_filed_under_the_task(tmp_path: Path) -> None:
    write(tmp_path, "Inbox/todo", "Todo: install retro")
    triage(tmp_path, WhyModel(), [])
    proposal = only_proposal(tmp_path)
    assert f"  - [x] Keep the why: {proposal.why} `kd:{proposal.id}:why`" in triage_text(tmp_path)
    tick(tmp_path, proposal.id)
    triage(tmp_path, WhyModel(), [])
    assert (
        "- [ ] Install retro #queue\n  Why: A comment written twice means the process is wrong.\n  Source:"
        in (filed_page(tmp_path))
    )


def test_an_unticked_why_is_left_out_and_stays_unticked(tmp_path: Path) -> None:
    write(tmp_path, "Inbox/todo", "Todo: install retro")
    triage(tmp_path, WhyModel(), [])
    proposal_id = only_proposal(tmp_path).id
    untick(tmp_path, f"{proposal_id}:why")
    triage(tmp_path, WhyModel(), [])
    assert "  - [ ] Keep the why: " in triage_text(tmp_path)
    tick(tmp_path, proposal_id)
    triage(tmp_path, WhyModel(), [])
    assert "Why:" not in filed_page(tmp_path)


def test_deleting_the_why_line_drops_the_why(tmp_path: Path) -> None:
    write(tmp_path, "Inbox/todo", "Todo: install retro")
    triage(tmp_path, WhyModel(), [])
    proposal_id = only_proposal(tmp_path).id
    lines = [
        line for line in triage_text(tmp_path).splitlines() if not line.endswith(f"`kd:{proposal_id}:why`")
    ]
    (tmp_path / "Triage.md").write_text("\n".join(lines) + "\n")
    tick(tmp_path, proposal_id)
    triage(tmp_path, WhyModel(), [])
    assert "Why:" not in filed_page(tmp_path)
