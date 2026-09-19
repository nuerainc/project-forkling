"""Forkland Forkling system tray icon (Windows-only via ctypes).

Why a tray icon? The desktop window is good when you're actively
looking at Forkland. The tray icon is for the *other* 99% of the
time — you want it running silently in the background, and you
want to be told when something needs your attention (heartbeat
RED, ledger corruption, etc.).

Design constraints (project-wide):
  - **stdlib only.** Uses ctypes + shell32 + user32, all stdlib on
    Windows. No PyQt, no pystray, no third-party deps.
  - **Read-only by default.** The tray polls and shows notifications.
    Actions (run heartbeat, quit) require a menu click.
  - **Survives sovereign mode / non-Windows.** On macOS/Linux,
    ``forkling tray`` exits 0 with a friendly message instead of
    crashing. On a headless Windows server without a desktop
    session, the icon registration silently fails and the command
    exits with a hint.

What you get
  - Tray icon always visible (uses the system info icon for simplicity)
  - Tooltip refreshes every 15s with: status · last heartbeat age ·
    stage · day N/365
  - Right-click menu:
        Status: GREEN / YELLOW / RED  (current status, read-only)
        Show desktop window
        Run heartbeat now  (--skip-improve so it can't commit anything)
        Run heartbeat (full)   (the real one — includes self-improve)
        Verify ledger
        Export dataset
        View paper
        ---
        Quit
  - Balloon notification on heartbeat GREEN -> YELLOW -> RED transition
"""

from __future__ import annotations

import ctypes
import os
import struct
import sys
import threading
import time
from ctypes import wintypes
from pathlib import Path

from . import desktop as _desktop
from .config import Config


# ---- Win32 constants ------------------------------------------------------

WM_USER = 0x0400
WM_DESTROY = 0x0002
WM_RBUTTONUP = 0x0205
WM_LBUTTONDBLCLK = 0x0203
WM_COMMAND = 0x0111
WM_TIMER = 0x0118

IDI_INFORMATION = 32516  # system info icon

NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002
NIM_SETVERSION = 0x00000004

NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
NIF_STATE = 0x00000008
NIF_INFO = 0x00000010
NIF_SHOWTIP = 0x00000080

NIS_HIDDEN = 0x00000001
NIS_SHAREDICON = 0x00000002

NOTIFYICON_VERSION_4 = 4

# Menu IDs (>= WM_USER + 100 to avoid colliding with our msg ids).
IDM_STATUS = WM_USER + 100       # disabled "Status: …" item
IDM_SHOW_DESKTOP = WM_USER + 101
IDM_RUN_HEARTBEAT_SAFE = WM_USER + 102
IDM_RUN_HEARTBEAT_FULL = WM_USER + 103
IDM_VERIFY = WM_USER + 104
IDM_EXPORT = WM_USER + 105
IDM_VIEW_PAPER = WM_USER + 106
IDM_QUIT = WM_USER + 107

# Tray callback messages (>= WM_USER + 200).
APP_TRAY_MSG = WM_USER + 200      # menu/balloon events
APP_TRAY_TIMER_ID = WM_USER + 201

# NOTIFYICONDATAW layout (the V4 variant is larger; we just use V3 for
# compatibility — works on every Windows version we care about).
# https://learn.microsoft.com/en-us/windows/win32/api/shellapi/ns-shellapi-notifyicondataw
NID_W_STRUCT = (
    "DWORD cbSize;"            # 4
    "HWND  hWnd;"              # 4 (or 8 on 64-bit; pad accordingly)
    "UINT  uID;"               # 4
    "UINT  uFlags;"            # 4
    "UINT  uCallbackMessage;"  # 4
    "HICON hIcon;"             # 4 (or 8)
    "WCHAR szTip[128];"        # 256
    "DWORD dwState;"           # 4
    "DWORD dwStateMask;"       # 4
    "WCHAR szInfo[256];"       # 512
    "UINT  uTimeoutOrVersion;" # 4 (union with uVersion)
    "WCHAR szInfoTitle[64];"   # 128
    "DWORD dwInfoFlags;"       # 4
    "GUID  guidItem;"          # 16
    "HICON hBalloonIcon;"      # 4 (or 8)
)

# We don't really need the union semantics — define a flat struct.
class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", ctypes.c_wchar * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", ctypes.c_wchar * 256),
        ("uTimeoutOrVersion", wintypes.UINT),
        ("szInfoTitle", ctypes.c_wchar * 64),
        ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", ctypes.c_byte * 16),
        ("hBalloonIcon", wintypes.HICON),
    ]


# ---- module-level Win32 handles ------------------------------------------

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_shell32 = ctypes.WinDLL("shell32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT,
                             wintypes.WPARAM, wintypes.LPARAM)


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HANDLE),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON),
    ]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hWnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


