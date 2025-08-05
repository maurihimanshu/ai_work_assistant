"""End-to-end tests for AI Work Assistant."""

import json
import logging
import os
import shutil
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Generator, List, Optional

import pytest
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from src.core.entities.activity import Activity
from src.core.events.event_dispatcher import EventDispatcher
from src.core.interfaces.activity_repository import ActivityRepository
from src.core.services.activity_monitor import ActivityMonitor
from src.core.services.analytics_service import AnalyticsService
from src.core.services.session_service import SessionService
from src.core.services.task_suggestion_service import TaskSuggestionService
from src.presentation.ui.dashboard import Dashboard
from src.presentation.ui.settings_dialog import SettingsDialog
from src.presentation.ui.system_tray import SystemTrayApp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockRepository(ActivityRepository):
    """Mock repository for testing."""

    def __init__(self):
        """Initialize mock repository."""
        self.activities: Dict[str, Activity] = {}

    def add(self, activity: Activity) -> str:
        """Add a new activity."""
        activity_id = str(uuid.uuid4())
        self.activities[activity_id] = activity
        return activity_id

    def get(self, activity_id: str) -> Optional[Activity]:
        """Get activity by ID."""
        return self.activities.get(activity_id)

    def get_all(self) -> List[Activity]:
        """Get all activities."""
        return list(self.activities.values())

    def get_by_timerange(
        self, start_time: datetime, end_time: datetime
    ) -> List[Activity]:
        """Get activities in time range."""
        return [
            a
            for a in self.activities.values()
            if a.start_time >= start_time and (not a.end_time or a.end_time <= end_time)
        ]

    def get_by_app(self, app_name: str) -> List[Activity]:
        """Get activities by app name."""
        return [a for a in self.activities.values() if a.app_name == app_name]

    def update(self, activity: Activity) -> bool:
        """Update an activity."""
        if not activity.id or activity.id not in self.activities:
            return False
        self.activities[activity.id] = activity
        return True

    def delete(self, activity_id: str) -> bool:
        """Delete an activity."""
        if activity_id not in self.activities:
            return False
        del self.activities[activity_id]
        return True

    def delete_by_timerange(self, start_time: datetime, end_time: datetime) -> None:
        """Delete activities in time range."""
        to_delete = [
            aid
            for aid, a in self.activities.items()
            if a.start_time >= start_time and (not a.end_time or a.end_time <= end_time)
        ]
        for aid in to_delete:
            del self.activities[aid]

    def cleanup_old_activities(self, before_date: datetime) -> int:
        """Delete activities older than the specified date."""
        to_delete = [
            aid for aid, a in self.activities.items() if a.start_time < before_date
        ]
        for aid in to_delete:
            del self.activities[aid]
        return len(to_delete)

    def clear(self) -> None:
        """Clear all activities."""
        self.activities.clear()


@pytest.fixture
def mock_repository():
    """Create mock repository for testing."""
    return MockRepository()


@pytest.fixture(scope="session")
def test_app() -> Generator[QApplication, None, None]:
    """Create QApplication for testing."""
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    yield app
    app.quit()


@pytest.fixture
def test_dir(tmp_path) -> Path:
    """Create test directory structure."""
    # Create directories
    data_dir = tmp_path / "data"
    config_dir = tmp_path / "config"
    session_dir = tmp_path / "sessions"

    data_dir.mkdir()
    config_dir.mkdir()
    session_dir.mkdir()

    # Create default config
    config = {
        "session": {"inactivity_timeout": 30, "auto_start": False},
        "notifications": {
            "show_productivity_alerts": True,
            "show_suggestions": True,
            "duration": 5,
        },
        "privacy": {
            "data_retention_days": 30,
            "collect_app_usage": True,
            "collect_window_titles": False,
        },
        "analytics": {"productivity_threshold": 70, "analysis_window_days": 7},
        "ml": {"enable_predictions": True, "prediction_confidence": 80},
    }

    config_path = config_dir / "settings.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    yield tmp_path

    # Cleanup
    shutil.rmtree(tmp_path)


