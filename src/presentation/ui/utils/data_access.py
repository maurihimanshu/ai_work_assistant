"""Data access utilities for UI components."""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from ..utils.data_mappers import DataMapper
from ..utils.config_store import ConfigStore
from ..utils.data_mappers import AppNameMapper

logger = logging.getLogger(__name__)


class DataAccessManager:
    """Manages data access and transformation for UI components."""

    def __init__(
        self,
        analytics_service,
        session_service,
        suggestion_service,
        max_retries: int = 3,
        retry_delay: float = 0.5,
    ):
        """Initialize data access manager.

        Args:
            analytics_service: Analytics service instance
            session_service: Session service instance
            suggestion_service: Task suggestion service instance
            max_retries: Maximum number of retries for data access
            retry_delay: Base delay between retries in seconds
        """
        self.analytics_service = analytics_service
        self.session_service = session_service
        self.suggestion_service = suggestion_service
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._workspace_service = None
        # Load presentation-layer mappings
        self._config_store = ConfigStore()
        self._app_mapper = AppNameMapper(self._config_store.mapping_lookup())

    def _reload_mappings(self) -> None:
        """Reload mappings from JSON so changes take effect without restart."""
        try:
            self._app_mapper = AppNameMapper(self._config_store.mapping_lookup())
        except Exception:
            pass

    # Workspace ops (lazy load to avoid core service changes)
    @property
    def workspace_service(self):
        if self._workspace_service is None:
            from core.services.workspace_service import WorkspaceService

            self._workspace_service = WorkspaceService()
        return self._workspace_service

    def workspace_save(self) -> str:
        snap = self.workspace_service.create_snapshot(note="manual")
        return snap.id

    def workspace_restore(self) -> int:
        snap = self.workspace_service.load_last_snapshot()
        if not snap:
            return 0
        return self.workspace_service.restore_snapshot(snap)

    def workspace_close(self) -> int:
        return self.workspace_service.close_workspace()

    # Detailed workspace ops for UI tables
    def workspace_save_details(self) -> Dict[str, Any]:
        self._reload_mappings()
        snap = self.workspace_service.create_snapshot(note="manual")
        details = []
        for app in snap.apps:
            name, category = self._app_mapper.map_executable(app.executable_path)
            details.append(
                {
                    "action": "save",
                    "executable": app.executable_path,
                    "app_name": name,
                    "category": category,
                    "args": " ".join(app.args) if app.args else "",
                    "title": app.window_title or "",
                    "result": "saved",
                }
            )
        return {"snapshot_id": snap.id, "apps": details}

    def workspace_restore_details(self) -> Dict[str, Any]:
        self._reload_mappings()
        snap = self.workspace_service.load_last_snapshot()
        if not snap:
            return {"snapshot_id": None, "apps": []}
        details = []
        # Attempt launches with per-app status using the existing controller
        controller = self.workspace_service.controller
        for app in snap.apps:
            ok = controller.start_app(app.executable_path, app.args)
            name, category = self._app_mapper.map_executable(app.executable_path)
            details.append(
                {
                    "action": "restore",
                    "executable": app.executable_path,
                    "app_name": name,
                    "category": category,
                    "args": " ".join(app.args) if app.args else "",
                    "title": app.window_title or "",
                    "result": "launched" if ok else "failed",
                }
            )
        return {"snapshot_id": snap.id, "apps": details}

    def workspace_close_details(self) -> Dict[str, Any]:
        self._reload_mappings()
        controller = self.workspace_service.controller
        running = controller.list_running_apps()
        details = []
        for app in running:
            ok = False
            try:
                if app.name:
                    ok = controller.close_app_by_exe(app.name)
            except Exception:
                ok = False
            name, category = self._app_mapper.map_executable(app.exe)
            details.append(
                {
                    "action": "close",
                    "executable": app.exe,
                    "app_name": name,
                    "category": category,
                    "args": " ".join(app.cmdline[1:]) if len(app.cmdline) > 1 else "",
                    "title": app.window_title or "",
                    "result": "closed" if ok else "failed",
                }
            )
        return {"apps": details}

    def _retry_operation(self, operation, *args, **kwargs) -> Any:
        """Retry an operation with exponential backoff."""
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2**attempt)
                    logger.warning(
                        f"Data access attempt {attempt + 1} failed, "
                        f"retrying in {delay:.1f}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"All data access retries failed: {e}", exc_info=True)

        # Return empty data structure on failure
        if "get_activities" in str(operation):
            return []
        elif "get_productivity_report" in str(operation):
            return {
                "daily_metrics": {"total_time": 0, "active_time": 0, "idle_time": 0},
                "app_patterns": {},
                "category_patterns": {},
                "productivity_trends": {"hourly": [0.0] * 24, "daily": [0.0] * 7},
                "activities": [],
                "insights": {
                    "categories": {},
                    "overall_productivity": 0.0,
                    "suggestions": [],
                },
            }
        elif "get_current_suggestions" in str(operation):
            return []
        else:
            return None

    def get_activities(self, time_window: timedelta) -> Dict[str, Any]:
        """Get activities within time window with retry logic."""
        self._reload_mappings()
        end_time = datetime.now()
        start_time = end_time - time_window

        try:
            activities = self._retry_operation(
                self.session_service.repository.get_by_timerange, start_time, end_time
            )

            # Transform Activity objects to dictionaries
            activity_list = []
            total_active_time = 0
            total_idle_time = 0

            for activity in activities:
                # Handle both dictionary and Activity object formats
                if isinstance(activity, dict):
                    activity_dict = activity
                else:
                    # Activity object - access attributes directly
                    activity_dict = {
                        "id": getattr(activity, "id", ""),
                        "app_name": getattr(activity, "app_name", "Unknown"),
                        "window_title": getattr(activity, "window_title", ""),
                        "start_time": getattr(activity, "start_time", None),
                        "end_time": getattr(activity, "end_time", None),
                        "active_time": getattr(activity, "active_time", 0),
                        "idle_time": getattr(activity, "idle_time", 0),
                        "executable_path": getattr(activity, "executable_path", ""),
                    }

                # Ensure datetime objects for timestamps
                if isinstance(activity_dict["start_time"], str):
                    try:
                        activity_dict["start_time"] = datetime.fromisoformat(
                            activity_dict["start_time"]
                        )
                    except (ValueError, TypeError):
                        activity_dict["start_time"] = None

                if isinstance(activity_dict["end_time"], str):
                    try:
                        activity_dict["end_time"] = datetime.fromisoformat(
                            activity_dict["end_time"]
                        )
                    except (ValueError, TypeError):
                        activity_dict["end_time"] = None

                # Apply app mapping
                exe_source = activity_dict.get("executable_path") or activity_dict.get(
                    "app_name", ""
                )
                friendly_name, category = self._app_mapper.map_executable(exe_source)

                # Format timestamps for UI
                activity_dict["start_time"] = (
                    activity_dict["start_time"].strftime("%Y-%m-%d %H:%M:%S")
                    if activity_dict["start_time"]
                    else "N/A"
                )
                activity_dict["end_time"] = (
                    activity_dict["end_time"].strftime("%Y-%m-%d %H:%M:%S")
                    if activity_dict["end_time"]
                    else "N/A"
                )

                # Ensure numeric values
                try:
                    active_time = float(activity_dict["active_time"])
                except (ValueError, TypeError):
                    active_time = 0
                try:
                    idle_time = float(activity_dict["idle_time"])
                except (ValueError, TypeError):
                    idle_time = 0

                total_time = active_time + idle_time
                activity_list.append(
                    {
                        **activity_dict,
                        "display_name": friendly_name,
                        "category": category,
                        "total_time": total_time,
                    }
                )
                total_active_time += active_time
                total_idle_time += idle_time

            return {
                "list": activity_list,
                "total_active_time": total_active_time,
                "total_idle_time": total_idle_time,
                "total_time": total_active_time + total_idle_time,
            }

        except Exception as e:
            logger.error(f"Error getting activities: {e}", exc_info=True)
            return {
                "list": [],
                "total_active_time": 0,
                "total_idle_time": 0,
                "total_time": 0,
            }

    def _parse_time_to_seconds(self, time_str: str) -> float:
        """Parse time string to seconds for sorting."""
        try:
            if "h" in time_str:
                parts = time_str.split("h")
                hours = float(parts[0].strip())
                minutes = float(parts[1].strip("m").strip()) if "m" in parts[1] else 0
                return hours * 3600 + minutes * 60
            elif "m" in time_str:
                minutes = float(time_str.strip("m").strip())
                return minutes * 60
            elif "s" in time_str:
                seconds = float(time_str.strip("s").strip())
                return seconds
            return 0
        except Exception as e:
            logger.error(f"Error parsing time string '{time_str}': {e}")
            return 0

    def get_productivity_data(self, time_window: timedelta) -> Dict[str, Any]:
        """Get productivity data with retry logic."""
        self._reload_mappings()
        try:
            report = self._retry_operation(
                self.analytics_service.get_productivity_report, time_window
            )

            if not report:
                logger.warning("No productivity report data received")
                return self._get_empty_metrics()

            # Mapping for app names
            exe_map = self._app_mapper

            # Get daily metrics
            daily_metrics = report.get("daily_metrics", {})
            total_time = float(daily_metrics.get("total_time", 0))
            active_time = float(daily_metrics.get("active_time", 0))
            idle_time = float(daily_metrics.get("idle_time", 0))

            # Get app patterns
            app_patterns = report.get("app_patterns", {})
            app_data = []
            for app_key, stats in app_patterns.items():
                friendly_name, category = exe_map.map_executable(app_key)
                app_time = float(stats.get("total_time", 0))
                app_percentage = float(stats.get("usage_percentage", 0)) * 100
                app_data.append(
                    [
                        friendly_name,
                        DataMapper.format_time(app_time),
                        DataMapper.format_percentage(app_percentage / 100),
                    ]
                )

            # Sort app data by time descending
            app_data.sort(key=lambda x: self._parse_time_to_seconds(x[1]), reverse=True)

            # Build category totals strictly from mapped app totals to avoid double counting
            merged_category = {}
            for app_key, stats in app_patterns.items():
                _, mapped_category = exe_map.map_executable(app_key)
                t = float(stats.get("total_time", 0))
                agg = merged_category.setdefault(
                    mapped_category, {"total_time": 0.0, "usage_percentage": 0.0}
                )
                agg["total_time"] += t

            # Compute category usage percentage as share of overall total_time
            safe_total = total_time if total_time > 0 else 1.0
            for cat_name, stats in merged_category.items():
                stats["usage_percentage"] = stats["total_time"] / safe_total

            category_data = []
            for cat_name, stats in merged_category.items():
                cat_time = float(stats.get("total_time", 0))
                cat_percentage_ratio = float(stats.get("usage_percentage", 0))
                category_data.append(
                    [
                        cat_name,
                        DataMapper.format_time(cat_time),
                        DataMapper.format_percentage(cat_percentage_ratio),
                    ]
                )

            # Sort category data by time descending
            category_data.sort(
                key=lambda x: self._parse_time_to_seconds(x[1]), reverse=True
            )

            # Calculate focus and break time
            # Focus time: sum of active time for apps with high within-app efficiency and productive category
            # Break time: keep existing heuristic based on very low usage share (< 10%)
            focus_time = 0
            break_time = 0

            # Build category productivity map from insights if available
            try:
                _insights_for_focus = (
                    report.get("insights", {}) if isinstance(report, dict) else {}
                )
                _cat_prod_map = {
                    cat: float(info.get("productivity_score", 0.0))
                    for cat, info in (
                        _insights_for_focus.get("category_distribution", {}) or {}
                    ).items()
                }
            except Exception:
                _cat_prod_map = {}

            for app_key, stats in app_patterns.items():
                app_active_time = float(stats.get("active_time", 0))
                app_total_time = float(stats.get("total_time", 0))
                app_efficiency = (
                    (app_active_time / app_total_time) if app_total_time > 0 else 0.0
                )

                # Map app to category using UI mapper
                _, category = exe_map.map_executable(app_key)
                category_productivity = float(_cat_prod_map.get(category, 0.4))

                # Focus: high efficiency and productive category
                if app_efficiency >= 0.8 and category_productivity >= 0.8:
                    focus_time += app_active_time
                # Break: retain existing rule for very low usage share
                elif float(stats.get("usage_percentage", 0)) < 0.1:
                    break_time += app_active_time

            # Get productivity score from insights
            insights = report.get("insights", {})
            productivity_score = float(insights.get("overall_productivity", 0))

            # Calculate efficiency (active vs total time)
            efficiency_score = active_time / total_time if total_time > 0 else 0

            # Calculate average session time from active periods
            activities = report.get("activities", [])
            if activities:
                # Sort activities by start time
                sorted_activities = sorted(
                    activities, key=lambda x: x.get("start_time", datetime.min)
                )

                # Find continuous sessions (gaps less than 5 minutes)
                sessions = []
                current_session = []

                for activity in sorted_activities:
                    if not current_session:
                        current_session = [activity]
                    else:
                        prev_end = current_session[-1].get("end_time")
                        curr_start = activity.get("start_time")

                        if prev_end and curr_start:
                            gap = (curr_start - prev_end).total_seconds()
                            if gap < 300:  # 5 minutes
                                current_session.append(activity)
                            else:
                                if len(current_session) > 1:
                                    sessions.append(current_session)
                                current_session = [activity]

                if len(current_session) > 1:
                    sessions.append(current_session)

                # Calculate average session duration
                if sessions:
                    session_durations = []
                    for session in sessions:
                        if len(session) > 1:
                            start = session[0].get("start_time")
                            end = session[-1].get("end_time")
                            if start and end:
                                duration = (end - start).total_seconds()
                                session_durations.append(duration)

                    avg_session_time = (
                        sum(session_durations) / len(session_durations)
                        if session_durations
                        else 0
                    )
                else:
                    avg_session_time = 0
            else:
                avg_session_time = 0

            # Calculate hourly distribution
            hourly_distribution = {}
            for activity in activities:
                try:
                    start_time = activity.get("start_time")
                    if isinstance(start_time, str):
                        start_time = datetime.fromisoformat(start_time)

                    if not isinstance(start_time, datetime):
                        continue

                    hour = start_time.hour
                    duration = float(activity.get("active_time", 0))

                    if hour not in hourly_distribution:
                        hourly_distribution[hour] = 0
                    hourly_distribution[hour] += duration

                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Error processing activity for hourly distribution: {e}"
                    )
                    continue

            # Transform productivity data for UI
            metrics = {
                "total_time": total_time,
                "active_time": active_time,
                "idle_time": idle_time,
                "focus_time": focus_time,
                "break_time": break_time,
                "productivity_score": productivity_score,
                "efficiency_score": efficiency_score,
                "avg_session_time": avg_session_time,
            }

            # Create statistics data structure
            statistics = {
                "app_count": len(app_patterns),
                "category_count": len(merged_category),
                "productivity_score": productivity_score,
                "app_data": app_data,
                "category_data": category_data,
            }

            # Get productivity trends
            trends = report.get("productivity_trends", {})
            daily_trends = trends.get("daily", [])

            # Ensure trends are valid numbers between 0 and 1
            daily_trends = [
                max(0.0, min(1.0, float(x)))
                for x in daily_trends
                if isinstance(x, (int, float, str))
            ]

            return {
                "metrics": metrics,
                "trends": {"productivity_trends": {"daily": daily_trends}},
                "categories": merged_category,
                "statistics": statistics,
                "hourly_distribution": hourly_distribution,
            }

        except Exception as e:
            logger.error(f"Error getting productivity data: {e}", exc_info=True)
            return self._get_empty_metrics()

    def _get_empty_metrics(self) -> Dict[str, Any]:
        """Get empty metrics structure."""
        return {
            "metrics": {
                "total_time": 0,
                "active_time": 0,
                "idle_time": 0,
                "focus_time": 0,
                "break_time": 0,
                "productivity_score": 0,
                "efficiency_score": 0,
                "avg_session_time": 0,
            },
            "trends": {"productivity_trends": {"daily": []}},
            "categories": {},
            "statistics": {
                "app_count": 0,
                "category_count": 0,
                "productivity_score": 0,
                "app_data": [],
                "category_data": [],
            },
            "hourly_distribution": {},
        }

    def get_suggestions(self, time_window: timedelta) -> List[str]:
        """Get suggestions with retry logic."""
        try:
            return (
                self._retry_operation(
                    self.suggestion_service.get_current_suggestions, time_window
                )
                or []
            )
        except Exception as e:
            logger.error(f"Error getting suggestions: {e}", exc_info=True)
            return []

    def get_dashboard_data(self, time_window: timedelta) -> Dict[str, Any]:
        """Get all dashboard data with retry logic."""
        try:
            activities = self.get_activities(time_window)
            productivity = self.get_productivity_data(time_window)
            suggestions = self.get_suggestions(time_window)

            return {
                "activities": activities,
                "productivity": productivity,
                "suggestions": suggestions,
            }

        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}", exc_info=True)
            return {
                "activities": {
                    "list": [],
                    "total_active_time": 0,
                    "total_idle_time": 0,
                    "total_time": 0,
                },
                "productivity": self._get_empty_metrics(),
                "suggestions": [],
            }
