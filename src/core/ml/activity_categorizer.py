"""Activity categorization and pattern analysis system."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

from ..entities.activity import Activity
from .feature_extractor import ActivityFeatureExtractor

logger = logging.getLogger(__name__)


class ActivityCategory:
    """Represents a category of related activities."""

    def __init__(
        self,
        name: str,
        apps: Set[str],
        typical_duration: float,
        time_patterns: Dict[str, float],
        productivity_score: float
    ):
        """Initialize activity category.

        Args:
            name: Category name
            apps: Set of applications in this category
            typical_duration: Typical duration in seconds
            time_patterns: Time patterns (e.g., {'morning': 0.7})
            productivity_score: Productivity score (0-1)
        """
        self.name = name
        self.apps = apps
        self.typical_duration = typical_duration
        self.time_patterns = time_patterns
        self.productivity_score = productivity_score
        self.occurrence_count = 0
        self.total_duration = 0.0

    def update_stats(self, duration: float) -> None:
        """Update category statistics.

        Args:
            duration: Duration of activity in seconds
        """
        self.occurrence_count += 1
        self.total_duration += duration
        # Update typical duration with moving average
        self.typical_duration = (
            (self.typical_duration * (self.occurrence_count - 1) + duration) /
            self.occurrence_count
        )


class ActivityCategorizer:
    """Analyzes and categorizes user activities."""

    def __init__(
        self,
        min_cluster_size: int = 5,
        similarity_threshold: float = 0.3,
        productivity_rules: Optional[Dict[str, float]] = None
    ):
        """Initialize activity categorizer.

        Args:
            min_cluster_size: Minimum activities for a category
            similarity_threshold: Threshold for activity similarity
            productivity_rules: Manual productivity scores for apps
        """
        self.min_cluster_size = min_cluster_size
        self.similarity_threshold = similarity_threshold
        self.productivity_rules = productivity_rules or {
            # Development tools
            'code.exe': 1.0,
            'visual studio code': 1.0,
            'intellij': 1.0,
            'pycharm': 1.0,

            # Productivity apps
            'excel.exe': 0.9,
            'word.exe': 0.9,
            'powerpoint.exe': 0.9,
            'outlook.exe': 0.8,
            'teams.exe': 0.7,
            'slack.exe': 0.7,

            # Browsers (context-dependent)
            'chrome.exe': 0.6,
            'firefox.exe': 0.6,
            'edge.exe': 0.6,

            # Entertainment
            'spotify.exe': 0.3,
            'netflix.exe': 0.1,
            'game': 0.1
        }

        self.feature_extractor = ActivityFeatureExtractor()
        self.categories: Dict[str, ActivityCategory] = {}
        self.scaler = StandardScaler()
        self.clustering = DBSCAN(
            eps=similarity_threshold,
            min_samples=min_cluster_size
        )

    def _get_time_period(self, timestamp: datetime) -> str:
        """Get time period of day.

        Args:
            timestamp: Time to categorize

        Returns:
            str: Time period (morning, afternoon, evening, night)
        """
        hour = timestamp.hour
        if 5 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 17:
            return 'afternoon'
        elif 17 <= hour < 22:
            return 'evening'
        else:
            return 'night'

    def _calculate_productivity_score(
        self,
        app_names: Set[str],
        durations: List[float]
    ) -> float:
        """Calculate productivity score for a set of applications.

        Args:
            app_names: Set of application names
            durations: List of activity durations

        Returns:
            float: Productivity score (0-1)
        """
        total_duration = sum(durations)
        if total_duration == 0:
            return 0.5

        weighted_score = 0.0
        matched_duration = 0.0

        for app in app_names:
            app_lower = app.lower()
            score = 0.5  # Default score

            # Find matching rule
            for rule, rule_score in self.productivity_rules.items():
                if rule.lower() in app_lower:
                    score = rule_score
                    break

            # Find matching activities and their durations
            app_duration = sum(
                d for a, d in zip(app_names, durations)
                if a.lower() == app_lower
            )

            weighted_score += score * app_duration
            matched_duration += app_duration

        if matched_duration == 0:
            return 0.5

        return weighted_score / matched_duration

    def _extract_category_features(
        self,
        activities: List[Activity]
    ) -> Tuple[np.ndarray, List[str], List[float]]:
        """Extract features for categorization.

        Args:
            activities: List of activities to categorize

        Returns:
            tuple: (feature_matrix, app_names, durations)
        """
        features_df = self.feature_extractor.extract_features(activities)
        if features_df.empty:
            return np.array([]), [], []

        # Get relevant features for categorization
        feature_matrix = features_df[[
            'active_time',
            'idle_time',
            'hour',
            'is_work_hours',
            'is_weekend',
            'activity_rate'
        ]].values

        # Scale features
        if not hasattr(self.scaler, 'mean_'):
            self.scaler.fit(feature_matrix)
        feature_matrix = self.scaler.transform(feature_matrix)

        app_names = [a.app_name for a in activities]
        durations = [a.active_time + a.idle_time for a in activities]

        return feature_matrix, app_names, durations

    def _create_category(
        self,
        activities: List[Activity],
        cluster_activities: List[Activity]
    ) -> ActivityCategory:
        """Create a new activity category.

        Args:
            activities: All activities
            cluster_activities: Activities in this cluster

        Returns:
            ActivityCategory: New category
        """
        app_names = {a.app_name for a in cluster_activities}
        durations = [a.active_time + a.idle_time for a in cluster_activities]

        # Analyze time patterns
        time_patterns = {
            'morning': 0.0,
            'afternoon': 0.0,
            'evening': 0.0,
            'night': 0.0
        }

        for activity in cluster_activities:
            period = self._get_time_period(activity.start_time)
            time_patterns[period] += 1

        # Normalize time patterns
        total_occurrences = len(cluster_activities)
        time_patterns = {
            k: v / total_occurrences
            for k, v in time_patterns.items()
        }

        # Calculate productivity score
        productivity_score = self._calculate_productivity_score(
            app_names,
            durations
        )

        # Generate category name
        main_app = max(
            app_names,
            key=lambda x: sum(
                1 for a in cluster_activities
                if a.app_name == x
            )
        )
        category_name = f"Category_{len(self.categories)}_{main_app}"

        return ActivityCategory(
            name=category_name,
            apps=app_names,
            typical_duration=np.mean(durations),
            time_patterns=time_patterns,
            productivity_score=productivity_score
        )

    def categorize_activities(
        self,
        activities: List[Activity]
    ) -> Dict[str, ActivityCategory]:
        """Categorize a list of activities.

        Args:
            activities: Activities to categorize

        Returns:
            dict: Mapping of category names to categories
        """
        if not activities:
            return {}

        try:
            # Extract features
            features, app_names, durations = self._extract_category_features(
                activities
            )
            if len(features) == 0:
                return {}

            # Perform clustering
            labels = self.clustering.fit_predict(features)

            # Create categories for each cluster
            new_categories = {}
            for label in set(labels):
                if label == -1:  # Noise points
                    continue

                # Get activities in this cluster
                cluster_indices = np.where(labels == label)[0]
                cluster_activities = [
                    activities[i] for i in cluster_indices
                ]

                # Create category
                category = self._create_category(
                    activities,
                    cluster_activities
                )
                new_categories[category.name] = category

            # Update existing categories or add new ones
            for name, category in new_categories.items():
                if name in self.categories:
                    # Update existing category
                    existing = self.categories[name]
                    existing.apps.update(category.apps)
                    existing.time_patterns = {
                        k: (existing.time_patterns[k] + v) / 2
                        for k, v in category.time_patterns.items()
                    }
                    existing.productivity_score = (
                        existing.productivity_score * 0.7 +
                        category.productivity_score * 0.3
                    )
                else:
                    # Add new category
                    self.categories[name] = category

            return self.categories

        except Exception as e:
            logger.error(f"Error categorizing activities: {e}")
            return {}

    def _get_activity_productivity(self, activity: Activity) -> float:
        """Calculate productivity score for a single activity.

        Args:
            activity: Activity to analyze

        Returns:
            float: Productivity score (0-1)
        """
        app_name = activity.app_name.lower()
        score = 0.5  # Default score

        # Find matching rule
        for rule, rule_score in self.productivity_rules.items():
            if rule.lower() in app_name:
                score = rule_score
                break

        return score

    def _get_time_productivity(self, activities: List[Activity]) -> Dict[str, float]:
        """Get productivity by time of day.

        Args:
            activities: List of activities to analyze

        Returns:
            dict: Time period to productivity score mapping
        """
        time_periods = {
            'morning': 0.0,
            'afternoon': 0.0,
            'evening': 0.0,
            'night': 0.0
        }

        period_counts = {
            'morning': 0,
            'afternoon': 0,
            'evening': 0,
            'night': 0
        }

        for activity in activities:
            period = self._get_time_period(activity.start_time)
            productivity = self._get_activity_productivity(activity)
            time_periods[period] += productivity
            period_counts[period] += 1

        # Calculate average productivity for each period
        for period in time_periods:
            if period_counts[period] > 0:
                time_periods[period] = round(
                    time_periods[period] / period_counts[period],
                    3  # Round to 3 decimal places for consistent comparison
                )
            else:
                time_periods[period] = 0.1  # Default productivity for periods without data

        return time_periods

    def get_activity_insights(
        self,
        activities: List[Activity]
    ) -> Dict[str, any]:
        """Get insights about activities.

        Args:
            activities: Activities to analyze

        Returns:
            dict: Activity insights
        """
        if not activities:
            return {}

        try:
            categories = self.categorize_activities(activities)

            # Calculate overall productivity
            total_duration = sum(
                a.active_time + a.idle_time
                for a in activities
            )
            weighted_productivity = sum(
                c.productivity_score * c.total_duration
                for c in categories.values()
            )
            overall_productivity = (
                weighted_productivity / total_duration
                if total_duration > 0 else 0.5
            )

            # Find most productive times
            time_productivity = self._get_time_productivity(activities)

            # Get category distribution
            category_distribution = {
                name: {
                    'occurrence_count': cat.occurrence_count,
                    'total_duration': cat.total_duration,
                    'productivity_score': cat.productivity_score,
                    'time_patterns': cat.time_patterns
                }
                for name, cat in categories.items()
            }

            return {
                'overall_productivity': overall_productivity,
                'time_productivity': time_productivity,
                'category_distribution': category_distribution,
                'total_duration': total_duration,
                'unique_apps': len({a.app_name for a in activities}),
                'activity_count': len(activities)
            }

        except Exception as e:
            logger.error(f"Error getting activity insights: {e}")
            return {}