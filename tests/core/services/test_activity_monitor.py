"""Tests for the ActivityMonitor service."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.core.entities.activity import Activity
from src.core.events.event_dispatcher import EventDispatcher
from src.core.services.activity_monitor import ActivityMonitor


@pytest.fixture
def mock_repository():
    """Create a mock activity repository."""
    return MagicMock()


@pytest.fixture
def event_dispatcher():
    """Create an event dispatcher instance."""
    return EventDispatcher()


@pytest.fixture
def mock_platform_monitor():
    """Create a mock platform monitor."""
    monitor = MagicMock()
    monitor.get_active_window_info.return_value = (
        "test_app.exe",
        "Test Window",
        12345,
        r"C:\test\test_app.exe",
    )
    monitor.get_idle_time.return_value = 0
    return monitor


@pytest.fixture
def monitor(mock_repository, event_dispatcher, mock_platform_monitor):
    """Create an ActivityMonitor instance with mocks."""
    with patch(
        "src.core.services.activity_monitor.create_platform_monitor"
    ) as mock_create:
        mock_create.return_value = mock_platform_monitor
        return ActivityMonitor(
            repository=mock_repository,
            event_dispatcher=event_dispatcher,
            idle_threshold=300,
            update_interval=1,
        )


def test_monitor_initialization(monitor, mock_repository, event_dispatcher):
    """Test monitor initialization."""
    assert monitor.repository == mock_repository
    assert monitor.event_dispatcher == event_dispatcher
    assert monitor.idle_threshold == 300
    assert monitor.update_interval == 1
    assert monitor.current_activity is None


def test_get_active_window_info(monitor, mock_platform_monitor):
    """Test getting active window information."""
    app_name, window_title, pid, exe_path = monitor._get_active_window_info()

    assert app_name == "test_app.exe"
    assert window_title == "Test Window"
    assert pid == 12345
    assert exe_path == r"C:\test\test_app.exe"
    assert mock_platform_monitor.get_active_window_info.called


def test_is_idle_detection(monitor, mock_platform_monitor):
    """Test idle detection."""
    # Not idle
    mock_platform_monitor.get_idle_time.return_value = 0
    assert not monitor._is_idle()

    # Idle
    mock_platform_monitor.get_idle_time.return_value = monitor.idle_threshold + 10
    assert monitor._is_idle()


def test_update_activity_new_window(monitor, mock_repository, mock_platform_monitor):
    """Test updating activity when window changes."""
    # First update - should create new activity
    monitor.update_activity()

    assert monitor.current_activity is not None
    assert monitor.current_activity.app_name == "test_app.exe"
    assert mock_repository.add.called

    # Change window
    mock_platform_monitor.get_active_window_info.return_value = (
        "another_app.exe",
        "Another Window",
        67890,
        r"C:\test\another_app.exe",
    )

    # Second update - should save current and create new
    monitor.update_activity()

    assert monitor.current_activity.app_name == "another_app.exe"
    assert mock_repository.update.called


def test_cleanup_old_data(monitor, mock_repository):
    """Test cleaning up old data."""
    monitor.cleanup_old_data(retention_days=30)

    cutoff_date = datetime.now() - timedelta(days=30)
    mock_repository.cleanup_old_activities.assert_called_once()
    assert (
        mock_repository.cleanup_old_activities.call_args[0][0].date()
        == cutoff_date.date()
    )


@patch("src.core.services.activity_monitor.time.sleep", side_effect=KeyboardInterrupt)
def test_start_monitoring_graceful_shutdown(
    mock_sleep, monitor, mock_repository, mock_platform_monitor
):
    """Test graceful shutdown of monitoring."""
    # Start monitoring (will raise KeyboardInterrupt due to mock)
    monitor.start_monitoring()

    # Verify current activity was saved
    assert mock_repository.update.called
