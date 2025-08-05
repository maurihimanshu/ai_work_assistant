"""Load tests for AI Work Assistant."""

import logging
import multiprocessing as mp
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import pytest
from PyQt6.QtCore import QThread, QTimer
from PyQt6.QtWidgets import QApplication

from src.core.entities.activity import Activity
from src.core.events.event_dispatcher import EventDispatcher
from src.core.events.event_types import ActivityEndEvent, ActivityStartEvent
from src.core.services.activity_monitor import ActivityMonitor
from src.core.services.analytics_service import AnalyticsService
from src.core.services.session_service import SessionService
from src.core.services.task_suggestion_service import TaskSuggestionService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LoadTestWorker(QThread):
    """Worker thread for load testing."""

    def __init__(self, repository, event_dispatcher, duration: int = 60, parent=None):
        """Initialize worker.

        Args:
            repository: Activity repository
            event_dispatcher: Event dispatcher
            duration: Test duration in seconds
            parent: Parent widget
        """
        super().__init__(parent)
        self.repository = repository
        self.event_dispatcher = event_dispatcher
        self.duration = duration
        self.running = False

    def run(self) -> None:
        """Run load test."""
        self.running = True
        start_time = time.time()

        while self.running and time.time() - start_time < self.duration:
            try:
                # Generate random activity
                current_time = datetime.now()
                activity = Activity(
                    app_name=f"test_app_{random.randint(1, 10)}",
                    window_title=f"Test Window {random.randint(1, 100)}",
                    process_id=random.randint(1000, 9999),
                    executable_path="/path/to/test",
                    start_time=current_time,
                    end_time=current_time + timedelta(minutes=1),
                    active_time=random.randint(30, 60),
                    idle_time=random.randint(0, 10),
                )

                # Dispatch events
                self.event_dispatcher.dispatch(ActivityStartEvent(activity=activity))
                time.sleep(0.1)  # Simulate activity duration
                self.event_dispatcher.dispatch(
                    ActivityEndEvent(activity=activity, duration=60)
                )

            except Exception as e:
                logger.error(f"Error in worker thread: {e}")

            time.sleep(0.1)  # Prevent CPU overload

    def stop(self) -> None:
        """Stop worker."""
        self.running = False


@pytest.fixture
def load_test_app(qtbot):
    """Create QApplication for load testing."""
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    return app


def test_concurrent_activity_monitoring(load_test_app, mock_repository, qtbot):
    """Test concurrent activity monitoring."""
    dispatcher = EventDispatcher()
    monitor = ActivityMonitor(mock_repository, dispatcher)

    # Create workers
    workers = []
    for _ in range(4):  # 4 concurrent workers
        worker = LoadTestWorker(
            mock_repository, dispatcher, duration=10  # 10 seconds test
        )
        workers.append(worker)

    # Start workers
    for worker in workers:
        worker.start()

    # Wait for completion
    for worker in workers:
        worker.wait()
        worker.stop()

    # Verify results
    activities = mock_repository.get_all()
    assert len(activities) > 0
    logger.info(f"Processed {len(activities)} activities")


def test_analytics_under_load(load_test_app, mock_repository, qtbot):
    """Test analytics service under load."""
    dispatcher = EventDispatcher()
    analytics = AnalyticsService(
        repository=mock_repository, event_dispatcher=dispatcher, categorizer=None
    )

    # Create update timer
    update_times = []

    def update_analytics():
        """Update analytics and measure time."""
        start_time = time.time()
        report = analytics.get_productivity_report(time_window=timedelta(days=1))
        update_time = time.time() - start_time
        update_times.append(update_time)

    timer = QTimer()
    timer.timeout.connect(update_analytics)
    timer.start(1000)  # Update every second

    # Create activity generator
    worker = LoadTestWorker(mock_repository, dispatcher, duration=10)  # 10 seconds test
    worker.start()

    # Wait for completion
    worker.wait()
    worker.stop()
    timer.stop()

    # Verify performance
    avg_update_time = sum(update_times) / len(update_times)
    logger.info(f"Average analytics update time: {avg_update_time:.3f}s")
    assert avg_update_time < 0.5  # Should update in under 500ms


