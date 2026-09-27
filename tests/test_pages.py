from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from kd.pages import name_problem, page_name, page_path

VAULT = Path("/vault")


@pytest.mark.parametrize(
    "name",
    ["Cues/Change data capture", "People/Ada Lovelace", "Debezium", "a/b/c", "Ünïcode page"],
)
def test_accepts_ordinary_names(name: str) -> None:
    assert name_problem(name) is None


@pytest.mark.parametrize(
    "name",
    [
        "",
        "Inbox",
        "Inbox/x",
        "Triage",
        "Library/Std/Config",
        "../escape",
        "a/../b",
        "a//b",
        ".kd/state",
        "a/.hidden",
        " padded",
        "trailing/ ",
        "page.md",
        "link]]break",
        "pipe|x",
        "tag#x",
        "back\\slash",
        "new\nline",
        "x" * 201,
    ],
)
def test_rejects_unsafe_names(name: str) -> None:
    assert name_problem(name) is not None


@given(st.text(min_size=1, max_size=80))
def test_any_accepted_name_stays_inside_the_vault_and_round_trips(name: str) -> None:
    if name_problem(name) is not None:
        return
    path = page_path(VAULT, name)
    assert VAULT in path.parents
    assert ".." not in path.relative_to(VAULT).parts
    assert page_name(VAULT, path) == name
