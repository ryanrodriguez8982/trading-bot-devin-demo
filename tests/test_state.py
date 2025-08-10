import os
from pathlib import Path

from trading_bot.utils import state


def test_default_state_dir_windows(monkeypatch):
    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setenv("APPDATA", "C:\\AppData")
    assert state.default_state_dir() == os.path.join("C:\\AppData", "trading-bot")


def test_default_state_dir_windows_no_appdata(monkeypatch):
    fake_home = Path("/home/test")
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.delenv("APPDATA", raising=False)
    expected = os.path.join(str(fake_home), "AppData", "Roaming", "trading-bot")
    assert state.default_state_dir() == expected


def test_default_state_dir_non_windows(monkeypatch):
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.setenv("XDG_STATE_HOME", "/tmp/state")
    assert state.default_state_dir() == os.path.join("/tmp/state", "trading-bot")


def test_default_state_dir_non_windows_no_xdg(monkeypatch):
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    home = str(Path.home())
    expected = os.path.join(home, ".local", "state", "trading-bot")
    assert state.default_state_dir() == expected
