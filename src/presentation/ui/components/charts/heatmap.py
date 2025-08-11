"""Time heatmap component for visualizing activity distribution."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QPushButton,
    QLabel,
    QFrame,
    QToolTip,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QRectF, QPointF, Signal as pyqtSignal, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPalette, QMouseEvent
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple, Optional
from zoneinfo import ZoneInfo, available_timezones
import numpy as np

logger = logging.getLogger(__name__)


class ColorScale:
    """Color scale for heatmap."""

    SCALES = {
        "Blue": [
            QColor("#F5F5F5"),  # Very light gray
            QColor("#E3F2FD"),  # Very light blue
            QColor("#90CAF9"),  # Light blue
            QColor("#42A5F5"),  # Blue
            QColor("#1E88E5"),  # Dark blue
            QColor("#1565C0"),  # Very dark blue
        ],
        "Green": [
            QColor("#F5F5F5"),
            QColor("#E8F5E9"),
            QColor("#A5D6A7"),
            QColor("#66BB6A"),
            QColor("#43A047"),
            QColor("#2E7D32"),
        ],
        "Purple": [
            QColor("#F5F5F5"),
            QColor("#F3E5F5"),
            QColor("#CE93D8"),
            QColor("#AB47BC"),
            QColor("#8E24AA"),
            QColor("#6A1B9A"),
        ],
        "Orange": [
            QColor("#F5F5F5"),
            QColor("#FFF3E0"),
            QColor("#FFCC80"),
            QColor("#FFA726"),
            QColor("#F57C00"),
            QColor("#E65100"),
        ],
    }

    @staticmethod
    def get_color(scale_name: str, intensity: float) -> QColor:
        """Get color for given intensity value."""
        try:
            colors = ColorScale.SCALES.get(scale_name, ColorScale.SCALES["Blue"])

            if intensity == 0:
                return colors[0]

            # Map intensity to color index
            index = min(int(intensity * (len(colors) - 1)) + 1, len(colors) - 1)
            return colors[index]

        except Exception as e:
            logger.error(f"Error getting color: {e}", exc_info=True)
            return QColor("#F5F5F5")  # Default to light gray


class TimeHeatmap(QWidget):
    """Heatmap for displaying time distribution."""

    # Signals
    interval_changed = pyqtSignal(int)  # Interval in minutes
    cell_clicked = pyqtSignal(int, float)  # Hour and value

    def __init__(self, parent=None):
        """Initialize time heatmap."""
        try:
            super().__init__(parent)

            # Data
            self.data = {}  # Hour -> value mapping
            self.max_value = 0
            self.selected_cell = None
            self.hover_cell = None

            # Settings
            self.timezone = ZoneInfo("UTC")  # Fixed to UTC
            self.interval = 120  # 2 hours default
            self.color_scale = "Blue"
            self.show_legend = True
            self.show_tooltips = True

            # Dimensions
            self.cell_min_width = 40
            self.chart_min_height = 120
            self.legend_width = 80
            self.axis_label_height = 25

            # Setup UI
            self.setup_ui()
            self.setMouseTracking(True)

            logger.debug("Time heatmap initialized")

        except Exception as e:
            logger.error(f"Error initializing time heatmap: {e}", exc_info=True)
            raise

    def setup_ui(self):
        """Set up the heatmap UI."""
        try:
            # Create main layout
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)

            # Create header section
            header = QFrame(self)
            header.setObjectName("heatmap_header")
            header.setStyleSheet(
                """
                QFrame#heatmap_header {
                    background-color: #f8f9fa;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    margin: 20px 20px 0px 20px;  /* Top, Right, Bottom, Left */
                    padding-top: 10px;
                }
                QLabel {
                    color: #333333;
                    font-weight: 600;
                }
                QComboBox {
                    padding: 4px 8px;
                    border: 1px solid #e0e0e0;
                    border-radius: 4px;
                    background-color: white;
                    min-width: 120px;
                    color: #333333;
                }
                QComboBox:hover {
                    border: 1px solid #bdbdbd;
                }
                QPushButton {
                    padding: 4px 12px;
                    border: 1px solid #e0e0e0;
                    border-radius: 4px;
                    background-color: white;
                    color: #333333;
                }
                QPushButton:hover {
                    border: 1px solid #bdbdbd;
                    background-color: #f5f5f5;
                }
                QPushButton:checked {
                    background-color: #e3f2fd;
                    border: 1px solid #90caf9;
                    color: #1976d2;
                }
            """
            )

            header_layout = QHBoxLayout(header)
            header_layout.setContentsMargins(20, 15, 20, 15)
            header_layout.setSpacing(20)

            # Add interval selector
            interval_layout = QHBoxLayout()
            interval_layout.setSpacing(8)

            interval_label = QLabel("Interval:", header)
            interval_layout.addWidget(interval_label)

            self.interval_selector = QComboBox(header)
            self.interval_selector.addItems(
                ["30 minutes", "1 hour", "2 hours", "3 hours", "4 hours", "6 hours"]
            )
            self.interval_selector.setCurrentText("2 hours")  # Set default to 2 hours
            self.interval_selector.currentTextChanged.connect(
                self._handle_interval_change
            )
            interval_layout.addWidget(self.interval_selector)

            header_layout.addLayout(interval_layout)

            # Add color scale selector
            color_layout = QHBoxLayout()
            color_layout.setSpacing(8)

            color_label = QLabel("Colors:", header)
            color_layout.addWidget(color_label)

            self.color_selector = QComboBox(header)
            self.color_selector.addItems(list(ColorScale.SCALES.keys()))
            self.color_selector.setCurrentText(self.color_scale)
            self.color_selector.currentTextChanged.connect(self._handle_color_change)
            color_layout.addWidget(self.color_selector)

            header_layout.addLayout(color_layout)

            # Add legend toggle
            self.legend_button = QPushButton("Show Legend", header)
            self.legend_button.setCheckable(True)
            self.legend_button.setChecked(self.show_legend)
            self.legend_button.clicked.connect(self._toggle_legend)
            header_layout.addWidget(self.legend_button)

            # Add stretch to push controls to left
            header_layout.addStretch()

            main_layout.addWidget(header)

            # Create chart section
            chart_section = QFrame(self)
            chart_section.setObjectName("chart_section")
            chart_section.setStyleSheet(
                """
                QFrame#chart_section {
                    background-color: white;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    margin: 20px;
                }
            """
            )

            chart_layout = QVBoxLayout(chart_section)
            chart_layout.setContentsMargins(20, 20, 20, 20)
            chart_layout.setSpacing(0)

            # Create chart widget
            self.chart_widget = QWidget(chart_section)
            self.chart_widget.setMouseTracking(True)
            self.chart_widget.paintEvent = self._paint_chart
            self.chart_widget.mousePressEvent = self._handle_mouse_press
            self.chart_widget.mouseMoveEvent = self._handle_mouse_move
            self.chart_widget.setMinimumHeight(self.chart_min_height)
            self.chart_widget.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Expanding
            )

            chart_layout.addWidget(self.chart_widget)
            main_layout.addWidget(chart_section)

            # Set minimum width for proper display
            self.setMinimumWidth(800)

        except Exception as e:
            logger.error(f"Error setting up heatmap UI: {e}", exc_info=True)
            raise

    def setup_styles(self):
        """Set up the card styles."""
        try:
            # Base styles - more compact and efficient
            base_styles = """
                MetricCard {
                    background-color: white;
                    border-radius: 6px;
                    border: 1px solid #e0e0e0;
                }
                MetricCard:hover {
                    border: 1px solid #bdbdbd;
                }
                #icon_container {
                    background-color: #f5f5f5;
                    border-radius: 4px;
                }
                #title {
                    color: #333333;
                }
                #value_container {
                    background-color: #f8f9fa;
                    border-radius: 4px;
                    margin: 2px 0px;  /* Added vertical margin */
                }
                #value {
                    color: #1a1a1a;
                    font-size: 14px;
                    font-weight: 600;
                    padding: 0px 2px;  /* Added padding */
                }
                #progress_frame {
                    background-color: #e3f2fd;
                    border-radius: 4px;
                    margin: 2px 0px;  /* Added vertical margin */
                }
                #description {
                    color: #666666;
                    font-size: 11px;
                }
            """

            # Dark theme styles
            dark_styles = """
                MetricCard {
                    background-color: #2d2d2d;
                    border: 1px solid #404040;
                }
                MetricCard:hover {
                    border: 1px solid #505050;
                }
                #icon_container {
                    background-color: #383838;
                }
                #title {
                    color: #e0e0e0;
                }
                #value_container {
                    background-color: #383838;
                }
                #value {
                    color: #ffffff;
                }
                #progress_frame {
                    background-color: #0d47a1;
                    opacity: 0.7;
                }
                #description {
                    color: #999999;
                }
            """

            self.setStyleSheet(dark_styles if self.theme == "dark" else base_styles)

        except Exception as e:
            logger.error(f"Error setting up metric card styles: {e}", exc_info=True)
            raise

    def _validate_data(self, data: Dict[str, Any]) -> Dict[int, float]:
        """Validate and transform input data.

        Args:
            data: Dictionary containing hourly distribution

        Returns:
            Dictionary mapping hours to values
        """
        try:
            if not data:
                return {}

            # Get hourly distribution
            hourly_data = data.get("hourly_distribution", {})
            if not hourly_data:
                # Try fallback to activities
                activities = data.get("activities", [])
                if activities:
                    hourly_data = self._calculate_hourly_distribution(activities)
                else:
                    return {}

            # Convert to target timezone
            result = {}
            total_time = sum(float(v) for v in hourly_data.values())

            for hour, value in hourly_data.items():
                try:
                    # Validate hour
                    hour = int(hour)
                    if not 0 <= hour < 24:
                        continue

                    # Convert hour to target timezone
                    dt = datetime.now(timezone.utc).replace(
                        hour=hour, minute=0, second=0, microsecond=0
                    )
                    local_hour = dt.astimezone(self.timezone).hour

                    # Validate and normalize value
                    value = float(value)
                    if value < 0:
                        value = 0

                    # Convert to percentage
                    if total_time > 0:
                        value = value / total_time

                    # Aggregate by interval
                    interval_hour = (local_hour // (self.interval // 60)) * (
                        self.interval // 60
                    )
                    if interval_hour in result:
                        result[interval_hour] += value
                    else:
                        result[interval_hour] = value

                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid hour or value: {e}")
                    continue

            return result

        except Exception as e:
            logger.error(f"Error validating heatmap data: {e}", exc_info=True)
            return {}

    def _calculate_hourly_distribution(
        self, activities: List[Dict[str, Any]]
    ) -> Dict[int, float]:
        """Calculate hourly distribution from activities."""
        try:
            result = {}

            for activity in activities:
                try:
                    # Get start time
                    start_time = activity.get("start_time")
                    if isinstance(start_time, str):
                        start_time = datetime.fromisoformat(start_time)

                    if not isinstance(start_time, datetime):
                        continue

                    # Convert to target timezone
                    if start_time.tzinfo is None:
                        start_time = start_time.replace(tzinfo=timezone.utc)
                    local_time = start_time.astimezone(self.timezone)

                    # Get hour and duration
                    hour = local_time.hour
                    duration = float(activity.get("active_time", 0))

                    # Add to result
                    if hour in result:
                        result[hour] += duration
                    else:
                        result[hour] = duration

                except (ValueError, TypeError) as e:
                    logger.warning(f"Error processing activity: {e}")
                    continue

            return result

        except Exception as e:
            logger.error(f"Error calculating hourly distribution: {e}", exc_info=True)
            return {}

    def update_data(self, data: Dict[str, Any]):
        """Update heatmap with new data.

        Args:
            data: Dictionary containing hourly distribution
        """
        try:
            # Validate and transform data
            validated_data = self._validate_data(data)

            if not validated_data:
                logger.warning("No valid hourly distribution data")
                self.data = {}
                self.max_value = 0
                self.update()
                return

            # Update data
            self.data = validated_data
            self.max_value = max(validated_data.values())

            # Update display
            self.update()
            logger.debug(f"Heatmap updated with {len(validated_data)} intervals")

        except Exception as e:
            logger.error(f"Error updating heatmap data: {e}", exc_info=True)
            self.data = {}
            self.max_value = 0
            self.update()

    def _handle_timezone_change(self, timezone_str: str):
        """Handle timezone selection change."""
        # Removed as timezone is now fixed to UTC
        pass

    def _handle_interval_change(self, interval_str: str):
        """Handle interval selection change."""
        try:
            # Parse interval
            if interval_str == "30 minutes":
                minutes = 60  # Clamp to 60 to avoid half-hour bucket complexity
            elif interval_str == "1 hour":
                minutes = 60
            elif interval_str == "2 hours":
                minutes = 120
            elif interval_str == "3 hours":
                minutes = 180
            elif interval_str == "4 hours":
                minutes = 240
            else:  # 6 hours
                minutes = 360

            # Update interval
            self.interval = minutes
            self.interval_changed.emit(minutes)
            self.update()
            logger.debug(f"Interval changed to {minutes} minutes")

        except Exception as e:
            logger.error(f"Error handling interval change: {e}", exc_info=True)

    def _handle_color_change(self, scale_name: str):
        """Handle color scale selection change."""
        try:
            self.color_scale = scale_name
            self.update()
            logger.debug(f"Color scale changed to {scale_name}")
        except Exception as e:
            logger.error(f"Error handling color change: {e}", exc_info=True)

    def _toggle_legend(self, checked: bool):
        """Toggle legend display."""
        try:
            self.show_legend = checked
            self.update()
            logger.debug(f"Legend display {'enabled' if checked else 'disabled'}")
        except Exception as e:
            logger.error(f"Error toggling legend: {e}", exc_info=True)

    def _paint_chart(self, event):
        """Paint the chart."""
        try:
            painter = QPainter(self.chart_widget)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Get chart area
            chart_rect = self._get_chart_rect()

            # Draw background
            painter.fillRect(
                self.chart_widget.rect(), QColor("#ffffff")
            )  # White background

            # If no data, draw empty state
            if not self.data:
                self._draw_empty_state(painter)
                return

            # Draw cells
            self._draw_cells(painter, chart_rect)

            # Draw axes
            self._draw_axes(painter, chart_rect)

            # Draw legend
            if self.show_legend:
                self._draw_legend(painter, chart_rect)

        except Exception as e:
            logger.error(f"Error painting heatmap: {e}", exc_info=True)

    def _handle_mouse_press(self, event):
        """Handle mouse press events."""
        try:
            if event.button() == Qt.MouseButton.LeftButton:
                cell = self._get_cell_at_pos(event.pos())
                if cell is not None:
                    self.selected_cell = cell
                    self.cell_clicked.emit(cell, self.data.get(cell, 0))
                    self.chart_widget.update()
            event.accept()
        except Exception as e:
            logger.error(f"Error handling mouse press: {e}", exc_info=True)

    def _handle_mouse_move(self, event):
        """Handle mouse move events."""
        try:
            if self.show_tooltips:
                cell = self._get_cell_at_pos(event.pos())
                if cell != self.hover_cell:
                    self.hover_cell = cell
                    if cell is not None:
                        self._show_tooltip(event.pos())
                    self.chart_widget.update()
            event.accept()
        except Exception as e:
            logger.error(f"Error handling mouse move: {e}", exc_info=True)

    def _get_cell_at_pos(self, pos: QPointF) -> Optional[int]:
        """Get cell hour at mouse position."""
        try:
            # Get chart area
            chart_rect = self._get_chart_rect()
            if not chart_rect.contains(pos):
                return None

            # Calculate cell width
            cell_width = chart_rect.width() / (24 / (self.interval / 60))

            # Calculate hour
            x_offset = pos.x() - chart_rect.left()
            cell_index = int(x_offset / cell_width)
            hour = cell_index * (self.interval // 60)

            if 0 <= hour < 24:
                return hour
            return None

        except Exception as e:
            logger.error(f"Error getting cell at position: {e}", exc_info=True)
            return None

    def _show_tooltip(self, pos: QPointF):
        """Show tooltip at position."""
        try:
            # Get cell at position
            cell = self._get_cell_at_pos(pos)
            if cell is None:
                return

            # Get time range
            start_hour = cell
            end_hour = min(24, start_hour + (self.interval // 60))
            value = self.data.get(cell, 0)

            # Create tooltip text
            tooltip = (
                f"Time: {start_hour:02d}:00 - {end_hour:02d}:00\n"
                f"Activity: {value * 100:.1f}%"
            )

            # Convert QPointF to QPoint and map to global coordinates
            point = QPoint(int(pos.x()), int(pos.y()))
            global_pos = self.chart_widget.mapToGlobal(point)

            # Show tooltip
            QToolTip.showText(global_pos, tooltip, self.chart_widget)

        except Exception as e:
            logger.error(f"Error showing tooltip: {e}", exc_info=True)

    def _get_chart_rect(self) -> QRectF:
        """Get chart drawing area."""
        try:
            width = self.chart_widget.width()
            height = self.chart_widget.height()

            # Calculate padding
            left_pad = 60  # Space for y-axis labels
            right_pad = 20
            top_pad = 20
            bottom_pad = self.axis_label_height  # Space for x-axis labels

            # Adjust for legend
            if self.show_legend:
                right_pad += self.legend_width + 20  # Legend width + spacing

            return QRectF(
                left_pad,
                top_pad,
                width - (left_pad + right_pad),
                height - (top_pad + bottom_pad),
            )
        except Exception as e:
            logger.error(f"Error calculating chart rect: {e}", exc_info=True)
            return QRectF(0, 0, self.chart_widget.width(), self.chart_widget.height())

    def paintEvent(self, event):
        """Override to prevent double painting."""
        # Do nothing - all painting is handled by chart_widget
        pass

    def _draw_empty_state(self, painter: QPainter):
        """Draw empty state message."""
        try:
            painter.setPen(QColor("#666666"))  # Dark gray text
            font = QFont()
            font.setPointSize(10)
            painter.setFont(font)
            painter.drawText(
                self.chart_widget.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "No activity data available",
            )
        except Exception as e:
            logger.error(f"Error drawing empty state: {e}", exc_info=True)

    def _draw_cells(self, painter: QPainter, rect: QRectF):
        """Draw heatmap cells."""
        try:
            cell_width = rect.width() / (24 / (self.interval / 60))
            cell_height = rect.height()
            step_hours = max(1, self.interval // 60)

            # Draw background grid
            painter.setPen(QPen(QColor("#f0f0f0")))  # Light gray for grid
            for hour in range(0, 25, step_hours):
                x = rect.left() + hour * (cell_width / (self.interval / 60))
                painter.drawLine(int(x), int(rect.top()), int(x), int(rect.bottom()))

            # Draw horizontal grid lines
            for i in range(6):
                y = rect.top() + (i * rect.height() / 5)
                painter.drawLine(int(rect.left()), int(y), int(rect.right()), int(y))

            # Draw cells
            for hour in range(0, 24, step_hours):
                x = rect.left() + hour * (cell_width / (self.interval / 60))

                # Get value and calculate color
                value = self.data.get(hour, 0)
                intensity = value / self.max_value if self.max_value > 0 else 0
                color = ColorScale.get_color(self.color_scale, intensity)

                # Draw cell
                cell_rect = QRectF(x, rect.top(), cell_width, cell_height)
                painter.setPen(QPen(QColor("#e0e0e0")))  # Light border
                painter.setBrush(QBrush(color))
                painter.drawRect(cell_rect)

                # Draw value if significant
                if value > 0.01:  # 1%
                    text_color = (
                        QColor("#000000") if intensity < 0.5 else QColor("#ffffff")
                    )
                    painter.setPen(text_color)
                    font = QFont()
                    font.setPointSize(9)
                    painter.setFont(font)
                    painter.drawText(
                        cell_rect, Qt.AlignmentFlag.AlignCenter, f"{value * 100:.1f}%"
                    )

                # Draw selection/hover indicators
                if hour == self.selected_cell:
                    painter.setPen(QPen(QColor("#2196F3"), 2))  # Blue highlight
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawRect(cell_rect)
                elif hour == self.hover_cell:
                    painter.setPen(QPen(QColor("#90CAF9"), 1))  # Light blue
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawRect(cell_rect)

        except Exception as e:
            logger.error(f"Error drawing cells: {e}", exc_info=True)

    def _draw_axes(self, painter: QPainter, rect: QRectF):
        """Draw chart axes and labels."""
        try:
            # Draw axes lines
            painter.setPen(QPen(QColor("#666666")))  # Darker gray for axes

            # Draw horizontal axis
            painter.drawLine(
                int(rect.left() - 5),
                int(rect.bottom()),
                int(rect.right()),
                int(rect.bottom()),
            )

            # Draw vertical axis
            painter.drawLine(
                int(rect.left()),
                int(rect.top() - 5),
                int(rect.left()),
                int(rect.bottom() + 5),
            )

            # Set up font
            font = QFont()
            font.setPointSize(9)
            painter.setFont(font)

            # Draw hour labels
            cell_width = rect.width() / (24 / (self.interval / 60))
            step_hours = max(1, self.interval // 60)
            for hour in range(0, 25, step_hours):
                x = rect.left() + hour * (cell_width / (self.interval / 60))

                # Draw tick mark
                painter.drawLine(
                    int(x), int(rect.bottom()), int(x), int(rect.bottom() + 5)
                )

                # Draw hour label
                if hour < 24:  # Don't draw 24:00
                    label = f"{hour:02d}:00"
                    painter.drawText(
                        int(x - cell_width / 2),
                        int(rect.bottom() + 8),
                        int(cell_width),
                        self.axis_label_height,
                        Qt.AlignmentFlag.AlignCenter,
                        label,
                    )

            # Draw percentage labels
            for i in range(0, 6):
                percentage = i * 20
                y = rect.bottom() - (i * rect.height() / 5)

                # Draw tick mark
                painter.drawLine(int(rect.left() - 5), int(y), int(rect.left()), int(y))

                # Draw percentage label
                label = f"{percentage}%"
                painter.drawText(
                    int(rect.left() - 45),
                    int(y - 10),
                    40,
                    20,
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    label,
                )

        except Exception as e:
            logger.error(f"Error drawing axes: {e}", exc_info=True)

    def _draw_legend(self, painter: QPainter, rect: QRectF):
        """Draw color scale legend."""
        try:
            # Calculate legend area
            legend_x = rect.right() + 20
            legend_width = self.legend_width
            legend_height = min(rect.height(), 180)  # Cap legend height
            y_offset = (rect.height() - legend_height) / 2  # Center vertically
            segment_height = legend_height / len(ColorScale.SCALES[self.color_scale])

            # Draw legend title
            font = QFont()
            font.setPointSize(9)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QColor("#333333"))
            painter.drawText(
                int(legend_x),
                int(rect.top() - 20),
                legend_width,
                20,
                Qt.AlignmentFlag.AlignLeft,
                "Activity Level",
            )

            # Draw color segments
            for i, color in enumerate(ColorScale.SCALES[self.color_scale]):
                y = rect.top() + y_offset + i * segment_height
                segment_rect = QRectF(legend_x, y, legend_width - 30, segment_height)

                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(color))
                painter.drawRect(segment_rect)

                # Draw label
                last_idx = len(ColorScale.SCALES[self.color_scale]) - 1
                if i == 0:
                    label = "Low"
                elif i == last_idx:
                    label = "High"
                else:
                    percentage = (i / last_idx) * 100
                    label = f"{percentage:.0f}%"

                painter.setPen(QColor("#666666"))
                font = QFont()
                font.setPointSize(8)
                painter.setFont(font)
                painter.drawText(
                    int(legend_x + legend_width - 25),
                    int(y),
                    25,
                    int(segment_height),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    label,
                )

        except Exception as e:
            logger.error(f"Error drawing legend: {e}", exc_info=True)
