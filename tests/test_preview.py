from pathlib import Path

from test_triage import FakeModel, write

from kd.preview import preview


def test_preview_shows_proposals_for_named_items_and_writes_nothing(tmp_path: Path) -> None:
    write(tmp_path, "Inbox/one", "x")
    write(tmp_path, "Inbox/two", "y")
    before = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*"))
    lines = preview(tmp_path, FakeModel("Cues/X"), ["Inbox/two"])
    assert lines == ["Inbox/two -> Cues/X (about i1)", "from i1", ""]
    assert sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*")) == before


def test_preview_defaults_to_every_item(tmp_path: Path) -> None:
    write(tmp_path, "Inbox/one", "x")
    write(tmp_path, "Inbox/two", "y")
    lines = preview(tmp_path, FakeModel(), [])
    assert [line for line in lines if " -> " in line] == [
        "Inbox/one -> Cues/Change data capture (about i1)",
        "Inbox/two -> Cues/Change data capture (about i2)",
    ]


def test_preview_reports_unknown_items_and_discards(tmp_path: Path) -> None:
    write(tmp_path, "Inbox/junk", "test")

    def discard(prompt: str) -> dict[str, object]:
        return {"proposals": [{"item": "i1", "action": "discard", "summary": "a test"}]}

    assert preview(tmp_path, discard, ["Inbox/nope"]) == ["problem: no Inbox page 'Inbox/nope'"]
    assert preview(tmp_path, discard, []) == ["Inbox/junk -> discard (a test)", ""]


def test_empty_inbox_skips_the_model(tmp_path: Path) -> None:
    model = FakeModel()
    assert preview(tmp_path, model, []) == ["the Inbox is empty"]
    assert model.calls == 0
