#!/usr/bin/env python3
"""Install or upgrade the host side of knowledge-dump. Run on the host, not in the sandbox.

Sets up, as systemd user services:
  kd-silverbullet     SilverBullet serving the vault on loopback, published to the tailnet
                      with `tailscale serve` so the phone can reach it over HTTPS
  kd-git-daemon       git daemon on loopback, how the sandbox's triage agent syncs
  kd-autocommit       a timer committing the vault every few minutes

Re-run to upgrade. --uninstall removes the services and leaves the vault alone.
Standard library only.
"""

from __future__ import annotations

import argparse
import getpass
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import NoReturn

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kd_host  # noqa: E402

SB_VERSION = "2.11.1"
SB_ARCH = {"x86_64": "x86_64", "amd64": "x86_64", "aarch64": "aarch64", "arm64": "aarch64"}
SB_URL = "https://github.com/silverbulletmd/silverbullet/releases/download/{v}/silverbullet-server-linux-{arch}.zip"

HOME = Path.home()
LIB_DIR = HOME / ".local" / "lib" / "knowledge-dump"
SB_BINARY = LIB_DIR / "silverbullet"
CONFIG_DIR = HOME / ".config" / "knowledge-dump"
SB_ENV = CONFIG_DIR / "silverbullet.env"
UNIT_DIR = HOME / ".config" / "systemd" / "user"

SB_UNIT = "kd-silverbullet.service"
GIT_UNIT = "kd-git-daemon.service"
COMMIT_SERVICE = "kd-autocommit.service"
COMMIT_TIMER = "kd-autocommit.timer"
STARTED_UNITS = [SB_UNIT, GIT_UNIT, COMMIT_TIMER]


def say(message: str) -> None:
    print(f"knowledge-dump: {message}", flush=True)


def fail(message: str) -> NoReturn:
    print(f"knowledge-dump: {message}", file=sys.stderr)
    sys.exit(1)


def in_sandbox() -> bool:
    return bool(os.environ.get("SANDBOX_VM_ID")) or Path("/run/sandbox").exists()


def run(*cmd: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def unit_files(vault: Path, sb_port: int, git_port: int, git: str) -> dict[str, str]:
    """Every unit file's name and text. Pure, so the tests can read them."""
    docs = f"file://{HERE.parent}/README.md"
    python, script = sys.executable, HERE / "kd_host.py"
    daemon = kd_host.git_daemon_command(vault, git_port)
    daemon[0] = git
    return {
        SB_UNIT: f"""[Unit]
Description=knowledge-dump: SilverBullet serving the vault
Documentation={docs}

[Service]
ExecStart={SB_BINARY} --single -L 127.0.0.1 -p {sb_port} {vault}
EnvironmentFile={SB_ENV}
Restart=on-failure
RestartSec=5
NoNewPrivileges=yes

[Install]
WantedBy=default.target
""",
        GIT_UNIT: f"""[Unit]
Description=knowledge-dump: git daemon for the sandbox's triage agent
Documentation={docs}

[Service]
ExecStart={" ".join(daemon)}
Restart=on-failure
RestartSec=5
NoNewPrivileges=yes

[Install]
WantedBy=default.target
""",
        COMMIT_SERVICE: f"""[Unit]
Description=knowledge-dump: commit the vault
Documentation={docs}

[Service]
Type=oneshot
ExecStart={python} {script} autocommit {vault}
NoNewPrivileges=yes
""",
        COMMIT_TIMER: """[Unit]
Description=knowledge-dump: commit the vault every 5 minutes

[Timer]
OnCalendar=*:0/5
AccuracySec=30s

[Install]
WantedBy=timers.target
""",
    }


def installed_sb_version() -> str | None:
    if not SB_BINARY.exists():
        return None
    result = run(str(SB_BINARY), "version", check=False)
    return result.stdout.strip().split("-")[0] if result.returncode == 0 else None


def install_silverbullet() -> None:
    if installed_sb_version() == SB_VERSION:
        say(f"SilverBullet {SB_VERSION} already installed")
        return
    arch = SB_ARCH.get(platform.machine())
    if arch is None:
        fail(f"no SilverBullet build for {platform.machine()}")
    url = SB_URL.format(v=SB_VERSION, arch=arch)
    say(f"downloading SilverBullet {SB_VERSION}")
    with urllib.request.urlopen(url, timeout=120) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))
    LIB_DIR.mkdir(parents=True, exist_ok=True)
    staged = SB_BINARY.with_suffix(".new")
    staged.write_bytes(archive.read("silverbullet"))
    staged.chmod(0o755)
    staged.replace(SB_BINARY)  # a running service never sees a half-written binary


