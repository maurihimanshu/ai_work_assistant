"""Productivity data mapping utilities."""

import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)


class ProductivityMapper:
    """Maps productivity data for UI components."""

    @staticmethod
    def map_productivity_metrics(report: Dict[str, Any]) -> Dict[str, Any]:
        """Map productivity metrics for overview display.

        Args:
            report: Raw productivity report

        Returns:
            Mapped productivity metrics
        """
        try:
            if not isinstance(report, dict):
                raise ValueError(f"Invalid report type: {type(report)}")

            total_time = report.get("total_time", 0)
            active_time = report.get("active_time", 0)
            idle_time = report.get("idle_time", 0)

            # Calculate productivity score
            productivity_score = active_time / total_time if total_time > 0 else 0.0

            # Calculate focus time (continuous active periods)
            focus_time = report.get("focus_time", 0)

            # Calculate break time (appropriate idle periods)
            break_time = report.get("break_time", 0)

            return {
                "productivity_score": productivity_score,
                "focus_time": focus_time,
                "break_time": break_time,
                "efficiency_score": report.get("efficiency_score", 0.0),
                "active_apps": report.get("active_apps", 0),
                "total_time": total_time,
                "active_time": active_time,
                "idle_time": idle_time,
            }
        except Exception as e:
            logger.error(f"Error mapping productivity metrics: {e}", exc_info=True)
            return {
                "productivity_score": 0.0,
                "focus_time": 0,
                "break_time": 0,
                "efficiency_score": 0.0,
                "active_apps": 0,
                "total_time": 0,
                "active_time": 0,
                "idle_time": 0,
            }

    @staticmethod
    def map_productivity_trends(report: Dict[str, Any]) -> Dict[str, Any]:
        """Map productivity trends for charts.

        Args:
            report: Raw productivity report

        Returns:
            Mapped productivity trends
        """
        try:
            if not isinstance(report, dict):
                raise ValueError(f"Invalid report type: {type(report)}")

            # Get hourly trends
            hourly_trends = report.get("hourly_trends", [0.0] * 24)
            if len(hourly_trends) != 24:
                logger.warning(f"Invalid hourly trends length: {len(hourly_trends)}")
                hourly_trends = [0.0] * 24

            # Get daily trends
            daily_trends = report.get("daily_trends", [0.0] * 7)
            if len(daily_trends) != 7:
                logger.warning(f"Invalid daily trends length: {len(daily_trends)}")
                daily_trends = [0.0] * 7

            # Create heatmap data
            heatmap_data = np.zeros((7, 24))
            for day in range(7):
                for hour in range(24):
                    heatmap_data[day, hour] = hourly_trends[hour]

            return {
                "hourly_trends": hourly_trends,
                "daily_trends": daily_trends,
                "heatmap_data": heatmap_data,
            }
        except Exception as e:
            logger.error(f"Error mapping productivity trends: {e}", exc_info=True)
            return {
                "hourly_trends": [0.0] * 24,
                "daily_trends": [0.0] * 7,
                "heatmap_data": np.zeros((7, 24)),
            }

    @staticmethod
    def map_category_stats(report: Dict[str, Any]) -> Dict[str, Any]:
        """Map category statistics for charts.

        Args:
            report: Raw productivity report

        Returns:
            Mapped category statistics
        """
        try:
            if not isinstance(report, dict):
                raise ValueError(f"Invalid report type: {type(report)}")

            categories = report.get("categories", {})
            if not isinstance(categories, dict):
                raise ValueError(f"Invalid categories type: {type(categories)}")

            category_data = {}
            total_time = sum(
                cat.get("duration", 0)
                for cat in categories.values()
                if isinstance(cat, dict)
            )

            for name, data in categories.items():
                if not isinstance(data, dict):
                    continue

                duration = data.get("duration", 0)
                category_data[name] = {
                    "duration": duration,
                    "percentage": duration / total_time if total_time > 0 else 0,
                    "productivity_score": data.get("productivity_score", 0.0),
                }

            return {
                "categories": category_data,
                "total_categories": len(category_data),
                "total_time": total_time,
            }
        except Exception as e:
            logger.error(f"Error mapping category statistics: {e}", exc_info=True)
            return {"categories": {}, "total_categories": 0, "total_time": 0}
