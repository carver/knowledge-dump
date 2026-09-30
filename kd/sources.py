"""Source material fetched for an Item before triage asks the model about it.

For now that's YouTube captions around a timestamped link, which is where the
argument that persuaded the user usually is. The model reads it to draft a
to-do's Why. When a source can't be fetched right now (YouTube is blocking
this IP, say), its Item is held back for a later run rather than proposed
without it.
"""

import re
import subprocess
from collections.abc import Callable

from kd.vault import InboxItem

MAX_LINKS = 3
TIMEOUT_SECONDS = 60
TRY_LATER = 3  # yt-transcript's exit status when YouTube refused the request
_TIMESTAMPED_YOUTUBE = re.compile(
    r"https?://(?:[\w-]+\.)?(?:youtube\.com|youtu\.be)/[^\s<>()\[\]]*[?&](?:t|start)=[^\s<>()\[\]]+"
)


class Unavailable(Exception):
    """The source can't be fetched now, but may be later."""


# Takes a URL, returns its excerpt, or None when it has none. Raises Unavailable to try later.
Fetch = Callable[[str], str | None]


def timestamped_youtube_links(text: str) -> list[str]:
    return list(dict.fromkeys(_TIMESTAMPED_YOUTUBE.findall(text)))[:MAX_LINKS]


def yt_transcript(url: str) -> str | None:
    """Captions around the link's timestamp, from llm-toolbox's yt-transcript."""
    try:
        result = subprocess.run(
            ["yt-transcript", url], capture_output=True, text=True, timeout=TIMEOUT_SECONDS
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        raise Unavailable(f"yt-transcript did not run: {e}") from e
    if result.returncode == TRY_LATER:
        lines = result.stderr.strip().splitlines()
        raise Unavailable(lines[0] if lines else "YouTube refused the request")
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def excerpts(text: str, fetch: Fetch = yt_transcript) -> str:
    """The source material for an Item's text, as prompt sections, or "" when there is none."""
    sections = []
    for url in timestamped_youtube_links(text):
        if found := fetch(url):
            sections.append(f"Transcript around {url}:\n\n{found}")
    return "\n\n".join(sections)


def gather(items: list[InboxItem], fetch: Fetch = yt_transcript) -> tuple[dict[str, str], dict[str, str]]:
    """Source material by Inbox page, and, for each page held back, why its source can't be fetched now."""
    found: dict[str, str] = {}
    held: dict[str, str] = {}
    for item in items:
        try:
            if text := excerpts(item.text, fetch):
                found[item.page] = text
        except Unavailable as e:
            held[item.page] = str(e)
    return found, held