# Function prototypes we use.
_user32.DefWindowProcW.restype = LRESULT
_user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT,
                                   wintypes.WPARAM, wintypes.LPARAM]
_user32.RegisterClassExW.restype = wintypes.ATOM
_user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
_user32.CreateWindowExW.restype = wintypes.HWND
_user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR,
                                    wintypes.LPCWSTR, wintypes.DWORD,
                                    ctypes.c_int, ctypes.c_int,
                                    ctypes.c_int, ctypes.c_int,
                                    wintypes.HWND, wintypes.HMENU,
                                    wintypes.HINSTANCE, wintypes.LPVOID]
_user32.DestroyWindow.argtypes = [wintypes.HWND]
_user32.DestroyWindow.restype = wintypes.BOOL
_user32.LoadIconW.restype = wintypes.HICON
_user32.LoadIconW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR]
_user32.PostQuitMessage.argtypes = [c_int := ctypes.c_int]
_user32.GetMessageW.restype = wintypes.BOOL
_user32.GetMessageW.argtypes = [ctypes.POINTER(MSG), wintypes.HWND,
                                wintypes.UINT, wintypes.UINT]
_user32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
_user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
_user32.DispatchMessageW.restype = LRESULT
_user32.SetTimer.argtypes = [wintypes.HWND, wintypes.UINT,
                             wintypes.UINT, wintypes.LPVOID]
_user32.SetTimer.restype = wintypes.UINT
_user32.KillTimer.argtypes = [wintypes.HWND, wintypes.UINT]
_user32.TrackPopupMenu.argtypes = [wintypes.HMENU, wintypes.UINT,
                                   ctypes.c_int, ctypes.c_int,
                                   ctypes.c_int, wintypes.HWND,
                                   wintypes.LPVOID]
_user32.TrackPopupMenu.restype = wintypes.BOOL
_user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
_user32.SetForegroundWindow.argtypes = [wintypes.HWND]
_user32.CreatePopupMenu.restype = wintypes.HMENU
_user32.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT,
                                wintypes.UINT, wintypes.LPCWSTR]
_user32.EnableMenuItem.argtypes = [wintypes.HMENU, wintypes.UINT,
                                   wintypes.UINT]
_user32.SetMenuDefaultItem.argtypes = [wintypes.HMENU, wintypes.UINT,
                                       wintypes.UINT]

_shell32.Shell_NotifyIconW.restype = wintypes.BOOL
_shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD,
                                       ctypes.POINTER(NOTIFYICONDATAW)]

_kernel32.GetModuleHandleW.restype = wintypes.HMODULE
_kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]


# ---- helpers --------------------------------------------------------------


def _make_wchar(text: str, maxlen: int) -> ctypes.Array:
    """Build a fixed-size wchar buffer, truncating safely."""
    s = text[: maxlen - 1] if len(text) >= maxlen else text
    buf = (ctypes.c_wchar * maxlen)()
    buf.value = s
    return buf


# ---- the WndProc ---------------------------------------------------------


