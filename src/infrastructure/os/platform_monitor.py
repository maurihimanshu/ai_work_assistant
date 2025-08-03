"""Platform-specific activity monitoring."""

import sys
from typing import Optional

from .base_monitor import BaseMonitor
from .linux_monitor import LinuxMonitor
from .macos_monitor import MacOSMonitor
from .windows_monitor import WindowsMonitor


def create_platform_monitor() -> BaseMonitor:
    """Create appropriate platform monitor.

    Returns:
        BaseMonitor: Platform-specific monitor instance

    Raises:
        NotImplementedError: If platform is not supported
    """
    platform = sys.platform

    if platform == 'win32':
        return WindowsMonitor()
    elif platform == 'linux':
        return LinuxMonitor()
    elif platform == 'darwin':
        return MacOSMonitor()
    else:
        raise NotImplementedError(f"Platform '{platform}' is not supported")