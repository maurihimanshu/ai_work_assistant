"""Chart components for data visualization."""

import logging
from typing import Dict, List, Optional

import numpy as np
from PyQt6.QtCore import QPoint, QPointF, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


class ChartError(Exception):
    """Base exception for chart-related errors."""

    pass


class ChartDataError(ChartError):
    """Exception raised for invalid chart data."""

    pass


class PainterError(ChartError):
    """Exception raised for painter-related errors."""

    pass


class BaseChart(QWidget):
    """Base class for all charts with common functionality."""

    error_occurred = pyqtSignal(str)  # Signal to notify about errors

    def __init__(self, parent=None):
        """Initialize base chart."""
        super().__init__(parent)
        self._error_state = False
        self._error_message = ""
        self._data_valid = False
        self._painter = None
        self.setMinimumSize(100, 100)  # Set minimum size

    def _validate_dimensions(self) -> tuple[int, int]:
        """Validate and return widget dimensions.

        Returns:
            tuple: (width, height) of usable chart area

        Raises:
            ChartError: If dimensions are invalid
        """
        rect = self.geometry()
        width = rect.width()
        height = rect.height()
        if width < self.minimumWidth() or height < self.minimumHeight():
            raise ChartError("Chart dimensions too small")
        return width, height

    def _handle_error(self, e: Exception, during_paint: bool = False) -> None:
        """Handle chart errors.

        Args:
            e: Exception that occurred
            during_paint: Whether error occurred during paint event
        """
        self._error_state = True
        self._error_message = str(e)
        logger.error(f"Chart error: {e}")
        self.error_occurred.emit(str(e))

        if not during_paint:
            self.update()  # Trigger repaint to show error state

    def _clear_error(self) -> None:
        """Clear error state."""
        self._error_state = False
        self._error_message = ""
        self.update()

    def _draw_error_state(self, painter: QPainter) -> None:
        """Draw error state on chart.

        Args:
            painter: QPainter instance
        """
        if not painter.isActive():
            return
        painter.setPen(QPen(Qt.GlobalColor.red, 1))
        rect = self.geometry()
        painter.drawText(
            QRect(10, 10, rect.width() - 20, rect.height() - 20),
            Qt.AlignmentFlag.AlignCenter,
            f"Error: {self._error_message}",
        )

    def _ensure_painter_active(self, painter: QPainter) -> bool:
        """Ensure painter is active.

        Args:
            painter: QPainter instance

        Returns:
            bool: True if painter is active
        """
        if not painter.isActive():
            if not painter.begin(self):
                self._handle_error(PainterError("Failed to initialize painter"))
                return False
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        return True

    def resizeEvent(self, event) -> None:
        """Handle resize events.

        Args:
            event: Resize event
        """
        super().resizeEvent(event)
        try:
            self._validate_dimensions()
            self._clear_error()
        except ChartError as e:
            self._handle_error(e)
        self.update()

    def paintEvent(self, event) -> None:
        """Base paint event handler."""
        # First validate dimensions
        try:
            self._validate_dimensions()
        except ChartError as e:
            self._handle_error(e)
            painter = QPainter()
            if self._ensure_painter_active(painter):
                self._draw_error_state(painter)
                painter.end()
            return

        painter = QPainter()
        try:
            if not self._ensure_painter_active(painter):
                return

            if self._error_state:
                self._draw_error_state(painter)
                return

            self._paint_chart(painter)

        except Exception as e:
            self._handle_error(e, during_paint=True)
            if painter.isActive():
                painter.end()
            painter = QPainter()
            if self._ensure_painter_active(painter):
                self._draw_error_state(painter)
                painter.end()
        finally:
            if painter.isActive():
                painter.end()

    def _paint_chart(self, painter: QPainter) -> None:
        """Paint chart content. To be implemented by subclasses.

        Args:
            painter: QPainter instance

        Raises:
            ChartError: If painting fails
        """
        pass


