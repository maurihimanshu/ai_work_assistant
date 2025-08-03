"""Windows-specific activity monitoring."""

import ctypes
import logging
import os
from ctypes import wintypes
from typing import Dict

import win32gui
import win32process

from .base_monitor import BaseMonitor

logger = logging.getLogger(__name__)


class WindowsMonitor(BaseMonitor):
    """Windows implementation of platform monitoring."""

    def __init__(self):
        """Initialize Windows monitor."""
        try:
            self.user32 = ctypes.windll.user32
            self.kernel32 = ctypes.windll.kernel32

            # Set up function argument types
            self.user32.GetLastInputInfo.argtypes = [
                ctypes.POINTER(ctypes.c_uint)
            ]

            # Test Windows API availability
            if not self.user32.GetForegroundWindow():
                logger.warning("Could not get foreground window")
        except Exception as e:
            logger.error(f"Error initializing Windows monitor: {e}")

    def get_active_window_info(self) -> Dict[str, str]:
        """Get information about the currently active window.

        Returns:
            dict: Window information including:
                - app_name: Name of the application
                - window_title: Title of the window
                - process_id: Process ID
                - executable_path: Path to the executable
        """
        try:
            # Get window handle
            hwnd = self.user32.GetForegroundWindow()
            if not hwnd:
                return {
                    'app_name': 'Unknown',
                    'window_title': 'Unknown',
                    'process_id': 0,
                    'executable_path': ''
                }

            # Get window title
            title_length = self.user32.GetWindowTextLengthW(hwnd) + 1
            title = ctypes.create_unicode_buffer(title_length)
            self.user32.GetWindowTextW(hwnd, title, title_length)

            # Get process ID
            _, process_id = win32process.GetWindowThreadProcessId(hwnd)

            # Get executable path
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
                            executable_path = path_buffer.value
                        else:
                            executable_path = ''
                    finally:
                        self.kernel32.CloseHandle(process_handle)
                else:
                    executable_path = ''
            except Exception as e:
                logger.error(f"Error getting executable path: {e}")
                executable_path = ''

            # Get application name from executable path
            app_name = os.path.basename(executable_path) if executable_path else 'Unknown'

            return {
                'app_name': app_name,
                'window_title': title.value,
                'process_id': process_id,
                'executable_path': executable_path
            }

        except Exception as e:
            logger.error(f"Error getting active window info: {e}")
            return {
                'app_name': 'Unknown',
                'window_title': 'Unknown',
                'process_id': 0,
                'executable_path': ''
            }

    def get_idle_time(self) -> float:
        """Get system idle time in seconds.

        Returns:
            float: Idle time in seconds
        """
        try:
            last_input = ctypes.c_uint()
            self.user32.GetLastInputInfo(ctypes.byref(last_input))
            idle_time = (self.kernel32.GetTickCount() - last_input.value) / 1000.0
            return idle_time
        except Exception as e:
            logger.error(f"Error getting idle time: {e}")
            return 0.0