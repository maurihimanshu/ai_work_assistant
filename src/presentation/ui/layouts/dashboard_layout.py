"""Main dashboard layout with metrics and heatmap sections."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QScrollArea,
    QFrame,
    QSizePolicy,
    QLabel,
    QGridLayout,
)
from PySide6.QtCore import Qt
import logging

from ..components.common.metric_card import MetricCard
from ..components.charts.heatmap import TimeHeatmap

logger = logging.getLogger(__name__)


class DashboardLayout(QWidget):
    """Main dashboard layout."""

    def __init__(self, parent=None):
        """Initialize dashboard layout."""
        try:
            super().__init__(parent)
            self.setup_ui()
            logger.debug("Dashboard layout initialized")
        except Exception as e:
            logger.error(f"Error initializing dashboard layout: {e}", exc_info=True)
            raise

    def setup_ui(self):
        """Set up the dashboard UI."""
        try:
            # Create main layout
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)

            # Create scroll area for entire content
            scroll_area = QScrollArea(self)
            scroll_area.setWidgetResizable(True)
            scroll_area.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            scroll_area.setFrameShape(QFrame.Shape.NoFrame)
            main_layout.addWidget(scroll_area)

            # Create content widget
            content = QWidget(scroll_area)
            content_layout = QVBoxLayout(content)
            content_layout.setContentsMargins(20, 20, 20, 20)
            content_layout.setSpacing(20)
            scroll_area.setWidget(content)

            # Create metrics section
            metrics_section = QFrame(content)
            metrics_section.setObjectName("metrics_section")
            metrics_section.setStyleSheet(
                """
                QFrame#metrics_section {
                    background-color: white;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                }
            """
            )
            metrics_layout = QVBoxLayout(metrics_section)
            metrics_layout.setContentsMargins(0, 0, 0, 0)
            metrics_layout.setSpacing(0)

            # Add section title
            metrics_title = QLabel("Overview", metrics_section)
            metrics_title.setStyleSheet(
                """
                QLabel {
                    color: #333333;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 16px 20px;
                    background-color: #f8f9fa;
                    border-bottom: 1px solid #e0e0e0;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                }
            """
            )
            metrics_layout.addWidget(metrics_title)

            # Create metrics grid container
            metrics_container = QWidget(metrics_section)
            metrics_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

            # Create grid layout for metric cards
            self.metrics_grid = QGridLayout(metrics_container)
            self.metrics_grid.setContentsMargins(20, 20, 20, 20)
            self.metrics_grid.setSpacing(20)

            # Set equal column stretching (4 columns)
            for i in range(4):
                self.metrics_grid.setColumnStretch(i, 1)
                self.metrics_grid.setColumnMinimumWidth(
                    i, 200
                )  # Minimum width for cards

            metrics_layout.addWidget(metrics_container)
            content_layout.addWidget(metrics_section)

            # Create heatmap section
            heatmap_section = QFrame(content)
            heatmap_section.setObjectName("heatmap_section")
            heatmap_section.setStyleSheet(
                """
                QFrame#heatmap_section {
                    background-color: white;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                }
            """
            )
            heatmap_layout = QVBoxLayout(heatmap_section)
            heatmap_layout.setContentsMargins(0, 0, 0, 0)
            heatmap_layout.setSpacing(0)

            # Add section title
            heatmap_title = QLabel("Activity Distribution", heatmap_section)
            heatmap_title.setStyleSheet(
                """
                QLabel {
                    color: #333333;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 16px 20px;
                    background-color: #f8f9fa;
                    border-bottom: 1px solid #e0e0e0;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                }
            """
            )
            heatmap_layout.addWidget(heatmap_title)

            # Add heatmap
            self.heatmap = TimeHeatmap(heatmap_section)
            heatmap_layout.addWidget(self.heatmap)
            content_layout.addWidget(heatmap_section)

            # Set size policies
            metrics_section.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            heatmap_section.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

            # Set minimum heights
            metrics_section.setMinimumHeight(200)
            heatmap_section.setMinimumHeight(400)

            # Set minimum width for the entire dashboard
            self.setMinimumWidth(900)  # Accommodates 4 cards (200px each) plus margins

            logger.debug("Dashboard layout UI setup complete")

        except Exception as e:
            logger.error(f"Error setting up dashboard layout UI: {e}", exc_info=True)
            raise

    def add_metric_card(
        self, title: str, value: str, icon: str, description: str, row: int, col: int
    ):
        """Add a metric card to the grid."""
        try:
            if col >= 4:  # Ensure we don't exceed 4 columns
                logger.warning(
                    f"Column index {col} exceeds maximum (3), card will not be added"
                )
                return

            card = MetricCard(
                title=title,
                value=value,
                icon=icon,
                description=description,
                parent=self.metrics_grid.parentWidget(),
            )
            self.metrics_grid.addWidget(card, row, col)
            logger.debug(f"Added metric card: {title} at position ({row}, {col})")
        except Exception as e:
            logger.error(f"Error adding metric card: {e}", exc_info=True)
            raise

    def update_data(self, data):
        """Update dashboard with new data."""
        try:
            # Update heatmap
            if "hourly_distribution" in data:
                self.heatmap.update_data(data)

            logger.debug("Dashboard data updated")

        except Exception as e:
            logger.error(f"Error updating dashboard data: {e}", exc_info=True)
            raise