class ProductivityLineChart(BaseChart):
    """Line chart for productivity trends."""

    def __init__(self, parent=None):
        """Initialize productivity line chart."""
        super().__init__(parent)
        self.data: List[float] = []
        self.setMinimumHeight(200)
        self.setMinimumWidth(300)

    def update_data(self, data: List[float]) -> None:
        """Update chart data.

        Args:
            data: List of productivity scores

        Raises:
            ChartDataError: If data is invalid
        """
        try:
            if not isinstance(data, list):
                raise ChartDataError("Data must be a list")

            # Validate data values
            clean_data = []
            for i, value in enumerate(data):
                try:
                    float_val = float(value)
                    if not 0 <= float_val <= 1:
                        logger.warning(
                            f"Value at index {i} out of range [0,1]: {float_val}"
                        )
                        float_val = max(0, min(1, float_val))  # Clamp to valid range
                    clean_data.append(float_val)
                except (TypeError, ValueError):
                    logger.warning(f"Invalid value at index {i}: {value}")
                    continue

            if not clean_data:
                raise ChartDataError("No valid data points")

            self.data = clean_data
            self._data_valid = True
            self._clear_error()
            self.update()

        except Exception as e:
            self._data_valid = False
            self._handle_error(e)

    def _paint_chart(self, painter: QPainter) -> None:
        """Paint the chart."""
        if not self.data or not self._data_valid:
            return

        try:
            width, height = self._validate_dimensions()

            # Calculate dimensions
            chart_width = width - 40  # Leave space for labels
            chart_height = height - 40
            x_step = (
                chart_width / (len(self.data) - 1)
                if len(self.data) > 1
                else chart_width
            )

            # Draw grid
            painter.setPen(QPen(QColor("#ecf0f1"), 1))
            for i in range(5):
                y = int(i * chart_height / 4 + 20)
                painter.drawLine(QPoint(20, y), QPoint(chart_width + 20, y))
                # Draw y-axis labels
                painter.drawText(
                    QRect(0, y - 10, 20, 20),
                    Qt.AlignmentFlag.AlignRight,
                    f"{(1 - i/4):.1f}",
                )

            # Draw axes
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            painter.drawLine(QPoint(20, 20), QPoint(20, chart_height + 20))  # y-axis
            painter.drawLine(
                QPoint(20, chart_height + 20),
                QPoint(chart_width + 20, chart_height + 20),
            )  # x-axis

            # Create path
            path = QPainterPath()
            start_y = int(chart_height - (self.data[0] * chart_height) + 20)
            path.moveTo(QPointF(20, start_y))

            for i in range(1, len(self.data)):
                x = int(i * x_step + 20)
                y = int(chart_height - (self.data[i] * chart_height) + 20)
                path.lineTo(QPointF(x, y))

            # Draw line
            painter.setPen(QPen(QColor("#3498db"), 2))
            painter.drawPath(path)

            # Draw points
            painter.setBrush(QColor("#3498db"))
            for i, value in enumerate(self.data):
                x = int(i * x_step + 20)
                y = int(chart_height - (value * chart_height) + 20)
                painter.drawEllipse(QPoint(x, y), 3, 3)

        except Exception as e:
            raise ChartError(f"Error drawing chart elements: {e}")


