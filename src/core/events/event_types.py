"""Event type definitions."""

from dataclasses import dataclass, fields
from datetime import datetime
from typing import Dict, List, Optional, Any

from ..entities.activity import Activity


class EventValidationMixin:
    """Mixin class for event validation."""

    def validate(self) -> None:
        """Validate event data.

        Raises:
            ValueError: If validation fails
        """
        # Check required fields
        for field in fields(self):
            value = getattr(self, field.name)
            if not field.default and not field.default_factory and value is None:
                raise ValueError(f"Required field '{field.name}' is None")

        # Validate timestamp
        if not isinstance(self.timestamp, datetime):
            raise ValueError("timestamp must be a datetime object")

        # Validate event_type
        if not isinstance(self.event_type, str):
            raise ValueError("event_type must be a string")

        # Event-specific validation
        self._validate_specific()

    def _validate_specific(self) -> None:
        """Validate event-specific fields.

        Override this method in specific event classes.
        """
        pass


@dataclass
class ActivityStartEvent(EventValidationMixin):
    """Event emitted when an activity starts."""
    activity: Activity
    timestamp: datetime
    event_type: str = "activity_start"

    def _validate_specific(self) -> None:
        """Validate activity start event fields."""
        if not self.activity:
            raise ValueError("activity is required")


@dataclass
class ActivityEndEvent(EventValidationMixin):
    """Event emitted when an activity ends."""
    activity: Activity
    duration: float  # Duration in seconds
    timestamp: datetime
    event_type: str = "activity_end"

    def _validate_specific(self) -> None:
        """Validate activity end event fields."""
        if not self.activity:
            raise ValueError("activity is required")
        if self.duration < 0:
            raise ValueError("duration must be non-negative")


@dataclass
class IdleStartEvent(EventValidationMixin):
    """Event emitted when the system becomes idle."""
    last_activity: Optional[Activity]
    timestamp: datetime
    event_type: str = "idle_start"


@dataclass
class IdleEndEvent(EventValidationMixin):
    """Event emitted when the system becomes active after being idle."""
    idle_duration: float  # Duration in seconds
    timestamp: datetime
    event_type: str = "idle_end"

    def _validate_specific(self) -> None:
        """Validate idle end event fields."""
        if self.idle_duration < 0:
            raise ValueError("idle_duration must be non-negative")


@dataclass
class ProductivityAlertEvent(EventValidationMixin):
    """Event emitted for productivity alerts."""
    productivity_score: float
    time_window: str  # e.g., "last_hour", "last_4_hours", "today"
    suggestions: List[str]
    timestamp: datetime
    event_type: str = "productivity_alert"

    def _validate_specific(self) -> None:
        """Validate productivity alert event fields."""
        if not 0 <= self.productivity_score <= 1:
            raise ValueError("productivity_score must be between 0 and 1")
        if not self.time_window:
            raise ValueError("time_window is required")
        if not isinstance(self.suggestions, list):
            raise ValueError("suggestions must be a list")


@dataclass
class BehaviorPatternEvent(EventValidationMixin):
    """Event emitted when significant behavior patterns are detected."""
    pattern_type: str  # e.g., "consistent_start_time", "productivity_trend"
    pattern_data: Dict  # Pattern-specific details
    significance: float  # Pattern significance score (0-1)
    timestamp: datetime
    event_type: str = "behavior_pattern"

    def _validate_specific(self) -> None:
        """Validate behavior pattern event fields."""
        if not 0 <= self.significance <= 1:
            raise ValueError("significance must be between 0 and 1")
        if not isinstance(self.pattern_data, dict):
            raise ValueError("pattern_data must be a dictionary")


@dataclass
class SessionEvent(EventValidationMixin):
    """Event emitted for session-related activities."""
    session_id: str
    timestamp: datetime
    event_type: str  # "session_start", "session_end", "session_restore"
    metadata: Optional[Dict] = None  # Additional event-specific data

    def _validate_specific(self) -> None:
        """Validate session event fields."""
        valid_types = {"session_start", "session_end", "session_restore"}
        if self.event_type not in valid_types:
            raise ValueError(f"event_type must be one of {valid_types}")
        if self.metadata is not None and not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a dictionary if provided")


@dataclass
class SystemStatusEvent(EventValidationMixin):
    """Event emitted for system status updates."""
    status: str
    timestamp: datetime
    event_type: str = "system_status"
    details: Optional[Dict] = None

    def _validate_specific(self) -> None:
        """Validate system status event fields."""
        if not self.status:
            raise ValueError("status is required")
        if self.details is not None and not isinstance(self.details, dict):
            raise ValueError("details must be a dictionary if provided")


@dataclass
class ErrorEvent(EventValidationMixin):
    """Event emitted when system errors occur."""
    error_type: str
    error_message: str
    timestamp: datetime
    event_type: str = "error"
    details: Optional[Dict] = None

    def _validate_specific(self) -> None:
        """Validate error event fields."""
        if not self.error_type:
            raise ValueError("error_type is required")
        if not self.error_message:
            raise ValueError("error_message is required")
        if self.details is not None and not isinstance(self.details, dict):
            raise ValueError("details must be a dictionary if provided")


@dataclass
class ConfigurationChangeEvent(EventValidationMixin):
    """Event emitted when system configuration changes."""
    setting_key: str
    old_value: Any
    new_value: Any
    timestamp: datetime
    event_type: str = "configuration_change"
    source: Optional[str] = None  # Source of the change (e.g., "user", "system", "api")

    def _validate_specific(self) -> None:
        """Validate configuration change event fields."""
        if not self.setting_key:
            raise ValueError("setting_key is required")
        if self.source and not isinstance(self.source, str):
            raise ValueError("source must be a string if provided")