def ensure_login() -> None:
    """SilverBullet's login, kept out of the vault in a file only you can read."""
    if SB_ENV.exists():
        return
    say("choose a SilverBullet login. The phone asks for it once, then remembers it.")
    user = input(f"  username [{getpass.getuser()}]: ").strip() or getpass.getuser()
    while True:
        password = getpass.getpass("  password: ")
        if len(password) < 12:
            print("  use at least 12 characters")
        elif password != getpass.getpass("  again: "):
            print("  they didn't match")
        else:
            break
    if ":" in user or "\n" in user + password:
        fail("the username can't contain ':' and neither can contain a newline")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    fd = os.open(SB_ENV, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(f"SB_USER={user}:{password}\n")


def write_units(vault: Path, sb_port: int, git_port: int) -> None:
    git = shutil.which("git")
    if git is None:
        fail("git is not installed")
    UNIT_DIR.mkdir(parents=True, exist_ok=True)
    for name, text in unit_files(vault, sb_port, git_port, git).items():
        (UNIT_DIR / name).write_text(text)
    run("systemctl", "--user", "daemon-reload")
    for unit in STARTED_UNITS:
        run("systemctl", "--user", "enable", "--quiet", unit)
        run("systemctl", "--user", "restart", unit)
    say(f"services running: {', '.join(STARTED_UNITS)}")


def enable_linger() -> None:
    user = getpass.getuser()
    linger = run("loginctl", "show-user", user, "--property=Linger", "--value", check=False).stdout.strip()
    if linger == "yes":
        return
    say("letting user services run without a login session (loginctl enable-linger)")
    if run("loginctl", "enable-linger", user, check=False).returncode != 0:
        subprocess.run(["sudo", "loginctl", "enable-linger", user], check=True)


def serve_handler(https_port: int) -> str | None:
    """What `tailscale serve` already proxies on this HTTPS port, if anything."""
    status = run("tailscale", "serve", "status", "--json", check=False)
    if status.returncode != 0 or not status.stdout.strip():
        return None
    web = json.loads(status.stdout).get("Web") or {}
    for host_port, config in web.items():
        if host_port.endswith(f":{https_port}"):
            for handler in (config.get("Handlers") or {}).values():
                return str(handler.get("Proxy") or handler)
    return None


def serve_on_tailnet(https_port: int, sb_port: int) -> None:
    target = f"http://127.0.0.1:{sb_port}"
    current = serve_handler(https_port)
    if current and current != target:
        fail(
            f"tailscale serve already sends HTTPS port {https_port} to {current}; "
            "pick another with --https-port"
        )
    cmd = ["tailscale", "serve", "--bg", f"--https={https_port}", target]
    if run(*cmd, check=False).returncode != 0:
        say("tailscale serve needs permission; retrying with sudo")
        subprocess.run(["sudo", *cmd], check=True, capture_output=True)


def tailnet_url(https_port: int) -> str:
    status = json.loads(run("tailscale", "status", "--json").stdout)
    name = status["Self"]["DNSName"].rstrip(".")
    return f"https://{name}" + ("" if https_port == 443 else f":{https_port}")


def wait_for(check: list[str]) -> bool:
    for _ in range(20):
        if run(*check, check=False).returncode == 0:
            return True
        time.sleep(0.5)
    return False


def check(sb_port: int, git_port: int, https_port: int) -> None:
    if wait_for(["curl", "-sS", "--max-time", "3", "-o", "/dev/null", f"http://127.0.0.1:{sb_port}/"]):
        say("SilverBullet answers on loopback")
    else:
        fail(f"SilverBullet isn't answering. See: journalctl --user -u {SB_UNIT} -n 50")
    if wait_for(["git", "ls-remote", f"git://127.0.0.1:{git_port}/notes"]):
        say("git daemon answers on loopback")
    else:
        fail(f"git daemon isn't answering. See: journalctl --user -u {GIT_UNIT} -n 50")
    url = tailnet_url(https_port)
    print()
    say("open this on the phone in Chrome, log in, then menu > Add to home screen > Install:")
    print(f"    {url}")


def uninstall(https_port: int) -> None:
    for unit in STARTED_UNITS:
        run("systemctl", "--user", "disable", "--now", unit, check=False)
    for name in [SB_UNIT, GIT_UNIT, COMMIT_SERVICE, COMMIT_TIMER]:
        (UNIT_DIR / name).unlink(missing_ok=True)
    run("systemctl", "--user", "daemon-reload", check=False)
    off = ["tailscale", "serve", f"--https={https_port}", "off"]
    if run(*off, check=False).returncode != 0:
        subprocess.run(["sudo", *off], check=False)
    shutil.rmtree(LIB_DIR, ignore_errors=True)
    say(f"uninstalled. The vault and {SB_ENV} were left alone.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--vault", type=Path, default=HOME / "notes", help="the vault folder (default %(default)s)"
    )
    parser.add_argument(
        "--sb-port", type=int, default=3817, help="SilverBullet's loopback port (default %(default)s)"
    )
    parser.add_argument(
        "--git-port", type=int, default=9418, help="git daemon's loopback port (default %(default)s)"
    )
    parser.add_argument(
        "--https-port", type=int, default=443, help="tailnet HTTPS port (default %(default)s)"
    )
    parser.add_argument("--uninstall", action="store_true", help="stop and remove the services")
    args = parser.parse_args(argv)

    if in_sandbox():
        fail(
            "this looks like the sandbox. These services run on the host, "
            "so they keep working while the sandbox is closed."
        )
    if args.uninstall:
        uninstall(args.https_port)
        return 0
    for tool in ["git", "tailscale", "curl", "systemctl"]:
        if shutil.which(tool) is None:
            fail(f"{tool} is not installed")
    vault = args.vault.expanduser().resolve()
    install_silverbullet()
    ensure_login()
    kd_host.init(vault)
    say(f"vault ready at {vault}")
    write_units(vault, args.sb_port, args.git_port)
    enable_linger()
    serve_on_tailnet(args.https_port, args.sb_port)
    check(args.sb_port, args.git_port, args.https_port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
