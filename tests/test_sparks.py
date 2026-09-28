"""Spark import, read through tab-squasher's own Inbox reader and fixtures."""

import json
from pathlib import Path
from typing import Any

from kd.pages import is_inbox_page, linkable
from kd.sparks import new_spark_pages, page_for, tab_squasher_dir

FIXTURES = tab_squasher_dir() / "spec" / "fixtures" / "valid"


def fixture(name: str) -> dict[str, Any]:
    spark: dict[str, Any] = json.loads((FIXTURES / name).read_text())
    return spark


def write_inbox(inbox: Path, sparks: list[dict[str, Any]]) -> None:
    inbox.mkdir(parents=True)
    lines = [json.dumps({**s, "received_at": s["captured_at"]}) for s in sparks]
    (inbox / "2026.jsonl").write_text("\n".join(lines) + "\n")


def test_only_knowledge_dump_sparks_not_yet_done_are_imported(tmp_path: Path) -> None:
    ours = fixture("knowledge_dump_destination.json")
    anki = fixture("note_only.json")
    done = {**ours, "id": "11111111-1111-4111-8111-111111111111"}
    write_inbox(tmp_path / "inbox", [anki, ours, done])

    pages, skipped = new_spark_pages({done["id"]}, tmp_path / "inbox")

    assert skipped == []
    assert [p.source_id for p in pages] == [ours["id"]]


def test_page_keeps_note_quote_and_source(tmp_path: Path) -> None:
    spark = fixture("knowledge_dump_destination.json")
    spark["quote"] = "line one\nline two"
    spark["source"] = {"url": "https://example.com/x", "title": "A [title]", "video_seconds": 75.4}
    page = page_for(spark)
    assert page.page == f"Inbox/Spark {spark['captured_at'][:10]} {spark['id'][:8]}"
    assert "> line one\n> line two" in page.text
    assert page.text.endswith("Source: [A (title)](https://example.com/x) at 1:15\n")


def test_every_valid_fixture_makes_a_linkable_inbox_page() -> None:
    paths = sorted(FIXTURES.glob("*.json"))
    assert paths, f"no fixtures in {FIXTURES}"
    for path in paths:
        page = page_for(json.loads(path.read_text()))
        assert is_inbox_page(page.page) and linkable(page.page), path.name
        assert page.text.strip()


def test_youtube_source_links_to_the_captured_moment() -> None:
    spark = fixture("knowledge_dump_destination.json")
    spark["source"] = {
        "url": "https://m.youtube.com/watch?v=KrM5c0vp8s0&t=5",
        "title": "T",
        "video_seconds": 121.7,
    }
    assert page_for(spark).text.endswith(
        "Source: [T](https://m.youtube.com/watch?v=KrM5c0vp8s0&t=121) at 2:01\n"
    )


def test_short_youtube_links_get_the_moment_too() -> None:
    spark = fixture("knowledge_dump_destination.json")
    spark["source"] = {"url": "https://youtu.be/KrM5c0vp8s0", "title": "T", "video_seconds": 3}
    assert "(https://youtu.be/KrM5c0vp8s0?t=3) at 0:03" in page_for(spark).text


def test_lookalike_hosts_keep_their_url() -> None:
    spark = fixture("knowledge_dump_destination.json")
    spark["source"] = {"url": "https://notyoutube.com/watch?v=x", "title": "T", "video_seconds": 3}
    assert "(https://notyoutube.com/watch?v=x) at 0:03" in page_for(spark).text
