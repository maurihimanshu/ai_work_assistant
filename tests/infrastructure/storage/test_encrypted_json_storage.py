"""Tests for the EncryptedJsonStorage class."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from src.core.entities.activity import Activity
from src.infrastructure.storage.encrypted_json_storage import EncryptedJsonStorage


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing."""
    test_dir = tmp_path / "test_storage"
    test_dir.mkdir()
    return test_dir


@pytest.fixture
def storage(temp_dir):
    """Create a storage instance for testing."""
    return EncryptedJsonStorage(str(temp_dir / "test.db"))


@pytest.fixture
def sample_activity():
    """Create a sample activity for testing."""
    return Activity(
        app_name="test_app",
        window_title="Test Window",
        process_id=1234,
        executable_path="/path/test",
        start_time=datetime.now()
    )


def test_storage_initialization(temp_dir):
    """Test storage initialization creates necessary files."""
    storage_path = temp_dir / "test.db"
    storage = EncryptedJsonStorage(str(storage_path))

    assert storage_path.exists()
    assert storage.key_path.exists()
    assert len(storage.key_path.read_bytes()) > 0


def test_encryption_key_persistence(temp_dir):
    """Test encryption key remains consistent across instances."""
    storage1 = EncryptedJsonStorage(str(temp_dir / "test.db"))
    key1 = storage1.encryption_key

    storage2 = EncryptedJsonStorage(str(temp_dir / "test.db"))
    key2 = storage2.encryption_key

    assert key1 == key2


def test_add_activity(storage, sample_activity):
    """Test adding an activity."""
    activity_id = storage.add(sample_activity)

    assert activity_id is not None
    retrieved = storage.get(activity_id)
    assert retrieved is not None
    assert retrieved.app_name == sample_activity.app_name
    assert retrieved.window_title == sample_activity.window_title


def test_get_nonexistent_activity(storage):
    """Test getting a non-existent activity returns None."""
    assert storage.get("nonexistent") is None


def test_update_activity(storage, sample_activity):
    """Test updating an activity."""
    activity_id = storage.add(sample_activity)

    sample_activity.window_title = "Updated Window"
    success = storage.update(sample_activity)

    assert success
    retrieved = storage.get(activity_id)
    assert retrieved.window_title == "Updated Window"


def test_delete_activity(storage, sample_activity):
    """Test deleting an activity."""
    activity_id = storage.add(sample_activity)

    success = storage.delete(activity_id)

    assert success
    assert storage.get(activity_id) is None


def test_get_by_timerange(storage):
    """Test retrieving activities within a time range."""
    now = datetime.now()

    # Create activities at different times
    activities = [
        Activity(
            app_name=f"app_{i}",
            window_title=f"window_{i}",
            process_id=i,
            executable_path=f"/path/{i}",
            start_time=now + timedelta(minutes=i)
        )
        for i in range(5)
    ]

    for activity in activities:
        storage.add(activity)

    # Get activities between 1 and 3 minutes from now
    start_time = now + timedelta(minutes=1)
    end_time = now + timedelta(minutes=3)

    results = storage.get_by_timerange(start_time, end_time)
    assert len(results) == 3  # Should get activities 1, 2, and 3


def test_cleanup_old_activities(storage):
    """Test cleaning up old activities."""
    now = datetime.now()

    # Create some old and new activities
    old_activity = Activity(
        app_name="old_app",
        window_title="Old Window",
        process_id=1,
        executable_path="/path/old",
        start_time=now - timedelta(days=40)
    )

    new_activity = Activity(
        app_name="new_app",
        window_title="New Window",
        process_id=2,
        executable_path="/path/new",
        start_time=now - timedelta(days=5)
    )

    old_id = storage.add(old_activity)
    new_id = storage.add(new_activity)

    # Clean up activities older than 30 days
    deleted_count = storage.cleanup_old_activities(now - timedelta(days=30))

    assert deleted_count == 1
    assert storage.get(old_id) is None
    assert storage.get(new_id) is not None


def test_data_encryption(temp_dir):
    """Test that stored data is actually encrypted."""
    storage_path = temp_dir / "test.db"
    storage = EncryptedJsonStorage(str(storage_path))

    # Add an activity
    activity = Activity(
        app_name="test_app",
        window_title="Test Window",
        process_id=1234,
        executable_path="/path/test",
        start_time=datetime.now()
    )
    storage.add(activity)

    # Read raw file content
    raw_content = storage_path.read_bytes()

    # Verify the content is encrypted (not plain JSON)
    assert b"test_app" not in raw_content
    assert b"Test Window" not in raw_content

    # Verify we can still read it through the storage interface
    activities = storage.get_by_timerange(
        datetime.now() - timedelta(minutes=1),
        datetime.now() + timedelta(minutes=1)
    )
    assert len(activities) == 1
    assert activities[0].app_name == "test_app"