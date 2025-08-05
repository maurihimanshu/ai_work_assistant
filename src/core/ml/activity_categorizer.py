"""Activity categorization module."""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class ActivityCategorizer:
    """Categorizes activities based on patterns and rules."""

    def __init__(self):
        """Initialize activity categorizer."""
        # Default category mappings
        self.app_categories = {
            # Development
            "vscode.exe": "Development",
            "code.exe": "Development",
            "python.exe": "Development",
            "git.exe": "Development",
            "powershell.exe": "Development",
            "cmd.exe": "Development",
            "WindowsTerminal.exe": "Development",
            "devenv.exe": "Development",
            "rider64.exe": "Development",
            "idea64.exe": "Development",
            "pycharm64.exe": "Development",
            "studio64.exe": "Development",
            "cursor.exe": "Development",

            # Productivity
            "outlook.exe": "Communication",
            "teams.exe": "Communication",
            "slack.exe": "Communication",
            "zoom.exe": "Communication",
            "skype.exe": "Communication",
            "discord.exe": "Communication",
            "msteams.exe": "Communication",

            # Browsers
            "chrome.exe": "Web Browsing",
            "firefox.exe": "Web Browsing",
            "msedge.exe": "Web Browsing",
            "opera.exe": "Web Browsing",
            "brave.exe": "Web Browsing",

            # Office
            "excel.exe": "Office Work",
            "word.exe": "Office Work",
            "powerpnt.exe": "Office Work",
            "onenote.exe": "Office Work",
            "winword.exe": "Office Work",
            "notepad.exe": "Office Work",
            "notepad++.exe": "Office Work",

            # Entertainment
            "spotify.exe": "Entertainment",
            "vlc.exe": "Entertainment",
            "steam.exe": "Entertainment",
            "netflix.exe": "Entertainment",
            "youtube.exe": "Entertainment",
            "wmplayer.exe": "Entertainment",

            # System
            "explorer.exe": "System",
            "taskmgr.exe": "System",
            "control.exe": "System",
            "systemsettings.exe": "System",
        }

        # Productivity scores for categories (0-1)
        self.category_productivity = {
            "Development": 0.9,
            "Communication": 0.8,
            "Office Work": 0.8,
            "Web Browsing": 0.6,
            "System": 0.5,
            "Entertainment": 0.2,
            "Unknown": 0.4,
        }

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
                    "suggestions": []
                }

            # Categorize activities
            categories = {}
            total_time = 0
            category_time = {}
            weighted_productivity = 0.0
            total_weighted_time = 0.0

            for activity in activities:
                app_name = activity.get("app_name", "").lower()
                duration = activity.get("duration", 0)
                active_time = activity.get("active_time", 0)

                # Skip invalid activities
                if duration <= 0:
                    continue

                # Get category
                category = self.app_categories.get(app_name, "Unknown")
                categories[app_name] = category

                # Update category time
                category_time[category] = category_time.get(category, 0) + duration

                # Update total time
                total_time += duration

                # Calculate activity productivity
                activity_productivity = active_time / duration  # Between 0 and 1
                category_productivity = self.category_productivity.get(category, 0.4)  # Between 0 and 1

                # Weight productivity by duration and category
                weighted_productivity += activity_productivity * category_productivity * duration
                total_weighted_time += duration

            # Calculate overall productivity (normalized between 0 and 1)
            overall_productivity = (
                min(1.0, weighted_productivity / total_weighted_time)
                if total_weighted_time > 0
                else 0.0
            )

            # Calculate category distribution
            category_distribution = {}
            for category, time in category_time.items():
                percentage = time / total_time if total_time > 0 else 0
                productivity = self.category_productivity.get(category, 0.4)
                category_distribution[category] = {
                    "time_percentage": percentage,
                    "productivity_score": productivity
                }

            # Generate suggestions based on insights
            suggestions = self._generate_suggestions(category_distribution, overall_productivity)

            return {
                "categories": categories,
                "overall_productivity": overall_productivity,
                "category_distribution": category_distribution,
                "suggestions": suggestions
            }

        except Exception as e:
            logger.error(f"Error categorizing activities: {e}", exc_info=True)
            return {
                "categories": {},
                "overall_productivity": 0.0,
                "category_distribution": {},
                "suggestions": []
            }

    def _generate_suggestions(self, category_distribution: Dict[str, Dict], overall_productivity: float) -> List[str]:
        """Generate suggestions based on activity patterns.

        Args:
            category_distribution: Distribution of time across categories
            overall_productivity: Overall productivity score

        Returns:
            list: List of suggestions
        """
        suggestions = []

        try:
            # Check overall productivity
            if overall_productivity < 0.4:
                suggestions.append("Consider focusing on more productive activities")
            elif overall_productivity < 0.6:
                suggestions.append("Try to increase time spent on development and work tasks")

            # Check entertainment time
            entertainment = category_distribution.get("Entertainment", {})
            entertainment_time = entertainment.get("time_percentage", 0)
            if entertainment_time > 0.3:
                suggestions.append("High entertainment time detected. Consider reducing non-work activities")

            # Check development time
            dev = category_distribution.get("Development", {})
            dev_time = dev.get("time_percentage", 0)
            if dev_time < 0.3:
                suggestions.append("Consider increasing time spent on development tasks")

            # Check communication balance
            comm = category_distribution.get("Communication", {})
            comm_time = comm.get("time_percentage", 0)
            if comm_time > 0.4:
                suggestions.append("High communication time. Consider setting aside focused work periods")

            # Limit suggestions
            return suggestions[:3]

        except Exception as e:
            logger.error(f"Error generating suggestions: {e}", exc_info=True)
            return []
