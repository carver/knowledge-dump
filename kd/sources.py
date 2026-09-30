"""Source material fetched for an Item before triage asks the model about it.

For now that's YouTube captions around a timestamped link, which is where the
argument that persuaded the user usually is. The model reads it to draft a
to-do's Why.
"""

import re
import subprocess
from collections.abc import Callable

MAX_LINKS = 3
TIMEOUT_SECONDS = 60
_TIMESTAMPED_YOUTUBE = re.compile(
    r"https?://(?:[\w-]+\.)?(?:youtube\.com|youtu\.be)/[^\s<>()\[\]]*[?&](?:t|start)=[^\s<>()\[\]]+"
)

# Takes a URL, returns its excerpt, or None when there's nothing to show.
Fetch = Callable[[str], str | None]


def timestamped_youtube_links(text: str) -> list[str]:
    return list(dict.fromkeys(_TIMESTAMPED_YOUTUBE.findall(text)))[:MAX_LINKS]


def yt_transcript(url: str) -> str | None:
    """Captions around the link's timestamp, from llm-toolbox's yt-transcript."""
    try:
        result = subprocess.run(
            ["yt-transcript", url], capture_output=True, text=True, timeout=TIMEOUT_SECONDS
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
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
