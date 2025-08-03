"""Continuous learning system for adapting to user behavior."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.base import BaseEstimator
from sklearn.ensemble import RandomForestClassifier

from ..entities.activity import Activity
from .feature_extractor import ActivityFeatureExtractor

logger = logging.getLogger(__name__)


class ContinuousLearner:
    """Manages continuous learning and model adaptation."""

    def __init__(
        self,
        base_model: Optional[BaseEstimator] = None,
        window_size: int = 1000,  # Number of samples to keep in memory
        adaptation_rate: float = 0.3,  # Weight for new data vs old model
        min_samples_adapt: int = 50,  # Minimum samples before adaptation
        performance_threshold: float = 0.7  # Minimum accuracy to accept adaptation
    ):
        """Initialize the continuous learner.

        Args:
            base_model: Initial model to start with (creates new if None)
            window_size: Maximum number of samples to keep for adaptation
            adaptation_rate: Weight given to new data (0-1)
            min_samples_adapt: Minimum samples needed before adapting
            performance_threshold: Minimum performance to accept adaptation
        """
        self.window_size = window_size
        self.adaptation_rate = adaptation_rate
        self.min_samples_adapt = min_samples_adapt
        self.performance_threshold = performance_threshold

        self.feature_extractor = ActivityFeatureExtractor()
        self.current_model = base_model or RandomForestClassifier(
            n_estimators=100,
            warm_start=True  # Enable incremental learning
        )

        # Initialize sample windows
        self.activity_window: List[Activity] = []
        self.performance_history: List[float] = []
        self.last_adaptation: Optional[datetime] = None

    def _update_window(self, activity: Activity) -> None:
        """Update the sliding window of activities.

        Args:
            activity: New activity to add
        """
        self.activity_window.append(activity)
        if len(self.activity_window) > self.window_size:
            self.activity_window.pop(0)

    def _should_adapt(self) -> bool:
        """Check if model should be adapted.

        Returns:
            bool: True if model should be adapted
        """
        if len(self.activity_window) < self.min_samples_adapt:
            return False

        if not self.last_adaptation:
            return True

        # Adapt if performance is degrading
        if (len(self.performance_history) >= 2 and
            self.performance_history[-1] < self.performance_history[-2]):
            return True

        return False

    def _prepare_adaptation_data(
        self
    ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """Prepare data for model adaptation.

        Returns:
            tuple: (features, labels, unique_apps)
        """
        # Extract features from window
        features_df = self.feature_extractor.extract_features(
            self.activity_window
        )

        # Prepare target variable (next app prediction)
        app_names = [a.app_name for a in self.activity_window]
        unique_apps = list(set(app_names))

        # Convert to numeric labels
        label_map = {app: i for i, app in enumerate(unique_apps)}
        labels = np.array([label_map[app] for app in app_names])

        return features_df.values, labels, unique_apps

    def _evaluate_adaptation(
        self,
        X: np.ndarray,
        y: np.ndarray,
        adapted_model: BaseEstimator
    ) -> float:
        """Evaluate adapted model performance.

        Args:
            X: Feature matrix
            y: True labels
            adapted_model: Model to evaluate

        Returns:
            float: Accuracy score
        """
        # Use last 20% of data for evaluation
        split_idx = int(len(X) * 0.8)
        X_eval = X[split_idx:]
        y_eval = y[split_idx:]

        predictions = adapted_model.predict(X_eval)
        accuracy = np.mean(predictions == y_eval)

        return float(accuracy)

    def adapt_model(self) -> Tuple[bool, Optional[float]]:
        """Adapt model to recent activities.

        Returns:
            tuple: (was_adapted, new_accuracy if adapted else None)
        """
        if not self._should_adapt():
            return False, None

        try:
            # Prepare adaptation data
            X, y, unique_apps = self._prepare_adaptation_data()

            # Create temporary model for adaptation
            adapted_model = RandomForestClassifier(
                n_estimators=max(
                    int(100 * self.adaptation_rate),
                    10
                ),
                warm_start=True
            )

            # Train on new data
            adapted_model.fit(X, y)

            # Evaluate adaptation
            accuracy = self._evaluate_adaptation(X, y, adapted_model)

            if accuracy >= self.performance_threshold:
                # Update current model
                if hasattr(self.current_model, 'estimators_'):
                    # For random forest, merge trees
                    old_trees = int(
                        len(self.current_model.estimators_) * 
                        (1 - self.adaptation_rate)
                    )
                    new_trees = len(adapted_model.estimators_)

                    self.current_model.estimators_ = (
                        self.current_model.estimators_[-old_trees:] +
                        adapted_model.estimators_
                    )
                else:
                    # For other models, replace with adapted model
                    self.current_model = adapted_model

                self.last_adaptation = datetime.now()
                self.performance_history.append(accuracy)

                logger.info(
                    f"Model adapted successfully. New accuracy: {accuracy:.3f}"
                )
                return True, accuracy
            else:
                logger.warning(
                    f"Adaptation rejected. Accuracy {accuracy:.3f} below "
                    f"threshold {self.performance_threshold}"
                )
                return False, accuracy

        except Exception as e:
            logger.error(f"Error during model adaptation: {e}")
            return False, None

    def update(self, activity: Activity) -> None:
        """Update learner with new activity.

        Args:
            activity: New activity to learn from
        """
        self._update_window(activity)
        self.adapt_model()

    def predict_next(self, recent_activities: List[Activity]) -> Optional[str]:
        """Predict next activity.

        Args:
            recent_activities: Recent activities to base prediction on

        Returns:
            str: Predicted next activity name or None if prediction not possible
        """
        try:
            # Extract features
            features_df = self.feature_extractor.extract_features(
                recent_activities
            )
            if features_df.empty:
                return None

            # Make prediction
            X = features_df.iloc[-1:].values
            prediction = self.current_model.predict(X)[0]

            # Convert numeric prediction back to app name
            app_names = [a.app_name for a in self.activity_window]
            unique_apps = list(set(app_names))

            return unique_apps[prediction]

        except Exception as e:
            logger.error(f"Error making prediction: {e}")
            return None

    def get_performance_stats(self) -> Dict[str, float]:
        """Get performance statistics.

        Returns:
            dict: Performance statistics
        """
        if not self.performance_history:
            return {}

        return {
            'current_accuracy': self.performance_history[-1],
            'average_accuracy': np.mean(self.performance_history),
            'min_accuracy': min(self.performance_history),
            'max_accuracy': max(self.performance_history),
            'adaptation_count': len(self.performance_history)
        }