"""Base class for platform-specific monitoring."""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple, Union


class BaseMonitor(ABC):
    """Base class for platform-specific monitoring."""

    @abstractmethod
    def get_active_window_info(self) -> Tuple[str, str]:
        """Get information about the currently active window.

        Returns:
            tuple: (window_title, application_name)
        """
        pass

    @abstractmethod
    def get_idle_time(self) -> float:
        """Get system idle time in seconds.

        Returns:
            float: Idle time in seconds
        """
        pass

    @abstractmethod
    def is_screen_locked(self) -> bool:
        """Check if screen is locked.

        Returns:
            bool: True if screen is locked, False otherwise
        """
        pass
