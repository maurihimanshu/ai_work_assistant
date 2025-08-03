"""Tests for the event system."""

from datetime import datetime
from threading import Thread
from time import sleep
from unittest.mock import MagicMock, patch
import pytest

from src.core.entities.activity import Activity
from src.core.events.event_dispatcher import (
    ActivityEventHandler,
    EventDispatcher,
    HandlerError,
    ProductivityEventHandler,
    SystemEventHandler
)
from src.core.events.event_types import (
    ActivityEndEvent,
    ActivityStartEvent,
    ConfigurationChangeEvent,
    ErrorEvent,
    ProductivityAlertEvent,
    SystemStatusEvent
)


@pytest.fixture
def dispatcher():
    """Create event dispatcher instance."""
    return EventDispatcher()


@pytest.fixture
def sample_activity():
    """Create sample activity."""
    return Activity(
        app_name="test_app",
        window_title="Test Window",
        process_id=1234,
        executable_path="/path/to/test",
        start_time=datetime.now()
    )


@pytest.fixture
def current_time():
    """Create a fixed timestamp for testing."""
    return datetime.now()


def test_event_dispatcher_initialization(dispatcher):
    """Test event dispatcher initialization."""
    assert len(dispatcher._handlers) == 0
    assert len(dispatcher._global_handlers) == 0
    assert len(dispatcher._event_history) == 0
    assert len(dispatcher._handler_errors) == 0


def test_event_subscription(dispatcher):
    """Test event subscription."""
    handler = MagicMock()

    # Subscribe to specific event
    dispatcher.subscribe(handler, "test_event")
    assert len(dispatcher._handlers["test_event"]) == 1

    # Subscribe to all events
    global_handler = MagicMock()
    dispatcher.subscribe(global_handler)
    assert len(dispatcher._global_handlers) == 1


def test_event_unsubscription(dispatcher):
    """Test event unsubscription."""
    handler = MagicMock()

    # Subscribe and unsubscribe from specific event
    dispatcher.subscribe(handler, "test_event")
    dispatcher.unsubscribe(handler, "test_event")
    assert "test_event" not in dispatcher._handlers

    # Subscribe and unsubscribe from all events
    dispatcher.subscribe(handler)
    dispatcher.unsubscribe(handler)
    assert len(dispatcher._global_handlers) == 0

    # Verify error tracking cleanup
    assert handler not in dispatcher._handler_errors


def test_event_validation(dispatcher, current_time, sample_activity):
    """Test event validation."""
    # Test valid event
    event = ActivityStartEvent(
        activity=sample_activity,
        timestamp=current_time
    )
    dispatcher.dispatch(event)  # Should not raise

    # Test invalid timestamp type
    with pytest.raises(ValueError) as exc_info:
        event = ActivityStartEvent(
            activity=sample_activity,
            timestamp="invalid"  # type: ignore
        )
        event.validate()  # Test validation directly
    assert "timestamp must be a datetime object" in str(exc_info.value)

    # Test invalid duration
    with pytest.raises(ValueError) as exc_info:
        event = ActivityEndEvent(
            activity=sample_activity,
            duration=-1,  # Invalid duration
            timestamp=current_time
        )
        event.validate()  # Test validation directly
    assert "duration must be non-negative" in str(exc_info.value)

    # Test configuration change event validation
    with pytest.raises(ValueError) as exc_info:
        event = ConfigurationChangeEvent(
            setting_key="test_setting",
            old_value="old",
            new_value="new",
            timestamp=current_time,
            source=123  # type: ignore
        )
        event.validate()  # Test validation directly
    assert "source must be a string if provided" in str(exc_info.value)


def test_thread_safety(dispatcher, current_time):
    """Test thread safety of event dispatcher."""
    events_dispatched = []

    def slow_handler(event):
        sleep(0.1)  # Simulate slow processing
        events_dispatched.append(event)

    dispatcher.subscribe(slow_handler)

    # Create and start multiple threads
    threads = []
    for i in range(10):
        event = SystemStatusEvent(
            status=f"test_{i}",
            timestamp=current_time
        )
        thread = Thread(target=dispatcher.dispatch, args=(event,))
        threads.append(thread)
        thread.start()

    # Wait for all threads
    for thread in threads:
        thread.join()

    # Verify all events were processed
    assert len(events_dispatched) == 10
    assert len(dispatcher._event_history) == 10


def test_error_recovery(dispatcher, current_time):
    """Test error recovery and retry logic."""
    error_count = 0

    def failing_handler(event):
        nonlocal error_count
        error_count += 1
        if error_count <= 2:  # Fail twice then succeed
            raise Exception("Test error")

    dispatcher.subscribe(failing_handler, "test_event")

    # First attempt - should fail
    event = SystemStatusEvent(
        status="test",
        timestamp=current_time,
        event_type="test_event"
    )
    dispatcher.dispatch(event)

    handler_status = dispatcher.get_handler_status()
    assert handler_status["test_event"][0]["error_count"] == 1

    # Second attempt - should fail
    dispatcher.dispatch(event)
    handler_status = dispatcher.get_handler_status()
    assert handler_status["test_event"][0]["error_count"] == 2

    # Third attempt - should succeed
    dispatcher.dispatch(event)
    handler_status = dispatcher.get_handler_status()
    assert handler_status["test_event"][0]["error_count"] == 0  # Reset after success


