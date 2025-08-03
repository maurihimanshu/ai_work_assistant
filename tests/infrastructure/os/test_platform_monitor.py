"""Tests for platform-specific monitoring."""

import sys
from unittest.mock import patch

import pytest

from src.infrastructure.os.platform_monitor import create_platform_monitor


def test_create_platform_monitor_windows():
    """Test creating Windows monitor."""
    with patch('sys.platform', 'win32'):
        monitor = create_platform_monitor()
        assert monitor.__class__.__name__ == 'WindowsMonitor'


def test_create_platform_monitor_linux():
    """Test creating Linux monitor."""
    with patch('sys.platform', 'linux'):
        with patch('src.infrastructure.os.platform_monitor.LinuxMonitor') as mock_monitor:
            monitor = create_platform_monitor()
            mock_monitor.assert_called_once()


def test_create_platform_monitor_macos():
    """Test creating macOS monitor."""
    with patch('sys.platform', 'darwin'):
        with patch('src.infrastructure.os.platform_monitor.MacOSMonitor') as mock_monitor:
            monitor = create_platform_monitor()
            mock_monitor.assert_called_once()


def test_create_platform_monitor_unsupported():
    """Test creating monitor for unsupported platform."""
    with patch('sys.platform', 'unsupported'):
        with pytest.raises(NotImplementedError, match="Platform 'unsupported' is not supported"):
            create_platform_monitor()


@pytest.mark.skipif(sys.platform != 'win32', reason="Windows-only test")
def test_windows_monitor_integration():
    """Integration test for Windows monitor."""
    monitor = create_platform_monitor()

    # Test getting window info
    info = monitor.get_active_window_info()
    assert isinstance(info, dict)
    assert 'app_name' in info
    assert 'window_title' in info
    assert 'process_id' in info
    assert 'executable_path' in info

    # Test getting idle time
    idle_time = monitor.get_idle_time()
    assert isinstance(idle_time, float)
    assert idle_time >= 0.0


@pytest.mark.skipif(sys.platform != 'linux', reason="Linux-only test")
def test_linux_monitor_integration():
    """Integration test for Linux monitor."""
    monitor = create_platform_monitor()

    # Test getting window info
    info = monitor.get_active_window_info()
    assert isinstance(info, dict)
    assert 'app_name' in info
    assert 'window_title' in info
    assert 'process_id' in info
    assert 'executable_path' in info

    # Test getting idle time
    idle_time = monitor.get_idle_time()
    assert isinstance(idle_time, float)
    assert idle_time >= 0.0


@pytest.mark.skipif(sys.platform != 'darwin', reason="macOS-only test")
def test_macos_monitor_integration():
    """Integration test for macOS monitor."""
    monitor = create_platform_monitor()

    # Test getting window info
    info = monitor.get_active_window_info()
    assert isinstance(info, dict)
    assert 'app_name' in info
    assert 'window_title' in info
    assert 'process_id' in info
    assert 'executable_path' in info

    # Test getting idle time
    idle_time = monitor.get_idle_time()
    assert isinstance(idle_time, float)
    assert idle_time >= 0.0