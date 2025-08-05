"""Performance tests for AI Work Assistant."""

import json
import logging
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import numpy as np
import pytest
from PyQt6.QtCore import QTimer

from src.core.entities.activity import Activity
from src.core.events.event_dispatcher import EventDispatcher
from src.core.events.event_types import (
    ActivityEndEvent,
    ActivityStartEvent,
    SystemStatusEvent,
)
from src.core.services.activity_monitor import ActivityMonitor
from src.core.services.analytics_service import AnalyticsService
from src.core.services.session_service import SessionService
from src.core.services.task_suggestion_service import TaskSuggestionService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture
def sample_activities(tmp_path) -> List[Activity]:
    """Create sample activities for testing.

    Args:
        tmp_path: Temporary directory path

    Returns:
        list: Sample activities
    """
    activities = []
    current_time = datetime.now()

    for i in range(1000):  # Generate 1000 activities
        start_time = current_time - timedelta(hours=i)
        end_time = start_time + timedelta(minutes=random.randint(10, 60))

        activity = Activity(
            app_name=f"test_app_{i % 10}",  # 10 different apps
            window_title=f"Test Window {i}",
            process_id=1000 + i,
            executable_path=f"/path/to/test_{i}",
            start_time=start_time,
            end_time=end_time,
            active_time=random.randint(300, 3000),  # 5-50 minutes
            idle_time=random.randint(0, 300),  # 0-5 minutes
        )
        activities.append(activity)

    return activities


@pytest.fixture
def mock_repository(sample_activities):
    """Create mock repository with sample data."""

    class MockRepository:
        def __init__(self, activities):
            self.activities = activities

        def get_by_timerange(self, start_time, end_time):
            return [
                a
                for a in self.activities
                if a.start_time >= start_time
                and (a.end_time or datetime.now()) <= end_time
            ]

        def save(self, activity):
            self.activities.append(activity)

        def get_all(self):
            return self.activities

    return MockRepository(sample_activities)


@pytest.mark.benchmark(min_rounds=100, max_time=1.0, warmup=True)
def test_activity_monitor_performance(benchmark, mock_repository):
    """Test activity monitor performance."""
    dispatcher = EventDispatcher()
    monitor = ActivityMonitor(mock_repository, dispatcher)

    def monitor_activity():
        """Simulate activity monitoring."""
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

        # Start activity
        dispatcher.dispatch(
            ActivityStartEvent(activity=activity, timestamp=current_time)
        )

        # End activity
        dispatcher.dispatch(
            ActivityEndEvent(activity=activity, duration=60, timestamp=current_time)
        )

    # Benchmark activity monitoring
    benchmark(monitor_activity)


@pytest.mark.benchmark(min_rounds=100, max_time=1.0, warmup=True)
def test_analytics_service_performance(benchmark, mock_repository):
    """Test analytics service performance."""
    dispatcher = EventDispatcher()
    analytics = AnalyticsService(
        repository=mock_repository, event_dispatcher=dispatcher, categorizer=None
    )

    def analyze_data():
        """Run analytics calculations."""
        report = analytics.get_productivity_report(time_window=timedelta(days=7))
        assert report is not None
        assert "daily_metrics" in report
        assert "productivity_trends" in report  # Changed from time_patterns
        assert "app_patterns" in report

    # Benchmark analytics
    benchmark(analyze_data)


@pytest.mark.benchmark(min_rounds=100, max_time=1.0, warmup=True)
def test_session_service_performance(benchmark, mock_repository, tmp_path):
    """Test session service performance."""
    dispatcher = EventDispatcher()
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()

    service = SessionService(
        repository=mock_repository,
        event_dispatcher=dispatcher,
        session_dir=str(session_dir),
    )

    def session_operations():
        """Run session operations."""
        # Start session
        session_id = service.start_session()

        # Update state
        for i in range(10):  # Simulate 10 app states
            service.update_session_state(f"app_{i}", {"state": f"state_{i}"})

        # End session
        service.end_session()

        # Restore session
        state = service.restore_session(session_id)
        assert state is not None

    # Benchmark session operations
    benchmark(session_operations)


