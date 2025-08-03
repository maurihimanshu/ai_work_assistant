"""Service for activity prediction."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

from ..entities.activity import Activity
from ..interfaces.activity_repository import ActivityRepository
from ..ml.activity_categorizer import ActivityCategorizer
from ..ml.continuous_learner import ContinuousLearner

logger = logging.getLogger(__name__)


class PredictionService:
    """Service for activity prediction."""

    def __init__(
        self,
        repository: ActivityRepository,
        learner: ContinuousLearner,
        categorizer: ActivityCategorizer,
        prediction_window: timedelta = timedelta(hours=1),
        min_activities_for_prediction: int = 5,
        load_initial_data: bool = False
    ):
        """Initialize prediction service.

        Args:
            repository: Activity repository
            learner: Continuous learning model
            categorizer: Activity categorizer
            prediction_window: Time window for predictions
            min_activities_for_prediction: Minimum activities needed
            load_initial_data: Whether to load initial data during initialization
        """
        self.repository = repository
        self.learner = learner
        self.categorizer = categorizer
        self.prediction_window = prediction_window
        self.min_activities_for_prediction = min_activities_for_prediction

        # Load initial data if requested
        if load_initial_data:
            self._load_initial_data()

    def _load_initial_data(self) -> None:
        """Load initial data for prediction."""
        current_time = datetime.now()
        start_time = current_time - self.prediction_window
        activities = self.repository.get_by_timerange(start_time, current_time)

        if activities:
            for activity in activities:
                self.learner.activity_window.append(activity)
                self.learner.adapt_model(activity)

    def _get_prediction_data(self) -> List[Activity]:
        """Get data for making predictions.

        Returns:
            list: Recent activities for prediction
        """
        current_time = datetime.now()
        start_time = current_time - self.prediction_window
        return self.repository.get_by_timerange(start_time, current_time)

    def update_model(self, activity: Activity) -> Tuple[bool, Optional[float]]:
        """Update model with new activity.

        Args:
            activity: Activity to learn from

        Returns:
            tuple: (was_adapted, new_accuracy)
        """
        try:
            # Update learner
            self.learner.adapt_model(activity)

            # Get adaptation results
            was_adapted = self.learner.last_adaptation is not None
            accuracy = (
                self.learner.performance_history[-1]
                if self.learner.performance_history
                else None
            )

            return was_adapted, accuracy

        except Exception as e:
            logger.error(f"Error updating model: {e}")
            return False, None

    def predict_next_activity(
        self,
        activities: Optional[List[Activity]] = None
    ) -> Optional[str]:
        """Predict next activity.

        Args:
            activities: Optional list of activities to use for prediction

        Returns:
            str: Predicted next activity app name
        """
        try:
            # Get activities if not provided
            if activities is None:
                activities = self._get_prediction_data()

            if len(activities) < self.min_activities_for_prediction:
                return None

            # Update model with recent activities
            for activity in activities:
                self.learner.adapt_model(activity)

            # Make prediction
            return self.learner.predict_next()

        except Exception as e:
            logger.error(f"Error predicting next activity: {e}")
            return None

    def get_activity_insights(
        self,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """Get insights about activities.

        Args:
            time_window: Optional custom time window

        Returns:
            dict: Activity insights
        """
        try:
            current_time = datetime.now()
            window = time_window or self.prediction_window
            start_time = current_time - window
            activities = self.repository.get_by_timerange(start_time, current_time)

            if not activities:
                return {
                    "productivity": {
                        "overall": 0.0,
                        "by_time": {
                            "morning": 0.0,
                            "afternoon": 0.0,
                            "evening": 0.0,
                            "night": 0.0
                        }
                    }
                }

            # Get insights from categorizer
            insights = self.categorizer.get_activity_insights(activities)

            # Get predictions using the same activities
            next_activity = self.predict_next_activity(activities)

            return {
                "productivity": {
                    "overall": insights.get("overall_productivity", 0.0),
                    "by_time": insights.get("time_productivity", {})
                },
                "predicted_next": next_activity
            }

        except Exception as e:
            logger.error(f"Error getting activity insights: {e}")
            return {}