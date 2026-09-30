import subprocess
from typing import Any

import pytest

from kd import sources
from kd.sources import Unavailable, excerpts, gather, timestamped_youtube_links
from kd.vault import InboxItem

VIDEO = "https://m.youtube.com/watch?v=LlgiOCmFG_w&t=1238"


def test_finds_timestamped_youtube_links_in_markdown() -> None:
    text = f"Todo: install retro\n\nSource: [Fixing the PR Bottleneck]({VIDEO}) at 20:38\nAgain: {VIDEO}"
    assert timestamped_youtube_links(text) == [VIDEO]


def test_skips_links_without_a_timestamp_and_other_sites() -> None:
    text = "https://www.youtube.com/watch?v=LlgiOCmFG_w https://example.com/watch?v=x&t=5 https://youtu.be/abc?t=90"
    assert timestamped_youtube_links(text) == ["https://youtu.be/abc?t=90"]


def test_excerpts_label_each_link_and_skip_empty_fetches() -> None:
    text = f"{VIDEO} https://youtu.be/abc?t=90"
    fetched = excerpts(text, lambda url: "[20:38] review the system" if url == VIDEO else None)
    assert fetched == f"Transcript around {VIDEO}:\n\n[20:38] review the system"


def test_no_links_means_no_excerpts() -> None:
    assert excerpts("Todo: take out the trash", lambda url: "never called") == ""


def test_yt_transcript_failure_gives_none(monkeypatch: Any) -> None:
    def fail(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="no transcript")

    monkeypatch.setattr(subprocess, "run", fail)
    assert sources.yt_transcript(VIDEO) is None


def test_yt_transcript_missing_is_unavailable(monkeypatch: Any) -> None:
    def missing(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError(cmd[0])

    monkeypatch.setattr(subprocess, "run", missing)
    with pytest.raises(Unavailable, match="did not run"):
        sources.yt_transcript(VIDEO)


def test_yt_transcript_try_later_is_unavailable(monkeypatch: Any) -> None:
    def blocked(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            cmd, 3, stdout="", stderr="yt-transcript: try later: IpBlocked\nmore"
        )

    monkeypatch.setattr(subprocess, "run", blocked)
    with pytest.raises(Unavailable, match=r"^yt-transcript: try later: IpBlocked$"):
        sources.yt_transcript(VIDEO)


def test_gather_holds_back_only_the_items_it_cant_fetch_now() -> None:
    def fetch(url: str) -> str | None:
        if "blocked" in url:
            raise Unavailable("IpBlocked")
        return f"said at {url}"

    items = [
        InboxItem("Inbox/ok", f"Todo: a\n{VIDEO}", "d"),
        InboxItem("Inbox/held", "Todo: b\nhttps://youtu.be/blocked00?t=5", "d"),
        InboxItem("Inbox/plain", "Todo: take out the trash", "d"),
    ]
    found, held = gather(items, fetch)
    assert found == {"Inbox/ok": f"Transcript around {VIDEO}:\n\nsaid at {VIDEO}"}
    assert held == {"Inbox/held": "IpBlocked"}