class _TrayHost:
    """Owns the hidden window, the tray icon, and the message loop."""

    CLASS_NAME = "ForklingTrayHost"

    def __init__(self, cfg: Config, repo: Path, refresh_seconds: int) -> None:
        self.cfg = cfg
        self.repo = repo
        self.refresh_seconds = refresh_seconds

        self.hwnd: wintypes.HWND | None = None
        self.hmenu: wintypes.HMENU | None = None
        self.icon_id = 1  # arbitrary, single icon per host
        self.nid = NOTIFYICONDATAW()
        self._wndproc_ref = WNDPROC(self._wndproc)

        self._last_status: str | None = None
        self._lock = threading.Lock()

    # ---- message handling --------------------------------------------------

    def _wndproc(self, hwnd, msg, wparam, lparam):
        if msg == WM_DESTROY:
            _user32.PostQuitMessage(0)
            return 0
        if msg == APP_TRAY_TIMER_ID:
            self._on_tick()
            return 0
        if msg == APP_TRAY_MSG:
            event = lparam & 0xFFFF
            if event == WM_RBUTTONUP:
                self._show_menu()
            elif event == WM_LBUTTONDBLCLK:
                self._action(IDM_SHOW_DESKTOP)
            return 0
        if msg == WM_COMMAND:
            menu_id = wparam & 0xFFFF
            if menu_id == IDM_QUIT:
                _user32.DestroyWindow(hwnd)
            else:
                self._action(menu_id)
            return 0
        return _user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    # ---- actions (called from the GUI thread) ------------------------------

    def _action(self, menu_id: int) -> None:
        # Run the action on a background thread so we don't block the
        # message pump (especially important for the heartbeat runs).
        threading.Thread(target=self._do_action, args=(menu_id,),
                         daemon=True).start()

    def _do_action(self, menu_id: int) -> None:
        if menu_id == IDM_STATUS:
            return
        if menu_id == IDM_SHOW_DESKTOP:
            self._open_desktop_window()
            return
        if menu_id == IDM_RUN_HEARTBEAT_SAFE:
            self._run_heartbeat(skip_improve=True)
            return
        if menu_id == IDM_RUN_HEARTBEAT_FULL:
            self._run_heartbeat(skip_improve=False)
            return
        if menu_id == IDM_VERIFY:
            self._run_subprocess(["python", "-m", "forkling", "verify"])
            return
        if menu_id == IDM_EXPORT:
            self._run_subprocess(["python", "-m", "forkling",
                                  "export-dataset"])
            return
        if menu_id == IDM_VIEW_PAPER:
            self._open_paper()
            return

    def _run_heartbeat(self, *, skip_improve: bool) -> None:
        argv = [sys.executable, "-m", "forkling", "heartbeat",
                "--repo", str(self.repo)]
        if skip_improve:
            argv.append("--skip-improve")
        self._run_subprocess(argv)

    def _run_subprocess(self, argv: list[str]) -> None:
        try:
            r = subprocess.run(argv, cwd=str(self.repo), capture_output=True,
                               text=True, timeout=900)
            tail = (r.stdout + r.stderr)[-300:]
            print(f"[tray] {argv[2]} exit={r.returncode} tail={tail!r}")
        except Exception as e:
            print(f"[tray] subprocess failed: {e!r}")

    def _open_desktop_window(self) -> None:
        # Spawn a separate process running forkling desktop, so the user
        # can close the tray without taking the desktop window with it.
        try:
            subprocess.Popen(
                [sys.executable, "-m", "forkling", "desktop",
                 "--repo", str(self.repo)],
                cwd=str(self.repo),
            )
        except Exception as e:
            print(f"[tray] desktop spawn failed: {e!r}")

    def _open_paper(self) -> None:
        paper = self.repo / "paper" / "paper.md"
        if not paper.exists():
            return
        try:
            if hasattr(os, "startfile"):
                os.startfile(str(paper))  # type: ignore[attr-defined]
        except Exception as e:
            print(f"[tray] open paper failed: {e!r}")

    # ---- status polling ---------------------------------------------------

    def _on_tick(self) -> None:
        try:
            snap = _desktop.collect_status(self.cfg, self.repo)
            self._apply_status(snap)
        except Exception as e:
            print(f"[tray] tick failed: {e!r}")

    def _apply_status(self, snap: dict) -> None:
        status = snap["status_label"]
        age = snap["last_heartbeat_age"]
        clock = snap["clock"]
        tip = (f"Forkland Forkling · {status} · "
               f"last heartbeat {age} · "
               f"day {clock['day_index']}/{clock['cycle_days']} "
               f"({clock['cycle_progress']*100:.1f}%)")
        if self.hwnd is None:
            return
        # Update tooltip.
        with self._lock:
            self.nid.uFlags = NIF_TIP | NIF_SHOWTIP
            self.nid.szTip = _make_wchar(tip, 128).value  # type: ignore[assignment]
            _shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(self.nid))

        # Notify on RED transition (and YELLOW, for early warning).
        if status != self._last_status:
            if status in ("YELLOW", "RED"):
                self._show_balloon(status, age, clock)
            self._last_status = status

    def _show_balloon(self, status: str, age: str, clock: dict) -> None:
        if self.hwnd is None:
            return
        title = f"Forkland Forkling · heartbeat {status}"
        body = (f"Last heartbeat: {age}\n"
                f"Stage: {clock['stage']} · "
                f"day {clock['day_index']}/{clock['cycle_days']}\n"
                f"Right-click the tray icon for actions.")
        with self._lock:
            self.nid.uFlags = NIF_INFO | NIF_SHOWTIP
            self.nid.szInfoTitle = _make_wchar(title, 64).value  # type: ignore[assignment]
            self.nid.szInfo = _make_wchar(body, 256).value  # type: ignore[assignment]
            self.nid.dwInfoFlags = 0x00000001  # NIIF_WARNING
            _shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(self.nid))

    # ---- menu --------------------------------------------------------------

    def _show_menu(self) -> None:
        if self.hwnd is None or self.hmenu is None:
            return
        pt = wintypes.POINT()
        _user32.GetCursorPos(ctypes.byref(pt))
        _user32.SetForegroundWindow(self.hwnd)
        _user32.TrackPopupMenu(self.hmenu, 0, pt.x, pt.y, 0, self.hwnd, None)

    def _build_menu(self, status_label: str) -> None:
        if self.hmenu is not None:
            _user32.DestroyMenu(self.hmenu)
        self.hmenu = _user32.CreatePopupMenu()
        _user32.AppendMenuW(self.hmenu, 0x00000003, IDM_STATUS,
                            f"Status: {status_label}")
        _user32.EnableMenuItem(self.hmenu, IDM_STATUS,
                               0x00000002)  # MF_GRAYED
        _user32.AppendMenuW(self.hmenu, 0x00000800, 0, "")  # MF_SEPARATOR
        _user32.AppendMenuW(self.hmenu, 0, IDM_SHOW_DESKTOP,
                            "Show desktop window")
        _user32.AppendMenuW(self.hmenu, 0, IDM_RUN_HEARTBEAT_SAFE,
                            "Run heartbeat (safe, --skip-improve)")
        _user32.AppendMenuW(self.hmenu, 0, IDM_RUN_HEARTBEAT_FULL,
                            "Run heartbeat (full, includes self-improve)")
        _user32.AppendMenuW(self.hmenu, 0x00000800, 0, "")  # MF_SEPARATOR
        _user32.AppendMenuW(self.hmenu, 0, IDM_VERIFY, "Verify ledger")
        _user32.AppendMenuW(self.hmenu, 0, IDM_EXPORT,
                            "Export dataset")
        _user32.AppendMenuW(self.hmenu, 0, IDM_VIEW_PAPER, "View paper")
        _user32.AppendMenuW(self.hmenu, 0x00000800, 0, "")
        _user32.AppendMenuW(self.hmenu, 0, IDM_QUIT, "Quit tray")

    # ---- lifecycle ---------------------------------------------------------

    def run(self) -> int:
        """Pump messages until the user clicks Quit. Returns 0."""
        hinst = _kernel32.GetModuleHandleW(None)

        wcx = WNDCLASSEXW()
        wcx.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wcx.lpfnWndProc = self._wndproc_ref
        wcx.hInstance = hinst
        wcx.lpszClassName = self.CLASS_NAME
        atom = _user32.RegisterClassExW(ctypes.byref(wcx))
        if not atom:
            err = ctypes.get_last_error()
            print(f"forkling tray: RegisterClassExW failed (err {err})")
            return 1

        self.hwnd = _user32.CreateWindowExW(
            0, self.CLASS_NAME, "Forkling Tray Host", 0,
            0, 0, 0, 0, wintypes.HWND(-3),  # HWND_MESSAGE = message-only
            None, hinst, None,
        )
        if not self.hwnd:
            err = ctypes.get_last_error()
            print(f"forkling tray: CreateWindowExW failed (err {err})")
            return 1

        # First status read so the menu shows the right label.
        try:
            snap = _desktop.collect_status(self.cfg, self.repo)
            self._last_status = snap["status_label"]
        except Exception:
            self._last_status = "UNKNOWN"
        self._build_menu(self._last_status)

        # Tray icon.
        hicon = _user32.LoadIconW(None, ctypes.c_wchar_p(IDI_INFORMATION))
        self.nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        self.nid.hWnd = self.hwnd
        self.nid.uID = self.icon_id
        self.nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP | NIF_SHOWTIP
        self.nid.uCallbackMessage = APP_TRAY_MSG
        self.nid.hIcon = hicon
        self.nid.szTip = _make_wchar(
            f"Forkland Forkling · {self._last_status}", 128).value  # type: ignore[assignment]
        self.nid.uTimeoutOrVersion = NOTIFYICON_VERSION_4
        ok = _shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(self.nid))
        if not ok:
            err = ctypes.get_last_error()
            print(f"forkling tray: Shell_NotifyIconW ADD failed (err {err})")
            print("This usually means the user session has no shell — "
                  "run from an interactive desktop session.")
            return 1

        # Polling timer.
        _user32.SetTimer(self.hwnd, APP_TRAY_TIMER_ID,
                         self.refresh_seconds * 1000, None)
        # Force an immediate update so the tooltip is fresh.
        self._on_tick()

        # Message loop.
        msg = MSG()
        while _user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            _user32.TranslateMessage(ctypes.byref(msg))
            _user32.DispatchMessageW(ctypes.byref(msg))

        # Cleanup.
        _shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self.nid))
        _user32.KillTimer(self.hwnd, APP_TRAY_TIMER_ID)
        _user32.DestroyWindow(self.hwnd)
        return 0


# ---- late import (ctypes-only module-level import avoids surprises) -------
import subprocess  # noqa: E402


# ---- public entry point ---------------------------------------------------

def launch(cfg: Config, repo: Path, refresh_seconds: int = 15) -> int:
    """Launch the system tray icon. Returns 0 on graceful exit, 1 on error."""
    if sys.platform != "win32":
        print("forkling tray: only Windows is supported via ctypes/shell32.")
        print(f"Detected platform: {sys.platform}")
        print("On macOS / Linux, run `forkling desktop` for the full Tk UI.")
        return 0
    host = _TrayHost(cfg, repo, refresh_seconds)
    return host.run()