class ActivityPieChart(BaseChart):
    """Pie chart for activity distribution."""

    def __init__(self, parent=None):
        """Initialize activity pie chart."""
        super().__init__(parent)
        self.data: Dict[str, float] = {}
        self.setMinimumSize(200, 200)

    def update_data(self, data: Dict[str, float]) -> None:
        """Update chart data.

        Args:
            data: Dictionary of activity names and durations

        Raises:
            ChartDataError: If data is invalid
        """
        try:
            if not isinstance(data, dict):
                raise ChartDataError("Data must be a dictionary")

            # Validate and clean data
            clean_data = {}
            for name, value in data.items():
                try:
                    if not isinstance(name, str) or not name.strip():
                        logger.warning(f"Invalid activity name: {name}")
                        continue

                    float_val = float(value)
                    if float_val < 0:
                        logger.warning(f"Negative value for {name}: {float_val}")
                        continue

                    clean_data[name.strip()] = float_val
                except (TypeError, ValueError):
                    logger.warning(f"Invalid value for {name}: {value}")
                    continue

            if not clean_data:
                raise ChartDataError("No valid data points")

            self.data = clean_data
            self._data_valid = True
            self._clear_error()
            self.update()

        except Exception as e:
            self._data_valid = False
            self._handle_error(e)

    def _paint_chart(self, painter: QPainter) -> None:
        """Paint the chart."""
        if not self.data or not self._data_valid:
            return

        try:
            width, height = self._validate_dimensions()

            # Calculate dimensions
            size = min(width, height) - 40
            center_x = width / 2
            center_y = height / 2

            # Calculate total and angles
            total = sum(self.data.values())
            if total <= 0:
                raise ChartDataError("Total value must be positive")

            start_angle = 0

            # Color palette
            colors = [
                "#3498db",
                "#e74c3c",
                "#2ecc71",
                "#f1c40f",
                "#9b59b6",
                "#1abc9c",
                "#e67e22",
                "#34495e",
            ]

            # Draw segments
            for i, (name, value) in enumerate(self.data.items()):
                if value <= 0:
                    continue

                angle = int(value * 5760 / total)  # 16 * 360 for precision
                color = QColor(colors[i % len(colors)])

                # Draw segment
                painter.setBrush(color)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawPie(
                    QRect(
                        int(center_x - size / 2), int(center_y - size / 2), size, size
                    ),
                    start_angle,
                    angle,
                )

                # Calculate label position
                mid_angle = start_angle + angle / 2
                rad_angle = mid_angle * np.pi / 2880  # Convert to radians
                label_x = int(center_x + (size / 2 + 20) * np.cos(rad_angle))
                label_y = int(center_y + (size / 2 + 20) * np.sin(rad_angle))

                # Draw label
                painter.setPen(Qt.GlobalColor.black)
                text = f"{name}\n{value/total:.1%}"
                painter.drawText(
                    QRect(label_x - 50, label_y - 10, 100, 20),
                    Qt.AlignmentFlag.AlignCenter,
                    text,
                )

                start_angle += angle

        except Exception as e:
            raise ChartError(f"Error drawing chart elements: {e}")


class ActivityBarChart(BaseChart):
    """Bar chart for activity categories."""

    def __init__(self, parent=None):
        """Initialize activity bar chart."""
        super().__init__(parent)
        self.data: Dict[str, float] = {}
        self.setMinimumHeight(200)
        self.setMinimumWidth(300)

    def update_data(self, data: Dict[str, float]) -> None:
        """Update chart data.

        Args:
            data: Dictionary of category names and scores

        Raises:
            ChartDataError: If data is invalid
        """
        try:
            if not isinstance(data, dict):
                raise ChartDataError("Data must be a dictionary")

            # Validate and clean data
            clean_data = {}
            for name, value in data.items():
                try:
                    if not isinstance(name, str) or not name.strip():
                        logger.warning(f"Invalid category name: {name}")
                        continue

                    float_val = float(value)
                    if not 0 <= float_val <= 1:
                        logger.warning(
                            f"Value out of range [0,1] for {name}: {float_val}"
                        )
                        float_val = max(0, min(1, float_val))  # Clamp to valid range

                    clean_data[name.strip()] = float_val
                except (TypeError, ValueError):
                    logger.warning(f"Invalid value for {name}: {value}")
                    continue

            if not clean_data:
                raise ChartDataError("No valid data points")

            self.data = clean_data
            self._data_valid = True
            self._clear_error()
            self.update()

        except Exception as e:
            self._data_valid = False
            self._handle_error(e)

    def _paint_chart(self, painter: QPainter) -> None:
        """Paint the chart."""
        if not self.data or not self._data_valid:
            return

        try:
            width, height = self._validate_dimensions()

            # Calculate dimensions
            chart_width = width - 100  # Leave space for labels
            chart_height = height - 40
            bar_height = chart_height / len(self.data)
            bar_spacing = bar_height * 0.2

            # Draw axes
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            painter.drawLine(QPoint(80, 20), QPoint(80, chart_height + 20))  # y-axis
            painter.drawLine(
                QPoint(80, chart_height + 20),
                QPoint(chart_width + 80, chart_height + 20),
            )  # x-axis

            # Draw scale
            painter.setPen(QPen(QColor("#ecf0f1"), 1))
            for i in range(5):
                x = int(i * chart_width / 4 + 80)
                painter.drawLine(QPoint(x, 20), QPoint(x, chart_height + 20))
                # Draw x-axis labels
                painter.setPen(Qt.GlobalColor.black)
                painter.drawText(
                    QRect(x - 15, chart_height + 20, 30, 20),
                    Qt.AlignmentFlag.AlignCenter,
                    f"{i/4:.1f}",
                )
                painter.setPen(QPen(QColor("#ecf0f1"), 1))

            # Draw bars
            for i, (name, value) in enumerate(self.data.items()):
                y = int(i * bar_height + 20)
                bar_width = int(value * chart_width)

                # Draw bar
                painter.setBrush(QColor("#3498db"))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRect(
                    QRect(
                        80,
                        int(y + bar_spacing / 2),
                        bar_width,
                        int(bar_height - bar_spacing),
                    )
                )

                # Draw label
                painter.setPen(Qt.GlobalColor.black)
                painter.drawText(
                    QRect(0, y, 75, int(bar_height)),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    name,
                )

                # Draw value
                painter.drawText(
                    QRect(85 + bar_width, y, 50, int(bar_height)),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    f"{value:.2f}",
                )

        except Exception as e:
            raise ChartError(f"Error drawing chart elements: {e}")


