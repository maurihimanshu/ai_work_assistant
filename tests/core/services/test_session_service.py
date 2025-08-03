"""Tests for the SessionService."""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.core.events.event_dispatcher import EventDispatcher
from src.core.services.session_service import SessionService


@pytest.fixture
def mock_repository():
    """Create mock repository."""
    return MagicMock()


@pytest.fixture
def mock_dispatcher():
    """Create mock event dispatcher."""
    return MagicMock(spec=EventDispatcher)


@pytest.fixture
def temp_session_dir(tmp_path):
    """Create a temporary directory for testing."""
    test_dir = tmp_path / "sessions"
    test_dir.mkdir()
    return str(test_dir)


@pytest.fixture
def session_service(temp_session_dir, mock_repository, mock_dispatcher):
    """Create a session service for testing."""
    service = SessionService(
        repository=mock_repository,
        event_dispatcher=mock_dispatcher,
        session_dir=temp_session_dir,
        inactivity_threshold=timedelta(minutes=30),
        auto_save_interval=timedelta(minutes=5)
    )
    yield service
    # Clean up any open files
    if service.current_session_id:
        service.end_session()


def test_session_initialization(session_service):
    """Test session service initialization."""
    assert session_service.current_session_id is None
    assert session_service.last_activity_time is None
    assert session_service.last_save_time is None
    assert len(session_service.active_apps) == 0
    assert isinstance(session_service.session_state, dict)
    assert session_service.session_state['state'] == {}


def test_session_state_persistence(session_service, temp_session_dir):
    """Test session state saving and loading."""
    # Start session and update state
    session_id = session_service.start_session()
    app_name = "test_app"
    state_data = {"window": "main", "position": [100, 100]}

    # Update state and force save
    session_service.update_session_state(app_name, state_data)
    session_service._save_session_state()  # Force immediate save

    # Verify file was created
    session_file = Path(temp_session_dir) / f"session_{session_id}.json"
    assert session_file.exists()

    # Verify file contents
    with open(session_file, 'r') as f:
        saved_state = json.load(f)
        assert saved_state['id'] == session_id
        assert saved_state['state'] == {app_name: state_data}
        assert 'start_time' in saved_state
        assert 'end_time' not in saved_state

    # Test state removal
    session_service.remove_app_state(app_name)
    with open(session_file, 'r') as f:
        saved_state = json.load(f)
        assert app_name not in saved_state['state']


def test_recent_sessions(session_service):
    """Test recent sessions retrieval."""
    # Create multiple sessions
    sessions = []
    for i in range(3):
        session_id = session_service.start_session()
        sessions.append(session_id)
        session_service.update_session_state(f"app_{i}", {"data": i})
        session_service._save_session_state()  # Force immediate save
        session_service.end_session()
        # Ensure file handles are closed
        import gc
        gc.collect()
        time.sleep(0.1)  # Add delay to ensure different timestamps

    # Get recent sessions
    recent = session_service.get_recent_sessions(limit=2)
    assert len(recent) == 2
    # Should be ordered by start time (most recent first)
    assert recent[0]['id'] == sessions[-1]
    assert recent[1]['id'] == sessions[-2]
    assert recent[0]['active_apps'] == ['app_2']
    assert recent[1]['active_apps'] == ['app_1']

    # Test with invalid files
    invalid_file = Path(session_service.session_dir) / "session_invalid.json"
    invalid_file.write_text("invalid json")
    recent = session_service.get_recent_sessions(limit=2)
    assert len(recent) == 2


def test_session_cleanup(session_service):
    """Test old session cleanup."""
    # Create old and new sessions
    old_session = session_service.start_session()
    session_service.update_session_state("test_app", {"data": "old"})
    session_service._save_session_state()
    session_service.end_session()

    # Ensure file handles are closed
    import gc
    gc.collect()
    time.sleep(0.1)  # Ensure different timestamps

    # Create a new session
    new_session = session_service.start_session()
    session_service.update_session_state("test_app", {"data": "new"})
    session_service._save_session_state()
    session_service.end_session()

    # Ensure file handles are closed
    gc.collect()
    time.sleep(0.1)  # Ensure different timestamps

    # Simulate old file by modifying session data
    old_file = session_service._get_session_file(old_session)
    with open(old_file, 'r+') as f:
        data = json.load(f)
        data['start_time'] = (datetime.now() - timedelta(days=31)).isoformat()
        data['end_time'] = (datetime.now() - timedelta(days=31)).isoformat()
        f.seek(0)
        json.dump(data, f)
        f.truncate()

    # Ensure file handle is closed
    gc.collect()
    time.sleep(0.1)  # Ensure file handle is released

    # Create an invalid file
    invalid_file = Path(session_service.session_dir) / "session_invalid.json"
    invalid_file.write_text("invalid json")

    # Run cleanup with shorter max age to ensure new session is kept
    session_service.cleanup_old_sessions(max_age=timedelta(days=1))

    # Old session file should be deleted
    assert not old_file.exists()
    # Invalid file should be deleted
    assert not invalid_file.exists()
    # New session file should still exist
    new_file = session_service._get_session_file(new_session)
    assert new_file.exists()


def test_session_timeout(session_service):
    """Test session timeout detection."""
    session_service.start_session()
    assert not session_service.check_session_timeout()

    # Simulate inactivity
    session_service.last_activity_time = datetime.now() - timedelta(minutes=31)
    assert session_service.check_session_timeout()


def test_session_restore(session_service):
    """Test session restoration."""
    # Create and save a session
    session_id = session_service.start_session()
    session_service.update_session_state("test_app", {"data": "test"})
    session_service._save_session_state()
    session_service.end_session()

    # Restore session
    restored_state = session_service.restore_session(session_id)
    assert restored_state['id'] == session_id
    assert "test_app" in restored_state['state']

    # Test restoring non-existent session
    with pytest.raises(FileNotFoundError):
        session_service.restore_session("nonexistent")


def test_get_session_activities(session_service, mock_repository):
    """Test getting session activities."""
    # Create a session
    session_id = session_service.start_session()
    session_service.end_session()

    # Mock repository response
    mock_activities = [MagicMock(), MagicMock()]
    mock_repository.get_by_timerange.return_value = mock_activities

    # Get activities
    activities = session_service.get_session_activities(session_id)
    assert activities == mock_activities

    # Test with non-existent session
    activities = session_service.get_session_activities("nonexistent")
    assert activities == []


def test_auto_save_interval(session_service):
    """Test auto-save functionality."""
    session_id = session_service.start_session()
    app_name = "test_app"

    # First update should save immediately
    session_service.update_session_state(app_name, {"data": 1})
    first_save_time = session_service.last_save_time

    # Update within auto-save interval shouldn't trigger save
    session_service.update_session_state(app_name, {"data": 2})
    assert session_service.last_save_time == first_save_time

    # Simulate auto-save interval passed
    session_service.last_save_time = datetime.now() - timedelta(minutes=6)
    session_service.update_session_state(app_name, {"data": 3})
    assert session_service.last_save_time > first_save_time