@pytest.mark.benchmark(min_rounds=100, max_time=1.0, warmup=True)
def test_task_suggestion_performance(benchmark, mock_repository):
    """Test task suggestion performance."""
    dispatcher = EventDispatcher()
    categorizer = None  # Mock categorizer would be needed
    learner = None  # Mock learner would be needed

    service = TaskSuggestionService(
        repository=mock_repository,
        event_dispatcher=dispatcher,
        categorizer=categorizer,
        learner=learner,
    )

    def generate_suggestions():
        """Generate task suggestions."""
        suggestions, score = service.get_current_suggestions()
        assert isinstance(suggestions, list)
        assert isinstance(score, float)

    # Benchmark suggestion generation
    benchmark(generate_suggestions)


@pytest.mark.benchmark(min_rounds=100, max_time=1.0, warmup=True)
def test_event_dispatcher_performance(benchmark):
    """Test event dispatcher performance."""
    dispatcher = EventDispatcher()
    current_time = datetime.now()

    def dispatch_events():
        """Dispatch multiple events."""
        received_events = []

        def handler(event):
            received_events.append(event)

        # Subscribe to events
        dispatcher.subscribe(handler, "system_status")

        # Dispatch events
        for i in range(100):  # Dispatch 100 events
            dispatcher.dispatch(
                SystemStatusEvent(status=f"test_{i}", timestamp=current_time)
            )

        # Verify event count
        assert len(received_events) == 100

        # Cleanup
        dispatcher.unsubscribe(handler, "system_status")
        dispatcher.clear_history()

    # Benchmark event dispatching
    benchmark(dispatch_events)


@pytest.mark.performance
@pytest.mark.qt
def test_ui_responsiveness(qtbot, mock_repository):
    """Test UI responsiveness."""
    from src.presentation.ui.dashboard import Dashboard
    from src.presentation.ui.system_tray import SystemTrayApp

    # Create services
    dispatcher = EventDispatcher()
    analytics = AnalyticsService(
        repository=mock_repository, event_dispatcher=dispatcher, categorizer=None
    )
    suggestion = TaskSuggestionService(
        repository=mock_repository,
        event_dispatcher=dispatcher,
        categorizer=None,
        learner=None,
    )
    session = SessionService(repository=mock_repository, event_dispatcher=dispatcher)

    # Create UI components
    dashboard = Dashboard(analytics, suggestion, session)
    tray = SystemTrayApp(session, analytics, suggestion, dispatcher)

    # Show dashboard
    dashboard.show()

    # Measure update time
    start_time = time.time()
    dashboard.update_data()
    update_time = time.time() - start_time

    assert update_time < 0.5  # UI updates should complete in under 500ms


@pytest.mark.benchmark(min_rounds=100, max_time=1.0, warmup=True)
def test_data_storage_performance(benchmark, tmp_path):
    """Test data storage performance."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    def write_data():
        """Write test data to storage."""
        data = {
            "activities": [
                {
                    "app_name": f"app_{i}",
                    "window_title": f"window_{i}",
                    "start_time": datetime.now().isoformat(),
                    "end_time": (datetime.now() + timedelta(minutes=1)).isoformat(),
                    "active_time": 55,
                    "idle_time": 5,
                }
                for i in range(1000)  # Write 1000 activities
            ]
        }

        file_path = data_dir / "test_data.json"
        with open(file_path, "w") as f:
            json.dump(data, f)

        # Verify data
        with open(file_path, "r") as f:
            loaded_data = json.load(f)
            assert len(loaded_data["activities"]) == 1000

    # Benchmark data operations
    benchmark(write_data)


@pytest.mark.performance
def test_memory_usage():
    """Test memory usage."""
    import psutil

    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    # Create test data
    data = []
    for i in range(10000):  # Create 10,000 activities
        data.append(
            {
                "app_name": f"app_{i}",
                "window_title": f"window_{i}",
                "start_time": datetime.now().isoformat(),
                "end_time": (datetime.now() + timedelta(minutes=1)).isoformat(),
                "active_time": 55,
                "idle_time": 5,
            }
        )

    # Measure memory after data creation
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory

    logger.info(f"Memory usage increased by {memory_increase:.2f} MB")
    assert memory_increase < 100  # Should use less than 100MB additional memory
