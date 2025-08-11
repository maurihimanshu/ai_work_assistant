"""Metric card component for displaying key metrics."""

from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QStackedLayout,
    QWidget,
    QGridLayout,
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QVariantAnimation
from PySide6.QtGui import QColor
import logging
from typing import Optional, Union

logger = logging.getLogger(__name__)


class MetricCard(QFrame):
    """Card widget for displaying a metric with solid progress background."""

    def __init__(
        self,
        title: str,
        value: str,
        icon: str,
        description: str,
        show_progress: bool = False,
        theme: str = "light",
        parent=None,
    ):
        try:
            super().__init__(parent)
            self.title = title
            self.value = value
            self.icon = icon
            self.description = description
            self.show_progress = show_progress
            self.theme = theme
            self.progress = 0
            self.setup_ui()
            self.setup_styles()
            logger.debug(f"MetricCard initialized: {title}")
        except Exception as e:
            logger.error(f"Error initializing metric card: {e}", exc_info=True)
            raise

    def setup_ui(self):
        """Set up the card UI."""
        try:
            # Set size constraints
            self.setMinimumWidth(180)
            self.setMaximumWidth(280)  # Limit maximum width
            self.setMaximumHeight(120)  # Limit maximum height
            self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

            # Create main layout with minimal spacing
            main_layout = QVBoxLayout()
            main_layout.setContentsMargins(10, 10, 10, 10)  # Increased card margins
            main_layout.setSpacing(6)  # Slightly increased spacing
            self.setLayout(main_layout)

            # Header section - compact and efficient
            header_widget = QWidget()
            header_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            header_layout = QHBoxLayout(header_widget)
            header_layout.setContentsMargins(4, 2, 4, 2)  # Added horizontal margins
            header_layout.setSpacing(8)  # Increased spacing between icon and title

            # Icon container - smaller and more compact
            icon_container = QFrame()
            icon_container.setFixedSize(20, 20)
            icon_container.setObjectName("icon_container")
            icon_layout = QHBoxLayout(icon_container)
            icon_layout.setContentsMargins(0, 0, 0, 0)
            icon_layout.setSpacing(0)

            # Icon - slightly smaller
            icon_label = QLabel(self.icon)
            icon_label.setObjectName("icon")
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setStyleSheet("font-size: 12px;")
            icon_layout.addWidget(icon_label)

            header_layout.addWidget(icon_container)

            # Title - compact but clear
            title_label = QLabel(self.title)
            title_label.setObjectName("title")
            title_label.setStyleSheet(
                "font-size: 12px; font-weight: 600; padding: 0px 2px;"
            )  # Added padding
            title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            title_label.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            header_layout.addWidget(title_label)

            main_layout.addWidget(header_widget)

            # Value section container
            value_container = QWidget()
            value_container.setObjectName("value_container")
            value_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            value_container.setFixedHeight(32)

            # Value section layout
            value_layout = QHBoxLayout(value_container)
            value_layout.setContentsMargins(10, 0, 10, 0)
            value_layout.setSpacing(0)

            # Create stacked layout for progress and value
            content_widget = QWidget()
            content_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            content_layout = QStackedLayout(content_widget)
            content_layout.setStackingMode(
                QStackedLayout.StackingMode.StackAll
            )  # Show all widgets stacked

            # Progress layer (bottom layer)
            if self.show_progress:
                progress_container = QWidget()
                progress_container.setSizePolicy(
                    QSizePolicy.Expanding, QSizePolicy.Preferred
                )
                progress_layout = QHBoxLayout(progress_container)
                progress_layout.setContentsMargins(0, 0, 0, 0)
                progress_layout.setSpacing(0)

                self.progress_frame = QFrame()
                self.progress_frame.setObjectName("progress_frame")
                self.progress_frame.setAutoFillBackground(True)
                self.progress_frame.setSizePolicy(
                    QSizePolicy.Fixed, QSizePolicy.Expanding
                )
                progress_layout.addWidget(self.progress_frame)
                progress_layout.addStretch()

                content_layout.addWidget(progress_container)

            # Value layer (top layer)
            value_container_widget = QWidget()
            value_container_widget.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Preferred
            )
            value_container_layout = QHBoxLayout(value_container_widget)
            value_container_layout.setContentsMargins(0, 0, 0, 0)
            value_container_layout.setSpacing(0)

            # Add stretch on left to push value to right
            value_container_layout.addStretch()

            # Value label with fixed width and right alignment
            value_wrapper = QWidget()
            value_wrapper.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            value_wrapper.setMinimumWidth(60)
            value_wrapper.setMaximumWidth(120)
            value_wrapper_layout = QHBoxLayout(value_wrapper)
            value_wrapper_layout.setContentsMargins(4, 0, 4, 0)
            value_wrapper_layout.setSpacing(0)

            self.value_label = QLabel(self.value)
            self.value_label.setObjectName("value")
            self.value_label.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.value_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            value_wrapper_layout.addWidget(self.value_label)

            value_container_layout.addWidget(value_wrapper)
            content_layout.addWidget(value_container_widget)

            value_layout.addWidget(content_widget)
            main_layout.addWidget(value_container)

            # Description - only if needed
            if self.description:
                description_widget = QWidget()
                description_widget.setSizePolicy(
                    QSizePolicy.Expanding, QSizePolicy.Minimum
                )
                description_layout = QHBoxLayout(description_widget)
                description_layout.setContentsMargins(4, 2, 4, 4)  # Added margins

                self.description_label = QLabel(self.description)
                self.description_label.setObjectName("description")
                self.description_label.setWordWrap(True)
                self.description_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                self.description_label.setSizePolicy(
                    QSizePolicy.Expanding, QSizePolicy.Minimum
                )
                self.description_label.setStyleSheet(
                    "padding: 0px 2px;"
                )  # Added padding
                description_layout.addWidget(self.description_label)

                main_layout.addWidget(description_widget)
            else:
                self.description_label = None

            # Set up value animation
            self.value_animation = QVariantAnimation()
            self.value_animation.setDuration(300)
            self.value_animation.valueChanged.connect(self._update_progress)

        except Exception as e:
            logger.error(f"Error setting up metric card UI: {e}", exc_info=True)
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
                    background-color: #fafafa;
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
                    background-color: #333333;
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

    def resizeEvent(self, event):
        """Handle resize events to maintain proportions."""
        super().resizeEvent(event)
        width = event.size().width()

        # Conservative font scaling
        title_size = max(11, min(12, width / 25))
        value_size = max(13, min(15, width / 18))
        desc_size = max(10, min(11, width / 28))

        # Update font sizes
        self.findChild(QLabel, "title").setStyleSheet(
            f"font-size: {title_size}px; font-weight: 600; margin: 0px;"
        )
        self.value_label.setStyleSheet(
            f"""
            font-size: {value_size}px;
            font-weight: 600;
            color: {('#ffffff' if self.theme == 'dark' else '#1a1a1a')};
            padding: 0px 4px;
        """
        )

        if self.description_label:
            self.description_label.setStyleSheet(
                f"""
                font-size: {desc_size}px;
                color: {('#999999' if self.theme == 'dark' else '#666666')};
            """
            )

    def _update_progress(self, value):
        """Update the progress frame width."""
        try:
            if self.show_progress:
                content_width = (
                    self.findChild(QWidget, "value_container").width() - 16
                )  # Account for padding
                value_width = (
                    self.value_label.parentWidget().width()
                )  # Get wrapper width
                max_progress_width = content_width - value_width - 4  # Leave small gap
                progress_width = min(int(content_width * value), max_progress_width)
                self.progress_frame.setFixedWidth(progress_width)
                self.progress_frame.update()
        except Exception as e:
            logger.error(f"Error updating progress: {e}", exc_info=True)
            raise

    def set_value(self, value: str, progress: float = None):
        """Update the card value and progress."""
        try:
            self.value = value
            self.value_label.setText(value)

            if progress is not None and self.show_progress:
                self.value_animation.setStartValue(self.progress)
                self.value_animation.setEndValue(progress)
                self.value_animation.start()
                self.progress = progress

        except Exception as e:
            logger.error(f"Error updating metric card value: {e}", exc_info=True)
            raise