@pytest.fixture
def app_instance(test_app, test_dir, mock_repository):
    """Create application instance with all components."""
    # Create services
    dispatcher = EventDispatcher()

    session_service = SessionService(
        repository=mock_repository,
        event_dispatcher=dispatcher,
        session_dir=str(test_dir / "sessions"),
    )

    analytics_service = AnalyticsService(
        repository=mock_repository, event_dispatcher=dispatcher, categorizer=None
    )

    suggestion_service = TaskSuggestionService(
        repository=mock_repository,
        event_dispatcher=dispatcher,
        categorizer=None,
        learner=None,
    )

    monitor = ActivityMonitor(repository=mock_repository, event_dispatcher=dispatcher)

    # Create UI
    tray = SystemTrayApp(
        session_service=session_service,
        analytics_service=analytics_service,
        suggestion_service=suggestion_service,
        event_dispatcher=dispatcher,
    )

    return {
        "dispatcher": dispatcher,
        "session_service": session_service,
        "analytics_service": analytics_service,
        "suggestion_service": suggestion_service,
        "monitor": monitor,
        "tray": tray,
    }


def test_complete_workflow(test_app, app_instance, qtbot):
    """Test complete application workflow."""
    # Get components
    tray = app_instance["tray"]
    session_service = app_instance["session_service"]

    # 1. Start application
    assert tray.isVisible()

    # 2. Start session
    tray.start_session_action.trigger()
    assert session_service.current_session_id is not None
    assert not tray.start_session_action.isEnabled()
    assert tray.end_session_action.isEnabled()

    # 3. Open dashboard
    tray.show_dashboard_action.trigger()
    dashboard = None
    for widget in QApplication.topLevelWidgets():
        if isinstance(widget, Dashboard):
            dashboard = widget
            break
    assert dashboard is not None
    assert dashboard.isVisible()

    # 4. Check dashboard updates
    initial_data = dashboard.current_report
    QTest.qWait(2000)  # Wait for update
    dashboard.update_data()
    assert dashboard.current_report != initial_data

    # 5. Open settings
    tray.show_settings_action.trigger()
    settings = None
    for widget in QApplication.topLevelWidgets():
        if isinstance(widget, SettingsDialog):
            settings = widget
            break
    assert settings is not None
    assert settings.isVisible()

    # 6. Change settings
    settings.inactivity_timeout.setValue(45)
    settings.show_productivity_alerts.setChecked(True)
    settings._save_settings()
    assert not settings.isVisible()

    # 7. End session
    tray.end_session_action.trigger()
    assert session_service.current_session_id is None
    assert tray.start_session_action.isEnabled()
    assert not tray.end_session_action.isEnabled()

    # 8. Close application
    dashboard.close()
    assert not dashboard.isVisible()
    tray.setVisible(False)
    assert not tray.isVisible()


def test_activity_tracking(test_app, app_instance, qtbot):
    """Test activity tracking workflow."""
    monitor = app_instance["monitor"]
    repository = monitor.repository
    initial_count = len(repository.get_all())

    # Simulate activity
    current_time = datetime.now()
    activity = Activity(
        app_name="test_app",
        window_title="Test Window",
        process_id=1000,
        executable_path="/path/to/test",
        start_time=current_time,
        end_time=current_time + timedelta(minutes=1),
        active_time=55,
        idle_time=5,
    )

    # Track activity
    monitor.start_activity(activity)
    QTest.qWait(1000)
    monitor.end_activity(activity)

    # Verify tracking
    final_count = len(repository.get_all())
    assert final_count > initial_count


def test_analytics_workflow(test_app, app_instance, qtbot):
    """Test analytics workflow."""
    analytics = app_instance["analytics_service"]

    # Get initial report
    initial_report = analytics.get_productivity_report(time_window=timedelta(days=1))
    assert initial_report is not None

    # Add test activity
    current_time = datetime.now()
    activity = Activity(
        app_name="test_app",
        window_title="Test Window",
        process_id=1000,
        executable_path="/path/to/test",
        start_time=current_time - timedelta(minutes=30),
        end_time=current_time,
        active_time=1500,
        idle_time=300,
    )
    analytics.repository.save(activity)

    # Get updated report
    updated_report = analytics.get_productivity_report(time_window=timedelta(days=1))
    assert updated_report != initial_report


