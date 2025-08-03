"""Core service for monitoring user activity."""

import time
from datetime import datetime, timedelta
from typing import Optional

from ..entities.activity import Activity
from ..events.event_dispatcher import EventDispatcher
from ..events.event_types import (ActivityEndEvent, ActivityStartEvent,
                                IdleEndEvent, IdleStartEvent, SystemStatusEvent)
from ..interfaces.activity_repository import ActivityRepository
from ...infrastructure.os.platform_monitor import create_platform_monitor


class ActivityMonitor:
    """Service for monitoring and tracking user activity."""

    def __init__(
        self,
        repository: ActivityRepository,
        event_dispatcher: EventDispatcher,
        idle_threshold: int = 300,  # 5 minutes in seconds
        update_interval: int = 1  # 1 second
    ):
        """Initialize the activity monitor.

        Args:
            repository: Repository for storing activities
            event_dispatcher: Event dispatcher for system events
            idle_threshold: Time in seconds before considering user idle
            update_interval: Time in seconds between activity checks
        """
        self.repository = repository
        self.event_dispatcher = event_dispatcher
        self.idle_threshold = idle_threshold
        self.update_interval = update_interval
        self.current_activity: Optional[Activity] = None
        self.is_idle = False
        self.idle_start_time: Optional[datetime] = None

        # Initialize platform-specific monitor
        self.platform_monitor = create_platform_monitor()

        # Dispatch initial status
        self.event_dispatcher.dispatch(
            SystemStatusEvent(
                status="initialized",
                timestamp=datetime.now(),
                details={
                    "idle_threshold": idle_threshold,
                    "update_interval": update_interval
                }
            )
        )

    def _get_active_window_info(self):
        """Get information about the currently active window using platform monitor."""
        return self.platform_monitor.get_active_window_info()

    def _is_idle(self) -> bool:
        """Check if the user is idle using platform monitor.

        Returns:
            bool: True if user is idle, False otherwise
        """
        return self.platform_monitor.get_idle_time() >= self.idle_threshold

    def _handle_activity_change(
        self,
        app_name: str,
        window_title: str,
        process_id: int,
        executable_path: str
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
            duration = (
                current_time - self.current_activity.start_time
            ).total_seconds()

            # Dispatch activity end event
            self.event_dispatcher.dispatch(
                ActivityEndEvent(
                    activity=self.current_activity,
                    duration=duration,
                    timestamp=current_time
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
            start_time=current_time
        )

        # Dispatch activity start event
        self.event_dispatcher.dispatch(
            ActivityStartEvent(
                activity=self.current_activity,
                timestamp=current_time
            )
        )

        # Add to repository
        self.repository.add(self.current_activity)

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

            # Dispatch idle start event
            self.event_dispatcher.dispatch(
                IdleStartEvent(
                    last_activity=self.current_activity,
                    timestamp=current_time
                )
            )

        elif not is_idle and self.is_idle:
            # Transition from idle
            self.is_idle = False

            if self.idle_start_time:
                idle_duration = (
                    current_time - self.idle_start_time
                ).total_seconds()

                # Dispatch idle end event
                self.event_dispatcher.dispatch(
                    IdleEndEvent(
                        idle_duration=idle_duration,
                        timestamp=current_time
                    )
                )

                self.idle_start_time = None

    def update_activity(self) -> None:
        """Update the current activity state."""
        app_name, window_title, process_id, executable_path = self._get_active_window_info()
        current_time = datetime.now()
        is_idle = self._is_idle()

        # Handle idle state changes
        if is_idle != self.is_idle:
            self._handle_idle_state(is_idle)

        # Update current activity
        if self.current_activity:
            self.current_activity.update_times(current_time, is_idle)

            # Check for activity change
            if (
                app_name != self.current_activity.app_name or
                window_title != self.current_activity.window_title
            ):
                self._handle_activity_change(
                    app_name,
                    window_title,
                    process_id,
                    executable_path
                )

        elif not is_idle:
            # Start new activity if not idle
            self._handle_activity_change(
                app_name,
                window_title,
                process_id,
                executable_path
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
                        "cutoff_date": cutoff_date.isoformat()
                    }
                )
            )

        except Exception as e:
            self.event_dispatcher.dispatch(
                SystemStatusEvent(
                    status="cleanup_failed",
                    timestamp=datetime.now(),
                    details={
                        "error": str(e),
                        "retention_days": retention_days
                    }
                )
            )

    def start_monitoring(self) -> None:
        """Start the activity monitoring loop."""
        self.event_dispatcher.dispatch(
            SystemStatusEvent(
                status="monitoring_started",
                timestamp=datetime.now(),
                details={}
            )
        )

        try:
            while True:
                self.update_activity()
                time.sleep(self.update_interval)

        except KeyboardInterrupt:
            # Save the current activity before exiting
            if self.current_activity:
                self.current_activity.end_time = datetime.now()
                self.repository.update(self.current_activity)

            self.event_dispatcher.dispatch(
                SystemStatusEvent(
                    status="monitoring_stopped",
                    timestamp=datetime.now(),
                    details={
                        "reason": "keyboard_interrupt"
                    }
                )
            )

        except Exception as e:
            self.event_dispatcher.dispatch(
                SystemStatusEvent(
                    status="monitoring_error",
                    timestamp=datetime.now(),
                    details={
                        "error": str(e)
                    }
                )
            )