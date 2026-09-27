"""The whole loop against a real git daemon with the host's hooks installed."""

import socket
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import kd_host
import pytest
from test_triage import FakeModel, tick

from kd import state as kd_state
from kd.gitsync import VaultClone
from kd.run import run
from kd.triage import NewPage

HOST_SCRIPT = Path(kd_host.__file__)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port: int = s.getsockname()[1]
        return port


@pytest.fixture
def host_vault(tmp_path: Path) -> Iterator[tuple[Path, str]]:
    vault = tmp_path / "host" / "notes"
    subprocess.run([sys.executable, str(HOST_SCRIPT), "init", str(vault)], check=True)
    port = free_port()
    daemon = subprocess.Popen(kd_host.git_daemon_command(vault, port), stderr=subprocess.DEVNULL)
    url = f"git://127.0.0.1:{port}/notes"
    for _ in range(50):
        if subprocess.run(["git", "ls-remote", url], capture_output=True).returncode == 0:
            break
        time.sleep(0.1)
    yield vault, url
    daemon.terminate()
    daemon.wait()


def no_sparks(done: set[str]) -> tuple[list[NewPage], list[str]]:
    return [], []


def host_log(vault: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(vault), "log", "--format=%s"], capture_output=True, text=True
    ).stdout


def test_proposal_reaches_the_host_and_a_tick_there_gets_applied(
    host_vault: tuple[Path, str], tmp_path: Path
) -> None:
    vault, url = host_vault
    (vault / "Inbox").mkdir()
    (vault / "Inbox" / "one.md").write_text("Debezium for CDC")  # typed in SilverBullet
    kd_host.autocommit(vault)  # the timer's job
    clone = VaultClone(tmp_path / "sandbox" / "vault", url)
    logs: list[str] = []

    assert run(clone, FakeModel(), no_sparks, logs.append)
    assert "Triage: 1 proposed" in host_log(vault)
    assert "`kd:" in (vault / "Triage.md").read_text()

    tick(vault, kd_state.load(vault).proposals[0].id)  # ticked in SilverBullet
    kd_host.autocommit(vault)
    assert run(clone, FakeModel(), no_sparks, logs.append)
    assert (vault / "Cues" / "Change data capture.md").read_text() == "from i1\n"
    assert not (vault / "Inbox" / "one.md").exists()
    status = subprocess.run(
        ["git", "-C", str(vault), "status", "--porcelain"], capture_output=True, text=True
    )
    assert status.stdout == ""


class EditWhileThinking(FakeModel):
    """Runs `edit` on the host, as the user would in SilverBullet, during the first model call."""

    def __init__(self, edit: Callable[[], None]) -> None:
        super().__init__()
        self.edit = edit

    def __call__(self, prompt: str) -> dict[str, Any]:
        if self.calls == 0:
            self.edit()
        return super().__call__(prompt)


def untick(vault: Path, proposal_id: str) -> None:
    text = (vault / "Triage.md").read_text()
    lines = [
        line.replace("- [x]", "- [ ]") if f"kd:{proposal_id}" in line else line for line in text.splitlines()
    ]
    (vault / "Triage.md").write_text("\n".join(lines) + "\n")


def one_proposal_waiting(vault: Path, url: str, tmp_path: Path) -> tuple[VaultClone, str]:
    (vault / "Inbox").mkdir()
    (vault / "Inbox" / "one.md").write_text("first")
    kd_host.autocommit(vault)
    clone = VaultClone(tmp_path / "sandbox" / "vault", url)
    assert run(clone, FakeModel(), no_sparks, print)
    (vault / "Inbox" / "two.md").write_text("second")
    return clone, kd_state.load(vault).proposals[0].id


def test_tick_made_during_a_run_survives_the_merge(host_vault: tuple[Path, str], tmp_path: Path) -> None:
    vault, url = host_vault
    clone, first_id = one_proposal_waiting(vault, url, tmp_path)
    kd_host.autocommit(vault)

    assert run(clone, EditWhileThinking(lambda: tick(vault, first_id)), no_sparks, print)
    assert (
        f"- [x] File into [[Cues/Change data capture]]: about i1 ([[Inbox/one]]) `kd:{first_id}`"
        in (vault / "Triage.md").read_text()
    )

    assert run(clone, FakeModel(), no_sparks, print)
    assert not (vault / "Inbox" / "one.md").exists()


def test_conflicting_edit_wins_and_the_run_retries(host_vault: tuple[Path, str], tmp_path: Path) -> None:
    vault, url = host_vault
    clone, first_id = one_proposal_waiting(vault, url, tmp_path)
    tick(vault, first_id)
    kd_host.autocommit(vault)

    # The run applies the tick and drops that line; meanwhile the user unticks the same line.
    logs: list[str] = []
    assert run(clone, EditWhileThinking(lambda: untick(vault, first_id)), no_sparks, logs.append)

    assert any("retrying" in line for line in logs)
    assert (vault / "Inbox" / "one.md").exists(), "the untick won"
    assert sorted(p.item for p in kd_state.load(vault).proposals) == ["Inbox/one", "Inbox/two"]
    status = subprocess.run(
        ["git", "-C", str(vault), "status", "--porcelain"], capture_output=True, text=True
    )
    assert status.stdout == ""


@pytest.mark.parametrize("ref", ["main", "refs/heads/other", "refs/tags/v1"])
def test_host_refuses_pushes_outside_the_agent_branch(
    host_vault: tuple[Path, str], tmp_path: Path, ref: str
) -> None:
    vault, url = host_vault
    clone_dir = tmp_path / "rogue"
    subprocess.run(["git", "clone", "-q", url, str(clone_dir)], check=True)
    (clone_dir / "x.md").write_text("x")
    subprocess.run(["git", "-C", str(clone_dir), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(clone_dir), "-c", "user.name=a", "-c", "user.email=a@b", "commit", "-qm", "x"],
        check=True,
    )
    push = subprocess.run(
        ["git", "-C", str(clone_dir), "push", "origin", f"HEAD:{ref}"], capture_output=True, text=True
    )
    assert push.returncode != 0
    assert not (vault / "x.md").exists()
    refs = subprocess.run(
        ["git", "-C", str(vault), "for-each-ref", "--format=%(refname)"], capture_output=True, text=True
    ).stdout.split()
    assert refs == ["refs/heads/main"]


def test_unreachable_host_is_a_quiet_skip(tmp_path: Path) -> None:
    clone = VaultClone(tmp_path / "vault", f"git://127.0.0.1:{free_port()}/notes")
    logs: list[str] = []
    assert run(clone, FakeModel(), no_sparks, logs.append)
    assert logs and "vault unreachable" in logs[0]


def test_broken_spark_source_does_not_stop_triage(host_vault: tuple[Path, str], tmp_path: Path) -> None:
    vault, url = host_vault
    (vault / "Inbox").mkdir()
    (vault / "Inbox" / "one.md").write_text("x")
    kd_host.autocommit(vault)

    def missing_checkout(done: set[str]) -> tuple[list[NewPage], list[str]]:
        raise ModuleNotFoundError("No module named 'inbox'")

    logs: list[str] = []
    assert run(VaultClone(tmp_path / "clone", url), FakeModel(), missing_checkout, logs.append)
    assert any("skipping Sparks" in line for line in logs)
    assert kd_state.load(vault).proposals
