"""Service for activity prediction."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

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
        load_initial_data: bool = True,  # Changed default to True
        training_window: timedelta = timedelta(days=7),  # Added training window
    ):
        """Initialize prediction service.

        Args:
            repository: Activity repository
            learner: Continuous learning model
            categorizer: Activity categorizer
            prediction_window: Time window for predictions
            min_activities_for_prediction: Minimum activities needed
            load_initial_data: Whether to load initial data during initialization
            training_window: Time window for initial training data
        """
        self.repository = repository
        self.learner = learner
        self.categorizer = categorizer
        self.prediction_window = prediction_window
        self.min_activities_for_prediction = min_activities_for_prediction
        self.training_window = training_window

        # Load initial data if requested
        if load_initial_data:
            self._load_initial_data()

    def _load_initial_data(self) -> None:
        """Load initial data for prediction and train model."""
        try:
            # Get activities from the training window
            current_time = datetime.now()
            start_time = current_time - self.training_window
            activities = self.repository.get_by_timerange(start_time, current_time)

            if not activities:
                logger.warning("No activities found for initial training")
                return

            # Convert activities to dictionaries for training
            activity_dicts = []
            for activity in activities:
                if activity.end_time:  # Only include completed activities
                    duration = (activity.end_time - activity.start_time).total_seconds()
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

            if len(activity_dicts) >= self.min_activities_for_prediction:
                logger.info(f"Training model with {len(activity_dicts)} activities")
                self.learner.fit(activity_dicts)
            else:
                logger.warning(
                    f"Not enough activities for training (found {len(activity_dicts)}, "
                    f"need {self.min_activities_for_prediction})"
                )

        except Exception as e:
            logger.error(f"Error loading initial data: {e}", exc_info=True)

    def _get_prediction_data(self) -> List[Activity]:
        """Get data for making predictions.

        Returns:
            list: Recent activities for prediction
        """
        current_time = datetime.now()
        start_time = current_time - self.prediction_window
        return self.repository.get_by_timerange(start_time, current_time)

    def update_model(self, activities: List[Activity]) -> None:
        """Update model with new activities.

        Args:
            activities: Activities to learn from
        """
        try:
            # Convert activities to dictionaries
            activity_dicts = []
            for activity in activities:
                if activity.end_time:  # Only include completed activities
                    duration = (activity.end_time - activity.start_time).total_seconds()
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

            if activity_dicts:
                # Update the model
                self.learner.update(activity_dicts)
                logger.info(f"Updated model with {len(activity_dicts)} activities")

        except Exception as e:
            logger.error(f"Error updating model: {e}", exc_info=True)

    def predict_next_activity(
        self, activities: Optional[List[Activity]] = None
    ) -> List[Dict]:
        """Predict next activity.

        Args:
            activities: Optional list of activities to use for prediction

        Returns:
            list: List of predicted activities with confidence scores
        """
        try:
            # Get activities if not provided
            if activities is None:
                activities = self._get_prediction_data()

            if len(activities) < self.min_activities_for_prediction:
                logger.warning("Not enough activities for prediction")
                return []

            # Convert activities to dictionaries
            activity_dicts = []
            for activity in activities:
                if activity.end_time:
                    duration = (activity.end_time - activity.start_time).total_seconds()
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

            # Make prediction
            return self.learner.predict_next(activity_dicts)

        except Exception as e:
            logger.error(f"Error predicting next activity: {e}", exc_info=True)
            return []

    def get_activity_insights(
        self, time_window: Optional[timedelta] = None
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
                            "night": 0.0,
                        },
                    }
                }

            # Convert activities to dictionaries
            activity_dicts = []
            for activity in activities:
                if activity.end_time:
                    duration = (activity.end_time - activity.start_time).total_seconds()
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

            # Get insights from categorizer
            insights = self.categorizer.get_activity_insights(activity_dicts)

            # Get predictions
            predictions = self.predict_next_activity(activities)

            return {
                "productivity": {
                    "overall": insights.get("overall_productivity", 0.0),
                    "by_time": insights.get("time_productivity", {}),
                },
                "predicted_next": predictions,
            }

        except Exception as e:
            logger.error(f"Error getting activity insights: {e}", exc_info=True)
            return {}
