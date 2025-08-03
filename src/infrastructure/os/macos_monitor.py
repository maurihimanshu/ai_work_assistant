"""macOS-specific activity monitoring."""

import logging
import os
import subprocess
from typing import Dict

from .base_monitor import BaseMonitor

logger = logging.getLogger(__name__)


class MacOSMonitor(BaseMonitor):
    """macOS implementation of platform monitoring."""

    def __init__(self):
        """Initialize macOS monitor."""
        try:
            # Check for required tools
            self._check_dependencies()
        except Exception as e:
            logger.error(f"Error initializing macOS monitor: {e}")

    def _check_dependencies(self) -> None:
        """Check if required tools are available."""
        try:
            subprocess.run(['osascript', '--version'], capture_output=True)
        except FileNotFoundError:
            logger.error("Required tool not found: osascript")
            raise RuntimeError("Missing required tool: osascript")

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
            # Get active application info using AppleScript
            script = '''
                tell application "System Events"
                    set frontApp to first application process whose frontmost is true
                    set appName to name of frontApp
                    set appPath to path of frontApp
                    set appPID to unix id of frontApp
                    set windowTitle to ""
                    try
                        set windowTitle to name of first window of frontApp
                    end try
                    return {appName, windowTitle, appPID, appPath}
                end tell
            '''

            result = subprocess.check_output(
                ['osascript', '-e', script]
            ).decode().strip()

            # Parse result
            app_name, window_title, pid, executable_path = result.split(', ')

            return {
                'app_name': app_name,
                'window_title': window_title or 'Unknown',
                'process_id': int(pid),
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
            # Get idle time using CGEventSourceSecondsSinceLastEventType
            script = '''
                tell application "System Events"
                    return idle time
                end tell
            '''

            idle_time = float(
                subprocess.check_output(
                    ['osascript', '-e', script]
                ).decode().strip()
            )
            return idle_time

        except Exception as e:
            logger.error(f"Error getting idle time: {e}")
            return 0.0