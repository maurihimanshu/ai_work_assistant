"""Platform-specific activity monitoring."""

import logging
import sys
from typing import Optional, Tuple

from .base_monitor import BaseMonitor
from .linux_monitor import LinuxMonitor
from .macos_monitor import MacOSMonitor
from .windows_monitor import WindowsMonitor

logger = logging.getLogger(__name__)

class PlatformMonitor:
    """Platform-agnostic monitor that delegates to platform-specific implementations."""

    def __init__(self):
        """Initialize platform monitor."""
        self._monitor = self._create_platform_monitor()
        logger.info(f"Initialized platform monitor for {sys.platform}")

    def _create_platform_monitor(self) -> BaseMonitor:
        """Create appropriate platform monitor.

        Returns:
            BaseMonitor: Platform-specific monitor instance

        Raises:
            NotImplementedError: If platform is not supported
        """
        platform = sys.platform

        try:
            if platform == "win32":
                return WindowsMonitor()
            elif platform == "linux":
                return LinuxMonitor()
            elif platform == "darwin":
                return MacOSMonitor()
            else:
                raise NotImplementedError(f"Platform '{platform}' is not supported")
        except Exception as e:
            logger.error(f"Failed to create platform monitor: {e}", exc_info=True)
            raise

    def get_active_window_info(self) -> Tuple[str, str]:
        """Get information about the currently active window.

        Returns:
            tuple: (window_title, application_name)
        """
        try:
            return self._monitor.get_active_window_info()
        except Exception as e:
            logger.error(f"Error getting active window info: {e}", exc_info=True)
            return ("Unknown", "Unknown")

    def get_idle_time(self) -> float:
        """Get system idle time in seconds.

        Returns:
            float: Idle time in seconds
        """
        try:
            return self._monitor.get_idle_time()
        except Exception as e:
            logger.error(f"Error getting idle time: {e}", exc_info=True)
            return 0.0

    def is_screen_locked(self) -> bool:
        """Check if screen is locked.

        Returns:
            bool: True if screen is locked, False otherwise
        """
        try:
            return self._monitor.is_screen_locked()
        except Exception as e:
            logger.error(f"Error checking screen lock: {e}", exc_info=True)
            return False
