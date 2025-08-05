"""Linux-specific activity monitoring."""

import logging
import os
import subprocess
from typing import Dict, Union

from .base_monitor import BaseMonitor

logger = logging.getLogger(__name__)


class LinuxMonitor(BaseMonitor):
    """Linux implementation of platform monitoring."""

    def __init__(self) -> None:
        """Initialize Linux monitor."""
        try:
            # Check for required tools
            self._check_dependencies()
        except Exception as e:
            logger.error(f"Error initializing Linux monitor: {e}")

    def _check_dependencies(self) -> None:
        """Check if required tools are available."""
        try:
            subprocess.run(["xdotool", "--version"], capture_output=True)
            subprocess.run(["xprintidle"], capture_output=True)
        except FileNotFoundError:
            logger.error("Required tools not found: xdotool, xprintidle")
            raise RuntimeError("Missing required tools: xdotool, xprintidle")

    def get_active_window_info(self) -> Dict[str, Union[str, int]]:
        """Get information about the currently active window.

        Returns:
            dict: Window information including:
                - app_name: Name of the application (str)
                - window_title: Title of the window (str)
                - process_id: Process ID (int)
                - executable_path: Path to the executable (str)
        """
        try:
            # Get active window ID
            window_id = (
                subprocess.check_output(["xdotool", "getactivewindow"]).decode().strip()
            )

            # Get window title
            title = (
                subprocess.check_output(["xdotool", "getwindowname", window_id])
                .decode()
                .strip()
            )

            # Get window PID
            pid = (
                subprocess.check_output(["xdotool", "getwindowpid", window_id])
                .decode()
                .strip()
            )

            # Get executable path
            executable_path = os.path.realpath(f"/proc/{pid}/exe")

            # Get application name
            app_name = os.path.basename(executable_path)

            return {
                "app_name": app_name,
                "window_title": title,
                "process_id": int(pid),
                "executable_path": executable_path,
            }

        except Exception as e:
            logger.error(f"Error getting active window info: {e}")
            return {
                "app_name": "Unknown",
                "window_title": "Unknown",
                "process_id": 0,
                "executable_path": "",
            }

    def get_idle_time(self) -> float:
        """Get system idle time in seconds.

        Returns:
            float: Idle time in seconds
        """
        try:
            idle_time = (
                float(subprocess.check_output(["xprintidle"]).decode().strip()) / 1000.0
            )  # Convert from milliseconds to seconds
            return idle_time
        except Exception as e:
            logger.error(f"Error getting idle time: {e}")
            return 0.0
