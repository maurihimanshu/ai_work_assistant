"""Activity log layout module."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QComboBox,
    QTableView,
    QHeaderView,
)
from PySide6.QtCore import Qt, QSortFilterProxyModel, QPropertyAnimation, QEasingCurve
import logging
from typing import Dict, List, Any

from ..components.tables.activity_table import ActivityTableModel
from ..utils.data_mappers import DataMapper

logger = logging.getLogger(__name__)


class FilterBar(QFrame):
    """Filter bar for activity log."""

    def __init__(self, parent=None):
        """Initialize filter bar."""
        try:
            super().__init__(parent)
            self.setup_ui()
            logger.debug("Filter bar initialized")
        except Exception as e:
            logger.error(f"Error initializing filter bar: {e}", exc_info=True)

    def setup_ui(self):
        """Set up the filter bar UI."""
        try:
            # Create layout
            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(10)
            self.setLayout(layout)

            # Add search box
            self.search_box = QLineEdit()
            self.search_box.setPlaceholderText("Search activities...")
            self.search_box.setMinimumWidth(200)
            layout.addWidget(self.search_box)

            # Add app filter
            self.app_filter = QComboBox()
            self.app_filter.addItem("All Apps")
            self.app_filter.setMinimumWidth(150)
            layout.addWidget(self.app_filter)

            # Add status filter
            self.status_filter = QComboBox()
            self.status_filter.addItems(["All Status", "Active", "Idle"])
            self.status_filter.setMinimumWidth(100)
            layout.addWidget(self.status_filter)

            # Add stretch to push filters to left
            layout.addStretch()

            # Style
            self.setStyleSheet(
                """
                QFrame {
                    background-color: #f5f5f5;
                    border: 1px solid #e0e0e0;
                    border-radius: 4px;
                    padding: 10px;
                }
                QLineEdit {
                    padding: 5px;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                }
                QComboBox {
                    padding: 5px;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                }
            """
            )

            logger.debug("Filter bar UI setup complete")

        except Exception as e:
            logger.error(f"Error setting up filter bar UI: {e}", exc_info=True)
            raise


class CustomFilterProxyModel(QSortFilterProxyModel):
    """Custom filter proxy model for activity table."""

    def __init__(self, parent=None):
        """Initialize filter proxy model."""
        super().__init__(parent)
        self.app_filter = "All Apps"
        self.status_filter = "All Status"
        self.search_text = ""

    def filterAcceptsRow(self, source_row, source_parent):
        """Check if row matches current filters."""
        try:
            source_model = self.sourceModel()
            if not source_model:
                return False

            # Get row data
            app_name = str(
                source_model.data(
                    source_model.index(source_row, 1, source_parent),
                    Qt.ItemDataRole.DisplayRole,
                )
            )
            window_title = str(
                source_model.data(
                    source_model.index(source_row, 2, source_parent),
                    Qt.ItemDataRole.DisplayRole,
                )
            )
            status = str(
                source_model.data(
                    source_model.index(source_row, 5, source_parent),
                    Qt.ItemDataRole.DisplayRole,
                )
            )

            # Check app filter
            if self.app_filter != "All Apps" and app_name != self.app_filter:
                return False

            # Check status filter
            if self.status_filter != "All Status" and status != self.status_filter:
                return False

            # Check search text
            if self.search_text:
                search_lower = self.search_text.lower()
                if (
                    search_lower not in app_name.lower()
                    and search_lower not in window_title.lower()
                ):
                    return False

            return True

        except Exception as e:
            logger.error(f"Error filtering row: {e}", exc_info=True)
            return False


class ActivityLogLayout(QWidget):
    """Layout for the activity log tab."""

    def __init__(self, parent=None):
        """Initialize activity log layout."""
        try:
            super().__init__(parent)
            self.setup_ui()
            logger.debug("Activity log layout initialized")
        except Exception as e:
            logger.error(f"Error initializing activity log layout: {e}", exc_info=True)

    def setup_ui(self):
        """Set up the activity log layout UI."""
        try:
            # Create main layout
            layout = QVBoxLayout()
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(20)
            self.setLayout(layout)

            # Add filter bar
            self.filter_bar = FilterBar()
            layout.addWidget(self.filter_bar)

            # Create table view
            self.activity_model = ActivityTableModel()
            self.proxy_model = CustomFilterProxyModel()
            self.proxy_model.setSourceModel(self.activity_model)

            self.table_view = QTableView()
            self.table_view.setModel(self.proxy_model)
            self.table_view.setSortingEnabled(True)
            self.table_view.setAlternatingRowColors(True)
            self.table_view.setSelectionBehavior(
                QTableView.SelectionBehavior.SelectRows
            )
            self.table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)

            # Style the table
            self.table_view.setStyleSheet(
                """
                QTableView {
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    background-color: white;
                    alternate-background-color: #f5f5f5;
                    gridline-color: #e0e0e0;
                }
                QTableView::item {
                    padding: 5px;
                }
                QHeaderView::section {
                    background-color: #f0f0f0;
                    padding: 5px;
                    border: none;
                    border-bottom: 2px solid #cccccc;
                    font-weight: bold;
                    color: #666666;
                }
                QTableView::item:selected {
                    background-color: #2196F3;
                    color: white;
                }
            """
            )

            # Set up header
            header = self.table_view.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(
                2, QHeaderView.ResizeMode.Stretch
            )  # Window Title column

            # Add table to layout
            layout.addWidget(self.table_view)

            # Connect filter signals
            self.filter_bar.search_box.textChanged.connect(self._update_filters)
            self.filter_bar.app_filter.currentTextChanged.connect(self._update_filters)
            self.filter_bar.status_filter.currentTextChanged.connect(
                self._update_filters
            )

            # Add fade animation
            self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
            self.fade_animation.setDuration(150)
            self.fade_animation.setStartValue(0)
            self.fade_animation.setEndValue(1)
            self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

            logger.debug("Activity log layout UI setup complete")

        except Exception as e:
            logger.error(f"Error setting up activity log layout UI: {e}", exc_info=True)
            raise

    def showEvent(self, event):
        """Handle show event."""
        try:
            super().showEvent(event)
            self.fade_animation.start()
        except Exception as e:
            logger.error(f"Error in activity log layout show event: {e}", exc_info=True)

    def update_data(self, activities: List[Dict[str, Any]]):
        """Update the activity log with mapped data."""
        try:
            if not activities:
                return

            # Map activities to UI format
            mapped_activities = DataMapper.map_activity_list(activities)

            # Update activity model
            self.activity_model.update_activities(mapped_activities)

            # Update app filter options
            current_apps = sorted(
                {
                    activity.get("app_name", "Unknown")
                    for activity in mapped_activities
                    if activity.get("app_name")
                }
            )

            current_filter = self.filter_bar.app_filter.currentText()
            self.filter_bar.app_filter.clear()
            self.filter_bar.app_filter.addItem("All Apps")
            self.filter_bar.app_filter.addItems(current_apps)

            # Restore previous filter if it still exists
            index = self.filter_bar.app_filter.findText(current_filter)
            if index >= 0:
                self.filter_bar.app_filter.setCurrentIndex(index)

            logger.debug(
                f"Activity log updated with {len(mapped_activities)} activities"
            )

        except Exception as e:
            logger.error(f"Error updating activity log: {e}", exc_info=True)

    def _update_filters(self):
        """Update proxy model filters."""
        try:
            self.proxy_model.app_filter = self.filter_bar.app_filter.currentText()
            self.proxy_model.status_filter = self.filter_bar.status_filter.currentText()
            self.proxy_model.search_text = self.filter_bar.search_box.text()
            self.proxy_model.invalidateFilter()
        except Exception as e:
            logger.error(f"Error updating filters: {e}", exc_info=True)
