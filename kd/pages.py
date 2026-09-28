"""Page names and the files behind them.

A page is a markdown file in the vault. Its name is the file's path relative to
the vault without `.md`, which is how SilverBullet names pages.
"""

import re
from pathlib import Path

INBOX = "Inbox"
TRIAGE = "Triage"
# Lists the open #queue tasks from every page; the host creates it.
QUEUE = "Queue"
# SilverBullet keeps libraries and plugs here; they aren't notes.
LIBRARY = "Library"
STATE_DIR = ".kd"
MAX_NAME_LENGTH = 200

# Characters SilverBullet gives meaning to inside [[links]], control characters,
# and everything str.splitlines() breaks on, since the Triage page is parsed by line.
_FORBIDDEN = re.compile(r"[\[\]|#^\\\x00-\x1f\x7f\x85\u2028\u2029]")


def is_inbox_page(name: str) -> bool:
    return name.startswith(INBOX + "/")


def is_library_page(name: str) -> bool:
    return name == LIBRARY or name.startswith(LIBRARY + "/")


def linkable(name: str) -> bool:
    """Whether `[[name]]` survives as one link on one line of a page."""
    return _FORBIDDEN.search(name) is None


def name_problem(name: str) -> str | None:
    """Why `name` can't be a page to file into, or None."""
    if not name or len(name) > MAX_NAME_LENGTH:
        return f"page name must be 1 to {MAX_NAME_LENGTH} characters"
    if not linkable(name):
        return "page name has a character SilverBullet links can't hold"
    if name.lower().endswith(".md"):
        return "page name must not end in .md"
    for segment in name.split("/"):
        if segment != segment.strip() or not segment:
            return "page name has an empty or padded path segment"
        if segment.startswith("."):
            return "page name has a hidden path segment"
    if name in (INBOX, TRIAGE, QUEUE) or is_inbox_page(name) or is_library_page(name):
        return f"can't file into {INBOX}, {TRIAGE}, {QUEUE} or {LIBRARY}"
    return None


def page_path(vault: Path, name: str) -> Path:
    return vault / (name + ".md")


def page_name(vault: Path, path: Path) -> str:
    return path.relative_to(vault).with_suffix("").as_posix()


def is_hidden(vault: Path, path: Path) -> bool:
    return any(part.startswith(".") for part in path.relative_to(vault).parts)
