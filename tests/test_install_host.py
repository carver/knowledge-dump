from pathlib import Path

import install_host
import pytest


def test_units_bind_to_loopback_and_point_at_the_vault() -> None:
    units = install_host.unit_files(Path("/home/u/notes"), 3817, 9418, "/usr/bin/git")
    sb = units[install_host.SB_UNIT]
    assert "--single -L 127.0.0.1 -p 3817 /home/u/notes" in sb
    assert f"EnvironmentFile={install_host.SB_ENV}" in sb
    daemon = units[install_host.GIT_UNIT]
    assert "ExecStart=/usr/bin/git daemon" in daemon
    assert "--listen=127.0.0.1" in daemon and "--port=9418" in daemon
    assert "--interpolated-path=/home/u/notes" in daemon
    assert "autocommit /home/u/notes" in units[install_host.COMMIT_SERVICE]
    assert "OnCalendar=*:0/5" in units[install_host.COMMIT_TIMER]


def test_refuses_to_run_in_the_sandbox(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SANDBOX_VM_ID", "x")
    with pytest.raises(SystemExit) as exit_info:
        install_host.main([])
    assert exit_info.value.code == 1
