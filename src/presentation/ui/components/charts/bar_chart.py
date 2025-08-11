"""Bar chart component for activity distribution."""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QFont
import logging

logger = logging.getLogger(__name__)


class ActivityBarChart(QWidget):
    """Bar chart for displaying activity distribution."""

    COLORS = [
        ("#2196F3", "#64B5F6"),  # Blue
        ("#4CAF50", "#81C784"),  # Green
        ("#FFC107", "#FFD54F"),  # Amber
        ("#9C27B0", "#BA68C8"),  # Purple
        ("#F44336", "#E57373"),  # Red
        ("#00BCD4", "#4DD0E1"),  # Cyan
        ("#FF9800", "#FFB74D"),  # Orange
        ("#3F51B5", "#7986CB"),  # Indigo
        ("#E91E63", "#F06292"),  # Pink
        ("#009688", "#4DB6AC"),  # Teal
    ]

    def __init__(self, parent=None):
        try:
            super().__init__(parent)
            self.data = []  # List of (label, value) pairs
            self.setMinimumSize(200, 200)
            logger.info("Activity bar chart initialized")
        except Exception as e:
            logger.error(f"Error initializing activity bar chart: {e}", exc_info=True)
            raise

    def update_data(self, data):
        """Update chart with new data.

        Args:
            data: List of [name, duration, percentage] lists
        """
        try:
            if not data:
                logger.debug("No data provided to bar chart")
                return

            # Convert data to list of (label, value) pairs
            items = []

            for item in data:
                if len(item) >= 3:  # Ensure item has name and percentage
                    name = str(item[0])
                    try:
                        percentage = float(item[2].rstrip("%"))
                        if percentage >= 1:  # Only show items with >= 1%
                            items.append((name, percentage))
                    except (ValueError, AttributeError) as e:
                        logger.warning(
                            f"Invalid percentage value in bar chart data: {e}"
                        )
                        continue

            # Sort by percentage descending
            items.sort(key=lambda x: x[1], reverse=True)

            # Take top 10 items
            self.data = items[:10]

            self.update()
            logger.debug(f"Activity bar chart updated with {len(self.data)} items")

        except Exception as e:
            logger.error(f"Error updating activity bar chart data: {e}", exc_info=True)

    def paintEvent(self, event):
        """Paint the chart."""
        try:
            if not self.data:
                return

            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Calculate dimensions
            width = self.width()
            height = self.height()

            # Draw background
            painter.fillRect(0, 0, width, height, QColor("white"))

            # Calculate chart area
            margin = 40
            chart_x = margin * 2  # Extra space for labels
            chart_y = margin
            chart_width = width - margin * 3
            chart_height = height - margin * 2

            # Draw axes
            painter.setPen(QPen(QColor("#9E9E9E"), 1))
            # Y-axis
            painter.drawLine(chart_x, chart_y, chart_x, chart_y + chart_height)
            # X-axis
            painter.drawLine(
                chart_x,
                chart_y + chart_height,
                chart_x + chart_width,
                chart_y + chart_height,
            )

            # Draw Y-axis labels and grid lines
            font = QFont()
            font.setPointSize(8)
            painter.setFont(font)
            painter.setPen(QPen(Qt.black))

            for i in range(6):
                y = chart_y + (chart_height * (5 - i) / 5)
                value = i * 20
                painter.drawText(
                    margin,
                    int(y - 10),
                    margin,
                    20,
                    Qt.AlignRight | Qt.AlignVCenter,
                    f"{value}%",
                )
                # Draw grid line
                painter.setPen(QPen(QColor("#E0E0E0"), 1))
                painter.drawLine(chart_x, int(y), chart_x + chart_width, int(y))

            # Calculate bar dimensions
            bar_count = len(self.data)
            if bar_count == 0:
                return

            bar_width = chart_width / bar_count
            bar_margin = bar_width * 0.2

            # Draw bars
            for i, (label, value) in enumerate(self.data):
                # Calculate bar position
                x = chart_x + i * bar_width + bar_margin / 2
                y = chart_y + chart_height * (1 - value / 100)
                bar_height = chart_height * value / 100

                # Create gradient
                gradient = QLinearGradient(x, y, x, y + bar_height)
                color1 = QColor(self.COLORS[i % len(self.COLORS)][0])
                color2 = QColor(self.COLORS[i % len(self.COLORS)][1])
                gradient.setColorAt(0, color1)
                gradient.setColorAt(1, color2)

                # Draw bar
                bar_rect = QRectF(x, y, bar_width - bar_margin, bar_height)
                painter.fillRect(bar_rect, QBrush(gradient))

                # Draw value on top of bar
                painter.setPen(QPen(Qt.black))
                value_text = f"{value:.1f}%"
                painter.drawText(
                    int(x),
                    int(y - 20),
                    int(bar_width - bar_margin),
                    20,
                    Qt.AlignCenter,
                    value_text,
                )

                # Draw label below bar
                label_rect = QRectF(
                    x, chart_y + chart_height + 5, bar_width - bar_margin, margin - 10
                )
                painter.drawText(label_rect, Qt.AlignCenter | Qt.TextWordWrap, label)

        except Exception as e:
            logger.error(f"Error painting activity bar chart: {e}", exc_info=True)
