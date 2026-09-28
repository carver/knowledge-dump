"""Sparks sent to the knowledge-dump Destination, turned into Inbox pages.

tab-squasher's Inbox is read with its own reader, reader/inbox.py, which checks
every Spark against the spec. Which Sparks were already imported is tracked
in the vault's state (kd/state.py), not here.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from kd.pages import INBOX
from kd.triage import NewPage

DESTINATION = "knowledge-dump"
WORKSPACE = Path(__file__).resolve().parents[2]
REFRESH_MOUNT = WORKSPACE / "sandbox-setup" / "bin" / "refresh-mount"


def tab_squasher_dir() -> Path:
    return Path(os.environ.get("TAB_SQUASHER_DIR", WORKSPACE / "tab-squasher"))


def _reader() -> Any:
    reader = str(tab_squasher_dir() / "reader")
    if reader not in sys.path:
        sys.path.insert(0, reader)
    import inbox

    return inbox


def _is_youtube(host: str) -> bool:
    return host in ("youtu.be", "youtube.com") or host.endswith(".youtube.com")


def _at_moment(url: str, seconds: int) -> str:
    """`url` set to start playing at `seconds`, for sites whose links support it."""
    parts = urlsplit(url)
    if not _is_youtube(parts.hostname or ""):
        return url
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "t"]
    return urlunsplit(parts._replace(query=urlencode([*query, ("t", str(seconds))])))


def _source_line(source: dict[str, Any]) -> str:
    title = source.get("title") or source["url"]
    title = title.replace("[", "(").replace("]", ")")
    seconds = source.get("video_seconds")
    if seconds is None:
        return f"Source: [{title}]({source['url']})"
    minutes, secs = divmod(int(seconds), 60)
    return f"Source: [{title}]({_at_moment(source['url'], int(seconds))}) at {minutes}:{secs:02d}"


def page_for(spark: dict[str, Any]) -> NewPage:
    blocks = []
    if spark.get("note"):
        blocks.append(spark["note"])
    if spark.get("quote"):
        blocks.append("\n".join("> " + line for line in spark["quote"].splitlines()))
    blocks.append(_source_line(spark["source"]))
    day = spark["captured_at"][:10]
    name = f"{INBOX}/Spark {day} {spark['id'][:8]}"
    return NewPage(source_id=spark["id"], page=name, text="\n\n".join(blocks) + "\n")


def refresh_mount_view(inbox_dir: Path) -> None:
    """The Inbox is written on the host; drop the sandbox's stale view of it first."""
    if REFRESH_MOUNT.exists():
        subprocess.run([str(REFRESH_MOUNT), str(inbox_dir)], capture_output=True)


def new_spark_pages(done: set[str], inbox_dir: Path | None = None) -> tuple[list[NewPage], list[str]]:
    """Inbox pages for Sparks not in `done`, and a note for each Inbox line that isn't a Spark."""
    inbox_dir = inbox_dir or tab_squasher_dir() / "data" / "inbox"
    if not inbox_dir.is_dir():
        return [], []
    refresh_mount_view(inbox_dir)
    sparks, skipped = _reader().pending_sparks(str(inbox_dir), done, DESTINATION)
    return [page_for(spark) for spark in sparks], list(skipped)