def test_session_management_under_load(load_test_app, mock_repository, tmp_path, qtbot):
    """Test session management under load."""
    dispatcher = EventDispatcher()
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()

    service = SessionService(
        repository=mock_repository,
        event_dispatcher=dispatcher,
        session_dir=str(session_dir),
    )

    # Track session operations
    operation_times = []

    def run_session_operations():
        """Run session operations and measure time."""
        start_time = time.time()

        # Start session
        session_id = service.start_session()

        # Update state
        for i in range(10):
            service.update_session_state(f"app_{i}", {"state": f"state_{i}"})

        # End session
        service.end_session()

        # Restore session
        service.restore_session(session_id)

        operation_time = time.time() - start_time
        operation_times.append(operation_time)

    # Create workers
    workers = []
    for _ in range(4):  # 4 concurrent workers
        worker = QThread()
        worker.run = run_session_operations
        workers.append(worker)

    # Run operations
    for _ in range(10):  # 10 iterations
        for worker in workers:
            worker.start()

        # Wait for completion
        for worker in workers:
            worker.wait()

    # Verify performance
    avg_operation_time = sum(operation_times) / len(operation_times)
    logger.info(f"Average session operation time: {avg_operation_time:.3f}s")
    assert avg_operation_time < 0.2  # Should complete in under 200ms


def test_suggestion_service_under_load(load_test_app, mock_repository, qtbot):
    """Test suggestion service under load."""
    dispatcher = EventDispatcher()
    service = TaskSuggestionService(
        repository=mock_repository,
        event_dispatcher=dispatcher,
        categorizer=None,
        learner=None,
    )

    # Track suggestion times
    suggestion_times = []

    def get_suggestions():
        """Get suggestions and measure time."""
        start_time = time.time()
        suggestions, score = service.get_current_suggestions()
        suggestion_time = time.time() - start_time
        suggestion_times.append(suggestion_time)

        assert isinstance(suggestions, list)
        assert isinstance(score, float)

    # Create suggestion timer
    timer = QTimer()
    timer.timeout.connect(get_suggestions)
    timer.start(100)  # Get suggestions every 100ms

    # Create activity generator
    worker = LoadTestWorker(mock_repository, dispatcher, duration=10)  # 10 seconds test
    worker.start()

    # Wait for completion
    worker.wait()
    worker.stop()
    timer.stop()

    # Verify performance
    avg_suggestion_time = sum(suggestion_times) / len(suggestion_times)
    logger.info(f"Average suggestion time: {avg_suggestion_time:.3f}s")
    assert avg_suggestion_time < 0.1  # Should complete in under 100ms


def test_ui_responsiveness_under_load(load_test_app, mock_repository, qtbot):
    """Test UI responsiveness under load."""
    from src.presentation.ui.dashboard import Dashboard

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

    # Create dashboard
    dashboard = Dashboard(analytics, suggestion, session)
    dashboard.show()

    # Track update times
    update_times = []

    def measure_update():
        """Measure dashboard update time."""
        start_time = time.time()
        dashboard.update_data()
        update_time = time.time() - start_time
        update_times.append(update_time)

    # Create update timer
    timer = QTimer()
    timer.timeout.connect(measure_update)
    timer.start(500)  # Update every 500ms

    # Create activity generator
    worker = LoadTestWorker(mock_repository, dispatcher, duration=10)  # 10 seconds test
    worker.start()

    # Wait for completion
    worker.wait()
    worker.stop()
    timer.stop()

    # Verify performance
    avg_update_time = sum(update_times) / len(update_times)
    logger.info(f"Average UI update time: {avg_update_time:.3f}s")
    assert avg_update_time < 0.5  # Should update in under 500ms


def test_system_stability(load_test_app, mock_repository, tmp_path):
    """Test system stability under extended load."""
    import psutil

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
    session = SessionService(
        repository=mock_repository,
        event_dispatcher=dispatcher,
        session_dir=str(tmp_path / "sessions"),
    )

    # Track system metrics
    process = psutil.Process()
    initial_memory = process.memory_info().rss
    cpu_percentages = []
    memory_usages = []

    def monitor_system():
        """Monitor system resources."""
        cpu_percentages.append(process.cpu_percent())
        memory_usages.append(process.memory_info().rss - initial_memory)

    # Create monitoring timer
    timer = QTimer()
    timer.timeout.connect(monitor_system)
    timer.start(1000)  # Monitor every second

    # Create workers
    workers = []
    for _ in range(4):  # 4 concurrent workers
        worker = LoadTestWorker(
            mock_repository, dispatcher, duration=30  # 30 seconds test
        )
        workers.append(worker)

    # Start workers
    for worker in workers:
        worker.start()

    # Wait for completion
    for worker in workers:
        worker.wait()
        worker.stop()

    timer.stop()

    # Calculate metrics
    avg_cpu = sum(cpu_percentages) / len(cpu_percentages)
    max_memory = max(memory_usages) / 1024 / 1024  # Convert to MB

    logger.info(f"Average CPU usage: {avg_cpu:.1f}%")
    logger.info(f"Peak memory increase: {max_memory:.1f}MB")

    # Verify system stability
    assert avg_cpu < 50  # Should use less than 50% CPU
    assert max_memory < 200  # Should use less than 200MB additional memory
