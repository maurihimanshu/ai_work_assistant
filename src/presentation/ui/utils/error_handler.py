"""Error handling utilities."""

from PySide6.QtCore import Qt, QObject, Signal as pyqtSignal, QTimer, QPoint
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QFrame,
    QApplication,
)
from PySide6.QtGui import QColor, QPainter, QPainterPath, QIcon
from typing import Optional, Dict, Any, List
from enum import Enum
import logging
import traceback

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorNotification(QFrame):
    """Toast-style error notification widget."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        parent: Optional[QWidget] = None,
        timeout: int = 5000,  # 5 seconds
    ):
        """Initialize error notification."""
        super().__init__(parent)

        self.message = message
        self.severity = severity
        self.timeout = timeout

        # Colors for different severities
        self.colors = {
            ErrorSeverity.INFO: ("#E3F2FD", "#2196F3", "#1976D2"),  # Light Blue
            ErrorSeverity.WARNING: ("#FFF3E0", "#FF9800", "#F57C00"),  # Orange
            ErrorSeverity.ERROR: ("#FFEBEE", "#F44336", "#D32F2F"),  # Red
            ErrorSeverity.CRITICAL: ("#FCE4EC", "#E91E63", "#C2185B"),  # Pink
        }

        # Setup UI
        self.setup_ui()

        # Start auto-hide timer
        if timeout > 0:
            QTimer.singleShot(timeout, self.hide_animation)

    def setup_ui(self):
        """Set up the notification UI."""
        # Set frame style
        self.setFrameStyle(QFrame.Shape.NoFrame)

        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # Add icon based on severity
        icon_name = {
            ErrorSeverity.INFO: "SP_MessageBoxInformation",
            ErrorSeverity.WARNING: "SP_MessageBoxWarning",
            ErrorSeverity.ERROR: "SP_MessageBoxCritical",
            ErrorSeverity.CRITICAL: "SP_MessageBoxCritical",
        }[self.severity]

        icon_label = QLabel()
        icon_label.setPixmap(
            self.style()
            .standardIcon(getattr(self.style().StandardPixmap, icon_name))
            .pixmap(16, 16)
        )
        layout.addWidget(icon_label)

        # Add message
        message_label = QLabel(self.message)
        message_label.setWordWrap(True)
        layout.addWidget(message_label, 1)  # Stretch factor 1

        # Add close button
        close_button = QPushButton()
        close_button.setIcon(
            self.style().standardIcon(self.style().StandardPixmap.SP_DialogCloseButton)
        )
        close_button.setFlat(True)
        close_button.setFixedSize(16, 16)
        close_button.clicked.connect(self.hide_animation)
        layout.addWidget(close_button)

        # Set size policy
        self.setSizePolicy(
            self.sizePolicy().horizontalPolicy(), self.sizePolicy().Fixed
        )

        # Style
        bg_color, border_color, _ = self.colors[self.severity]
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 4px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
            QPushButton {{
                background: transparent;
                border: none;
            }}
            QPushButton:hover {{
                background: rgba(0, 0, 0, 0.1);
                border-radius: 2px;
            }}
        """
        )

    def hide_animation(self):
        """Animate hiding the notification."""
        self.hide()
        self.deleteLater()


