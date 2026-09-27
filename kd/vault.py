"""Reading and changing pages in a checked-out vault."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from kd.pages import INBOX, is_hidden, is_library_page, page_name, page_path


@dataclass(frozen=True)
class InboxItem:
    page: str
    text: str
    digest: str


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _markdown_files(root: Path, vault: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(p for p in root.rglob("*.md") if p.is_file() and not is_hidden(vault, p))


def inbox_items(vault: Path) -> list[InboxItem]:
    items = []
    for path in _markdown_files(vault / INBOX, vault):
        text = path.read_text(encoding="utf-8", errors="replace")
        items.append(InboxItem(page_name(vault, path), text, digest(text)))
    return items


def content_pages(vault: Path) -> list[str]:
    """Every note outside the Inbox, for the model to pick filing targets from."""
    inbox = vault / INBOX
    names = (page_name(vault, p) for p in _markdown_files(vault, vault) if inbox not in p.parents)
    return [name for name in names if not is_library_page(name)]


def append_to_page(vault: Path, name: str, content: str) -> None:
    """Add `content` as a new block at the end of the page, creating it if needed."""
    path = page_path(vault, name)
    block = content.strip("\n") + "\n"
    existing = path.read_text(encoding="utf-8").rstrip("\n") if path.exists() else ""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(existing + "\n\n" + block if existing else block, encoding="utf-8")


def remove_inbox_page(vault: Path, name: str) -> None:
    """Delete an Inbox page and any folders under the Inbox it leaves empty."""
    path = page_path(vault, name)
    path.unlink(missing_ok=True)
    inbox = vault / INBOX
    parent = path.parent
    while parent != inbox and inbox in parent.parents and not any(parent.iterdir()):
        parent.rmdir()
        parent = parent.parent


def write_if_changed(path: Path, text: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True
