"""Service for analytics and insights."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..entities.activity import Activity
from ..events.event_dispatcher import EventDispatcher
from ..events.event_types import BehaviorPatternEvent
from ..interfaces.activity_repository import ActivityRepository
from ..ml.activity_categorizer import ActivityCategorizer

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for analytics and insights."""

    def __init__(
        self,
        repository: ActivityRepository,
        event_dispatcher: EventDispatcher,
        categorizer: Optional[ActivityCategorizer] = None,
        update_interval: timedelta = timedelta(minutes=30),
        analysis_window: timedelta = timedelta(days=30),
    ):
        """Initialize analytics service.

        Args:
            repository: Activity repository
            event_dispatcher: Event dispatcher
            categorizer: Activity categorizer
            update_interval: Interval between updates
            analysis_window: Time window for analysis
        """
        self.repository = repository
        self.event_dispatcher = event_dispatcher
        self.categorizer = categorizer
        self.update_interval = update_interval
        self.analysis_window = analysis_window
        self.last_update = None

    def get_productivity_report(self, time_window: timedelta) -> Dict:
        """Get productivity report for time window.

        Args:
            time_window: Time window to get report for

        Returns:
            dict: Report data
        """
        try:
            # Get activities for time window
            end_time = datetime.now()
            start_time = end_time - time_window
            activities = self.repository.get_by_timerange(start_time, end_time)

            logger.info(f"Generating productivity report for {len(activities)} activities")

            if not activities:
                return self._get_empty_report()

            # Convert Activity objects to dictionaries
            activity_dicts = []
            total_time = 0
            total_active = 0
            total_idle = 0

            for activity in activities:
                duration = (activity.end_time - activity.start_time).total_seconds() if activity.end_time else 0
                activity_dict = {
                    "start_time": activity.start_time,
                    "end_time": activity.end_time,
                    "app_name": activity.app_name,
                    "window_title": activity.window_title,
                    "duration": duration,
                    "active_time": activity.active_time,
                    "idle_time": activity.idle_time,
                }
                activity_dicts.append(activity_dict)
                total_time += duration
                total_active += activity.active_time
                total_idle += activity.idle_time

            # Get insights from categorizer
            insights = self.categorizer.get_activity_insights(activity_dicts)

            # Calculate daily metrics
            daily_metrics = {
                "total_time": total_time,
                "active_time": total_active,
                "idle_time": total_idle,
            }

            # Calculate app patterns
            app_patterns = {}
            for activity in activity_dicts:
                app_name = activity["app_name"]
                if app_name not in app_patterns:
                    app_patterns[app_name] = {
                        "total_time": 0,
                        "active_time": 0,
                        "idle_time": 0,
                        "usage_percentage": 0,
                    }
                app_patterns[app_name]["total_time"] += activity["duration"]
                app_patterns[app_name]["active_time"] += activity["active_time"]
                app_patterns[app_name]["idle_time"] += activity["idle_time"]

            # Calculate usage percentages
            if total_time > 0:
                for app_stats in app_patterns.values():
                    app_stats["usage_percentage"] = app_stats["total_time"] / total_time

            # Calculate category patterns
            category_patterns = {}
            for activity in activity_dicts:
                category = insights.get("categories", {}).get(activity["app_name"], "Unknown")
                if category not in category_patterns:
                    category_patterns[category] = {
                        "total_time": 0,
                        "app_count": 0,
                        "usage_percentage": 0,
                    }
                category_patterns[category]["total_time"] += activity["duration"]
                if activity["app_name"] not in category_patterns[category].get("apps", set()):
                    category_patterns[category]["app_count"] += 1
                    category_patterns[category].setdefault("apps", set()).add(activity["app_name"])

            # Calculate category usage percentages
            if total_time > 0:
                for cat_stats in category_patterns.values():
                    cat_stats["usage_percentage"] = cat_stats["total_time"] / total_time
                    # Remove temporary apps set
                    cat_stats.pop("apps", None)

            # Calculate productivity trends
            hourly_trends = [0.0] * 24
            daily_trends = [0.0] * 7
            hourly_counts = [0] * 24
            daily_counts = [0] * 7

            for activity in activity_dicts:
                start = activity["start_time"]
                if start and activity["duration"] > 0:
                    hour = start.hour
                    day = start.weekday()
                    productivity = activity["active_time"] / activity["duration"]

                    hourly_trends[hour] = ((hourly_trends[hour] * hourly_counts[hour]) + productivity) / (hourly_counts[hour] + 1)
                    daily_trends[day] = ((daily_trends[day] * daily_counts[day]) + productivity) / (daily_counts[day] + 1)

                    hourly_counts[hour] += 1
                    daily_counts[day] += 1

            logger.info("Successfully generated productivity report")

            return {
                "daily_metrics": daily_metrics,
                "app_patterns": app_patterns,
                "category_patterns": category_patterns,
                "productivity_trends": {
                    "hourly": hourly_trends,
                    "daily": daily_trends,
                },
                "activities": activity_dicts,
                "insights": insights
            }

        except Exception as e:
            logger.error(f"Error generating productivity report: {e}", exc_info=True)
            return self._get_empty_report()

    def _get_empty_report(self) -> Dict:
        """Get empty report structure.

        Returns:
            dict: Empty report
        """
        return {
            "daily_metrics": {
                "total_time": 0,
                "active_time": 0,
                "idle_time": 0,
            },
            "app_patterns": {},
            "category_patterns": {},
            "productivity_trends": {
                "hourly": [0.0] * 24,
                "daily": [0.0] * 7,
            },
            "activities": [],
            "insights": {
                "categories": {},
                "overall_productivity": 0.0,
                "suggestions": []
            }
        }

    def update_analytics(self) -> None:
        """Update analytics data."""
        try:
            current_time = datetime.now()

            # Skip if last update was too recent
            if (
                self.last_update
                and current_time - self.last_update < self.update_interval
            ):
                return

            # Get activities since last update
            start_time = (
                self.last_update
                if self.last_update
                else current_time - timedelta(hours=1)
            )
            activities = self.repository.get_by_timerange(start_time, current_time)

            if activities:
                # Update patterns
                patterns = self._analyze_patterns(activities)

                # Dispatch events for significant patterns
                for pattern in patterns:
                    if pattern["significance"] > 0.5:  # Only significant patterns
                        self.event_dispatcher.dispatch(
                            BehaviorPatternEvent(
                                pattern_type=pattern["type"],
                                pattern_data=pattern["details"],
                                significance=pattern["significance"],
                                timestamp=current_time,
                            )
                        )

            self.last_update = current_time

        except Exception as e:
            logger.error(f"Error updating analytics: {e}")
            self.last_update = current_time  # Update timestamp even on error

    def _calculate_overall_productivity(self, activities: List[Activity]) -> float:
        """Calculate overall productivity score.

        Args:
            activities: List of activities

        Returns:
            float: Overall productivity score
        """
        if not activities:
            return 0.0

        total_time = sum(
            (a.end_time - a.start_time).total_seconds()
            for a in activities
            if a.end_time
        )
        if total_time == 0:
            return 0.0

        total_productive_time = sum(a.active_time for a in activities if a.end_time)
        return total_productive_time / total_time

    def _get_app_patterns(
        self, activities: List[Activity]
    ) -> Dict[str, Dict[str, float]]:
        """Get application usage patterns.

        Args:
            activities: List of activities

        Returns:
            dict: Application usage patterns
        """
        app_patterns = {}
        total_time = 0.0

        for activity in activities:
            app_name = activity.app_name
            if app_name not in app_patterns:
                app_patterns[app_name] = {
                    "total_time": 0.0,
                    "active_time": 0.0,
                    "idle_time": 0.0,
                }

            app_patterns[app_name]["total_time"] += (
                activity.active_time + activity.idle_time
            )
            app_patterns[app_name]["active_time"] += activity.active_time
            app_patterns[app_name]["idle_time"] += activity.idle_time
            total_time += activity.active_time + activity.idle_time

        # Calculate percentages
        if total_time > 0:
            for app_name in app_patterns:
                app_patterns[app_name]["usage_percentage"] = (
                    app_patterns[app_name]["total_time"] / total_time
                )

        return app_patterns

    def _get_behavior_patterns(
        self, activities: List[Activity]
    ) -> List[Dict[str, Any]]:
        """Get significant behavior patterns.

        Args:
            activities: List of activities

        Returns:
            list: Detected patterns
        """
        patterns = []

        # Analyze context switching
        app_switches = 0
        for i in range(1, len(activities)):
            if activities[i].app_name != activities[i - 1].app_name:
                app_switches += 1

        if app_switches > len(activities) * 0.3:  # High context switching
            patterns.append(
                {
                    "type": "context_switching",
                    "details": {
                        "switches": app_switches,
                        "total_activities": len(activities),
                    },
                    "significance": min(1.0, app_switches / len(activities)),
                }
            )

        # Analyze work patterns
        work_sessions = []
        current_session = []

        for activity in activities:
            if not current_session:
                current_session = [activity]
            elif (
                activity.start_time - current_session[-1].end_time
            ).total_seconds() < 300:  # 5 min gap
                current_session.append(activity)
            else:
                if len(current_session) > 3:  # Significant session
                    work_sessions.append(current_session)
                current_session = [activity]

        if current_session and len(current_session) > 3:
            work_sessions.append(current_session)

        if work_sessions:
            patterns.append(
                {
                    "type": "work_sessions",
                    "details": {
                        "count": len(work_sessions),
                        "avg_duration": sum(
                            (s[-1].end_time - s[0].start_time).total_seconds()
                            for s in work_sessions
                        )
                        / len(work_sessions),
                    },
                    "significance": min(1.0, len(work_sessions) * 0.2),
                }
            )

        return patterns

    def _get_daily_metrics(
        self, activities: List[Activity]
    ) -> Dict[str, Dict[str, float]]:
        """Get daily productivity metrics.

        Args:
            activities: List of activities

        Returns:
            dict: Daily productivity metrics
        """
        daily_metrics = {}

        for activity in activities:
            date = activity.start_time.date().isoformat()
            if date not in daily_metrics:
                daily_metrics[date] = {
                    "active_time": 0.0,
                    "idle_time": 0.0,
                    "productivity": 0.0,
                }

            daily_metrics[date]["active_time"] += activity.active_time
            daily_metrics[date]["idle_time"] += activity.idle_time

        # Calculate productivity
        for date in daily_metrics:
            total_time = (
                daily_metrics[date]["active_time"] + daily_metrics[date]["idle_time"]
            )
            if total_time > 0:
                daily_metrics[date]["productivity"] = (
                    daily_metrics[date]["active_time"] / total_time
                )

        return daily_metrics

    def _get_productivity_trends(
        self, activities: List[Activity]
    ) -> Dict[str, List[float]]:
        """Get productivity trends.

        Args:
            activities: List of activities

        Returns:
            dict: Productivity trends
        """
        trends = {"hourly": [0.0] * 24, "daily": [0.0] * 7}

        hour_counts = [0] * 24
        day_counts = [0] * 7

        for activity in activities:
            hour = activity.start_time.hour
            day = activity.start_time.weekday()

            total_time = activity.active_time + activity.idle_time
            if total_time > 0:
                productivity = activity.active_time / total_time
                trends["hourly"][hour] += productivity
                trends["daily"][day] += productivity
                hour_counts[hour] += 1
                day_counts[day] += 1

        # Calculate averages
        for hour in range(24):
            if hour_counts[hour] > 0:
                trends["hourly"][hour] /= hour_counts[hour]

        for day in range(7):
            if day_counts[day] > 0:
                trends["daily"][day] /= day_counts[day]

        return trends
