from pathlib import Path

import pytest
from test_triage import FakeModel, write

from kd import __main__ as kd_main
from kd import state as kd_state
from kd.preview import preview
from kd.triage import triage


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


def test_preview_reads_a_local_vault_with_uncommitted_edits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path, "Inbox/one", "not committed anywhere")
    model = FakeModel("Cues/X")
    monkeypatch.setattr(kd_main, "run_claude", model)
    assert kd_main.main(["preview", "--vault", str(tmp_path), "Inbox/one"]) == 0
    assert "Inbox/one -> Cues/X (about i1)" in capsys.readouterr().out
    assert model.calls == 1


def test_preview_rejects_a_vault_and_a_remote_together(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        kd_main.main(["preview", "--vault", str(tmp_path), "--remote", "git://x/notes"])


def test_compare_diffs_against_the_waiting_proposal(tmp_path: Path) -> None:
    write(tmp_path, "Inbox/one", "x")
    triage(tmp_path, FakeModel("Cues/X"), [])
    lines = preview(tmp_path, FakeModel("Cues/Y"), [], compare=True)
    assert lines[0] == "Inbox/one -> Cues/Y (about i1)"
    assert "--- current" in lines and "-> Cues/X" in [line[1:] for line in lines if line.startswith("-")]
    assert "+-> Cues/Y" in lines


def test_compare_says_when_nothing_changed(tmp_path: Path) -> None:
    write(tmp_path, "Inbox/one", "x")
    triage(tmp_path, FakeModel("Cues/X"), [])
    before = kd_state.load(tmp_path)
    assert preview(tmp_path, FakeModel("Cues/X"), [], compare=True)[1] == "(same as the current proposal)"
    assert kd_state.load(tmp_path) == before


def test_compare_marks_items_with_no_waiting_proposal(tmp_path: Path) -> None:
    write(tmp_path, "Inbox/one", "x")
    lines = preview(tmp_path, FakeModel("Cues/X"), [], compare=True)
    assert lines[1:4] == ["(no current proposal)", "-> Cues/X", "from i1"]
