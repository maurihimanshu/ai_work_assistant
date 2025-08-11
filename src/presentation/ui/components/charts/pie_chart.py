"""Pie chart component for activity distribution."""

from PySide6.QtWidgets import QWidget, QToolTip
from PySide6.QtCore import Qt, QRectF, QPointF, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath
import logging
import math

logger = logging.getLogger(__name__)


class ActivityPieChart(QWidget):
    """Pie chart for displaying activity distribution."""

    COLORS = [
        ("#2196F3", "#90CAF9"),  # Blue, Light Blue
        ("#4CAF50", "#A5D6A7"),  # Green, Light Green
        ("#FFC107", "#FFE082"),  # Amber, Light Amber
        ("#9C27B0", "#CE93D8"),  # Purple, Light Purple
        ("#F44336", "#EF9A9A"),  # Red, Light Red
        ("#00BCD4", "#80DEEA"),  # Cyan, Light Cyan
        ("#FF9800", "#FFCC80"),  # Orange, Light Orange
        ("#3F51B5", "#9FA8DA"),  # Indigo, Light Indigo
    ]

    def __init__(self, parent=None):
        try:
            super().__init__(parent)
            self.data = []  # List of (label, value) pairs
            self.hover_segment = -1  # Index of hovered segment
            self.setMinimumSize(
                500, 300
            )  # Reduced minimum width since legend is smaller
            self.setMouseTracking(True)
            # Cached layout and geometry for consistent hover detection
            self._last_chart_rect: QRectF | None = None
            self._last_segment_ranges: list[
                tuple[float, float]
            ] = []  # [(start_deg, end_deg)]
            # Cache legend item rectangles and labels for hover tooltips
            self._legend_item_rects: list[QRectF] = []
            self._legend_labels: list[str] = []
            logger.info("Activity pie chart initialized")
        except Exception as e:
            logger.error(f"Error initializing activity pie chart: {e}", exc_info=True)
            raise

    # Helper: compute responsive chart ratio consistently for paint and events
    def _chart_ratio(self, width: int) -> float:
        if width < 540:
            return 0.45
        elif width < 700:
            return 0.5
        elif width < 900:
            return 0.55
        return 0.6

    # Helper: compute chart rect consistently
    def _compute_chart_rect(self) -> QRectF:
        width = self.width()
        height = self.height()
        chart_ratio = self._chart_ratio(width)
        margin = 30
        outer_padding = 15
        chart_width = width * chart_ratio
        chart_size = min(chart_width - margin * 2, height - margin * 2)
        chart_x = outer_padding + (chart_width - chart_size) / 2
        chart_y = (height - chart_size) / 2
        return QRectF(chart_x, chart_y, chart_size, chart_size)

    # Helper: angle within segment (clockwise, 0 deg at 3 o'clock, we start at 90)
    def _angle_in_segment(
        self, angle_deg: float, start_deg: float, end_deg: float
    ) -> bool:
        start_deg = start_deg % 360
        end_deg = end_deg % 360
        if start_deg > end_deg:
            return end_deg < angle_deg <= start_deg
        # wrapped
        return angle_deg <= start_deg or angle_deg > end_deg

    def update_data(self, data):
        """Update chart with new data.

        Args:
            data: List of [name, duration, percentage] lists
        """
        try:
            if not data:
                logger.debug("No data provided to pie chart")
                self.data = []
                try:
                    if self.isVisible():
                        self.update()
                except RuntimeError:
                    return
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
                            f"Invalid percentage value in pie chart data: {e}"
                        )
                        continue

            # Sort by percentage descending
            items.sort(key=lambda x: x[1], reverse=True)

            # Take top 8 items
            self.data = items[:8]

            # Add "Others" category if needed
            if len(items) > 8:
                others = sum(item[1] for item in items[8:])
                if others > 0:
                    self.data.append(("Others", others))

            # Reset cached geometry
            self._last_chart_rect = None
            self._last_segment_ranges = []
            self._legend_item_rects = []
            # Keep labels for legend hover tooltips
            self._legend_labels = [label for label, _ in self.data]

            try:
                if self.isVisible():
                    self.update()
            except RuntimeError:
                return
            logger.debug(f"Activity pie chart updated with {len(self.data)} items")

        except Exception as e:
            logger.error(f"Error updating activity pie chart data: {e}", exc_info=True)

    def paintEvent(self, event):
        """Paint the chart."""
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Calculate dimensions
            width = self.width()
            height = self.height()
            chart_ratio = self._chart_ratio(width)

            # Draw background
            painter.fillRect(0, 0, width, height, QColor("#ffffff"))

            if not self.data:
                # Draw empty state
                font = QFont()
                font.setPointSize(10)
                painter.setFont(font)
                painter.setPen(QPen(QColor("#666666")))
                painter.drawText(
                    self.rect(),
                    Qt.AlignmentFlag.AlignCenter,
                    "No activity data available",
                )
                return

            # Calculate chart area (left side, responsive)
            chart_rect = self._compute_chart_rect()
            self._last_chart_rect = chart_rect

            # Draw pie segments and cache angle ranges
            self._last_segment_ranges = []
            current_angle_deg = 90.0  # Start from top (90 degrees)
            for i, (_, value) in enumerate(self.data):
                segment_angle_deg = (value * 360.0) / 100.0
                start_deg = current_angle_deg
                end_deg = (current_angle_deg - segment_angle_deg) % 360.0

                # Cache before drawing
                self._last_segment_ranges.append((start_deg, end_deg))

                # Convert to Qt angle units (clockwise negative, *16)
                span_angle = -segment_angle_deg * 16.0

                base_color = QColor(self.COLORS[i % len(self.COLORS)][0])
                highlight_color = QColor(self.COLORS[i % len(self.COLORS)][1])

                # Set colors based on hover state
                if i == self.hover_segment:
                    painter.setBrush(QBrush(highlight_color))
                    painter.setPen(QPen(base_color, 2))  # Highlight border
                else:
                    painter.setBrush(QBrush(base_color))
                    painter.setPen(QPen(Qt.white, 2))

                painter.drawPie(
                    chart_rect, int(current_angle_deg * 16.0), int(span_angle)
                )
                current_angle_deg = end_deg

            # Draw legend (right side)
            legend_x = width * chart_ratio + 15  # Start after chart area
            legend_width = width * (1 - chart_ratio) - 30  # 2*outer_padding
            compact_mode = legend_width < 140

            # Calculate maximum label width
            font = QFont()
            font.setPointSize(9)
            painter.setFont(font)

            # 12px color box + 8px gap ~ 20px; reserve 50px for percent if not compact
            reserve_for_percent = 50 if not compact_mode else 0
            max_label_width = max(40, legend_width - 20 - reserve_for_percent)

            # Calculate needed height for wrapped text
            total_height = 0
            wrapped_labels = []
            for label, value in self.data:
                words = label.split()
                current_line = words[0] if words else ""
                lines = [] if not words else []

                for word in words[1:]:
                    test_line = (current_line + " " + word).strip()
                    width_px = painter.fontMetrics().horizontalAdvance(test_line)
                    if width_px <= max_label_width:
                        current_line = test_line
                    else:
                        if current_line:
                            lines.append(current_line)
                        current_line = word
                if current_line:
                    lines.append(current_line)
                # Clamp to at most 2 lines and elide the second line if needed
                max_lines = 2
                if len(lines) > max_lines:
                    remaining = " ".join(lines[1:])
                    elided = painter.fontMetrics().elidedText(
                        remaining, Qt.TextElideMode.ElideRight, int(max_label_width)
                    )
                    lines = [lines[0], elided]

                wrapped_labels.append((lines, value))
                # Add extra height in compact mode to place percentage on its own line
                extra = 16 if compact_mode else 0
                total_height += len(lines) * 18 + 10 + extra

            # Draw legend title
            title_font = QFont()
            title_font.setPointSize(9)
            title_font.setBold(True)
            painter.setFont(title_font)
            painter.setPen(QPen(QColor("#333333")))

            legend_y = (height - total_height) / 2
            title_rect = QRectF(legend_x, legend_y - 25, legend_width, 20)
            painter.drawText(
                title_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                "Activity Distribution",
            )

            # Draw legend items
            font = QFont()
            font.setPointSize(9)
            painter.setFont(font)

            current_y = legend_y
            for i, (lines, value) in enumerate(wrapped_labels):
                base_color = QColor(self.COLORS[i % len(self.COLORS)][0])
                highlight_color = QColor(self.COLORS[i % len(self.COLORS)][1])

                # Add extra line for percentage in compact mode
                item_height = len(lines) * 18 + 10 + (16 if compact_mode else 0)

                # Draw background for hovered item
                # Cache legend item rectangle for hover detection and tooltips
                item_rect = QRectF(
                    legend_x - 5, current_y - 2, legend_width + 10, item_height + 4
                )
                # Ensure list length
                if i >= len(self._legend_item_rects):
                    self._legend_item_rects.append(item_rect)
                else:
                    self._legend_item_rects[i] = item_rect
                if i == self.hover_segment:
                    painter.fillRect(item_rect, QColor("#f5f5f5"))

                # Draw color box
                box_rect = QRectF(legend_x, current_y + 2, 12, 12)
                painter.setPen(QPen(base_color, 1))
                painter.setBrush(
                    QBrush(base_color if i != self.hover_segment else highlight_color)
                )
                painter.drawRect(box_rect)

                # Draw label lines
                painter.setPen(QPen(QColor("#333333")))
                for j, line in enumerate(lines):
                    text_rect = QRectF(
                        legend_x + 20, current_y + j * 18, max_label_width, 18
                    )
                    if i == self.hover_segment:
                        font.setBold(True)
                        painter.setFont(font)
                    painter.drawText(
                        text_rect,
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                        line,
                    )
                    if i == self.hover_segment:
                        font.setBold(False)
                        painter.setFont(font)

                if compact_mode:
                    # Draw percentage on its own line below labels
                    pct_rect = QRectF(
                        legend_x + 20, current_y + len(lines) * 18, max_label_width, 16
                    )
                    painter.drawText(
                        pct_rect,
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                        f"({value:.1f}%)",
                    )
                else:
                    # In non-compact mode, draw percentage in a right column
                    percentage_rect = QRectF(
                        legend_x + 20 + max_label_width, current_y, 50, 18
                    )
                    if i == self.hover_segment:
                        font.setBold(True)
                        painter.setFont(font)
                    painter.drawText(
                        percentage_rect,
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                        f"({value:.1f}%)",
                    )
                    if i == self.hover_segment:
                        font.setBold(False)
                        painter.setFont(font)

                current_y += item_height

            # Draw hover tooltip near chart center if segment hovered
            if 0 <= self.hover_segment < len(self.data) and self._last_chart_rect:
                label, value = self.data[self.hover_segment]
                # Optional: could draw a centered overlay; we use tooltip instead
                # Keep painting clean here.

        except Exception as e:
            logger.error(f"Error painting activity pie chart: {e}", exc_info=True)

    def mouseMoveEvent(self, event):
        """Handle mouse move events for hover effects."""
        try:
            # Get mouse position
            pos = event.position()
            hover_index = -1

            # First, check if mouse is over a legend item
            if self._legend_item_rects:
                for i, rect in enumerate(self._legend_item_rects):
                    if rect.contains(pos):
                        hover_index = i
                        break

            # If not over legend, check the chart area
            if hover_index == -1:
                chart_rect = self._compute_chart_rect()
                if chart_rect.contains(pos):
                    # Get center of the chart
                    center = chart_rect.center()

                    # Calculate vector from center to mouse
                    dx = pos.x() - center.x()
                    dy = (
                        center.y() - pos.y()
                    )  # Invert Y to match mathematical coordinate system

                    # Calculate distance from center
                    distance = math.hypot(dx, dy)
                    radius = chart_rect.width() / 2.0

                    # Check if within pie radius
                    if distance <= radius and self.data:
                        # Calculate angle in degrees (0-360), 0 deg = +X axis, increasing CCW
                        angle = math.degrees(math.atan2(dy, dx))
                        if angle < 0:
                            angle += 360.0
                        # We drew starting at 90 and going clockwise: test ranges
                        if not self._last_segment_ranges:
                            # Fallback: rebuild ranges like paintEvent
                            current_angle_deg = 90.0
                            self._last_segment_ranges = []
                            for _, value in self.data:
                                segment_angle_deg = (value * 360.0) / 100.0
                                start_deg = current_angle_deg
                                end_deg = (
                                    current_angle_deg - segment_angle_deg
                                ) % 360.0
                                self._last_segment_ranges.append((start_deg, end_deg))
                                current_angle_deg = end_deg
                        for i, (start_deg, end_deg) in enumerate(
                            self._last_segment_ranges
                        ):
                            if self._angle_in_segment(angle, start_deg, end_deg):
                                hover_index = i
                                break

            # Update hover state if changed
            if hover_index != self.hover_segment:
                self.hover_segment = hover_index
                self.update()
            # Show or hide tooltip with percentage for either legend or chart hover
            if self.hover_segment != -1 and self.hover_segment < len(self.data):
                label, value = self.data[self.hover_segment]
                text = f"{label}: {value:.1f}%"
                try:
                    QToolTip.showText(
                        self.mapToGlobal(event.position().toPoint()), text, self
                    )
                except Exception:
                    # Fallback for environments without global positioning
                    QToolTip.showText(self.cursor().pos(), text, self)
            else:
                QToolTip.hideText()

        except Exception as e:
            logger.error(f"Error handling mouse move in pie chart: {e}", exc_info=True)

    def leaveEvent(self, event):
        """Handle mouse leave events."""
        if self.hover_segment != -1:
            self.hover_segment = -1
            self.update()
        QToolTip.hideText()
