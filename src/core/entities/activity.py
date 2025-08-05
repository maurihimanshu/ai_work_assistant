"""Activity entity representing user activity."""

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Activity:
    """Represents a user activity session."""

    app_name: str
    window_title: str
    process_id: int
    executable_path: str
    start_time: datetime
    end_time: Optional[datetime] = None
    active_time: float = 0.0  # Time in seconds
    idle_time: float = 0.0  # Time in seconds
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def update_times(self, current_time: datetime, is_idle: bool) -> None:
        """Update activity times.

        Args:
            current_time: Current timestamp
            is_idle: Whether the system is idle
        """
        time_diff = (current_time - self.start_time).total_seconds()

        if is_idle:
            self.idle_time = time_diff - self.active_time
        else:
            self.active_time = time_diff - self.idle_time

    def to_dict(self) -> dict:
        """Convert activity to dictionary.

        Returns:
            dict: Activity data
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Activity":
        """Create activity from dictionary.

        Args:
            data: Activity data

        Returns:
            Activity: New activity instance
        """
        # Convert string timestamps to datetime
        if isinstance(data.get("start_time"), str):
            data["start_time"] = datetime.fromisoformat(data["start_time"])
        if isinstance(data.get("end_time"), str):
            data["end_time"] = datetime.fromisoformat(data["end_time"])

        return cls(**data)
