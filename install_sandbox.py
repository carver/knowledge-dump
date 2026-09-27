#!/usr/bin/env python3
"""Set up the sandbox side of knowledge-dump: dependencies, git hooks, the hourly triage cron job.

Idempotent; sandbox-setup/setup.py runs it on every rebuild. The host side is
host/install_host.py, which you run on the host.
"""

import pathlib
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent
MARKER = "# knowledge-dump triage"
CRON_LINES = [
    # Hourly at :23. A run with nothing new to do is silent and doesn't call the model.
    f"23 * * * * bash -lc 'cd {REPO} && python3 -u -m kd triage >> triage.log 2>&1' {MARKER}",
]

# (import name, pip name). jsonschema and regress are for tab-squasher's Inbox
# reader; the rest are for development.
PYTHON_DEPS = [
    ("jsonschema", "jsonschema"),
    ("regress", "regress"),
    ("pytest", "pytest"),
    ("hypothesis", "hypothesis"),
    ("ruff", "ruff"),
    ("mypy", "mypy"),
]


def install_dependencies() -> bool:
    missing = []
    for import_name, pip_name in PYTHON_DEPS:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pip_name)
    if not missing:
        print("✓ Python dependencies present")
        return True
    print(f"installing {' '.join(missing)} …")
    # The sandbox's system Python is "externally managed" (PEP 668); these go into the user site.
    cmd = [sys.executable, "-m", "pip", "install", "-q", "--user", "--break-system-packages", *missing]
    if subprocess.run(cmd).returncode != 0:
        print(f"✗ pip install failed for: {' '.join(missing)}")
        return False
    print(f"✓ installed {' '.join(missing)}")
    return True


def enable_git_hooks() -> bool:
    if subprocess.run(["git", "-C", str(REPO), "config", "core.hooksPath", ".githooks"]).returncode != 0:
        print("✗ could not enable the git hooks")
        return False
    print("✓ git hooks enabled (.githooks)")
    return True


def check_claude_cli() -> bool:
    if shutil.which("claude"):
        print("✓ claude CLI on PATH")
        return True
    print("✗ claude CLI not found on PATH; triage can't propose anything")
    return False


def check_cron_daemon() -> bool:
    if subprocess.run(["pgrep", "-x", "cron"], capture_output=True).returncode == 0:
        print("✓ cron daemon running")
        return True
    if subprocess.run(["sudo", "/usr/sbin/cron"], capture_output=True).returncode == 0:
        print("✓ cron daemon started")
        return True
    print("✗ no cron daemon and could not start one (is cron installed?)")
    return False


def install_crontab() -> bool:
    current = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    lines = current.stdout.splitlines() if current.returncode == 0 else []
    lines = [line for line in lines if MARKER not in line] + CRON_LINES
    result = subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", text=True, capture_output=True)
    if result.returncode != 0:
        print(f"✗ crontab install failed: {result.stderr.strip()}")
        return False
    for line in CRON_LINES:
        print(f"✓ crontab entry installed: {line}")
    return True


def main() -> int:
    ok = install_dependencies()
    ok = enable_git_hooks() and ok
    ok = check_claude_cli() and ok
    ok = check_cron_daemon() and ok
    ok = install_crontab() and ok
    print("install complete" if ok else "install finished WITH PROBLEMS (see above)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
