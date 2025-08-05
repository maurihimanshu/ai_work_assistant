"""Tests for the Activity entity."""

from datetime import datetime, timedelta

import pytest

from src.core.entities.activity import Activity


def test_activity_creation():
    """Test creating an activity with required fields."""
    now = datetime.now()
    activity = Activity(
        app_name="test_app",
        window_title="Test Window",
        process_id=1234,
        executable_path="/path/to/test",
        start_time=now,
    )

    assert activity.app_name == "test_app"
    assert activity.window_title == "Test Window"
    assert activity.process_id == 1234
    assert activity.executable_path == "/path/to/test"
    assert activity.start_time == now
    assert activity.end_time is None
    assert activity.idle_time == 0.0
    assert activity.active_time == 0.0


def test_activity_update_times_active():
    """Test updating activity times when active."""
    now = datetime.now()
    activity = Activity(
        app_name="test_app",
        window_title="Test Window",
        process_id=1234,
        executable_path="/path/to/test",
        start_time=now,
    )

    # Update time after 5 seconds of activity
    future_time = now + timedelta(seconds=5)
    activity.update_times(future_time, is_idle=False)

    assert activity.end_time is None  # End time should not be set by update_times
    assert activity.active_time == 5.0
    assert activity.idle_time == 0.0


def test_activity_update_times_idle():
    """Test updating activity times when idle."""
    now = datetime.now()
    activity = Activity(
        app_name="test_app",
        window_title="Test Window",
        process_id=1234,
        executable_path="/path/to/test",
        start_time=now,
    )

    # Update time after 5 seconds of idle time
    future_time = now + timedelta(seconds=5)
    activity.update_times(future_time, is_idle=True)

    assert activity.end_time is None  # End time should not be set by update_times
    assert activity.idle_time == 5.0
    assert activity.active_time == 0.0


def test_activity_serialization():
    """Test activity serialization to JSON."""
    now = datetime.now()
    activity = Activity(
        app_name="test_app",
        window_title="Test Window",
        process_id=1234,
        executable_path="/path/to/test",
        start_time=now,
        end_time=now + timedelta(seconds=10),
        active_time=8.0,
        idle_time=2.0,
    )

    # Convert to dict
    activity_dict = activity.to_dict()

    # Convert timestamps to ISO format strings
    activity_dict["start_time"] = activity_dict["start_time"].isoformat()
    activity_dict["end_time"] = activity_dict["end_time"].isoformat()

    # Create new activity from dict
    new_activity = Activity.from_dict(activity_dict)

    assert new_activity.app_name == activity.app_name
    assert new_activity.window_title == activity.window_title
    assert new_activity.process_id == activity.process_id
    assert new_activity.executable_path == activity.executable_path
    assert new_activity.start_time == activity.start_time
    assert new_activity.end_time == activity.end_time
    assert new_activity.active_time == activity.active_time
    assert new_activity.idle_time == activity.idle_time
    assert new_activity.id == activity.id
