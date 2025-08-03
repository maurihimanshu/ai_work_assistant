"""Feature extraction for activity data."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

from ..entities.activity import Activity


class ActivityFeatureExtractor:
    """Extracts features from activity data for machine learning."""

    def __init__(self):
        """Initialize feature extractor."""
        self.app_encoder = LabelEncoder()
        self.is_fitted = False

    def _extract_time_features(self, timestamp: datetime) -> Dict[str, int]:
        """Extract time-based features from timestamp.

        Args:
            timestamp: Datetime to extract features from

        Returns:
            dict: Time-based features
        """
        return {
            'hour': timestamp.hour,
            'day_of_week': timestamp.weekday(),
            'is_weekend': int(timestamp.weekday() >= 5),
            'is_work_hours': int(8 <= timestamp.hour <= 18),
            'time_period': (timestamp.hour // 4)  # 6 4-hour periods
        }

    def _extract_duration_features(
        self,
        activity: Activity,
        prev_activity: Optional[Activity] = None
    ) -> Dict[str, float]:
        """Extract duration-based features.

        Args:
            activity: Current activity
            prev_activity: Previous activity if available

        Returns:
            dict: Duration-based features
        """
        features = {
            'active_time': activity.active_time,
            'idle_time': activity.idle_time,
            'total_time': activity.active_time + activity.idle_time
        }

        # Add transition time if we have previous activity
        if prev_activity and prev_activity.end_time:
            transition_time = (
                activity.start_time - prev_activity.end_time
            ).total_seconds()
            features['transition_time'] = max(0, transition_time)
        else:
            features['transition_time'] = 0

        return features

    def _extract_app_features(
        self,
        activities: List[Activity]
    ) -> Dict[str, List[int]]:
        """Extract application-based features.

        Args:
            activities: List of activities to extract features from

        Returns:
            dict: Application-based features
        """
        app_names = [activity.app_name for activity in activities]

        if not self.is_fitted:
            self.app_encoder.fit(app_names)
            self.is_fitted = True

        app_encoded = self.app_encoder.transform(app_names)

        return {
            'app_id': app_encoded.tolist(),
            'app_switch': [
                1 if i > 0 and app_encoded[i] != app_encoded[i-1] else 0
                for i in range(len(app_encoded))
            ]
        }

    def _extract_window_features(
        self,
        activities: List[Activity],
        window_size: int = 5
    ) -> Dict[str, List[float]]:
        """Extract rolling window features.

        Args:
            activities: List of activities
            window_size: Size of the rolling window

        Returns:
            dict: Window-based features
        """
        df = pd.DataFrame([
            {
                'active_time': a.active_time,
                'idle_time': a.idle_time,
                'total_time': a.active_time + a.idle_time
            }
            for a in activities
        ])

        return {
            'active_time_mean': df['active_time']
                .rolling(window_size, min_periods=1)
                .mean()
                .fillna(0)
                .tolist(),
            'idle_time_mean': df['idle_time']
                .rolling(window_size, min_periods=1)
                .mean()
                .fillna(0)
                .tolist(),
            'activity_rate': df['active_time']
                .rolling(window_size, min_periods=1)
                .sum()
                .fillna(0)
                .div(df['total_time']
                    .rolling(window_size, min_periods=1)
                    .sum()
                    .fillna(1)
                )
                .fillna(0)
                .tolist()
        }

    def extract_features(
        self,
        activities: List[Activity],
        window_size: int = 5
    ) -> pd.DataFrame:
        """Extract all features from a list of activities.

        Args:
            activities: List of activities to extract features from
            window_size: Size of the rolling window for window features

        Returns:
            DataFrame: Extracted features
        """
        if not activities:
            return pd.DataFrame()

        features = []

        # Extract app-based features first (needs full list)
        app_features = self._extract_app_features(activities)
        window_features = self._extract_window_features(activities, window_size)

        for i, activity in enumerate(activities):
            # Time features
            feature_dict = self._extract_time_features(activity.start_time)

            # Duration features
            prev_activity = activities[i-1] if i > 0 else None
            feature_dict.update(
                self._extract_duration_features(activity, prev_activity)
            )

            # Add app features for this index
            feature_dict['app_id'] = app_features['app_id'][i]
            feature_dict['app_switch'] = app_features['app_switch'][i]

            # Add window features for this index
            for key, values in window_features.items():
                feature_dict[key] = values[i]

            features.append(feature_dict)

        return pd.DataFrame(features)

    def get_feature_names(self) -> List[str]:
        """Get list of feature names in order.

        Returns:
            list: Feature names
        """
        return [
            # Time features
            'hour',
            'day_of_week',
            'is_weekend',
            'is_work_hours',
            'time_period',

            # Duration features
            'active_time',
            'idle_time',
            'total_time',
            'transition_time',

            # App features
            'app_id',
            'app_switch',

            # Window features
            'active_time_mean',
            'idle_time_mean',
            'activity_rate'
        ]