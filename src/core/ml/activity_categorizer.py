"""Activity categorization module."""

import logging
from typing import Dict, List, Optional

from ..config.categorization_config import CategorizationConfig

logger = logging.getLogger(__name__)


class ActivityCategorizer:
    """Categorizes activities based on patterns and rules."""

    def __init__(self, load_config: bool = True, default_weight: float = 0.5):
        """Initialize activity categorizer.

        Args:
            load_config: If True, load overrides from data/config.
            default_weight: Fallback productivity weight when not configured.
        """
        self._config: Optional[CategorizationConfig] = None
        self._overrides: Dict[str, str] = {}
        self._weights: Dict[str, float] = {}
        self._default_weight: float = float(default_weight)

        if load_config:
            try:
                self._config = CategorizationConfig.load()
                self._weights = dict(self._config.category_weights or {})
            except Exception as e:
                logger.error(f"Failed to load categorization config: {e}")
                self._config = None
                self._weights = {}

    @staticmethod
    def _basename_lower(path_or_name: str) -> str:
        return (path_or_name or "").split("\\")[-1].split("/")[-1].lower()

    def _category_for_activity(self, activity: Dict) -> str:
        # Prefer explicit override
        exe = activity.get("executable_path") or activity.get("app_name") or ""
        exe_key = self._basename_lower(exe)
        if exe_key in self._overrides:
            return self._overrides[exe_key]
        # Configured mapping
        if self._config:
            configured = self._config.exe_to_category.get(exe_key)
            if configured:
                return configured
        # Unknown if no mapping
        return "Unknown"

    def _weight_for_category(self, category: str) -> float:
        try:
            return float(self._weights.get(category, self._default_weight))
        except Exception:
            return self._default_weight

    def get_activity_insights(self, activities: List[Dict]) -> Dict:
        """Get insights about activities.

        Args:
            activities: List of activity dictionaries

        Returns:
            dict: Activity insights including categories and productivity scores
        """
        try:
            if not activities:
                return {
                    "categories": {},
                    "overall_productivity": 0.0,
                    "category_distribution": {},
                    "suggestions": [],
                }

            # Categorize activities
            categories = {}
            total_time = 0.0
            category_time: Dict[str, float] = {}
            weighted_productivity = 0.0
            total_weighted_time = 0.0

            for activity in activities:
                duration = float(activity.get("duration", 0) or 0)
                active_time = float(activity.get("active_time", 0) or 0)

                # Skip invalid activities
                if duration <= 0:
                    continue

                # Get category
                category = self._category_for_activity(activity)
                # Use executable basename as key
                exe_or_name = (
                    activity.get("executable_path") or activity.get("app_name") or ""
                )
                app_key = self._basename_lower(exe_or_name)
                categories[app_key] = category

                # Update category time
                category_time[category] = category_time.get(category, 0.0) + duration

                # Update totals
                total_time += duration

                # Calculate activity productivity
                activity_productivity = (
                    (active_time / duration) if duration > 0 else 0.0
                )
                category_productivity = self._weight_for_category(category)

                # Weight productivity by duration and category
                weighted_productivity += (
                    activity_productivity * category_productivity * duration
                )
                total_weighted_time += duration

            # Calculate overall productivity (normalized between 0 and 1)
            overall_productivity = (
                min(1.0, weighted_productivity / total_weighted_time)
                if total_weighted_time > 0
                else 0.0
            )

            # Calculate category distribution
            category_distribution: Dict[str, Dict[str, float]] = {}
            for category, time_spent in category_time.items():
                percentage = (time_spent / total_time) if total_time > 0 else 0.0
                productivity = self._weight_for_category(category)
                category_distribution[category] = {
                    "time_percentage": percentage,
                    "productivity_score": productivity,
                }

            # Generate suggestions based on insights
            suggestions = self._generate_suggestions(
                category_distribution, overall_productivity
            )

            return {
                "categories": categories,
                "overall_productivity": overall_productivity,
                "category_distribution": category_distribution,
                "suggestions": suggestions,
            }

        except Exception as e:
            logger.error(f"Error categorizing activities: {e}", exc_info=True)
            return {
                "categories": {},
                "overall_productivity": 0.0,
                "category_distribution": {},
                "suggestions": [],
            }

    def _generate_suggestions(
        self, category_distribution: Dict[str, Dict], overall_productivity: float
    ) -> List[str]:
        """Generate suggestions based on activity patterns.

        Args:
            category_distribution: Distribution of time across categories
            overall_productivity: Overall productivity score

        Returns:
            list: List of suggestions
        """
        suggestions: List[str] = []

        try:
            # Check overall productivity
            if overall_productivity < 0.4:
                suggestions.append("Consider focusing on more productive activities")
            elif overall_productivity < 0.6:
                suggestions.append(
                    "Try to increase time spent on development and work tasks"
                )

            # Check entertainment time
            entertainment = category_distribution.get("Entertainment", {})
            entertainment_time = float(entertainment.get("time_percentage", 0) or 0)
            if entertainment_time > 0.3:
                suggestions.append(
                    "High entertainment time detected. Consider reducing non-work activities"
                )

            # Check development time
            dev = category_distribution.get("Development", {})
            dev_time = float(dev.get("time_percentage", 0) or 0)
            if dev_time < 0.3:
                suggestions.append(
                    "Consider increasing time spent on development tasks"
                )

            # Check communication balance
            comm = category_distribution.get("Communication", {})
            comm_time = float(comm.get("time_percentage", 0) or 0)
            if comm_time > 0.4:
                suggestions.append(
                    "High communication time. Consider setting aside focused work periods"
                )

            # Limit suggestions
            return suggestions[:3]

        except Exception as e:
            logger.error(f"Error generating suggestions: {e}", exc_info=True)
            return []

    # --- Feedback API ---
    def set_app_category(self, app_name: str, category: str) -> None:
        """Override category for a given application name/path (case-insensitive)."""
        try:
            if not app_name:
                return
            self._overrides[self._basename_lower(app_name)] = category
            logger.info(f"Set category override of {app_name} -> {category}")
        except Exception as e:
            logger.error(f"Error setting app category: {e}")

    def adjust_category_productivity(self, category: str, delta: float) -> None:
        """Adjust in-memory productivity weight for a category and clamp to [0,1]."""
        try:
            current = float(self._weights.get(category, self._default_weight))
            new_val = max(0.0, min(1.0, current + delta))
            self._weights[category] = new_val
            logger.info(
                f"Adjusted productivity of {category}: {current:.2f} -> {new_val:.2f}"
            )
        except Exception as e:
            logger.error(f"Error adjusting category productivity: {e}")
