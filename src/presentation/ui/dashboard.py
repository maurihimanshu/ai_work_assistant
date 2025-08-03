"""Analytics dashboard for visualizing productivity data."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
from PyQt6.QtCore import QTimer, Qt, pyqtSlot
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import (QComboBox, QFrame, QGridLayout, QGroupBox, QLabel,
                            QMainWindow, QPushButton, QSizePolicy, QVBoxLayout,
                            QWidget)

from ...core.services.analytics_service import AnalyticsService
from ...core.services.session_service import SessionService
from ...core.services.task_suggestion_service import TaskSuggestionService
from .charts import (ActivityBarChart, ActivityPieChart, ProductivityLineChart,
                    TimeHeatmap)

logger = logging.getLogger(__name__)


class Dashboard(QMainWindow):
    """Analytics dashboard window."""

    def __init__(
        self,
        analytics_service: AnalyticsService,
        suggestion_service: TaskSuggestionService,
        session_service: SessionService,
        parent=None
    ):
        """Initialize dashboard.

        Args:
            analytics_service: Service for analytics
            suggestion_service: Service for task suggestions
            session_service: Service for managing sessions
            parent: Parent widget
        """
        super().__init__(parent)

        # Services
        self.analytics_service = analytics_service
        self.suggestion_service = suggestion_service
        self.session_service = session_service

        # Data
        self.current_report: Optional[Dict] = None
        self.current_suggestions: List[str] = []
        self.current_productivity: float = 0.0

        # Set up UI
        self._setup_ui()

        # Set up update timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_data)
        self.update_timer.start(60000)  # Update every minute

        # Initial data load
        self.update_data()

        # Set window properties
        self.setWindowTitle("Analytics Dashboard")
        self.resize(1200, 800)

    def _setup_ui(self) -> None:
        """Set up the dashboard UI."""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create main layout
        layout = QGridLayout()
        central_widget.setLayout(layout)

        # Create widgets
        self._create_overview_widget(layout)
        self._create_productivity_widget(layout)
        self._create_activity_widget(layout)
        self._create_suggestions_widget(layout)

    def _create_overview_widget(self, layout: QGridLayout) -> None:
        """Create overview widget.

        Args:
            layout: Parent layout
        """
        overview_group = QGroupBox("Overview")
        overview_layout = QGridLayout()

        # Time period selector
        period_label = QLabel("Time Period:")
        self.period_combo = QComboBox()
        self.period_combo.addItems([
            "Today",
            "Last 7 Days",
            "Last 30 Days"
        ])
        self.period_combo.currentIndexChanged.connect(self.update_data)

        overview_layout.addWidget(period_label, 0, 0)
        overview_layout.addWidget(self.period_combo, 0, 1)

        # Stats
        self.total_time_label = QLabel("Total Time: 0h 0m")
        self.active_time_label = QLabel("Active Time: 0h 0m")
        self.productivity_label = QLabel("Productivity: 0%")

        overview_layout.addWidget(self.total_time_label, 1, 0)
        overview_layout.addWidget(self.active_time_label, 1, 1)
        overview_layout.addWidget(self.productivity_label, 1, 2)

        overview_group.setLayout(overview_layout)
        layout.addWidget(overview_group, 0, 0, 1, 2)

    def _create_productivity_widget(self, layout: QGridLayout) -> None:
        """Create productivity widget.

        Args:
            layout: Parent layout
        """
        productivity_group = QGroupBox("Productivity Trends")
        productivity_layout = QVBoxLayout()

        # Productivity chart
        self.productivity_chart = ProductivityLineChart()
        productivity_layout.addWidget(self.productivity_chart)

        # Time heatmap
        self.time_heatmap = TimeHeatmap()
        productivity_layout.addWidget(self.time_heatmap)

        productivity_group.setLayout(productivity_layout)
        layout.addWidget(productivity_group, 1, 0)

    def _create_activity_widget(self, layout: QGridLayout) -> None:
        """Create activity widget.

        Args:
            layout: Parent layout
        """
        activity_group = QGroupBox("Activity Analysis")
        activity_layout = QGridLayout()

        # App usage pie chart
        self.app_chart = ActivityPieChart()
        activity_layout.addWidget(self.app_chart, 0, 0)

        # Category bar chart
        self.category_chart = ActivityBarChart()
        activity_layout.addWidget(self.category_chart, 0, 1)

        activity_group.setLayout(activity_layout)
        layout.addWidget(activity_group, 1, 1)

    def _create_suggestions_widget(self, layout: QGridLayout) -> None:
        """Create suggestions widget.

        Args:
            layout: Parent layout
        """
        suggestions_group = QGroupBox("Suggestions")
        suggestions_layout = QVBoxLayout()

        # Suggestions list
        self.suggestions_list = QFrame()
        self.suggestions_list.setFrameStyle(
            QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken
        )
        self.suggestions_layout = QVBoxLayout()
        self.suggestions_list.setLayout(self.suggestions_layout)

        suggestions_layout.addWidget(self.suggestions_list)

        suggestions_group.setLayout(suggestions_layout)
        layout.addWidget(suggestions_group, 2, 0, 1, 2)

    def _format_time(self, seconds: float) -> str:
        """Format time in seconds to hours and minutes.

        Args:
            seconds: Time in seconds

        Returns:
            str: Formatted time string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

    def _get_time_range(self) -> Tuple[datetime, datetime]:
        """Get selected time range.

        Returns:
            tuple: Start and end time
        """
        end_time = datetime.now()

        if self.period_combo.currentText() == "Today":
            start_time = end_time.replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0
            )
        elif self.period_combo.currentText() == "Last 7 Days":
            start_time = end_time - timedelta(days=7)
        else:  # Last 30 Days
            start_time = end_time - timedelta(days=30)

        return start_time, end_time

    @pyqtSlot()
    def update_data(self) -> None:
        """Update dashboard data."""
        try:
            # Get time range
            time_window = None
            if self.period_combo.currentText() == "Today":
                time_window = timedelta(days=1)
            elif self.period_combo.currentText() == "Last 7 Days":
                time_window = timedelta(days=7)
            else:  # Last 30 Days
                time_window = timedelta(days=30)

            # Get analytics report
            self.current_report = self.analytics_service.get_productivity_report(
                time_window
            )

            if not self.current_report:
                return

            # Update overview
            daily_metrics = self.current_report.get('daily_metrics', {})
            if daily_metrics:
                total_time = sum(
                    m['total_hours'] * 3600
                    for m in daily_metrics.values()
                )
                active_time = sum(
                    m['total_hours'] * 3600 * m['active_ratio']
                    for m in daily_metrics.values()
                )

                self.total_time_label.setText(
                    f"Total Time: {self._format_time(total_time)}"
                )
                self.active_time_label.setText(
                    f"Active Time: {self._format_time(active_time)}"
                )

            productivity = self.current_report.get('productivity_trends', {}).get(
                'average',
                0.0
            )
            self.productivity_label.setText(
                f"Productivity: {productivity * 100:.1f}%"
            )

            # Update charts
            self._update_productivity_chart()
            self._update_time_heatmap()
            self._update_activity_charts()

            # Update suggestions
            self._update_suggestions()

        except Exception as e:
            logger.error(f"Error updating dashboard: {e}")

    def _update_productivity_chart(self) -> None:
        """Update productivity chart."""
        try:
            trends = self.current_report.get('productivity_trends', {})
            if trends and 'scores' in trends:
                self.productivity_chart.update_data(trends['scores'])

        except Exception as e:
            logger.error(f"Error updating productivity chart: {e}")

    def _update_time_heatmap(self) -> None:
        """Update time heatmap."""
        try:
            time_patterns = self.current_report.get('time_patterns', {})
            if time_patterns:
                data = np.zeros((7, 24))  # days x hours

                for hour, stats in time_patterns.items():
                    hour = int(hour)
                    total_time = stats['total_time']

                    # Distribute time across days based on activity count
                    activity_count = stats['activity_count']
                    if activity_count > 0:
                        avg_time = total_time / activity_count
                        for day in range(7):
                            data[day, hour] = avg_time

                self.time_heatmap.update_data(data)

        except Exception as e:
            logger.error(f"Error updating time heatmap: {e}")

    def _update_activity_charts(self) -> None:
        """Update activity charts."""
        try:
            app_patterns = self.current_report.get('app_patterns', {})
            if app_patterns:
                # App usage chart
                app_data = {
                    app: stats['total_hours']
                    for app, stats in app_patterns.items()
                }
                self.app_chart.update_data(app_data)

                # Category chart
                categories = self.current_report.get('categories', {}).get(
                    'category_distribution',
                    {}
                )
                if categories:
                    category_data = {
                        cat: data['productivity_score']
                        for cat, data in categories.items()
                    }
                    self.category_chart.update_data(category_data)

        except Exception as e:
            logger.error(f"Error updating activity charts: {e}")

    def _update_suggestions(self) -> None:
        """Update suggestions list."""
        try:
            # Clear current suggestions
            for i in reversed(range(self.suggestions_layout.count())):
                self.suggestions_layout.itemAt(i).widget().setParent(None)

            # Get current suggestions
            suggestions, productivity = (
                self.suggestion_service.get_current_suggestions()
            )

            # Add new suggestions
            for suggestion in suggestions:
                label = QLabel(f"• {suggestion}")
                label.setWordWrap(True)
                self.suggestions_layout.addWidget(label)

            # Add stretch to bottom
            self.suggestions_layout.addStretch()

        except Exception as e:
            logger.error(f"Error updating suggestions: {e}")

    def closeEvent(self, event) -> None:
        """Handle window close event."""
        # Stop update timer
        self.update_timer.stop()
        event.accept()