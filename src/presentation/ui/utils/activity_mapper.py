"""Activity data mapping utilities."""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from core.entities.activity import Activity

logger = logging.getLogger(__name__)


class ActivityMapper:
    """Maps activity data for UI components."""

    @staticmethod
    def map_activity_list(activities: List[Activity]) -> List[Dict[str, Any]]:
        """Map activity list to table format.

        Args:
            activities: List of activity entities

        Returns:
            List of mapped activity dictionaries
        """
        try:
            mapped_activities = []
            for activity in activities:
                if not isinstance(activity, Activity):
                    logger.warning(f"Invalid activity type: {type(activity)}")
                    continue

                mapped_activities.append(
                    {
                        "time": activity.start_time,
                        "app_name": activity.app_name,
                        "window_title": activity.window_title,
                        "duration": activity.active_time + activity.idle_time,
                        "status": "Active"
                        if activity.active_time > activity.idle_time
                        else "Idle",
                    }
                )
            return mapped_activities
        except Exception as e:
            logger.error(f"Error mapping activity list: {e}", exc_info=True)
            return []

    @staticmethod
    def map_activity_stats(activities: List[Activity]) -> Dict[str, Any]:
        """Map activities to statistics format.

        Args:
            activities: List of activity entities

        Returns:
            Dictionary of activity statistics
        """
        try:
            app_stats = {}
            total_time = 0

            for activity in activities:
                if not isinstance(activity, Activity):
                    continue

                duration = activity.active_time + activity.idle_time
                total_time += duration

                if activity.app_name not in app_stats:
                    app_stats[activity.app_name] = {
                        "total_time": 0,
                        "active_time": 0,
                        "idle_time": 0,
                    }

                stats = app_stats[activity.app_name]
                stats["total_time"] += duration
                stats["active_time"] += activity.active_time
                stats["idle_time"] += activity.idle_time

            # Calculate percentages
            if total_time > 0:
                for stats in app_stats.values():
                    stats["usage_percentage"] = stats["total_time"] / total_time

            return {
                "total_time": total_time,
                "app_stats": app_stats,
                "app_count": len(app_stats),
            }
        except Exception as e:
            logger.error(f"Error mapping activity statistics: {e}", exc_info=True)
            return {"total_time": 0, "app_stats": {}, "app_count": 0}

    @staticmethod
    def map_activity_timeline(activities: List[Activity]) -> Dict[str, List[float]]:
        """Map activities to timeline format.

        Args:
            activities: List of activity entities

        Returns:
            Dictionary with hourly and daily activity data
        """
        try:
            hourly_data = [0.0] * 24
            daily_data = [0.0] * 7

            for activity in activities:
                if not isinstance(activity, Activity):
                    continue

                hour = activity.start_time.hour
                day = activity.start_time.weekday()
                duration = activity.active_time + activity.idle_time

                hourly_data[hour] += duration
                daily_data[day] += duration

            # Normalize data
            max_hourly = max(hourly_data) if hourly_data else 1
            max_daily = max(daily_data) if daily_data else 1

            hourly_data = [h / max_hourly for h in hourly_data]
            daily_data = [d / max_daily for d in daily_data]

            return {"hourly": hourly_data, "daily": daily_data}
        except Exception as e:
            logger.error(f"Error mapping activity timeline: {e}", exc_info=True)
            return {"hourly": [0.0] * 24, "daily": [0.0] * 7}
