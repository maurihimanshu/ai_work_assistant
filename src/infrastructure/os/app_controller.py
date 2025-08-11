"""Application control utilities (start/close/list) with Windows-first support."""

from __future__ import annotations

import os
import platform
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

import psutil

try:
    import win32gui  # type: ignore
    import win32con  # type: ignore
    import win32process  # type: ignore

    HAS_PYWIN32 = True
except Exception:
    HAS_PYWIN32 = False


@dataclass
class RunningApp:
    pid: int
    name: str
    exe: str
    cmdline: List[str]
    started_at: Optional[datetime]
    window_title: Optional[str]


class AppController:
    """Controls starting and closing applications per OS.

    Notes:
      - Methods are best-effort and may vary by platform.
    """

    def __init__(self) -> None:
        self._system = platform.system().lower()

    def list_running_apps(self) -> List[RunningApp]:
        apps: List[RunningApp] = []
        for proc in psutil.process_iter(
            attrs=["pid", "name", "exe", "cmdline", "create_time"]
        ):
            try:
                info = proc.info
                window_title = None
                if self._system == "windows" and HAS_PYWIN32:
                    try:
                        hwnd = self._get_main_window_handle(proc.pid)
                        if hwnd:
                            title = win32gui.GetWindowText(hwnd)
                            window_title = title if title else None
                    except Exception:
                        window_title = None
                started_at = None
                try:
                    if info.get("create_time"):
                        started_at = datetime.fromtimestamp(info["create_time"])  # type: ignore[index]
                except Exception:
                    started_at = None
                apps.append(
                    RunningApp(
                        pid=info.get("pid", 0),
                        name=info.get("name") or "",
                        exe=info.get("exe") or "",
                        cmdline=info.get("cmdline") or [],
                        started_at=started_at,
                        window_title=window_title,
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return apps

    def list_visible_apps(self) -> List[RunningApp]:
        """Return only apps with a visible top-level window (Windows).

        On non-Windows platforms, falls back to list_running_apps().
        """
        if self._system != "windows" or not HAS_PYWIN32:
            return self.list_running_apps()
        result: List[RunningApp] = []
        for app in self.list_running_apps():
            if app.window_title and app.window_title.strip():
                result.append(app)
        return result

    def start_app(self, executable_path: str, args: Optional[List[str]] = None) -> bool:
        args = args or []
        try:
            if not executable_path:
                return False
            if self._system == "windows":
                subprocess.Popen([executable_path, *args], close_fds=False)
            else:
                subprocess.Popen([executable_path, *args])
            return True
        except Exception:
            return False

    def close_app_by_exe(self, exe_name: str, timeout_sec: float = 5.0) -> bool:
        """Attempt graceful close by window message on Windows; fallback to terminate."""
        success = False
        for proc in psutil.process_iter(attrs=["pid", "name"]):
            try:
                if (proc.info.get("name") or "").lower() != exe_name.lower():
                    continue
                if self._system == "windows" and HAS_PYWIN32:
                    try:
                        hwnd = self._get_main_window_handle(proc.pid)
                        if hwnd:
                            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                            # Wait a bit
                            end = time.time() + timeout_sec
                            while time.time() < end:
                                if not psutil.pid_exists(proc.pid):
                                    success = True
                                    break
                                time.sleep(0.1)
                    except Exception:
                        pass
                if psutil.pid_exists(proc.pid):
                    proc.terminate()
                    try:
                        proc.wait(timeout=timeout_sec)
                        success = True
                    except psutil.TimeoutExpired:
                        proc.kill()
                        success = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return success

    # --- Windows helpers ---
    def _get_main_window_handle(self, pid: int) -> Optional[int]:
        if not HAS_PYWIN32:
            return None
        hwnd_found: Optional[int] = None

        def callback(hwnd, extra):
            nonlocal hwnd_found
            try:
                _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                if found_pid == pid and win32gui.IsWindowVisible(hwnd):
                    hwnd_found = hwnd
                    return False
            except Exception:
                pass
            return True

        try:
            win32gui.EnumWindows(callback, None)
        except Exception:
            return None
        return hwnd_found

    def get_window_rect_by_pid(self, pid: int) -> Optional[Tuple[int, int, int, int]]:
        """Return (x, y, width, height) for the main window of the process if available (Windows)."""
        if self._system != "windows" or not HAS_PYWIN32:
            return None
        try:
            hwnd = self._get_main_window_handle(pid)
            if not hwnd:
                return None
            rect = win32gui.GetWindowRect(hwnd)
            x, y, right, bottom = rect
            return x, y, right - x, bottom - y
        except Exception:
            return None

    def move_window_by_pid(self, pid: int, x: int, y: int, w: int, h: int) -> bool:
        """Move/resize the main window for the process (Windows)."""
        if self._system != "windows" or not HAS_PYWIN32:
            return False
        try:
            hwnd = self._get_main_window_handle(pid)
            if not hwnd:
                return False
            win32gui.MoveWindow(hwnd, x, y, w, h, True)
            return True
        except Exception:
            return False

    def find_running_by_exe_and_title(
        self, exe_tail: str, title_contains: Optional[str] = None
    ) -> Optional[RunningApp]:
        """Best-effort match: find a running app by executable tail and optional title substring."""
        exe_tail_lower = (exe_tail or "").split("\\")[-1].split("/")[-1].lower()
        for app in self.list_running_apps():
            try:
                tail = (
                    (app.exe or app.name or "").split("\\")[-1].split("/")[-1].lower()
                )
                if tail != exe_tail_lower:
                    continue
                if title_contains and title_contains not in (app.window_title or ""):
                    continue
                return app
            except Exception:
                continue
        return None
