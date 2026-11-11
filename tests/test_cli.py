"""Tests for the command that starts the dashboard.

CI installs the package regularly, so these tests check the command of the
built package.
"""
import shutil
import socket
import subprocess
import sys
import sysconfig
import time
import urllib.request
from importlib import metadata
from pathlib import Path

import pytest

import owp_milp_optimization
from owp_milp_optimization import cli

PKG_DIR = Path(owp_milp_optimization.__file__).parent
COMMAND = 'owp-milp-optimization'


def test_command_is_installed():
    """The installed package provides the command."""
    entry_points = metadata.entry_points(group='console_scripts', name=COMMAND)
    assert [ep.value for ep in entry_points] == [
        'owp_milp_optimization.cli:main'
    ]


def test_command_runs_home_page(monkeypatch):
    """The command runs Home.py of the package and passes on arguments."""
    calls = []
    monkeypatch.setattr(sys, 'argv', [COMMAND, '--server.port', '8502'])
    monkeypatch.setattr(
        cli.stcli, 'main', lambda: calls.append(list(sys.argv))
    )
    cli.main()
    assert calls == [[
        'streamlit', 'run', str(PKG_DIR / 'Home.py'), '--server.port', '8502'
    ]]


def test_theme_ships_next_to_home_page():
    """The theme is found from any working directory.

    Streamlit reads .streamlit/config.toml from the working directory and
    from the folder of the main script, i.e. of Home.py.
    """
    config = PKG_DIR / '.streamlit' / 'config.toml'
    assert 'primaryColor' in config.read_text(encoding='utf-8')


def _free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


@pytest.mark.parametrize('how', ['command', 'python -m'])
def test_command_starts_dashboard(tmp_path, how):
    """The dashboard starts from any working directory."""
    if how == 'command':
        command = shutil.which(COMMAND, path=sysconfig.get_path('scripts'))
        assert command is not None, f'{COMMAND} is not installed'
        start = [command]
    else:
        start = [sys.executable, '-m', 'owp_milp_optimization']
    port = _free_port()
    start += [
        '--server.headless', 'true', '--server.port', str(port),
        '--browser.gatherUsageStats', 'false',
    ]
    log = tmp_path / 'streamlit.log'

    with open(log, 'w') as logfile:
        process = subprocess.Popen(
            start, cwd=tmp_path, stdin=subprocess.DEVNULL, stdout=logfile,
            stderr=subprocess.STDOUT,
        )
    try:
        deadline = time.monotonic() + 60
        while True:
            assert process.poll() is None, log.read_text()
            try:
                url = f'http://127.0.0.1:{port}/_stcore/health'
                with urllib.request.urlopen(url, timeout=2) as response:
                    if response.read() == b'ok':
                        break
            except OSError:
                pass
            assert time.monotonic() < deadline, log.read_text()
            time.sleep(0.2)
    finally:
        process.terminate()
        process.wait(timeout=30)
