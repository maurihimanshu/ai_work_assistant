"""Event dispatcher system for handling and distributing events."""

import logging
import time
from collections import defaultdict
from dataclasses import is_dataclass
from threading import Lock, RLock
from typing import Any, Callable, Dict, List, Optional, Set, Union

from .event_types import (
    ActivityEndEvent,
    ActivityStartEvent,
    BehaviorPatternEvent,
    ConfigurationChangeEvent,
    ErrorEvent,
    IdleEndEvent,
    IdleStartEvent,
    ProductivityAlertEvent,
    SessionEvent,
    SystemStatusEvent,
)

logger = logging.getLogger(__name__)

# Type alias for events
Event = Union[
    ActivityStartEvent,
    ActivityEndEvent,
    IdleStartEvent,
    IdleEndEvent,
    ProductivityAlertEvent,
    BehaviorPatternEvent,
    SessionEvent,
    SystemStatusEvent,
    ErrorEvent,
    ConfigurationChangeEvent,
]


class HandlerError:
    """Tracks handler errors for retry logic."""

    def __init__(self, handler: Callable, event_type: Optional[str]):
        """Initialize handler error tracking.

        Args:
            handler: The event handler function
            event_type: The event type this handler is for
        """
        self.handler = handler
        self.event_type = event_type
        self.error_count = 0
        self.last_error_time = 0
        self.last_error: Optional[Exception] = None
        self.disabled = False

    def record_error(self, error: Exception) -> None:
        """Record a handler error.

        Args:
            error: The exception that occurred
        """
        self.error_count += 1
        self.last_error_time = time.time()
        self.last_error = error

        # Check if should be disabled after recording error
        if self.error_count >= 3:
            self.disabled = True

    def should_retry(self) -> bool:
        """Check if handler should be retried.

        Returns:
            bool: True if handler should be retried
        """
        # Don't retry if already disabled
        if self.disabled:
            return False

        # Wait longer between retries
        if self.error_count > 0:
            wait_time = min(300, 2**self.error_count)  # Max 5 minutes
            if time.time() - self.last_error_time < wait_time:
                return False

        return True

    def reset(self) -> None:
        """Reset error tracking after successful execution."""
        self.error_count = 0
        self.last_error_time = 0
        self.last_error = None
        self.disabled = False


