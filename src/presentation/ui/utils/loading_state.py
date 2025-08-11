"""Loading state utilities."""

from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QProgressBar, QSizePolicy
from PySide6.QtGui import QPainter, QColor, QPen
import math
import logging

logger = logging.getLogger(__name__)


class SpinnerWidget(QWidget):
    """Custom loading spinner widget."""

    def __init__(self, parent=None, size=40, color="#2196F3"):
        """Initialize spinner widget."""
        super().__init__(parent)

        self.angle = 0
        self.size = size
        self.color = QColor(color)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._rotate)
        self.timer.start(50)  # 20 FPS

        # Set size
        self.setFixedSize(size, size)

        # Set background transparent
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def _rotate(self):
        """Update rotation angle."""
        self.angle = (self.angle + 30) % 360
        self.update()

    def paintEvent(self, event):
        """Paint the spinner."""
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Calculate center and radius
            center = self.rect().center()
            radius = (min(self.width(), self.height()) - 4) / 2

            # Draw arcs with varying opacity
            for i in range(12):
                # Calculate angle and opacity
                angle = (self.angle - i * 30) % 360
                opacity = 1.0 - (i / 12)

                # Set pen
                pen = QPen(
                    QColor(
                        self.color.red(),
                        self.color.green(),
                        self.color.blue(),
                        int(255 * opacity),
                    )
                )
                pen.setWidth(2)
                painter.setPen(pen)

                # Draw arc
                start_angle = angle * 16  # Qt uses 1/16th of a degree
                span_angle = 20 * 16
                painter.drawArc(
                    2, 2, self.width() - 4, self.height() - 4, start_angle, span_angle
                )

        except Exception as e:
            logger.error(f"Error painting spinner: {e}", exc_info=True)

    def showEvent(self, event):
        """Handle show event."""
        try:
            self.timer.start()
            super().showEvent(event)
        except Exception as e:
            logger.error(f"Error showing spinner: {e}", exc_info=True)

    def hideEvent(self, event):
        """Handle hide event."""
        try:
            self.timer.stop()
            super().hideEvent(event)
        except Exception as e:
            logger.error(f"Error hiding spinner: {e}", exc_info=True)


class LoadingStateWidget(QWidget):
    """Widget for displaying loading states."""

    def __init__(
        self,
        message: str = "Loading...",
        parent: QWidget = None,
        spinner_size: int = 40,
        spinner_color: str = "#2196F3",
    ):
        """Initialize loading state widget."""
        try:
            super().__init__(parent)

            # Create layout
            layout = QVBoxLayout(self)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.setSpacing(16)

            # Add spinner
            self.spinner = SpinnerWidget(self, spinner_size, spinner_color)
            layout.addWidget(self.spinner, 0, Qt.AlignmentFlag.AlignCenter)

            # Add message
            self.message_label = QLabel(message)
            self.message_label.setStyleSheet(
                """
                QLabel {
                    color: #757575;
                    font-size: 14px;
                }
            """
            )
            layout.addWidget(self.message_label, 0, Qt.AlignmentFlag.AlignCenter)

            # Set size policy
            self.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )

            logger.debug("Loading state widget initialized")

        except Exception as e:
            logger.error(f"Error initializing loading state: {e}", exc_info=True)
            raise

    def set_message(self, message: str):
        """Update loading message."""
        try:
            self.message_label.setText(message)
        except Exception as e:
            logger.error(f"Error setting message: {e}", exc_info=True)


class LoadingOverlay(QWidget):
    """Semi-transparent loading overlay."""

    def __init__(
        self,
        parent: QWidget = None,
        message: str = "Loading...",
        spinner_size: int = 40,
        spinner_color: str = "#2196F3",
    ):
        """Initialize loading overlay."""
        try:
            super().__init__(parent)

            # Set up overlay properties
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

            # Create loading state widget
            self.loading_widget = LoadingStateWidget(
                message, self, spinner_size, spinner_color
            )

            # Create layout
            layout = QVBoxLayout(self)
            layout.addWidget(self.loading_widget)

            # Style
            self.setStyleSheet(
                """
                LoadingOverlay {
                    background-color: rgba(255, 255, 255, 0.8);
                }
            """
            )

            # Hide initially
            self.hide()

            logger.debug("Loading overlay initialized")

        except Exception as e:
            logger.error(f"Error initializing loading overlay: {e}", exc_info=True)
            raise

    def showEvent(self, event):
        """Handle show event."""
        try:
            if self.parentWidget():
                self.resize(self.parentWidget().size())
            super().showEvent(event)
        except Exception as e:
            logger.error(f"Error showing overlay: {e}", exc_info=True)

    def set_message(self, message: str):
        """Update loading message."""
        try:
            self.loading_widget.set_message(message)
        except Exception as e:
            logger.error(f"Error setting overlay message: {e}", exc_info=True)
