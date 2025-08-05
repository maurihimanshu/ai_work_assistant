"""Windows-specific activity monitoring."""

import ctypes
import logging
import os
from ctypes import wintypes, WINFUNCTYPE, c_bool
from typing import Dict, Tuple, Union

import win32gui
import win32process

from .base_monitor import BaseMonitor

logger = logging.getLogger(__name__)

# Define Windows types and structures
class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ('cbSize', ctypes.c_uint),
        ('dwTime', ctypes.c_uint),
    ]

# Define callback type for EnumWindows
WNDENUMPROC = WINFUNCTYPE(c_bool, wintypes.HWND, wintypes.LPARAM)

class WindowsMonitor(BaseMonitor):
    """Windows implementation of platform monitoring."""

    def __init__(self) -> None:
        """Initialize Windows monitor."""
        try:
            self.user32 = ctypes.windll.user32
            self.kernel32 = ctypes.windll.kernel32

            # Set up function argument types
            self.user32.GetLastInputInfo.argtypes = [ctypes.POINTER(LASTINPUTINFO)]
            self.user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
            self.user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
            self.user32.IsWindowVisible.argtypes = [wintypes.HWND]
            self.user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
            self.user32.EnumWindows.restype = c_bool

            # Test Windows API availability
            if not self.user32.GetForegroundWindow():
                logger.warning("Could not get foreground window")

            # Cache for window titles and app names
            self._window_cache = {}
            self._max_cache_size = 100

            # Initialize last input info structure
            self._last_input_info = LASTINPUTINFO()
            self._last_input_info.cbSize = ctypes.sizeof(LASTINPUTINFO)

        except Exception as e:
            logger.error(f"Error initializing Windows monitor: {e}", exc_info=True)

    def get_active_window_info(self) -> Tuple[str, str]:
        """Get information about the currently active window.

        Returns:
            tuple: (window_title, application_name)
        """
        try:
            # Get window handle
            hwnd = self.user32.GetForegroundWindow()
            if not hwnd:
                # Try to find any visible window
                visible_hwnd = self._find_visible_window()
                if visible_hwnd:
                    hwnd = visible_hwnd
                    logger.debug("Using first visible window as fallback")
                else:
                    logger.warning("No foreground window found")
                    return ("Unknown", "Unknown")

            # Check cache first
            if hwnd in self._window_cache:
                title, app_name = self._window_cache[hwnd]
                # Verify the cached title is still valid
                current_title = self._get_window_title(hwnd)
                if current_title == title:
                    logger.debug(f"Using cached window info for {app_name}")
                    return (title, app_name)

            # Get window title
            title = self._get_window_title(hwnd)
            if not title:
                logger.debug("Empty window title")
                title = "Unknown"

            # Get process info
            try:
                _, process_id = win32process.GetWindowThreadProcessId(hwnd)
                app_name = self._get_process_name(process_id)
            except Exception as e:
                logger.error(f"Error getting process info: {e}")
                app_name = "Unknown"

            # Update cache
            self._update_cache(hwnd, title, app_name)

            logger.debug(f"Window info - Title: {title}, App: {app_name}")
            return (title, app_name)

        except Exception as e:
            logger.error(f"Error getting active window info: {e}", exc_info=True)
            return ("Unknown", "Unknown")

    def _find_visible_window(self) -> int:
        """Find first visible window.

        Returns:
            int: Window handle or 0 if none found
        """
        visible_hwnd = [0]

        def enum_windows_callback(hwnd, _):
            if self.user32.IsWindowVisible(hwnd):
                visible_hwnd[0] = hwnd
                return False  # Stop enumeration
            return True  # Continue enumeration

        try:
            callback = WNDENUMPROC(enum_windows_callback)
            self.user32.EnumWindows(callback, 0)
        except Exception as e:
            logger.error(f"Error enumerating windows: {e}")

        return visible_hwnd[0]

    def _get_window_title(self, hwnd: int) -> str:
        """Get window title safely.

        Args:
            hwnd: Window handle

        Returns:
            str: Window title
        """
        try:
            # Get required buffer size
            length = self.user32.GetWindowTextLengthW(hwnd) + 1
            if length > 1:
                title = ctypes.create_unicode_buffer(length)
                if self.user32.GetWindowTextW(hwnd, title, length):
                    return title.value.strip()
        except Exception as e:
            logger.error(f"Error getting window title: {e}")
        return ""

    def _get_process_name(self, process_id: int) -> str:
        """Get process name safely.

        Args:
            process_id: Process ID

        Returns:
            str: Process name
        """
        try:
            process_handle = self.kernel32.OpenProcess(
                0x1000,  # PROCESS_QUERY_LIMITED_INFORMATION
                False,
                process_id
            )
            if process_handle:
                try:
                    path_buffer = ctypes.create_unicode_buffer(260)  # MAX_PATH
                    path_length = ctypes.c_uint(260)
                    if self.kernel32.QueryFullProcessImageNameW(
                        process_handle,
                        0,
                        path_buffer,
                        ctypes.byref(path_length)
                    ):
                        return os.path.basename(path_buffer.value)
                finally:
                    self.kernel32.CloseHandle(process_handle)
        except Exception as e:
            logger.error(f"Error getting process name: {e}")
        return "Unknown"

    def _update_cache(self, hwnd: int, title: str, app_name: str) -> None:
        """Update window info cache.

        Args:
            hwnd: Window handle
            title: Window title
            app_name: Application name
        """
        # Remove oldest entry if cache is full
        if len(self._window_cache) >= self._max_cache_size:
            oldest_hwnd = next(iter(self._window_cache))
            del self._window_cache[oldest_hwnd]

        self._window_cache[hwnd] = (title, app_name)

    def get_idle_time(self) -> float:
        """Get system idle time in seconds.

        Returns:
            float: Idle time in seconds
        """
        try:
            if self.user32.GetLastInputInfo(ctypes.byref(self._last_input_info)):
                idle_time = (self.kernel32.GetTickCount() - self._last_input_info.dwTime) / 1000.0
                logger.debug(f"Current idle time: {idle_time:.1f}s")
                return idle_time
            else:
                error = ctypes.get_last_error()
                logger.warning(f"Failed to get last input info (error {error})")
                return 0.0
        except Exception as e:
            logger.error(f"Error getting idle time: {e}")
            return 0.0

    def is_screen_locked(self) -> bool:
        """Check if screen is locked.

        Returns:
            bool: True if screen is locked, False otherwise
        """
        try:
            # Check if any visible window exists
            visible_hwnd = self._find_visible_window()
            if not visible_hwnd:
                logger.debug("No visible windows found, screen might be locked")
                return True

            # Get foreground window
            hwnd = self.user32.GetForegroundWindow()
            if not hwnd:
                logger.debug("No foreground window, screen might be locked")
                return True

            # Check window title
            title = self._get_window_title(hwnd)
            lock_screen_titles = [
                "Windows Lock Screen",
                "Lock Screen",
                "Windows Security",
                "Sign in",
                "Sign In",
                "Windows Welcome Screen",
            ]
            return any(lock_title in title for lock_title in lock_screen_titles)

        except Exception as e:
            logger.error(f"Error checking screen lock: {e}")
            return False
