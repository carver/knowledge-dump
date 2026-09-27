"""The sandbox's clone of the vault, synced with the host over git daemon.

The sandbox only ever pushes to the `agent` branch. A hook on the host merges
it into `main`, the branch SilverBullet's folder has checked out. See
docs/adr/0001-vault-on-host-agents-over-git-daemon.md.
"""

import os
import subprocess
from pathlib import Path

MAIN = "main"
AGENT_BRANCH = "agent"
WORK_BRANCH = "work"
IDENTITY = {
    "GIT_AUTHOR_NAME": "knowledge-dump triage",
    "GIT_AUTHOR_EMAIL": "triage@knowledge-dump.invalid",
    "GIT_COMMITTER_NAME": "knowledge-dump triage",
    "GIT_COMMITTER_EMAIL": "triage@knowledge-dump.invalid",
    "GIT_TERMINAL_PROMPT": "0",
}


class Unreachable(RuntimeError):
    """The host's git daemon didn't answer, e.g. because the laptop is asleep."""


def _one_line(stderr: str) -> str:
    """git's error on one line, without its generic advice, so each skipped run is one log line."""
    advice = ("Please make sure you have the correct access rights", "and the repository exists.")
    lines = [
        line.strip() for line in stderr.splitlines() if line.strip() and not line.strip().startswith(advice)
    ]
    return " ".join(lines) or "no error message"


class VaultClone:
    def __init__(self, path: Path, remote: str) -> None:
        self.path = path
        self.remote = remote

    def _git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.path), *args],
            capture_output=True,
            text=True,
            check=check,
            env={**os.environ, **IDENTITY},
            timeout=120,
        )

    def ensure(self) -> None:
        if (self.path / ".git").is_dir():
            self._git("remote", "set-url", "origin", self.remote)
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["git", "clone", "-q", self.remote, str(self.path)],
            capture_output=True,
            text=True,
            env={**os.environ, **IDENTITY},
            timeout=120,
        )
        if result.returncode != 0:
            raise Unreachable(f"can't clone {self.remote}: {_one_line(result.stderr)}")

    def fetch(self) -> None:
        result = self._git("fetch", "-q", "--prune", "origin", check=False)
        if result.returncode != 0:
            raise Unreachable(f"can't fetch {self.remote}: {_one_line(result.stderr)}")

    def reset_to_main(self) -> None:
        """Throw away local work and start from the host's main."""
        self._git("checkout", "-q", "-B", WORK_BRANCH, f"origin/{MAIN}")
        self._git("reset", "-q", "--hard", f"origin/{MAIN}")
        self._git("clean", "-q", "-fd")

    def commit_all(self, message: str) -> bool:
        self._git("add", "-A")
        if self._git("diff", "--cached", "--quiet", check=False).returncode == 0:
            return False
        self._git("commit", "-q", "-m", message)
        return True

    def push(self) -> str:
        """Push HEAD to the agent branch and return its commit id."""
        head = self._git("rev-parse", "HEAD").stdout.strip()
        result = self._git("push", "-q", "--force", "origin", f"HEAD:refs/heads/{AGENT_BRANCH}", check=False)
        if result.returncode != 0:
            raise Unreachable(f"push failed: {_one_line(result.stderr)}")
        return head

    def merged(self, commit: str) -> bool:
        """Whether the host's main now contains `commit`."""
        self.fetch()
        check = self._git("merge-base", "--is-ancestor", commit, f"origin/{MAIN}", check=False)
        return check.returncode == 0