class EventDispatcher:
    """Handles event distribution and management."""

    def __init__(self):
        """Initialize event dispatcher."""
        self._handlers: Dict[str, Set[Callable]] = defaultdict(set)
        self._global_handlers: Set[Callable] = set()
        self._event_history: List[Event] = []
        self._max_history = 1000  # Keep last 1000 events

        # Locks for thread safety
        self._handlers_lock = RLock()  # Reentrant lock for handler operations
        self._history_lock = Lock()  # Lock for event history operations

        # Error tracking
        self._handler_errors: Dict[Callable, HandlerError] = {}
        self._errors_lock = Lock()

    def subscribe(
        self, handler: Callable[[Event], None], event_type: Optional[str] = None
    ) -> None:
        """Subscribe to events.

        Args:
            handler: Event handler function
            event_type: Specific event type to handle (None for all events)
        """
        with self._handlers_lock:
            if event_type:
                self._handlers[event_type].add(handler)
            else:
                self._global_handlers.add(handler)

    def unsubscribe(
        self, handler: Callable[[Event], None], event_type: Optional[str] = None
    ) -> None:
        """Unsubscribe from events.

        Args:
            handler: Event handler function
            event_type: Specific event type to unsubscribe from
        """
        with self._handlers_lock:
            if event_type:
                self._handlers[event_type].discard(handler)
                if not self._handlers[event_type]:
                    del self._handlers[event_type]
            else:
                self._global_handlers.discard(handler)

        # Clean up error tracking
        with self._errors_lock:
            if handler in self._handler_errors:
                del self._handler_errors[handler]

    def _get_handler_error(
        self, handler: Callable, event_type: Optional[str]
    ) -> HandlerError:
        """Get or create handler error tracking.

        Args:
            handler: Event handler function
            event_type: Event type the handler is for

        Returns:
            HandlerError: Error tracking for this handler
        """
        with self._errors_lock:
            if handler not in self._handler_errors:
                self._handler_errors[handler] = HandlerError(handler, event_type)
            return self._handler_errors[handler]

    def _call_handler(
        self,
        handler: Callable,
        event: Event,
        event_type: Optional[str] = None,
        is_error_handler: bool = False,
    ) -> bool:
        """Call a handler with error tracking and retry logic.

        Args:
            handler: Event handler function
            event: Event to handle
            event_type: Event type being handled
            is_error_handler: Whether this is an error handler

        Returns:
            bool: True if handler succeeded, False if it failed
        """
        error_tracker = self._get_handler_error(handler, event_type)

        try:
            handler(event)
            error_tracker.reset()  # Clear errors after success
            return True

        except Exception as e:
            error_tracker.record_error(e)
            logger.error(
                f"Error in handler {handler.__name__} for "
                f"{event_type or 'global'}: {e}",
                exc_info=True,
            )

            # Only disable handler after max retries
            if not error_tracker.should_retry():
                logger.error(
                    f"Handler {handler.__name__} for {event_type or 'global'} "
                    f"disabled after repeated errors"
                )

            # Only create error events for non-error handlers to avoid recursion
            if not is_error_handler:
                try:
                    error_event = ErrorEvent(
                        error_type="handler_error",
                        error_message=str(e),
                        timestamp=event.timestamp,
                        details={
                            "handler": handler.__name__,
                            "event_type": event_type,
                            "error": str(e),
                        },
                    )

                    # Call error handlers directly without validation
                    with self._handlers_lock:
                        error_handlers = list(self._handlers.get("error", set()))

                    for error_handler in error_handlers:
                        try:
                            self._call_handler(
                                error_handler,
                                error_event,
                                "error",
                                is_error_handler=True,
                            )
                        except Exception as e2:
                            logger.error(f"Error in error handler: {e2}", exc_info=True)

                    # Add error event to history after handlers are called
                    with self._history_lock:
                        self._event_history.append(error_event)
                        if len(self._event_history) > self._max_history:
                            self._event_history.pop(0)

                except Exception as e2:
                    logger.error(
                        f"Error creating/dispatching error event: {e2}", exc_info=True
                    )

            return False

    def dispatch(self, event: Event) -> None:
        """Dispatch an event to all relevant handlers.

        Args:
            event: Event to dispatch

        Raises:
            TypeError: If event is not a valid event dataclass
            ValueError: If event validation fails
        """
        try:
            # Validate event
            if not is_dataclass(event):
                raise TypeError("Event must be a dataclass")

            # Use validation mixin
            event.validate()

            # Add to history with thread safety
            with self._history_lock:
                self._event_history.append(event)
                if len(self._event_history) > self._max_history:
                    self._event_history.pop(0)

            # Get handlers with thread safety
            with self._handlers_lock:
                # Make copies to avoid holding the lock during handler execution
                specific_handlers = list(self._handlers.get(event.event_type, set()))
                global_handlers = list(self._global_handlers)

            # Call specific handlers
            for handler in specific_handlers:
                self._call_handler(handler, event, event.event_type)

            # Call global handlers
            for handler in global_handlers:
                self._call_handler(handler, event)

        except (TypeError, ValueError) as e:
            # Log validation errors but don't create error events for them
            logger.error(f"Event validation error: {e}", exc_info=True)
            raise  # Re-raise validation errors

        except Exception as e:
            logger.error(f"Error dispatching event: {e}", exc_info=True)
            # Only create error events for non-validation errors
            try:
                error_event = ErrorEvent(
                    error_type="dispatch_error",
                    error_message=str(e),
                    timestamp=event.timestamp,
                    details={
                        "event_type": getattr(event, "event_type", None),
                        "error": str(e),
                    },
                )

                # Call error handlers directly without validation
                with self._handlers_lock:
                    error_handlers = list(self._handlers.get("error", set()))

                for handler in error_handlers:
                    try:
                        self._call_handler(
                            handler, error_event, "error", is_error_handler=True
                        )
                    except Exception as e2:
                        logger.error(f"Error in error handler: {e2}", exc_info=True)

                # Add error event to history after handlers are called
                with self._history_lock:
                    self._event_history.append(error_event)
                    if len(self._event_history) > self._max_history:
                        self._event_history.pop(0)

            except Exception as e2:
                logger.error(
                    f"Error creating/dispatching error event: {e2}", exc_info=True
                )

    def get_recent_events(
        self, event_type: Optional[str] = None, limit: int = 100
    ) -> List[Event]:
        """Get recent events from history.

        Args:
            event_type: Filter by event type
            limit: Maximum number of events to return

        Returns:
            list: Recent events
        """
        with self._history_lock:
            if event_type:
                events = [e for e in self._event_history if e.event_type == event_type]
            else:
                events = self._event_history.copy()

            return events[-limit:]

    def clear_history(self) -> None:
        """Clear event history."""
        with self._history_lock:
            self._event_history.clear()

    def get_handler_status(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get status of event handlers including error information.

        Returns:
            dict: Handler status information
        """
        status: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        with self._errors_lock:
            for handler, error_info in self._handler_errors.items():
                handler_status = {
                    "handler": handler.__name__,
                    "error_count": error_info.error_count,
                    "last_error_time": error_info.last_error_time,
                    "last_error": str(error_info.last_error)
                    if error_info.last_error
                    else None,
                    "disabled": error_info.disabled,
                }

                event_type = error_info.event_type or "global"
                status[event_type].append(handler_status)

        return dict(status)


class EventHandler:
    """Base class for event handlers."""

    def __init__(self, dispatcher: EventDispatcher):
        """Initialize event handler.

        Args:
            dispatcher: Event dispatcher to use
        """
        self.dispatcher = dispatcher
        self.subscribed_events: Set[str] = set()
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register event handlers.

        Override this method to register handlers for specific events.
        """
        pass

    def handle_event(self, event: Event) -> None:
        """Handle an event.

        Args:
            event: Event to handle
        """
        pass


class ActivityEventHandler(EventHandler):
    """Handles activity-related events."""

    def _register_handlers(self) -> None:
        """Register activity event handlers."""
        self.dispatcher.subscribe(self.handle_event, "activity_start")
        self.dispatcher.subscribe(self.handle_event, "activity_end")
        self.subscribed_events.update(["activity_start", "activity_end"])

    def handle_event(self, event: Event) -> None:
        """Handle activity events.

        Args:
            event: Event to handle
        """
        if event.event_type == "activity_start":
            self._handle_activity_start(event)  # type: ignore
        elif event.event_type == "activity_end":
            self._handle_activity_end(event)  # type: ignore

    def _handle_activity_start(self, event: ActivityStartEvent) -> None:
        """Handle activity start event.

        Args:
            event: Activity start event
        """
        logger.info(f"Activity started: {event.activity.app_name}")

    def _handle_activity_end(self, event: ActivityEndEvent) -> None:
        """Handle activity end event.

        Args:
            event: Activity end event
        """
        logger.info(
            f"Activity ended: {event.activity.app_name} "
            f"(Duration: {event.duration:.2f}s)"
        )


class ProductivityEventHandler(EventHandler):
    """Handles productivity-related events."""

    def _register_handlers(self) -> None:
        """Register productivity event handlers."""
        self.dispatcher.subscribe(self.handle_event, "productivity_alert")
        self.subscribed_events.add("productivity_alert")

    def handle_event(self, event: Event) -> None:
        """Handle productivity events.

        Args:
            event: Event to handle
        """
        if event.event_type == "productivity_alert":
            self._handle_productivity_alert(event)  # type: ignore

    def _handle_productivity_alert(self, event: ProductivityAlertEvent) -> None:
        """Handle productivity alert event.

        Args:
            event: Productivity alert event
        """
        logger.info(
            f"Productivity alert: {event.productivity_score:.2%} "
            f"({event.time_window})"
        )
        if event.suggestions:
            logger.info(f"Suggestions: {', '.join(event.suggestions)}")


class SystemEventHandler(EventHandler):
    """Handles system-related events."""

    def _register_handlers(self) -> None:
        """Register system event handlers."""
        self.dispatcher.subscribe(self.handle_event, "system_status")
        self.dispatcher.subscribe(self.handle_event, "error")
        self.subscribed_events.update(["system_status", "error"])

    def handle_event(self, event: Event) -> None:
        """Handle system events.

        Args:
            event: Event to handle
        """
        if event.event_type == "system_status":
            self._handle_status_update(event)  # type: ignore
        elif event.event_type == "error":
            self._handle_error(event)  # type: ignore

    def _handle_status_update(self, event: SystemStatusEvent) -> None:
        """Handle system status event.

        Args:
            event: System status event
        """
        logger.info(f"System status: {event.status}")
        if event.details:
            logger.debug(f"Status details: {event.details}")

    def _handle_error(self, event: ErrorEvent) -> None:
        """Handle error event.

        Args:
            event: Error event
        """
        logger.error(f"System error ({event.error_type}): {event.error_message}")
        if event.details:
            logger.error(f"Error details: {event.details}")
