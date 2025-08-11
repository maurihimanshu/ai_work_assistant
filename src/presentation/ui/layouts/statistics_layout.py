"""Statistics layout module."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QFrame,
    QScrollArea,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QColor, QLinearGradient
import logging
from typing import Dict, Any

from ..components.common.metric_card import MetricCard
from ..components.tables.statistics_table import StatisticsTable
from ..components.charts.pie_chart import ActivityPieChart
from ..components.charts.bar_chart import ActivityBarChart
from ..utils.data_mappers import DataMapper

logger = logging.getLogger(__name__)


class StatisticsCard(QFrame):
    """Card widget for statistics section."""

    def __init__(self, title: str, parent=None):
        """Initialize statistics card."""
        try:
            super().__init__(parent)
            self.title = title
            self.setup_ui()
            logger.debug(f"Statistics card initialized: {title}")
        except Exception as e:
            logger.error(f"Error initializing statistics card: {e}", exc_info=True)
            raise

    def setup_ui(self):
        """Set up the card UI."""
        try:
            # Set frame style
            self.setStyleSheet(
                """
                QFrame {
                    background-color: white;
                    border: 1px solid #E0E0E0;
                    border-radius: 4px;
                }
                QLabel {
                    color: #424242;
                }
                QLabel#title {
                    font-size: 16px;
                    font-weight: bold;
                    color: #2196F3;
                }
            """
            )

            # Define a consistent minimum width for all cards
            self.setMinimumWidth(360)
            self.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )

            # Create layout
            layout = QVBoxLayout()
            layout.setContentsMargins(15, 15, 15, 15)
            layout.setSpacing(10)
            self.setLayout(layout)

            # Add title with fixed height for consistency
            title_label = QLabel(self.title)
            title_label.setObjectName("title")
            title_label.setFixedHeight(40)
            layout.addWidget(title_label)

            # Add content widget
            self.content = QWidget()
            self.content_layout = QVBoxLayout()
            self.content_layout.setContentsMargins(0, 0, 0, 0)
            self.content_layout.setSpacing(10)
            self.content.setLayout(self.content_layout)
            layout.addWidget(self.content)

            logger.debug(f"Statistics card UI setup complete: {self.title}")

        except Exception as e:
            logger.error(f"Error setting up statistics card UI: {e}", exc_info=True)
            raise


class StatisticsLayout(QWidget):
    """Layout for the statistics tab."""

    def __init__(self, parent=None):
        """Initialize statistics layout."""
        try:
            super().__init__(parent)
            self.setup_ui()
            logger.debug("Statistics layout initialized")
        except Exception as e:
            logger.error(f"Error initializing statistics layout: {e}", exc_info=True)

    def setup_ui(self):
        """Set up the statistics layout UI."""
        try:
            # Create main layout
            layout = QVBoxLayout()
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(20)
            self.setLayout(layout)

            # Create scroll area
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            layout.addWidget(scroll)

            # Create scroll content
            content = QWidget()
            content_layout = QVBoxLayout()
            content_layout.setContentsMargins(0, 0, 0, 0)
            content_layout.setSpacing(20)
            content.setLayout(content_layout)
            scroll.setWidget(content)

            # Add summary section
            summary_layout = QHBoxLayout()
            summary_layout.setSpacing(20)
            content_layout.addLayout(summary_layout)

            # Add metric cards
            self.app_count_card = MetricCard(
                "Active Applications",
                "0",
                "💻",
                "Number of unique applications used",
                show_progress=False,
            )
            summary_layout.addWidget(self.app_count_card)

            self.category_count_card = MetricCard(
                "Categories",
                "0",
                "📁",
                "Number of activity categories",
                show_progress=False,
            )
            summary_layout.addWidget(self.category_count_card)

            self.productivity_card = MetricCard(
                "Average Productivity",
                "0.0%",
                "📈",
                "Overall productivity score",
                show_progress=True,
            )
            summary_layout.addWidget(self.productivity_card)

            # Add charts section
            charts_layout = QHBoxLayout()
            charts_layout.setSpacing(20)
            content_layout.addLayout(charts_layout)

            # Add pie chart
            pie_card = StatisticsCard("Application Distribution")
            pie_layout = QVBoxLayout()
            pie_layout.setContentsMargins(0, 0, 0, 0)
            self.app_pie_chart = ActivityPieChart()
            pie_layout.addWidget(self.app_pie_chart)
            pie_card.content_layout.addLayout(pie_layout)
            pie_card.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            pie_card.setMinimumWidth(380)
            charts_layout.addWidget(pie_card)

            # Add bar chart
            bar_card = StatisticsCard("Category Distribution")
            bar_layout = QVBoxLayout()
            bar_layout.setContentsMargins(0, 0, 0, 0)
            self.cat_bar_chart = ActivityBarChart()
            bar_layout.addWidget(self.cat_bar_chart)
            bar_card.content_layout.addLayout(bar_layout)
            bar_card.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            bar_card.setMinimumWidth(380)
            charts_layout.addWidget(bar_card)
            charts_layout.setStretch(0, 1)
            charts_layout.setStretch(1, 1)

            # Add tables section
            tables_layout = QHBoxLayout()
            tables_layout.setSpacing(20)
            content_layout.addLayout(tables_layout)

            # Add application table
            app_table_card = StatisticsCard("Top Applications")
            app_table_layout = QVBoxLayout()
            app_table_layout.setContentsMargins(0, 0, 0, 0)
            self.app_table = StatisticsTable()
            app_table_layout.addWidget(self.app_table)
            app_table_card.content_layout.addLayout(app_table_layout)
            app_table_card.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            app_table_card.setMinimumWidth(380)
            tables_layout.addWidget(app_table_card)

            # Add category table
            cat_table_card = StatisticsCard("Top Categories")
            cat_table_layout = QVBoxLayout()
            cat_table_layout.setContentsMargins(0, 0, 0, 0)
            self.cat_table = StatisticsTable()
            cat_table_layout.addWidget(self.cat_table)
            cat_table_card.content_layout.addLayout(cat_table_layout)
            cat_table_card.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            cat_table_card.setMinimumWidth(380)
            tables_layout.addWidget(cat_table_card)
            tables_layout.setStretch(0, 1)
            tables_layout.setStretch(1, 1)

            # Add fade animation
            self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
            self.fade_animation.setDuration(150)
            self.fade_animation.setStartValue(0)
            self.fade_animation.setEndValue(1)
            self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

            logger.debug("Statistics layout UI setup complete")
        except Exception as e:
            logger.error(f"Error setting up statistics layout UI: {e}", exc_info=True)
            raise

    def update_data(self, data: Dict[str, Any]):
        """Update the statistics layout with mapped data."""
        try:
            if not data:
                logger.debug("No data provided to update statistics layout")
                return

            # Get app and category data
            app_data = data.get("app_data", [])
            category_data = data.get("category_data", [])

            # Update summary cards
            self.app_count_card.set_value(str(len(app_data)))
            self.category_count_card.set_value(str(len(category_data)))

            # Calculate average productivity from app data
            total_percentage = (
                sum(float(app[2].rstrip("%")) for app in app_data) if app_data else 0
            )
            avg_productivity = total_percentage / len(app_data) if app_data else 0

            self.productivity_card.set_value(
                DataMapper.format_percentage(avg_productivity / 100),
                progress=avg_productivity / 100,
            )

            # Update charts and tables
            self.app_pie_chart.update_data(app_data)
            self.cat_bar_chart.update_data(category_data)
            self.app_table.update_data(app_data)
            self.cat_table.update_data(category_data)

            logger.debug("Statistics layout data updated successfully")

        except Exception as e:
            logger.error(f"Error updating statistics layout: {e}", exc_info=True)

    def showEvent(self, event):
        """Handle show event with animation."""
        try:
            super().showEvent(event)
            self.fade_animation.start()
        except Exception as e:
            logger.error(f"Error in statistics layout show event: {e}", exc_info=True)

    def _format_time(self, seconds):
        """Format time in seconds to hours and minutes."""
        try:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        except Exception as e:
            logger.error(f"Error formatting time: {e}", exc_info=True)
            return "0h 0m"
