"""Feature extraction for activity data."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

from ..entities.activity import Activity


class ActivityFeatureExtractor:
    """Extract features from activities for ML models."""

    def extract_features(self, activities: List[Dict]) -> np.ndarray:
        """Extract features from activities.

        Args:
            activities: List of activity dictionaries

        Returns:
            ndarray: Feature matrix
        """
        try:
            if not activities:
                return np.array([])

            features = []
            for activity in activities:
                # Time-based features
                start_time = activity.get("start_time")
                if not start_time:
                    continue

                # Basic features
                duration = float(activity.get("duration", 0))
                active_time = float(activity.get("active_time", 0))
                idle_time = float(activity.get("idle_time", 0))

                # Calculate derived features
                hour = start_time.hour
                weekday = start_time.weekday()
                is_work_hours = 1 if 9 <= hour <= 17 else 0
                productivity = active_time / duration if duration > 0 else 0

                # Create feature vector
                feature_vector = [
                    hour / 24.0,  # Normalize hour to 0-1
                    weekday / 7.0,  # Normalize weekday to 0-1
                    is_work_hours,
                    duration / 3600.0,  # Convert to hours
                    active_time / duration if duration > 0 else 0,
                    idle_time / duration if duration > 0 else 0,
                    productivity,
                ]
                features.append(feature_vector)

            return np.array(features)

        except Exception as e:
            logger.error(f"Error extracting features: {e}", exc_info=True)
            return np.array([])

    def extract_labels(self, activities: List[Dict]) -> np.ndarray:
        """Extract labels from activities.

        Args:
            activities: List of activity dictionaries

        Returns:
            ndarray: Label array
        """
        try:
            if not activities:
                return np.array([])

            labels = []
            for activity in activities:
                app_name = activity.get("app_name", "unknown")
                labels.append(app_name)

            return np.array(labels)

        except Exception as e:
            logger.error(f"Error extracting labels: {e}", exc_info=True)
            return np.array([])
