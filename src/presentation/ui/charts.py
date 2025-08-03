"""Chart components for data visualization."""

import logging
from typing import Dict, List

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


class ProductivityLineChart(QWidget):
    """Line chart for productivity trends."""

    def __init__(self, parent=None):
        """Initialize productivity line chart."""
        super().__init__(parent)
        self.data: List[float] = []
        self.setMinimumHeight(200)

    def update_data(self, data: List[float]) -> None:
        """Update chart data.

        Args:
            data: List of productivity scores
        """
        self.data = data
        self.update()

    def paintEvent(self, event) -> None:
        """Paint the chart."""
        if not self.data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate dimensions
        width = self.width() - 40  # Leave space for labels
        height = self.height() - 40
        x_step = width / (len(self.data) - 1) if len(self.data) > 1 else width

        # Create path
        path = QPainterPath()
        path.moveTo(20, height - (self.data[0] * height) + 20)

        for i in range(1, len(self.data)):
            x = i * x_step + 20
            y = height - (self.data[i] * height) + 20
            path.lineTo(x, y)

        # Draw grid
        painter.setPen(QPen(QColor("#ecf0f1"), 1))
        for i in range(5):
            y = i * height / 4 + 20
            painter.drawLine(20, y, width + 20, y)
            # Draw y-axis labels
            painter.drawText(
                0,
                y - 10,
                20,
                20,
                Qt.AlignmentFlag.AlignRight,
                f"{(1 - i/4):.1f}"
            )

        # Draw axes
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.drawLine(20, 20, 20, height + 20)  # y-axis
        painter.drawLine(20, height + 20, width + 20, height + 20)  # x-axis

        # Draw line
        painter.setPen(QPen(QColor("#3498db"), 2))
        painter.drawPath(path)

        # Draw points
        painter.setBrush(QColor("#3498db"))
        for i, value in enumerate(self.data):
            x = i * x_step + 20
            y = height - (value * height) + 20
            painter.drawEllipse(int(x - 3), int(y - 3), 6, 6)


class ActivityPieChart(QWidget):
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
        """
        self.data = data
        self.update()

    def paintEvent(self, event) -> None:
        """Paint the chart."""
        if not self.data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate dimensions
        width = self.width()
        height = self.height()
        size = min(width, height) - 40
        center_x = width / 2
        center_y = height / 2

        # Calculate total and angles
        total = sum(self.data.values())
        start_angle = 0

        # Color palette
        colors = [
            "#3498db", "#e74c3c", "#2ecc71", "#f1c40f",
            "#9b59b6", "#1abc9c", "#e67e22", "#34495e"
        ]

        # Draw segments
        for i, (name, value) in enumerate(self.data.items()):
            angle = int(value * 5760 / total)  # 16 * 360 for precision
            color = QColor(colors[i % len(colors)])

            # Draw segment
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPie(
                int(center_x - size/2),
                int(center_y - size/2),
                size,
                size,
                start_angle,
                angle
            )

            # Calculate label position
            mid_angle = start_angle + angle/2
            rad_angle = mid_angle * np.pi / 2880  # Convert to radians
            label_x = center_x + (size/2 + 20) * np.cos(rad_angle)
            label_y = center_y + (size/2 + 20) * np.sin(rad_angle)

            # Draw label
            painter.setPen(Qt.GlobalColor.black)
            text = f"{name}\n{value/total:.1%}"
            painter.drawText(
                int(label_x - 50),
                int(label_y - 10),
                100,
                20,
                Qt.AlignmentFlag.AlignCenter,
                text
            )

            start_angle += angle


class ActivityBarChart(QWidget):
    """Bar chart for activity categories."""

    def __init__(self, parent=None):
        """Initialize activity bar chart."""
        super().__init__(parent)
        self.data: Dict[str, float] = {}
        self.setMinimumHeight(200)

    def update_data(self, data: Dict[str, float]) -> None:
        """Update chart data.

        Args:
            data: Dictionary of category names and scores
        """
        self.data = data
        self.update()

    def paintEvent(self, event) -> None:
        """Paint the chart."""
        if not self.data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate dimensions
        width = self.width() - 100  # Leave space for labels
        height = self.height() - 40
        bar_height = height / len(self.data)
        bar_spacing = bar_height * 0.2

        # Draw axes
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.drawLine(80, 20, 80, height + 20)  # y-axis
        painter.drawLine(80, height + 20, width + 80, height + 20)  # x-axis

        # Draw scale
        painter.setPen(QPen(QColor("#ecf0f1"), 1))
        for i in range(5):
            x = i * width / 4 + 80
            painter.drawLine(x, 20, x, height + 20)
            # Draw x-axis labels
            painter.setPen(Qt.GlobalColor.black)
            painter.drawText(
                x - 15,
                height + 20,
                30,
                20,
                Qt.AlignmentFlag.AlignCenter,
                f"{i/4:.1f}"
            )
            painter.setPen(QPen(QColor("#ecf0f1"), 1))

        # Draw bars
        for i, (name, value) in enumerate(self.data.items()):
            y = i * bar_height + 20
            bar_width = value * width

            # Draw bar
            painter.setBrush(QColor("#3498db"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(
                80,
                y + bar_spacing/2,
                bar_width,
                bar_height - bar_spacing
            )

            # Draw label
            painter.setPen(Qt.GlobalColor.black)
            painter.drawText(
                0,
                y,
                75,
                bar_height,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                name
            )

            # Draw value
            painter.drawText(
                85 + bar_width,
                y,
                50,
                bar_height,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                f"{value:.2f}"
            )


class TimeHeatmap(QWidget):
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
        """
        self.data = data
        self.update()

    def paintEvent(self, event) -> None:
        """Paint the heatmap."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate dimensions
        width = self.width() - 100  # Leave space for labels
        height = self.height() - 60
        cell_width = width / 24
        cell_height = height / 7

        # Color scale
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
        for day in range(7):
            # Draw day label
            day_name = [
                "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"
            ][day]
            painter.setPen(Qt.GlobalColor.black)
            painter.drawText(
                0,
                day * cell_height + 30,
                60,
                cell_height,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                day_name
            )

            for hour in range(24):
                value = self.data[day, hour]

                # Draw cell
                painter.setBrush(get_color(value))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRect(
                    hour * cell_width + 70,
                    day * cell_height + 30,
                    cell_width - 1,
                    cell_height - 1
                )

        # Draw hour labels
        for hour in range(24):
            if hour % 3 == 0:  # Show every 3 hours
                painter.setPen(Qt.GlobalColor.black)
                painter.drawText(
                    hour * cell_width + 70,
                    height + 35,
                    cell_width,
                    20,
                    Qt.AlignmentFlag.AlignCenter,
                    f"{hour:02d}:00"
                )