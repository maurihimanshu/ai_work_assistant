"""Core service for monitoring user activity."""

import logging
import os
import sys
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Union, cast

# Add the parent directory to Python path to make the src package importable
parent_dir = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from core.entities.activity import Activity
from core.events.event_dispatcher import EventDispatcher
from core.events.event_types import (
    ActivityEndEvent,
    ActivityStartEvent,
    IdleEndEvent,
    IdleStartEvent,
    SystemStatusEvent,
)
from core.interfaces.activity_repository import ActivityRepository
from infrastructure.os.platform_monitor import PlatformMonitor

# Configure logger
logger = logging.getLogger(__name__)


class ActivityMonitor:
    """Service for monitoring and tracking user activity."""

    def __init__(
        self,
        platform_monitor: PlatformMonitor,
        activity_storage: ActivityRepository,
        event_dispatcher: EventDispatcher,
        idle_threshold: int = 300,  # 5 minutes in seconds
        update_interval: int = 1,  # 1 second
    ) -> None:
        """Initialize the activity monitor.

        Args:
            platform_monitor: Platform-specific monitor
            activity_storage: Repository for storing activities
            event_dispatcher: Event dispatcher for system events
            idle_threshold: Time in seconds before considering user idle
            update_interval: Time in seconds between activity checks
        """
        self.platform_monitor = platform_monitor
        self.repository = activity_storage
        self.event_dispatcher = event_dispatcher
        self.idle_threshold = idle_threshold
        self.update_interval = update_interval
        self.current_activity: Optional[Activity] = None
        self.is_idle = False
        self.idle_start_time: Optional[datetime] = None
        self.last_update_time: Optional[datetime] = None

        # Threading control
        self._monitoring_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()

        # Dispatch initial status
        self.event_dispatcher.dispatch(
            SystemStatusEvent(
                status="initialized",
                timestamp=datetime.now(),
                details={
                    "idle_threshold": idle_threshold,
                    "update_interval": update_interval,
                },
            )
        )

    def _get_active_window_info(self) -> Tuple[str, str, int, str]:
        """Get information about the currently active window using platform monitor.

        Returns:
            tuple: A tuple containing (app_name, window_title, process_id, executable_path)
        """
        window_title, app_name = self.platform_monitor.get_active_window_info()
        return (
            app_name,
            window_title,
            0,  # process_id is no longer used
            "",  # executable_path is no longer used
        )

    def _is_idle(self) -> bool:
        """Check if the user is idle using platform monitor.

        Returns:
            bool: True if user is idle, False otherwise
        """
        idle_time = self.platform_monitor.get_idle_time()
        logger.debug(
            f"Current idle time: {idle_time:.1f}s (threshold: {self.idle_threshold}s)"
        )
        return (
            idle_time >= self.idle_threshold or self.platform_monitor.is_screen_locked()
        )

    def _handle_activity_change(
        self, app_name: str, window_title: str, process_id: int, executable_path: str
    ) -> None:
        """Handle change in active window/application.

        Args:
            app_name: Name of the new application
            window_title: Title of the new window
            process_id: Process ID of the new application
            executable_path: Path to the new executable
        """
        current_time = datetime.now()

        # End current activity if exists
        if self.current_activity:
            self.current_activity.end_time = current_time
            duration = (current_time - self.current_activity.start_time).total_seconds()
            total_time = (
                self.current_activity.active_time + self.current_activity.idle_time
            )

            logger.info(
                f"Ending activity: {self.current_activity.app_name} "
                f"(Duration: {duration:.1f}s, Active: {self.current_activity.active_time:.1f}s, "
                f"Idle: {self.current_activity.idle_time:.1f}s, Total: {total_time:.1f}s)"
            )

            # Dispatch activity end event
            self.event_dispatcher.dispatch(
                ActivityEndEvent(
                    activity=self.current_activity,
                    duration=duration,
                    timestamp=current_time,
                )
            )

            # Update repository
            self.repository.update(self.current_activity)

        # Create new activity
        self.current_activity = Activity(
            app_name=app_name,
            window_title=window_title,
            process_id=process_id,
            executable_path=executable_path,
            start_time=current_time,
            active_time=0.0,
            idle_time=0.0,
        )

        logger.info(f"Starting activity: {app_name} ({window_title})")

        # Dispatch activity start event
        self.event_dispatcher.dispatch(
            ActivityStartEvent(activity=self.current_activity, timestamp=current_time)
        )

        # Add to repository
        self.repository.add(self.current_activity)

        # Update last update time
        self.last_update_time = current_time

    def _handle_idle_state(self, is_idle: bool) -> None:
        """Handle changes in idle state.

        Args:
            is_idle: Whether the system is now idle
        """
        current_time = datetime.now()

        if is_idle and not self.is_idle:
            # Transition to idle
            self.is_idle = True
            self.idle_start_time = current_time

            logger.info("User became idle")

            # Dispatch idle start event
            self.event_dispatcher.dispatch(
                IdleStartEvent(
                    last_activity=self.current_activity, timestamp=current_time
                )
            )

        elif not is_idle and self.is_idle:
            # Transition from idle
            self.is_idle = False

            if self.idle_start_time:
                idle_duration = (current_time - self.idle_start_time).total_seconds()

                logger.info(f"User returned from idle (Duration: {idle_duration:.1f}s)")

                # Dispatch idle end event
                self.event_dispatcher.dispatch(
                    IdleEndEvent(idle_duration=idle_duration, timestamp=current_time)
                )

                self.idle_start_time = None

    def update_activity(self) -> None:
        """Update the current activity state."""
        try:
            current_time = datetime.now()

            # Initialize last_update_time if not set
            if self.last_update_time is None:
                self.last_update_time = current_time

            # Get current window info
            (
                app_name,
                window_title,
                process_id,
                executable_path,
            ) = self._get_active_window_info()

            is_idle = self._is_idle()

            # Log current state
            logger.debug(
                f"Current state - App: {app_name}, Window: {window_title}, "
                f"Process: {process_id}, Idle: {is_idle}"
            )

            # Handle idle state changes
            if is_idle != self.is_idle:
                logger.info(f"Idle state changed: {self.is_idle} -> {is_idle}")
                self._handle_idle_state(is_idle)

            # Update current activity
            if self.current_activity:
                # Calculate time since last update
                time_since_last = (current_time - self.last_update_time).total_seconds()

                # Update activity times
                if not is_idle:
                    self.current_activity.active_time += time_since_last
                else:
                    self.current_activity.idle_time += time_since_last

                # Check for activity change
                if (
                    app_name != self.current_activity.app_name
                    or window_title != self.current_activity.window_title
                ):
                    logger.debug(
                        f"Activity changed: {self.current_activity.app_name} -> {app_name}"
                    )
                    self._handle_activity_change(
                        app_name, window_title, process_id, executable_path
                    )

            elif not is_idle:
                # Start new activity if not idle
                logger.debug(f"Starting new activity: {app_name}")
                self._handle_activity_change(
                    app_name, window_title, process_id, executable_path
                )

            # Update last update time
            self.last_update_time = current_time

        except Exception as e:
            logger.error(f"Error updating activity: {e}", exc_info=True)

    def _monitoring_loop(self) -> None:
        """Main monitoring loop running in a separate thread."""
        logger = logging.getLogger(__name__)
        logger.debug("Activity monitoring loop started")

        try:
            while not self._stop_monitoring.is_set():
                self.update_activity()
                self._stop_monitoring.wait(self.update_interval)

        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}", exc_info=True)
        finally:
            logger.debug("Activity monitoring loop stopped")

    def start_monitoring(self) -> None:
        """Start the activity monitoring in a separate thread."""
        if self._monitoring_thread is not None and self._monitoring_thread.is_alive():
            return  # Already running

        logger = logging.getLogger(__name__)
        logger.debug("Starting activity monitoring...")

        # Add a test activity to verify storage
        try:
            test_activity = Activity(
                app_name="Test App",
                window_title="Test Window",
                process_id=0,
                executable_path="test.exe",
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(minutes=5),
                active_time=300,  # 5 minutes
                idle_time=0,
            )
            self.repository.add(test_activity)
            logger.debug("Added test activity to verify storage")
        except Exception as e:
            logger.error(f"Error adding test activity: {e}")

        self._stop_monitoring.clear()
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            name="ActivityMonitorThread",
            daemon=True,  # Thread will be terminated when main thread exits
        )
        self._monitoring_thread.start()

        self.event_dispatcher.dispatch(
            SystemStatusEvent(
                status="monitoring_started",
                timestamp=datetime.now(),
                details={},
            )
        )

    def stop_monitoring(self) -> None:
        """Stop the activity monitoring."""
        if self._monitoring_thread is None:
            return  # Not running

        logger = logging.getLogger(__name__)
        logger.debug("Stopping activity monitoring...")

        self._stop_monitoring.set()
        if self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=5.0)  # Wait up to 5 seconds

        # Save the current activity before stopping
        if self.current_activity:
            self.current_activity.end_time = datetime.now()
            self.repository.update(self.current_activity)

        self.event_dispatcher.dispatch(
            SystemStatusEvent(
                status="monitoring_stopped",
                timestamp=datetime.now(),
                details={"reason": "user_request"},
            )
        )

    def cleanup_old_data(self, retention_days: int = 30) -> None:
        """Clean up activities older than the specified number of days.

        Args:
            retention_days: Number of days to keep activities for
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            deleted_count = self.repository.cleanup_old_activities(cutoff_date)

            # Dispatch status event
            self.event_dispatcher.dispatch(
                SystemStatusEvent(
                    status="cleanup_completed",
                    timestamp=datetime.now(),
                    details={
                        "deleted_count": deleted_count,
                        "retention_days": retention_days,
                        "cutoff_date": cutoff_date.isoformat(),
                    },
                )
            )

        except Exception as e:
            self.event_dispatcher.dispatch(
                SystemStatusEvent(
                    status="cleanup_failed",
                    timestamp=datetime.now(),
                    details={"error": str(e), "retention_days": retention_days},
                )
            )
