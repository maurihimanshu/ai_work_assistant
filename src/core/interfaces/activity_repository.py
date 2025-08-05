"""Interface for activity data storage."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from ..entities.activity import Activity


class ActivityRepository(ABC):
    """Abstract interface for activity storage operations."""

    @abstractmethod
    def add(self, activity: Activity) -> str:
        """Add a new activity.

        Args:
            activity: Activity to store

        Returns:
            str: ID of the stored activity
        """
        pass

    @abstractmethod
    def get(self, activity_id: str) -> Optional[Activity]:
        """Retrieve an activity by ID.

        Args:
            activity_id: ID of the activity to retrieve

        Returns:
            Activity if found, None otherwise
        """
        pass

    @abstractmethod
    def get_by_timerange(
        self, start_time: datetime, end_time: datetime
    ) -> List[Activity]:
        """Retrieve activities within a time range.

        Args:
            start_time: Start of the time range
            end_time: End of the time range

        Returns:
            List of activities within the range
        """
        pass

    @abstractmethod
    def update(self, activity: Activity) -> bool:
        """Update an existing activity.

        Args:
            activity: Activity with updated data

        Returns:
            bool: True if update successful, False otherwise
        """
        pass

    @abstractmethod
    def delete(self, activity_id: str) -> bool:
        """Delete an activity.

        Args:
            activity_id: ID of the activity to delete

        Returns:
            bool: True if deletion successful, False otherwise
        """
        pass

    @abstractmethod
    def cleanup_old_activities(self, before_date: datetime) -> int:
        """Delete activities older than the specified date.

        Args:
            before_date: Delete activities before this date

        Returns:
            int: Number of activities deleted
        """
        pass
