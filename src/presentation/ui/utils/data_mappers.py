"""Mapping helpers for transforming raw data for UI display."""

from __future__ import annotations

from typing import Dict, Tuple, List, Any
from datetime import datetime


class AppNameMapper:
    """Maps process executables to user-friendly names and categories."""

    def __init__(self, exe_to_name_category: Dict[str, Tuple[str, str]]):
        self._map = {k.lower(): v for k, v in exe_to_name_category.items()}

    def map_executable(self, executable_path_or_name: str) -> Tuple[str, str]:
        exe = (executable_path_or_name or "").split("\\")[-1].split("/")[-1]
        key = exe.lower()
        name, category = self._map.get(key, (exe, "Unknown"))
        return name, category


class DataMapper:
    """Backward-compatible helpers for time and percentage formatting."""

    @staticmethod
    def format_time(seconds: float) -> str:
        seconds = float(seconds or 0)
        if seconds < 60:
            return f"{int(seconds)}s"
        minutes = seconds // 60
        hours = minutes // 60
        minutes = minutes % 60
        if hours:
            return f"{int(hours)}h {int(minutes)}m"
        return f"{int(minutes)}m"

    @staticmethod
    def format_percentage(value: float) -> str:
        try:
            # DataAccess passes 0..1 values; keep behavior
            return f"{float(value) * 100:.1f}%"
        except Exception:
            return "0.0%"

    @staticmethod
    def map_activity_list(activities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Adapt activity dicts for the Activity table, using display_name when present."""
        mapped: List[Dict[str, Any]] = []
        for a in activities:
            try:
                app_name = a.get("display_name") or a.get("app_name") or "Unknown"
                window_title = a.get("window_title", "")
                start_time = a.get("start_time", "N/A")
                # Durations
                active = a.get("active_time", 0) or 0
                idle = a.get("idle_time", 0) or 0
                total = (
                    a.get("total_time")
                    if a.get("total_time") is not None
                    else (active + idle)
                )
                mapped.append(
                    {
                        "id": str(a.get("id", "")),
                        "app_name": str(app_name),
                        "window_title": str(window_title),
                        "start_time": str(start_time),
                        "duration": DataMapper.format_time(total),
                        "active_time": DataMapper.format_time(active),
                        "idle_time": DataMapper.format_time(idle),
                    }
                )
            except Exception:
                continue
        return mapped