class ErrorStateWidget(QWidget):
    """Widget for displaying error states."""

    # Signals
    retryClicked = pyqtSignal()

    def __init__(
        self,
        message: str,
        detail: str = "",
        can_retry: bool = True,
        parent: Optional[QWidget] = None,
    ):
        """Initialize error state widget."""
        super().__init__(parent)

        self.message = message
        self.detail = detail
        self.can_retry = can_retry

        # Setup UI
        self.setup_ui()

    def setup_ui(self):
        """Set up the error state UI."""
        # Create layout
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        # Add icon
        icon_label = QLabel()
        icon_label.setPixmap(
            self.style()
            .standardIcon(self.style().StandardPixmap.SP_MessageBoxCritical)
            .pixmap(48, 48)
        )
        layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignCenter)

        # Add message
        message_label = QLabel(self.message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet(
            """
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #D32F2F;
            }
        """
        )
        layout.addWidget(message_label, 0, Qt.AlignmentFlag.AlignCenter)

        # Add detail if provided
        if self.detail:
            detail_label = QLabel(self.detail)
            detail_label.setWordWrap(True)
            detail_label.setStyleSheet(
                """
                QLabel {
                    color: #757575;
                }
            """
            )
            layout.addWidget(detail_label, 0, Qt.AlignmentFlag.AlignCenter)

        # Add retry button if enabled
        if self.can_retry:
            retry_button = QPushButton("Retry")
            retry_button.setIcon(
                self.style().standardIcon(self.style().StandardPixmap.SP_BrowserReload)
            )
            retry_button.clicked.connect(self.retryClicked)
            retry_button.setStyleSheet(
                """
                QPushButton {
                    padding: 8px 16px;
                    background-color: #F44336;
                    color: white;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #E53935;
                }
                QPushButton:pressed {
                    background-color: #D32F2F;
                }
            """
            )
            layout.addWidget(retry_button, 0, Qt.AlignmentFlag.AlignCenter)


class ErrorHandler(QObject):
    """Global error handler."""

    # Singleton instance
    _instance = None

    # Signals
    errorOccurred = pyqtSignal(str, ErrorSeverity)  # message, severity

    def __new__(cls):
        """Create or return singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize error handler."""
        if not hasattr(self, "_initialized"):
            super().__init__()
            self._initialized = True
            self._active_notifications: List[ErrorNotification] = []

            # Set up logging handler
            self._setup_logging()

    def _setup_logging(self):
        """Set up logging handler to capture errors."""

        class UILogHandler(logging.Handler):
            def __init__(self, error_handler):
                super().__init__()
                self.error_handler = error_handler

            def emit(self, record):
                try:
                    # Map logging levels to severity
                    severity_map = {
                        logging.INFO: ErrorSeverity.INFO,
                        logging.WARNING: ErrorSeverity.WARNING,
                        logging.ERROR: ErrorSeverity.ERROR,
                        logging.CRITICAL: ErrorSeverity.CRITICAL,
                    }
                    severity = severity_map.get(record.levelno, ErrorSeverity.ERROR)

                    # Show notification for warning and above
                    if record.levelno >= logging.WARNING:
                        self.error_handler.show_notification(
                            record.getMessage(), severity
                        )
                except Exception:
                    pass  # Avoid infinite recursion

        # Add handler to root logger
        logging.getLogger().addHandler(UILogHandler(self))

    def show_notification(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        timeout: int = 5000,
    ):
        """Show error notification."""
        try:
            # Get main window
            main_window = None
            for widget in QApplication.topLevelWidgets():
                if widget.isWindow():
                    main_window = widget
                    break

            if not main_window:
                return

            # Create notification
            notification = ErrorNotification(message, severity, main_window, timeout)

            # Position notification
            self._position_notification(notification)

            # Show notification
            notification.show()

            # Add to active notifications
            self._active_notifications.append(notification)

            # Clean up hidden notifications
            self._active_notifications = [
                n for n in self._active_notifications if not n.isHidden()
            ]

            # Emit signal
            self.errorOccurred.emit(message, severity)

        except Exception as e:
            logger.error(f"Error showing notification: {e}", exc_info=True)

    def _position_notification(self, notification: ErrorNotification):
        """Position notification widget."""
        try:
            if not notification.parentWidget():
                return

            # Get parent geometry
            parent_rect = notification.parentWidget().geometry()

            # Calculate initial position (bottom-right corner)
            x = parent_rect.width() - notification.sizeHint().width() - 20
            y = parent_rect.height() - 20

            # Adjust for existing notifications
            for n in reversed(self._active_notifications):
                if not n.isHidden():
                    y -= n.height() + 10

            # Set position
            notification.move(x, y)

        except Exception as e:
            logger.error(f"Error positioning notification: {e}", exc_info=True)

    def create_error_state(
        self,
        message: str,
        detail: str = "",
        can_retry: bool = True,
        parent: Optional[QWidget] = None,
    ) -> ErrorStateWidget:
        """Create error state widget."""
        try:
            return ErrorStateWidget(message, detail, can_retry, parent)
        except Exception as e:
            logger.error(f"Error creating error state: {e}", exc_info=True)
            return None


# Global instance
error_handler = ErrorHandler()