def test_handler_error_tracking(dispatcher, current_time):
    """Test handler error tracking and disabling."""
    def failing_handler(event):
        raise Exception("Test error")

    dispatcher.subscribe(failing_handler, "test_event")

    event = SystemStatusEvent(
        status="test",
        timestamp=current_time,
        event_type="test_event"
    )

    # Fail three times
    for _ in range(3):
        dispatcher.dispatch(event)

    # Check handler status
    handler_status = dispatcher.get_handler_status()
    assert len(handler_status["test_event"]) == 1
    assert handler_status["test_event"][0]["error_count"] == 3
    assert handler_status["test_event"][0]["disabled"] is True

def test_activity_event_handler(dispatcher, sample_activity, current_time):
    """Test activity event handler."""
    handler = ActivityEventHandler(dispatcher)

    # Test activity start
    start_event = ActivityStartEvent(
        activity=sample_activity,
        timestamp=current_time
    )
    dispatcher.dispatch(start_event)

    # Test activity end
    end_event = ActivityEndEvent(
        activity=sample_activity,
        duration=60.0,
        timestamp=current_time
    )
    dispatcher.dispatch(end_event)

    assert len(dispatcher.get_recent_events("activity_start")) == 1
    assert len(dispatcher.get_recent_events("activity_end")) == 1


def test_productivity_event_handler(dispatcher, current_time):
    """Test productivity event handler."""
    handler = ProductivityEventHandler(dispatcher)

    event = ProductivityAlertEvent(
        productivity_score=0.75,
        time_window="last_hour",
        suggestions=["Take a break", "Switch tasks"],
        timestamp=current_time
    )
    dispatcher.dispatch(event)

    assert len(dispatcher.get_recent_events("productivity_alert")) == 1


def test_system_event_handler(dispatcher, current_time):
    """Test system event handler."""
    handler = SystemEventHandler(dispatcher)

    # Test status event
    status_event = SystemStatusEvent(
        status="running",
        timestamp=current_time,
        details={"uptime": 3600}
    )
    dispatcher.dispatch(status_event)

    # Test error event
    error_event = ErrorEvent(
        error_type="test_error",
        error_message="Test error occurred",
        timestamp=current_time,
        details={"stack_trace": "..."}
    )
    dispatcher.dispatch(error_event)

    assert len(dispatcher.get_recent_events("system_status")) == 1
    assert len(dispatcher.get_recent_events("error")) == 1


def test_event_history(dispatcher, current_time):
    """Test event history management."""
    # Add events
    for i in range(1100):  # More than _max_history
        event = SystemStatusEvent(
            status=f"test_{i}",
            timestamp=current_time
        )
        dispatcher.dispatch(event)

    # Check history limit
    assert len(dispatcher._event_history) == 1000

    # Test getting recent events
    recent = dispatcher.get_recent_events(limit=10)
    assert len(recent) == 10
    assert recent[-1].status == "test_1099"

    # Test clearing history
    dispatcher.clear_history()
    assert len(dispatcher._event_history) == 0


def test_error_handling(dispatcher, current_time):
    """Test error handling in event dispatch."""
    error_events = []

    def error_handler(event):
        if event.event_type == "error":
            error_events.append(event)

    def failing_handler(event):
        raise Exception("Test error")

    # Subscribe to error events
    dispatcher.subscribe(error_handler, "error")
    dispatcher.subscribe(failing_handler, "test_event")

    event = SystemStatusEvent(
        status="test",
        timestamp=current_time,
        event_type="test_event"
    )

    # Should not raise exception
    dispatcher.dispatch(event)

    # Check error event was created
    assert len(error_events) == 1
    assert error_events[0].error_type == "handler_error"
    assert "Test error" in error_events[0].error_message
    assert error_events[0].details["handler"] == "failing_handler"
    assert error_events[0].details["event_type"] == "test_event"

    # Test validation error
    with pytest.raises(ValueError):
        invalid_event = SystemStatusEvent(
            status="test",
            timestamp="invalid",  # type: ignore
            event_type="test_event"
        )
        dispatcher.dispatch(invalid_event)

    # No error event should be created for validation errors
    assert len(error_events) == 1  # Still only one from before


def test_multiple_handlers(dispatcher, current_time):
    """Test multiple handlers for same event."""
    handler1 = MagicMock()
    handler2 = MagicMock()

    dispatcher.subscribe(handler1, "test_event")
    dispatcher.subscribe(handler2, "test_event")

    event = SystemStatusEvent(
        status="test",
        timestamp=current_time,
        event_type="test_event"
    )
    dispatcher.dispatch(event)

    handler1.assert_called_once_with(event)
    handler2.assert_called_once_with(event)