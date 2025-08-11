"""Overview layout module."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QScrollArea,
    QFrame,
    QSizePolicy,
    QLabel,
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
import logging
from typing import Dict, Any

from ..components.common.metric_card import MetricCard
from ..components.charts.heatmap import TimeHeatmap
from ..utils.data_mappers import DataMapper

logger = logging.getLogger(__name__)


class OverviewLayout(QWidget):
    """Layout for the overview tab."""

    def __init__(self, parent=None):
        """Initialize overview layout."""
        try:
            super().__init__(parent)
            self.setup_ui()
            logger.debug("Overview layout initialized")
        except Exception as e:
            logger.error(f"Error initializing overview layout: {e}", exc_info=True)
            raise

    def setup_ui(self):
        """Set up the overview layout UI."""
        try:
            # Create main layout
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)

            # Create scroll area
            scroll_area = QScrollArea(self)
            scroll_area.setWidgetResizable(True)
            scroll_area.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            scroll_area.setFrameShape(QFrame.Shape.NoFrame)
            main_layout.addWidget(scroll_area)

            # Create content widget
            content = QWidget(scroll_area)
            content_layout = QVBoxLayout(content)
            content_layout.setContentsMargins(
                20, 20, 20, 20
            )  # Add padding around content
            content_layout.setSpacing(20)  # Add spacing between sections
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
            metrics_layout.setContentsMargins(20, 20, 20, 20)
            metrics_layout.setSpacing(20)

            # Create metrics grid
            metrics_grid = QGridLayout()
            metrics_grid.setSpacing(20)
            metrics_layout.addLayout(metrics_grid)

            # Add metric cards in a 4x2 grid
            self.total_time_card = MetricCard(
                "Total Time", "0h 0m", "⏱️", "Total time tracked", show_progress=False
            )
            metrics_grid.addWidget(self.total_time_card, 0, 0)

            self.active_time_card = MetricCard(
                "Active Time",
                "0h 0m",
                "⚡",
                "Time spent actively using applications",
                show_progress=True,
            )
            metrics_grid.addWidget(self.active_time_card, 0, 1)

            self.idle_time_card = MetricCard(
                "Idle Time", "0h 0m", "💤", "Time spent idle", show_progress=False
            )
            metrics_grid.addWidget(self.idle_time_card, 0, 2)

            self.focus_time_card = MetricCard(
                "Focus Time",
                "0h 0m",
                "🎯",
                "Time spent focused on productive tasks",
                show_progress=True,
            )
            metrics_grid.addWidget(self.focus_time_card, 0, 3)

            self.break_time_card = MetricCard(
                "Break Time", "0h 0m", "☕", "Time spent on breaks", show_progress=False
            )
            metrics_grid.addWidget(self.break_time_card, 1, 0)

            self.productivity_card = MetricCard(
                "Productivity",
                "0%",
                "📈",
                "Overall productivity score",
                show_progress=True,
            )
            metrics_grid.addWidget(self.productivity_card, 1, 1)

            self.efficiency_card = MetricCard(
                "Efficiency", "0%", "⚙️", "Work efficiency score", show_progress=True
            )
            metrics_grid.addWidget(self.efficiency_card, 1, 2)

            self.session_card = MetricCard(
                "Session", "0h 0m", "🔄", "Current session duration", show_progress=False
            )
            metrics_grid.addWidget(self.session_card, 1, 3)

            # Set column stretching for grid
            for i in range(4):
                metrics_grid.setColumnStretch(i, 1)
                metrics_grid.setColumnMinimumWidth(i, 200)

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

            # Add time heatmap
            self.time_heatmap = TimeHeatmap(heatmap_section)
            heatmap_layout.addWidget(self.time_heatmap)
            content_layout.addWidget(heatmap_section)

            # Suggestions section
            self.suggestions_section = QFrame(content)
            self.suggestions_section.setObjectName("card")
            suggestions_layout = QVBoxLayout(self.suggestions_section)
            suggestions_layout.setContentsMargins(16, 16, 16, 16)
            suggestions_layout.setSpacing(8)
            self.suggestions_title = QLabel("Suggestions")
            self.suggestions_list = QLabel("")
            self.suggestions_list.setWordWrap(True)
            self.suggestions_list.setStyleSheet("color: #374151")
            suggestions_layout.addWidget(self.suggestions_title)
            suggestions_layout.addWidget(self.suggestions_list)
            content_layout.addWidget(self.suggestions_section)

            # Set size policies
            metrics_section.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            heatmap_section.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            self.suggestions_section.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Minimum
            )

            # Set minimum heights
            metrics_section.setMinimumHeight(200)
            heatmap_section.setMinimumHeight(400)
            self.suggestions_section.setMinimumHeight(120)

            # Set minimum width for proper card display
            self.setMinimumWidth(900)

            # Add fade animation
            self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
            self.fade_animation.setDuration(150)
            self.fade_animation.setStartValue(0)
            self.fade_animation.setEndValue(1)
            self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

            logger.debug("Overview layout UI setup complete")

        except Exception as e:
            logger.error(f"Error setting up overview layout UI: {e}", exc_info=True)
            raise

    def showEvent(self, event):
        """Handle show event."""
        try:
            super().showEvent(event)
            self.fade_animation.start()
        except Exception as e:
            logger.error(f"Error in overview layout show event: {e}", exc_info=True)

    def update_data(self, data: Dict[str, Any]):
        """Update the overview layout with mapped data."""
        try:
            if not data:
                logger.warning("No data provided to overview layout")
                return

            # Get activity stats
            total_time = float(data.get("total_time", 0))
            active_time = float(data.get("active_time", 0))
            idle_time = float(data.get("idle_time", 0))
            focus_time = float(data.get("focus_time", 0))
            break_time = float(data.get("break_time", 0))
            avg_session_time = float(data.get("avg_session_time", 0))
            productivity_score = float(data.get("productivity_score", 0))
            efficiency_score = float(data.get("efficiency_score", 0))

            # Update time metrics
            self.total_time_card.set_value(DataMapper.format_time(total_time))

            self.active_time_card.set_value(
                DataMapper.format_time(active_time),
                progress=(active_time / total_time * 100 if total_time > 0 else 0),
            )

            self.idle_time_card.set_value(DataMapper.format_time(idle_time))

            self.focus_time_card.set_value(
                DataMapper.format_time(focus_time),
                progress=(focus_time / active_time * 100 if active_time > 0 else 0),
            )

            self.break_time_card.set_value(DataMapper.format_time(break_time))

            # Update score metrics
            self.productivity_card.set_value(
                DataMapper.format_percentage(productivity_score),
                progress=productivity_score * 100,
            )

            self.efficiency_card.set_value(
                DataMapper.format_percentage(efficiency_score),
                progress=efficiency_score * 100,
            )

            # Update session length
            self.session_card.set_value(DataMapper.format_time(avg_session_time))

            # Update heatmap with hourly data
            hourly_data = data.get("hourly_distribution", {})
            if hourly_data:
                heatmap_data = {"hourly_distribution": hourly_data}
                # Only add activities if they exist
                if "activities" in data:
                    heatmap_data["activities"] = data["activities"]

                self.time_heatmap.update_data(heatmap_data)
                logger.debug("Heatmap data updated successfully")
            else:
                logger.warning("No hourly distribution data available for heatmap")

            logger.debug("Overview layout data updated successfully")

            # Update suggestions if present
            raw = data.get("suggestions") or []
            # Deduplicate and clean simple .exe suffixes
            seen = set()
            cleaned = []
            for s in raw:
                text = str(s)
                text = text.replace(".exe", "")
                if text not in seen:
                    seen.add(text)
                    cleaned.append(text)
            if cleaned:
                self.suggestions_list.setText("\n• ".join([""] + cleaned))
            else:
                self.suggestions_list.setText("No suggestions at the moment.")

        except Exception as e:
            logger.error(f"Error updating overview layout: {e}", exc_info=True)