class TimeHeatmap(BaseChart):
    """Heatmap for time-based activity patterns."""

    def __init__(self, parent=None):
        """Initialize time heatmap."""
        super().__init__(parent)
        self.data = np.zeros((7, 24))  # days x hours
        self.setMinimumSize(600, 200)

    def update_data(self, data: np.ndarray) -> None:
        """Update heatmap data.

        Args:
            data: 2D array of activity values (days x hours)

        Raises:
            ChartDataError: If data is invalid
        """
        try:
            if not isinstance(data, np.ndarray):
                raise ChartDataError("Data must be a numpy array")

            if data.shape != (7, 24):
                raise ChartDataError(
                    f"Invalid data shape: {data.shape}, expected (7, 24)"
                )

            # Validate data values
            if np.any(np.isnan(data)) or np.any(np.isinf(data)):
                raise ChartDataError("Data contains NaN or infinite values")

            if np.any(data < 0):
                logger.warning("Negative values in data will be clamped to 0")
                data = np.maximum(data, 0)

            self.data = data
            self._data_valid = True
            self._clear_error()
            self.update()

        except Exception as e:
            self._data_valid = False
            self._handle_error(e)

    def _paint_chart(self, painter: QPainter) -> None:
        """Paint the heatmap."""
        if not self._data_valid:
            return

        try:
            width, height = self._validate_dimensions()

            # Calculate dimensions
            chart_width = width - 100  # Leave space for labels
            chart_height = height - 60
            cell_width = chart_width / 24
            cell_height = chart_height / 7

            def get_color(value: float) -> QColor:
                """Get color for value."""
                if value == 0:
                    return QColor("#ecf0f1")

                # Normalize value
                max_val = np.max(self.data)
                if max_val > 0:
                    value = value / max_val

                # Color interpolation
                r = int(52 + value * (41 - 52))
                g = int(152 + value * (128 - 152))
                b = int(219 + value * (185 - 219))
                return QColor(r, g, b)

            # Draw cells
            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            for day in range(7):
                # Draw day label
                painter.setPen(Qt.GlobalColor.black)
                painter.drawText(
                    QRect(0, int(day * cell_height + 30), 60, int(cell_height)),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    day_names[day],
                )

                for hour in range(24):
                    value = float(self.data[day, hour])  # Convert to float

                    # Draw cell
                    painter.setBrush(get_color(value))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawRect(
                        QRect(
                            int(hour * cell_width + 70),
                            int(day * cell_height + 30),
                            int(cell_width - 1),
                            int(cell_height - 1),
                        )
                    )

            # Draw hour labels
            for hour in range(24):
                if hour % 3 == 0:  # Show every 3 hours
                    painter.setPen(Qt.GlobalColor.black)
                    painter.drawText(
                        QRect(
                            int(hour * cell_width + 70),
                            int(chart_height + 35),
                            int(cell_width),
                            20,
                        ),
                        Qt.AlignmentFlag.AlignCenter,
                        f"{hour:02d}:00",
                    )

        except Exception as e:
            raise ChartError(f"Error drawing chart elements: {e}")