def test_suggestion_workflow(test_app, app_instance, qtbot):
    """Test task suggestion workflow."""
    suggestion = app_instance["suggestion_service"]

    # Get initial suggestions
    suggestions, score = suggestion.get_current_suggestions()
    assert isinstance(suggestions, list)
    assert isinstance(score, float)

    # Add test activity
    current_time = datetime.now()
    activity = Activity(
        app_name="test_app",
        window_title="Test Window",
        process_id=1000,
        executable_path="/path/to/test",
        start_time=current_time - timedelta(minutes=30),
        end_time=current_time,
        active_time=1500,
        idle_time=300,
    )
    suggestion.repository.save(activity)

    # Get updated suggestions
    new_suggestions, new_score = suggestion.get_current_suggestions()
    assert new_suggestions != suggestions or new_score != score


def test_session_workflow(test_app, app_instance, qtbot):
    """Test session management workflow."""
    session = app_instance["session_service"]

    # Start session
    session_id = session.start_session()
    assert session_id is not None
    assert session.current_session_id == session_id

    # Update session state
    session.update_session_state("test_app", {"window": "main", "position": [100, 100]})

    # Get recent sessions
    recent = session.get_recent_sessions()
    assert len(recent) > 0
    assert recent[0]["id"] == session_id

    # End session
    session.end_session()
    assert session.current_session_id is None

    # Restore session
    state = session.restore_session(session_id)
    assert state is not None
    assert state["id"] == session_id


def test_error_handling(test_app, app_instance, qtbot):
    """Test error handling in workflows."""
    tray = app_instance["tray"]
    session = app_instance["session_service"]

    # Test invalid session restoration
    with pytest.raises(FileNotFoundError):
        session.restore_session("invalid_session")

    # Test UI error handling
    tray.show_dashboard_action.trigger()
    dashboard = None
    for widget in QApplication.topLevelWidgets():
        if isinstance(widget, Dashboard):
            dashboard = widget
            break
    assert dashboard is not None

    # Simulate error in data update
    session.repository.get_by_timerange = lambda *args: None
    dashboard.update_data()  # Should not raise exception

    # Test settings error handling
    tray.show_settings_action.trigger()
    settings = None
    for widget in QApplication.topLevelWidgets():
        if isinstance(widget, SettingsDialog):
            settings = widget
            break
    assert settings is not None

    # Simulate error in settings save
    settings.config_path = Path("/invalid/path/settings.json")
    settings._save_settings()  # Should not raise exception


def test_data_persistence(test_app, app_instance, test_dir):
    """Test data persistence across sessions."""
    session = app_instance["session_service"]

    # Create test data
    session_id = session.start_session()
    session.update_session_state("test_app", {"state": "test"})
    session.end_session()

    # Verify file creation
    session_file = test_dir / "sessions" / f"session_{session_id}.json"
    assert session_file.exists()

    # Read file content
    with open(session_file, "r") as f:
        data = json.load(f)
        assert data["id"] == session_id
        assert "state" in data
        assert "test_app" in data["state"]


def test_system_integration(test_app, app_instance, qtbot):
    """Test system component integration."""
    dispatcher = app_instance["dispatcher"]
    monitor = app_instance["monitor"]
    analytics = app_instance["analytics_service"]
    suggestion = app_instance["suggestion_service"]

    # Track event propagation
    received_events = []

    def event_handler(event):
        received_events.append(event)

    # Subscribe to events
    dispatcher.subscribe(event_handler, "activity_start")
    dispatcher.subscribe(event_handler, "activity_end")
    dispatcher.subscribe(event_handler, "productivity_alert")

    # Generate activity
    current_time = datetime.now()
    activity = Activity(
        app_name="test_app",
        window_title="Test Window",
        process_id=1000,
        executable_path="/path/to/test",
        start_time=current_time,
        end_time=current_time + timedelta(minutes=1),
        active_time=55,
        idle_time=5,
    )

    # Track activity
    monitor.start_activity(activity)
    QTest.qWait(1000)
    monitor.end_activity(activity)

    # Verify event propagation
    assert len(received_events) >= 2  # At least start and end events

    # Verify analytics update
    report = analytics.get_productivity_report(time_window=timedelta(days=1))
    assert report is not None

    # Verify suggestions update
    suggestions, score = suggestion.get_current_suggestions()
    assert isinstance(suggestions, list)
    assert isinstance(score, float)
