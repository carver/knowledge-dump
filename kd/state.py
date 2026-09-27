"""What the triage agent remembers between runs, kept in the vault at .kd/state.json.

Only the triage agent writes this file, so it never has two writers.
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from kd.pages import STATE_DIR

Action = Literal["file", "discard"]
STATE_FILE = "state.json"


@dataclass(frozen=True)
class Proposal:
    """A suggestion for one Inbox item, waiting on the Triage page for a tick."""

    id: str
    item: str
    digest: str
    action: Action
    summary: str
    page: str | None = None
    content: str | None = None


@dataclass
class State:
    proposals: list[Proposal] = field(default_factory=list)
    # Inbox page -> digest of its text, for items left in the Inbox: the user turned
    # the proposal down, or the model had nothing usable. They're proposed again
    # only once their text changes.
    parked: dict[str, str] = field(default_factory=dict)
    imported_sparks: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        data = {
            "proposals": [asdict(p) for p in self.proposals],
            "parked": dict(sorted(self.parked.items())),
            "imported_sparks": self.imported_sparks,
        }
        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    @classmethod
    def from_json(cls, text: str) -> "State":
        data: dict[str, Any] = json.loads(text)
        return cls(
            proposals=[Proposal(**p) for p in data.get("proposals", [])],
            parked=dict(data.get("parked", {})),
            imported_sparks=list(data.get("imported_sparks", [])),
        )


def state_path(vault: Path) -> Path:
    return vault / STATE_DIR / STATE_FILE


def load(vault: Path) -> State:
    path = state_path(vault)
    return State.from_json(path.read_text(encoding="utf-8")) if path.exists() else State()
