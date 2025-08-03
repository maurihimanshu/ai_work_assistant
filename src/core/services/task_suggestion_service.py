"""Service for generating task suggestions based on activity patterns."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from ..entities.activity import Activity
from ..events.event_dispatcher import EventDispatcher
from ..events.event_types import (ActivityEndEvent, ActivityStartEvent,
                              ProductivityAlertEvent)
from ..interfaces.activity_repository import ActivityRepository
from ..ml.activity_categorizer import ActivityCategorizer
from ..ml.continuous_learner import ContinuousLearner

logger = logging.getLogger(__name__)


class TaskSuggestionService:
    """Service for analyzing work patterns and suggesting tasks."""

    def __init__(
        self,
        repository: ActivityRepository,
        event_dispatcher: EventDispatcher,
        categorizer: ActivityCategorizer,
        learner: ContinuousLearner,
        productivity_threshold: float = 0.7,
        suggestion_interval: timedelta = timedelta(hours=1),
        analysis_window: timedelta = timedelta(days=7)
    ):
        """Initialize task suggestion service.

        Args:
            repository: Repository for accessing activity data
            event_dispatcher: Event dispatcher for system events
            categorizer: Activity categorizer for pattern analysis
            learner: Continuous learner for predictions
            productivity_threshold: Threshold for productivity alerts
            suggestion_interval: How often to generate suggestions
            analysis_window: Time window for pattern analysis
        """
        self.repository = repository
        self.event_dispatcher = event_dispatcher
        self.categorizer = categorizer
        self.learner = learner
        self.productivity_threshold = productivity_threshold
        self.suggestion_interval = suggestion_interval
        self.analysis_window = analysis_window

        self.last_suggestion_time: Optional[datetime] = None

        # Subscribe to relevant events
        self.event_dispatcher.subscribe(
            self._handle_activity_end,
            "activity_end"
        )

    def _get_time_based_suggestions(
        self,
        current_time: datetime,
        recent_activities: List[Activity]
    ) -> List[str]:
        """Generate time-based task suggestions.

        Args:
            current_time: Current time
            recent_activities: Recent activities to analyze

        Returns:
            list: Time-based suggestions
        """
        suggestions = []
        hour = current_time.hour

        # Morning suggestions (9-11 AM)
        if 9 <= hour < 11:
            suggestions.extend([
                "Review your goals for the day",
                "Tackle your most challenging task first",
                "Check and respond to important emails"
            ])

        # Lunch break suggestions (12-2 PM)
        elif 12 <= hour < 14:
            suggestions.extend([
                "Take a proper lunch break",
                "Go for a short walk",
                "Do some quick stretches"
            ])

        # Afternoon focus (2-5 PM)
        elif 14 <= hour < 17:
            suggestions.extend([
                "Focus on completing ongoing tasks",
                "Schedule any remaining meetings",
                "Review progress on daily goals"
            ])

        # End of day suggestions (5-7 PM)
        elif 17 <= hour < 19:
            suggestions.extend([
                "Plan tasks for tomorrow",
                "Clear your workspace",
                "Document any unfinished work"
            ])

        return suggestions

    def _get_productivity_based_suggestions(
        self,
        productivity_score: float,
        recent_activities: List[Activity]
    ) -> List[str]:
        """Generate productivity-based suggestions.

        Args:
            productivity_score: Current productivity score
            recent_activities: Recent activities to analyze

        Returns:
            list: Productivity-based suggestions
        """
        suggestions = []

        if productivity_score < self.productivity_threshold:
            # Analyze patterns
            categories = self.categorizer.get_activity_insights(
                recent_activities
            )

            # Low productivity suggestions
            suggestions.extend([
                "Take a short break to refresh",
                "Switch to a different task type",
                "Set a focused work timer (25 minutes)"
            ])

            # Add category-specific suggestions
            if categories.get("category_distribution"):
                low_prod_categories = [
                    cat for cat, data in categories["category_distribution"].items()
                    if data["productivity_score"] < self.productivity_threshold
                ]
                if low_prod_categories:
                    suggestions.append(
                        f"Consider limiting time on: {', '.join(low_prod_categories)}"
                    )

        return suggestions

    def _get_pattern_based_suggestions(
        self,
        activities: List[Activity]
    ) -> List[str]:
        """Get suggestions based on activity patterns.

        Args:
            activities: List of activities to analyze

        Returns:
            list: Pattern-based suggestions
        """
        suggestions = []

        # Get next activity prediction
        next_activity = self.learner.predict_next()
        if next_activity:
            suggestions.append(
                f"Consider switching to {next_activity} based on your usual workflow"
            )

        # Get activity insights
        insights = self.categorizer.get_activity_insights(activities)

        # Check context switching
        if (
            'context_switches' in insights and
            insights['context_switches']['frequency'] == 'high' and
            insights['context_switches']['impact'] < 0
        ):
            suggestions.append(
                "Consider reducing context switching to improve productivity"
            )

        # Check time-based patterns
        time_productivity = insights.get('time_productivity', {})
        if time_productivity:
            most_productive = max(
                time_productivity.items(),
                key=lambda x: x[1]
            )[0]
            suggestions.append(
                f"You're most productive during {most_productive} hours"
            )

        return suggestions

    def _get_break_suggestions(
        self,
        activities: List[Activity]
    ) -> List[str]:
        """Get break-related suggestions.

        Args:
            activities: List of activities to analyze

        Returns:
            list: Break-related suggestions
        """
        suggestions = []

        # Calculate total work time
        total_work_time = sum(
            activity.active_time
            for activity in activities
            if activity.active_time
        )

        # Suggest breaks based on work duration
        if total_work_time > 7200:  # 2 hours
            suggestions.append(
                "Take a break to maintain productivity - consider a short walk or stretch"
            )

        # Check for long sessions without breaks
        continuous_work = any(
            activity.active_time > 3600  # 1 hour
            for activity in activities
        )
        if continuous_work:
            suggestions.append(
                "You've been working continuously for over an hour. Consider a short break."
            )

        return suggestions

    def _handle_activity_end(self, event: ActivityEndEvent) -> None:
        """Handle activity end events.

        Args:
            event: Activity end event
        """
        # Check if it's time for new suggestions
        if (
            not self.last_suggestion_time or
            event.timestamp - self.last_suggestion_time >= self.suggestion_interval
        ):
            self._generate_suggestions(event.timestamp)
            self.last_suggestion_time = event.timestamp

    def _generate_suggestions(self, current_time: datetime) -> None:
        """Generate and dispatch task suggestions.

        Args:
            current_time: Current timestamp
        """
        try:
            start_time = current_time - self.analysis_window

            # Get recent activities
            recent_activities = self.repository.get_by_timerange(
                start_time,
                current_time
            )

            if not recent_activities:
                return

            # Get productivity score
            insights = self.categorizer.get_activity_insights(recent_activities)
            productivity_score = (
                insights.get("overall_productivity", 0.5)
                if insights
                else 0.5
            )

            # Generate suggestions
            suggestions = []
            suggestions.extend(
                self._get_time_based_suggestions(
                    current_time,
                    recent_activities
                )
            )
            suggestions.extend(
                self._get_productivity_based_suggestions(
                    productivity_score,
                    recent_activities
                )
            )
            suggestions.extend(
                self._get_pattern_based_suggestions(
                    recent_activities
                )
            )
            suggestions.extend(
                self._get_break_suggestions(
                    recent_activities
                )
            )

            # Remove duplicates and limit suggestions
            suggestions = list(dict.fromkeys(suggestions))[:5]

            if suggestions:
                # Determine time window description
                if self.suggestion_interval <= timedelta(hours=1):
                    time_window = "last_hour"
                elif self.suggestion_interval <= timedelta(hours=4):
                    time_window = "last_4_hours"
                else:
                    time_window = "today"

                # Dispatch productivity alert event
                self.event_dispatcher.dispatch(
                    ProductivityAlertEvent(
                        productivity_score=productivity_score,
                        time_window=time_window,
                        suggestions=suggestions,
                        timestamp=current_time
                    )
                )

        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")

    def get_current_suggestions(self) -> Tuple[List[str], float]:
        """Get current task suggestions and productivity score.

        Returns:
            tuple: (suggestions, productivity_score)
        """
        try:
            current_time = datetime.now()
            start_time = current_time - self.analysis_window

            # Get recent activities
            recent_activities = self.repository.get_by_timerange(
                start_time,
                current_time
            )

            if not recent_activities:
                return [], 0.5

            # Get productivity score
            insights = self.categorizer.get_activity_insights(recent_activities)
            productivity_score = (
                insights.get("overall_productivity", 0.5)
                if insights
                else 0.5
            )

            # Generate suggestions
            suggestions = []
            suggestions.extend(
                self._get_time_based_suggestions(
                    current_time,
                    recent_activities
                )
            )
            suggestions.extend(
                self._get_productivity_based_suggestions(
                    productivity_score,
                    recent_activities
                )
            )
            suggestions.extend(
                self._get_pattern_based_suggestions(
                    recent_activities
                )
            )
            suggestions.extend(
                self._get_break_suggestions(
                    recent_activities
                )
            )

            # Remove duplicates and limit suggestions
            suggestions = list(dict.fromkeys(suggestions))[:5]

            return suggestions, productivity_score

        except Exception as e:
            logger.error(f"Error getting current suggestions: {e}")
            return [], 0.5