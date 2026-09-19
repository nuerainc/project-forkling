"""Tests for the tray module.

The Windows tray icon itself can't be exercised in a headless test
environment — there's no shell to register a NotifyIcon against — but
we can verify the cross-platform fallback and the menu-ID constants
are stable.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from forkling import tray as _tray
from forkling.config import Config


def test_menu_ids_are_distinct():
    """Each menu item must have a unique ID — the WndProc dispatches on it."""
    ids = [
        _tray.IDM_STATUS,
        _tray.IDM_SHOW_DESKTOP,
        _tray.IDM_RUN_HEARTBEAT_SAFE,
        _tray.IDM_RUN_HEARTBEAT_FULL,
        _tray.IDM_VERIFY,
        _tray.IDM_EXPORT,
        _tray.IDM_VIEW_PAPER,
        _tray.IDM_QUIT,
    ]
    assert len(set(ids)) == len(ids)


def test_callback_msg_distinct_from_menu_ids():
    """Tray callback messages must not collide with menu command IDs."""
    assert _tray.APP_TRAY_MSG != _tray.IDM_QUIT
    assert _tray.APP_TRAY_TIMER_ID != _tray.IDM_QUIT


def test_make_wchar_truncates_long_input():
    buf = _tray._make_wchar("a" * 1000, maxlen=128)
    # ctypes c_wchar array length is 128, but Python-level .value drops
    # the trailing null. Just confirm the value is bounded by maxlen-1.
    assert len(buf.value) <= 127


def test_tray_falls_back_off_windows(tmp_path, monkeypatch, capsys):
    """On macOS / Linux, `forkling tray` should print a friendly message
    and return 0, NOT crash trying to load shell32."""
    if sys.platform == "win32":
        pytest.skip("windows-only test for the tray launch path; "
                    "covered on macOS/Linux by this assertion")
    monkeypatch.setenv("FORKLING_MEMORY", str(tmp_path / "mem"))
    cfg = Config.from_env()
    rc = _tray.launch(cfg, repo=tmp_path)
    assert rc == 0
    out = capsys.readouterr().out
    assert "forkling tray" in out.lower() or "only Windows" in out


def test_tray_cli_falls_back_off_windows(tmp_path, monkeypatch, capsys):
    """The `forkling tray` CLI command also exits 0 with a friendly message
    on non-Windows platforms."""
    if sys.platform == "win32":
        pytest.skip("windows-only test for the tray CLI; "
                    "covered on macOS/Linux by this assertion")
    monkeypatch.setenv("FORKLING_MEMORY", str(tmp_path / "mem"))
    monkeypatch.setenv("FORKLING_REPO", str(tmp_path))
    from forkling.__main__ import main
    rc = main(["tray", "--repo", str(tmp_path)])
    assert rc == 0
