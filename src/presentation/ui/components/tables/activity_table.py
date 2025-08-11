"""Activity table module."""

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from typing import List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ActivityTableModel(QAbstractTableModel):
    """Model for activity table data."""

    def __init__(self, parent=None):
        """Initialize activity table model."""
        super().__init__(parent)
        self.activities = []
        self._sort_column = -1
        self._sort_order = Qt.SortOrder.AscendingOrder
        self.headers = [
            "Time",
            "Application",
            "Window Title",
            "Duration",
            "Active Time",
            "Status",
        ]

    def rowCount(self, parent=QModelIndex()):
        """Get number of rows."""
        return len(self.activities)

    def columnCount(self, parent=QModelIndex()):
        """Get number of columns."""
        return len(self.headers)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        """Get header data."""
        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Horizontal
        ):
            return self.headers[section]
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """Get cell data."""
        try:
            if not index.isValid():
                return None

            if role == Qt.ItemDataRole.DisplayRole:
                activity = self.activities[index.row()]
                column = index.column()

                if column == 0:  # Time
                    return activity.get("start_time", "")
                elif column == 1:  # Application
                    return activity.get("app_name", "Unknown")
                elif column == 2:  # Window Title
                    return activity.get("window_title", "")
                elif column == 3:  # Duration
                    return activity.get("duration", "0s")
                elif column == 4:  # Active Time
                    return activity.get("active_time", "0s")
                elif column == 5:  # Status
                    active_time = activity.get("active_time", "0s")
                    idle_time = activity.get("idle_time", "0s")
                    return "Active" if active_time > idle_time else "Idle"

            elif role == Qt.ItemDataRole.TextAlignmentRole:
                column = index.column()
                if column in [0, 3, 4]:  # Time, Duration, Active Time
                    return int(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            elif role == Qt.ItemDataRole.ToolTipRole:
                activity = self.activities[index.row()]
                column = index.column()

                if column == 0:  # Time
                    return f"Start time: {activity.get('start_time', '')}"
                elif column == 1:  # Application
                    return activity.get("app_name", "Unknown")
                elif column == 2:  # Window Title
                    return activity.get("window_title", "")
                elif column == 3:  # Duration
                    return f"Total duration: {activity.get('duration', '0s')}"
                elif column == 4:  # Active Time
                    return f"Active time: {activity.get('active_time', '0s')}"
                elif column == 5:  # Status
                    active_time = activity.get("active_time", "0s")
                    idle_time = activity.get("idle_time", "0s")
                    return f"Active time: {active_time}\nIdle time: {idle_time}"

        except Exception as e:
            logger.error(f"Error getting table data: {e}", exc_info=True)
            return None

        return None

    def _parse_time(self, time_str: str) -> datetime:
        """Parse time string to datetime for sorting."""
        try:
            return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return datetime.min

    def _parse_duration(self, duration_str: str) -> float:
        """Parse duration string to seconds for sorting."""
        try:
            if "h" in duration_str:
                parts = duration_str.split("h")
                hours = float(parts[0].strip())
                minutes = float(parts[1].strip("m").strip()) if "m" in parts[1] else 0
                return hours * 3600 + minutes * 60
            elif "m" in duration_str:
                minutes = float(duration_str.strip("m").strip())
                return minutes * 60
            elif "s" in duration_str:
                seconds = float(duration_str.strip("s").strip())
                return seconds
            return 0
        except (ValueError, TypeError):
            return 0

    def sort(self, column, order=Qt.SortOrder.AscendingOrder):
        """Sort table by column."""
        try:
            self.layoutAboutToBeChanged.emit()

            self._sort_column = column
            self._sort_order = order

            if column == 0:  # Time
                self.activities.sort(
                    key=lambda x: self._parse_time(x.get("start_time", "")),
                    reverse=(order == Qt.SortOrder.DescendingOrder),
                )
            elif column == 1:  # Application
                self.activities.sort(
                    key=lambda x: x.get("app_name", "").lower(),
                    reverse=(order == Qt.SortOrder.DescendingOrder),
                )
            elif column == 2:  # Window Title
                self.activities.sort(
                    key=lambda x: x.get("window_title", "").lower(),
                    reverse=(order == Qt.SortOrder.DescendingOrder),
                )
            elif column == 3:  # Duration
                self.activities.sort(
                    key=lambda x: self._parse_duration(x.get("duration", "0s")),
                    reverse=(order == Qt.SortOrder.DescendingOrder),
                )
            elif column == 4:  # Active Time
                self.activities.sort(
                    key=lambda x: self._parse_duration(x.get("active_time", "0s")),
                    reverse=(order == Qt.SortOrder.DescendingOrder),
                )
            elif column == 5:  # Status
                self.activities.sort(
                    key=lambda x: (
                        "Active"
                        if x.get("active_time", "0s") > x.get("idle_time", "0s")
                        else "Idle"
                    ),
                    reverse=(order == Qt.SortOrder.DescendingOrder),
                )

            self.layoutChanged.emit()

        except Exception as e:
            logger.error(f"Error sorting activities: {e}", exc_info=True)

    def update_activities(self, activities: List[Dict[str, Any]]):
        """Update model with new activities."""
        try:
            if not activities:
                self.beginResetModel()
                self.activities = []
                self.endResetModel()
                return

            # Only update changed rows
            old_count = len(self.activities)
            new_count = len(activities)

            if new_count < old_count:
                self.beginRemoveRows(QModelIndex(), new_count, old_count - 1)
                self.activities = activities
                self.endRemoveRows()
            elif new_count > old_count:
                self.beginInsertRows(QModelIndex(), old_count, new_count - 1)
                self.activities = activities
                self.endInsertRows()
            else:
                self.activities = activities
                self.dataChanged.emit(
                    self.index(0, 0), self.index(new_count - 1, self.columnCount() - 1)
                )

            # Re-sort if needed
            if self._sort_column >= 0:
                self.sort(self._sort_column, self._sort_order)

        except Exception as e:
            logger.error(f"Error updating activities: {e}", exc_info=True)
            # Fall back to full reset if update fails
            self.beginResetModel()
            self.activities = activities
            self.endResetModel()
