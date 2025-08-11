"""Custom title bar component."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QFrame
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QFont

import logging

logger = logging.getLogger(__name__)


class TitleBar(QFrame):
    """Custom title bar with window control buttons."""

    # Signals for window controls
    minimize_clicked = Signal()
    maximize_clicked = Signal()
    close_clicked = Signal()

    def __init__(self, parent=None):
        """Initialize title bar."""
        try:
            super().__init__(parent)
            self.setup_ui()
            logger.info("Title bar initialized")
        except Exception as e:
            logger.error(f"Error initializing title bar: {e}", exc_info=True)
            raise

    def setup_ui(self):
        """Set up the title bar UI."""
        try:
            # Set frame style
            self.setStyleSheet(
                """
                QFrame {
                    background-color: #2196F3;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                }
                QLabel {
                    color: white;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 0 10px;
                }
                QPushButton {
                    background-color: transparent;
                    border: none;
                    min-width: 45px;
                    min-height: 30px;
                    padding: 0;
                    margin: 0;
                    color: white;
                    font-family: "Segoe UI";
                    font-size: 16px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                }
                QPushButton#close_button:hover {
                    background-color: #E81123;
                }
            """
            )

            # Create layout
            layout = QHBoxLayout()
            layout.setContentsMargins(10, 0, 0, 0)
            layout.setSpacing(0)
            self.setLayout(layout)

            # Add title
            self.title_label = QLabel("AI Work Assistant")
            self.title_label.setFont(QFont("Segoe UI", 12))
            layout.addWidget(self.title_label)

            # Add stretch to push buttons to right
            layout.addStretch()

            # Create button container for consistent spacing
            button_container = QWidget()
            button_layout = QHBoxLayout()
            button_layout.setContentsMargins(0, 0, 0, 0)
            button_layout.setSpacing(0)
            button_container.setLayout(button_layout)

            # Add window control buttons
            self.minimize_button = QPushButton("—")
            self.minimize_button.setToolTip("Minimize")
            self.minimize_button.clicked.connect(self.minimize_clicked)
            button_layout.addWidget(self.minimize_button)

            self.maximize_button = QPushButton("□")
            self.maximize_button.setToolTip("Maximize")
            self.maximize_button.clicked.connect(self.maximize_clicked)
            button_layout.addWidget(self.maximize_button)

            self.close_button = QPushButton("✕")
            self.close_button.setObjectName("close_button")
            self.close_button.setToolTip("Close")
            self.close_button.clicked.connect(self.close_clicked)
            button_layout.addWidget(self.close_button)

            # Add button container to main layout
            layout.addWidget(button_container)

            # Set fixed height
            self.setFixedHeight(40)

            logger.info("Title bar UI setup complete")

        except Exception as e:
            logger.error(f"Error setting up title bar UI: {e}", exc_info=True)
            raise

    def set_title(self, title):
        """Set the window title."""
        try:
            self.title_label.setText(title)
            logger.debug(f"Title set to: {title}")
        except Exception as e:
            logger.error(f"Error setting title: {e}", exc_info=True)

    def update_maximize_button(self, is_maximized):
        """Update maximize button text based on window state."""
        try:
            if is_maximized:
                self.maximize_button.setText("❐")
                self.maximize_button.setToolTip("Restore Down")
            else:
                self.maximize_button.setText("□")
                self.maximize_button.setToolTip("Maximize")
            logger.debug(f"Maximize button updated: maximized={is_maximized}")
        except Exception as e:
            logger.error(f"Error updating maximize button: {e}", exc_info=True)

    def mousePressEvent(self, event):
        """Handle mouse press events for window dragging."""
        try:
            if event.button() == Qt.LeftButton:
                # Store the mouse position relative to the window
                self.drag_position = (
                    event.globalPosition().toPoint() - self.window().pos()
                )
                event.accept()
            logger.debug("Mouse press event handled")
        except Exception as e:
            logger.error(f"Error handling mouse press: {e}", exc_info=True)

    def mouseMoveEvent(self, event):
        """Handle mouse move events for window dragging."""
        try:
            if hasattr(self, "drag_position"):
                # Move the window to follow the mouse
                self.window().move(
                    event.globalPosition().toPoint() - self.drag_position
                )
                event.accept()
            logger.debug("Mouse move event handled")
        except Exception as e:
            logger.error(f"Error handling mouse move: {e}", exc_info=True)

    def mouseDoubleClickEvent(self, event):
        """Handle double click events for maximize/restore."""
        try:
            if event.button() == Qt.LeftButton:
                # Toggle maximize state
                self.maximize_clicked.emit()
                event.accept()
            logger.debug("Mouse double click event handled")
        except Exception as e:
            logger.error(f"Error handling mouse double click: {e}", exc_info=True)
