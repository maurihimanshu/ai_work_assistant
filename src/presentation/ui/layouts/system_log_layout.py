"""System log layout module."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTextEdit,
    QFrame,
    QHBoxLayout,
    QComboBox,
    QLabel,
    QPushButton,
    QApplication,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QTextCharFormat, QColor, QTextCursor
import logging
from collections import deque
from threading import Lock

logger = logging.getLogger(__name__)

# Constants
MAX_LOG_ENTRIES = 10000  # Maximum number of log entries to store
BATCH_SIZE = 100  # Number of logs to process in one batch
BATCH_UPDATE_INTERVAL = 100  # Milliseconds between batch updates


class SystemLogLayout(QWidget):
    """System log layout widget."""

    def __init__(self, parent=None):
        """Initialize system log layout."""
        try:
            super().__init__(parent)
            # Initialize log storage with thread safety
            self.all_logs = deque(maxlen=MAX_LOG_ENTRIES)
            self.pending_logs = deque()
            self.log_lock = Lock()

            # Initialize UI
            self.setup_ui()
            self.setup_batch_processing()

            logger.debug("System log layout initialized")
        except Exception as e:
            logger.error(f"Error initializing system log layout: {e}", exc_info=True)
            raise

    def setup_ui(self):
        """Set up the system log layout UI."""
        try:
            # Create main layout
            layout = QVBoxLayout(self)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(10)

            # Create filter bar
            filter_frame = QFrame()
            filter_frame.setStyleSheet(
                """
                QFrame {
                    background-color: white;
                    border: 1px solid #e0e0e0;
                    border-radius: 4px;
                }
                QComboBox {
                    padding: 5px;
                    border: 1px solid #e0e0e0;
                    border-radius: 4px;
                    min-width: 100px;
                }
                QPushButton {
                    padding: 5px 15px;
                    border: none;
                    border-radius: 4px;
                    background-color: #2196F3;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """
            )
            filter_layout = QHBoxLayout(filter_frame)
            filter_layout.setContentsMargins(10, 10, 10, 10)
            filter_layout.setSpacing(10)

            # Add level filter
            filter_layout.addWidget(QLabel("Level:"))
            self.level_filter = QComboBox()
            self.level_filter.addItems(
                ["All", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            )
            self.level_filter.currentTextChanged.connect(self._filter_logs)
            filter_layout.addWidget(self.level_filter)

            # Add clear button
            self.clear_button = QPushButton("Clear")
            self.clear_button.clicked.connect(self._clear_logs)
            filter_layout.addWidget(self.clear_button)

            filter_layout.addStretch()
            layout.addWidget(filter_frame)

            # Create log viewer
            self.log_viewer = QTextEdit()
            self.log_viewer.setReadOnly(True)
            self.log_viewer.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
            self.log_viewer.setStyleSheet(
                """
                QTextEdit {
                    background-color: #1e1e1e;
                    color: #ffffff;
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 12px;
                    padding: 10px;
                    border: none;
                }
            """
            )
            self.log_viewer.document().setMaximumBlockCount(MAX_LOG_ENTRIES)
            layout.addWidget(self.log_viewer)

            # Set up text formats for different log levels
            self.formats = {
                logging.DEBUG: self._create_format("#757575"),  # Gray
                logging.INFO: self._create_format("#FFFFFF"),  # White
                logging.WARNING: self._create_format("#FFA726"),  # Orange
                logging.ERROR: self._create_format("#EF5350"),  # Red
                logging.CRITICAL: self._create_format(
                    "#D32F2F", True
                ),  # Dark Red, Bold
            }

        except Exception as e:
            logger.error(f"Error setting up system log layout UI: {e}", exc_info=True)
            raise

    def setup_batch_processing(self):
        """Set up batch processing for log updates."""
        try:
            self.update_timer = QTimer(self)
            self.update_timer.setInterval(BATCH_UPDATE_INTERVAL)
            self.update_timer.timeout.connect(self._process_pending_logs)
            self.update_timer.start()
        except Exception as e:
            logger.error(f"Error setting up batch processing: {e}", exc_info=True)

    def _create_format(self, color: str, bold: bool = False) -> QTextCharFormat:
        """Create text format for log level.

        Args:
            color: Color in hex format
            bold: Whether to make text bold

        Returns:
            QTextCharFormat with specified formatting
        """
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if bold:
            fmt.setFontWeight(700)
        return fmt

    def handle_log_message(self, message: str, level: int):
        """Handle incoming log message.

        Args:
            message: Log message text
            level: Log level (e.g., logging.INFO)
        """
        try:
            with self.log_lock:
                self.pending_logs.append((message, level))
        except Exception as e:
            print(f"Error handling log message: {e}")

    def _process_pending_logs(self):
        """Process pending logs in batches."""
        try:
            with self.log_lock:
                # Process up to BATCH_SIZE logs
                for _ in range(min(len(self.pending_logs), BATCH_SIZE)):
                    message, level = self.pending_logs.popleft()
                    self.all_logs.append((message, level))

                    # Check if message should be shown based on current filter
                    if self._should_show_message(level):
                        cursor = self.log_viewer.textCursor()
                        cursor.movePosition(QTextCursor.End)
                        cursor.insertText(
                            message + "\n",
                            self.formats.get(level, self.formats[logging.INFO]),
                        )

                # Auto-scroll if near bottom
                scrollbar = self.log_viewer.verticalScrollBar()
                if scrollbar.value() >= scrollbar.maximum() - 50:
                    scrollbar.setValue(scrollbar.maximum())

        except Exception as e:
            print(f"Error processing pending logs: {e}")

    def _should_show_message(self, level: int) -> bool:
        """Check if message should be shown based on current filter.

        Args:
            level: Log level to check

        Returns:
            True if message should be shown, False otherwise
        """
        try:
            filter_text = self.level_filter.currentText()
            if filter_text == "All":
                return True
            return level >= getattr(logging, filter_text)
        except Exception as e:
            print(f"Error checking message visibility: {e}")
            return True

    def _filter_logs(self):
        """Filter log messages based on selected level."""
        try:
            self.log_viewer.clear()

            with self.log_lock:
                for message, level in self.all_logs:
                    if self._should_show_message(level):
                        cursor = self.log_viewer.textCursor()
                        cursor.movePosition(QTextCursor.End)
                        cursor.insertText(
                            message + "\n",
                            self.formats.get(level, self.formats[logging.INFO]),
                        )

            # Maintain scroll position at bottom
            scrollbar = self.log_viewer.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

        except Exception as e:
            print(f"Error filtering logs: {e}")

    def _clear_logs(self):
        """Clear all log messages."""
        try:
            with self.log_lock:
                self.all_logs.clear()
                self.pending_logs.clear()
                self.log_viewer.clear()
        except Exception as e:
            print(f"Error clearing logs: {e}")

    def closeEvent(self, event):
        """Handle cleanup on close."""
        try:
            self.update_timer.stop()
            super().closeEvent(event)
        except Exception as e:
            print(f"Error in close event: {e}")
            event.accept()
