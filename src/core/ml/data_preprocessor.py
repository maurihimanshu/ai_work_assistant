"""Advanced data preprocessing for activity analysis."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, StandardScaler

from ..entities.activity import Activity
from ..config.categorization_config import CategorizationConfig

logger = logging.getLogger(__name__)


class DataPreprocessor:
    """Advanced data preprocessing for activity analysis."""

    def __init__(self) -> None:
        """Initialize data preprocessor."""
        self.time_scaler = MinMaxScaler()
        self.duration_scaler = StandardScaler()
        self.is_fitted = False
        try:
            self._cat_config = CategorizationConfig.load()
        except Exception as e:
            logger.error(
                f"Failed to load categorization config in DataPreprocessor: {e}"
            )
            self._cat_config = CategorizationConfig(
                exe_to_category={}, category_weights={}
            )

    def _extract_time_features(self, timestamp: datetime) -> Dict[str, float]:
        """Extract advanced time-based features.

        Args:
            timestamp: Time to extract features from

        Returns:
            dict: Time-based features
        """
        return {
            "hour_sin": float(np.sin(2 * np.pi * timestamp.hour / 24)),
            "hour_cos": float(np.cos(2 * np.pi * timestamp.hour / 24)),
            "day_sin": float(np.sin(2 * np.pi * timestamp.weekday() / 7)),
            "day_cos": float(np.cos(2 * np.pi * timestamp.weekday() / 7)),
            "month_sin": float(np.sin(2 * np.pi * timestamp.month / 12)),
            "month_cos": float(np.cos(2 * np.pi * timestamp.month / 12)),
            "is_weekend": float(timestamp.weekday() >= 5),
            "is_work_hours": float(9 <= timestamp.hour <= 17),
            "is_lunch_time": float(12 <= timestamp.hour <= 13),
            "is_morning": float(5 <= timestamp.hour < 12),
            "is_afternoon": float(12 <= timestamp.hour < 17),
            "is_evening": float(17 <= timestamp.hour < 22),
        }

    def _extract_duration_features(
        self, activity: Activity, prev_activity: Optional[Activity] = None
    ) -> Dict[str, float]:
        """Extract advanced duration-based features.

        Args:
            activity: Current activity
            prev_activity: Previous activity if available

        Returns:
            dict: Duration-based features
        """
        features: Dict[str, float] = {
            "active_time": float(activity.active_time),
            "idle_time": float(activity.idle_time),
            "total_time": float(activity.active_time + activity.idle_time),
            "active_ratio": (
                float(activity.active_time)
                / float(activity.active_time + activity.idle_time)
                if activity.active_time + activity.idle_time > 0
                else 0.0
            ),
            "transition_time": 0.0,
            "same_app": 0.0,
            "same_category": 0.0,
        }

        # Add transition features if we have previous activity
        if prev_activity and prev_activity.end_time:
            transition_time = (
                activity.start_time - prev_activity.end_time
            ).total_seconds()
            features.update(
                {
                    "transition_time": max(0.0, transition_time),
                    "same_app": float(activity.app_name == prev_activity.app_name),
                    "same_category": float(
                        self._get_app_category(activity.app_name)
                        == self._get_app_category(prev_activity.app_name)
                    ),
                }
            )

        return features

    def _get_app_category(self, executable_or_name: str) -> str:
        """Get category using config-based mapping only.

        Returns "Unknown" if not mapped.
        """
        base = (executable_or_name or "").split("\\")[-1].split("/")[-1].lower()
        return self._cat_config.exe_to_category.get(base, "Unknown")

    def _extract_sequence_features(
        self, activities: List[Activity], window_size: int = 5
    ) -> Dict[str, List[float]]:
        """Extract sequence-based features using sliding window.

        Args:
            activities: List of activities
            window_size: Size of sliding window

        Returns:
            dict: Sequence-based features
        """
        df = pd.DataFrame(
            [
                {
                    "app": a.app_name,
                    "category": self._get_app_category(a.app_name),
                    "active_time": a.active_time,
                    "idle_time": a.idle_time,
                    "total_time": a.active_time + a.idle_time,
                }
                for a in activities
            ]
        )

        # Calculate rolling statistics
        features = {
            "active_time_mean": df["active_time"]
            .rolling(window_size, min_periods=1)
            .mean()
            .fillna(0)
            .tolist(),
            "active_time_std": df["active_time"]
            .rolling(window_size, min_periods=1)
            .std()
            .fillna(0)
            .tolist(),
            "idle_time_mean": df["idle_time"]
            .rolling(window_size, min_periods=1)
            .mean()
            .fillna(0)
            .tolist(),
            "idle_time_std": df["idle_time"]
            .rolling(window_size, min_periods=1)
            .std()
            .fillna(0)
            .tolist(),
        }

        # Calculate app and category transition rates
        features.update(
            {
                "app_transitions": [
                    float(i > 0 and row.app != df.iloc[i - 1].app)
                    for i, row in df.iterrows()
                ],
                "category_transitions": [
                    float(i > 0 and row.category != df.iloc[i - 1].category)
                    for i, row in df.iterrows()
                ],
            }
        )

        # Calculate activity rates by category
        for category in ["development", "productivity", "browser", "entertainment"]:
            mask = df["category"] == category
            features[f"{category}_rate"] = (
                mask.rolling(window_size, min_periods=1).mean().fillna(0).tolist()
            )

        return features

    def preprocess_activities(
        self, activities: List[Activity], window_size: int = 5
    ) -> Tuple[np.ndarray, List[str]]:
        """Preprocess activities for analysis and modeling.

        Args:
            activities: List of activities to preprocess
            window_size: Size of sliding window for sequence features

        Returns:
            tuple: (feature_matrix, feature_names)
        """
        if not activities:
            return np.array([]), []

        try:
            feature_dicts = []

            # Extract features for each activity
            for i, activity in enumerate(activities):
                features = {}

                # Time features
                features.update(self._extract_time_features(activity.start_time))

                # Duration features
                prev_activity = activities[i - 1] if i > 0 else None
                features.update(
                    self._extract_duration_features(activity, prev_activity)
                )

                feature_dicts.append(features)

            # Convert to DataFrame
            features_df = pd.DataFrame(feature_dicts)

            # Add sequence features
            sequence_features = self._extract_sequence_features(activities, window_size)
            for name, values in sequence_features.items():
                features_df[name] = values

            # Scale features
            if not self.is_fitted:
                # Scale time-based features to [0, 1]
                time_columns = [
                    col
                    for col in features_df.columns
                    if any(x in col for x in ["time", "rate", "ratio"])
                ]
                if time_columns:
                    self.time_scaler.fit(features_df[time_columns])

                # Standardize duration features
                duration_columns = [
                    col
                    for col in features_df.columns
                    if "duration" in col or "transition" in col
                ]
                if duration_columns:
                    self.duration_scaler.fit(features_df[duration_columns])

                self.is_fitted = True

            # Apply scaling
            feature_matrix = features_df.values
            feature_names = features_df.columns.tolist()

            return feature_matrix, feature_names

        except Exception as e:
            logger.error(f"Error preprocessing activities: {e}")
            return np.array([]), []

    def get_feature_importance(
        self, feature_matrix: np.ndarray, feature_names: List[str], target: np.ndarray
    ) -> Dict[str, float]:
        """Calculate feature importance scores.

        Args:
            feature_matrix: Matrix of features
            feature_names: List of feature names
            target: Target values

        Returns:
            dict: Feature importance scores
        """
        try:
            from sklearn.ensemble import RandomForestClassifier

            # Train a random forest for feature importance
            model = RandomForestClassifier(n_estimators=100, random_state=42)
            model.fit(feature_matrix, target)

            # Get feature importance scores
            importance = model.feature_importances_

            return dict(zip(feature_names, importance))

        except Exception as e:
            logger.error(f"Error calculating feature importance: {e}")
            return {}
