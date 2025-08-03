"""Base class for platform-specific monitoring."""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple


class BaseMonitor(ABC):
    """Base class for platform-specific monitoring."""

    @abstractmethod
    def get_active_window_info(self) -> Dict[str, str]:
        """Get information about the currently active window.

        Returns:
            dict: Window information including:
                - app_name: Name of the application
                - window_title: Title of the window
                - process_id: Process ID
                - executable_path: Path to the executable
        """
        pass

    @abstractmethod
    def get_idle_time(self) -> float:
        """Get system idle time in seconds.

        Returns:
            float: Idle time in seconds
        """
        pass