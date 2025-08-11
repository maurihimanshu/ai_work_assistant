"""Empty state utilities."""

from PySide6.QtCore import Qt, Signal as pyqtSignal
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QSizePolicy
from PySide6.QtGui import QIcon, QPixmap
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


class EmptyStateWidget(QWidget):
    """Widget for displaying empty states."""

    # Signals
    actionTriggered = pyqtSignal()

    def __init__(
        self,
        message: str,
        detail: str = "",
        action_text: str = "",
        icon_name: str = "SP_MessageBoxInformation",
        parent: Optional[QWidget] = None,
    ):
        """Initialize empty state widget."""
        try:
            super().__init__(parent)

            self.message = message
            self.detail = detail
            self.action_text = action_text
            self.icon_name = icon_name

            # Setup UI
            self.setup_ui()

            logger.debug("Empty state widget initialized")

        except Exception as e:
            logger.error(f"Error initializing empty state: {e}", exc_info=True)
            raise

    def setup_ui(self):
        """Set up the empty state UI."""
        try:
            # Create layout
            layout = QVBoxLayout(self)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.setSpacing(16)

            # Add icon
            icon_label = QLabel()
            icon = self.style().standardIcon(
                getattr(self.style().StandardPixmap, self.icon_name)
            )
            icon_label.setPixmap(icon.pixmap(64, 64))
            layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignCenter)

            # Add message
            message_label = QLabel(self.message)
            message_label.setWordWrap(True)
            message_label.setStyleSheet(
                """
                QLabel {
                    font-size: 16px;
                    font-weight: bold;
                    color: #424242;
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

            # Add action button if provided
            if self.action_text:
                action_button = QPushButton(self.action_text)
                action_button.setStyleSheet(
                    """
                    QPushButton {
                        padding: 8px 16px;
                        background-color: #2196F3;
                        color: white;
                        border: none;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #1976D2;
                    }
                    QPushButton:pressed {
                        background-color: #1565C0;
                    }
                """
                )
                action_button.clicked.connect(self.actionTriggered)
                layout.addWidget(action_button, 0, Qt.AlignmentFlag.AlignCenter)

            # Set size policy
            self.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )

            # Style
            self.setStyleSheet(
                """
                EmptyStateWidget {
                    background-color: #fafafa;
                    border-radius: 8px;
                }
            """
            )

            logger.debug("Empty state UI setup complete")

        except Exception as e:
            logger.error(f"Error setting up empty state UI: {e}", exc_info=True)
            raise


class NoDataWidget(EmptyStateWidget):
    """Widget for displaying no data state."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        message: str = "No Data Available",
        detail: str = "There is no data to display at this time.",
        action_text: str = "Refresh",
    ):
        """Initialize no data widget."""
        try:
            super().__init__(message, detail, action_text, "SP_FileIcon", parent)

            logger.debug("No data widget initialized")

        except Exception as e:
            logger.error(f"Error initializing no data widget: {e}", exc_info=True)
            raise


class NoResultsWidget(EmptyStateWidget):
    """Widget for displaying no search results state."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        message: str = "No Results Found",
        detail: str = "Try adjusting your search criteria.",
        action_text: str = "Clear Filters",
    ):
        """Initialize no results widget."""
        try:
            super().__init__(
                message, detail, action_text, "SP_FileDialogContentsView", parent
            )

            logger.debug("No results widget initialized")

        except Exception as e:
            logger.error(f"Error initializing no results widget: {e}", exc_info=True)
            raise


class NoActivityWidget(EmptyStateWidget):
    """Widget for displaying no activity state."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        message: str = "No Activity Recorded",
        detail: str = "Start using your computer to record activity.",
        action_text: str = "",
    ):
        """Initialize no activity widget."""
        try:
            super().__init__(message, detail, action_text, "SP_ComputerIcon", parent)

            logger.debug("No activity widget initialized")

        except Exception as e:
            logger.error(f"Error initializing no activity widget: {e}", exc_info=True)
            raise


class NoStatisticsWidget(EmptyStateWidget):
    """Widget for displaying no statistics state."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        message: str = "No Statistics Available",
        detail: str = "More activity is needed to generate statistics.",
        action_text: str = "",
    ):
        """Initialize no statistics widget."""
        try:
            super().__init__(
                message, detail, action_text, "SP_TitleBarContextHelpButton", parent
            )

            logger.debug("No statistics widget initialized")

        except Exception as e:
            logger.error(f"Error initializing no statistics widget: {e}", exc_info=True)
            raise


class EmptyChartWidget(EmptyStateWidget):
    """Widget for displaying empty chart state."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        message: str = "No Chart Data",
        detail: str = "There is no data to display in this chart.",
        action_text: str = "",
    ):
        """Initialize empty chart widget."""
        try:
            super().__init__(
                message, detail, action_text, "SP_DialogApplyButton", parent
            )

            logger.debug("Empty chart widget initialized")

        except Exception as e:
            logger.error(f"Error initializing empty chart widget: {e}", exc_info=True)
            raise


class EmptyTableWidget(EmptyStateWidget):
    """Widget for displaying empty table state."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        message: str = "No Table Data",
        detail: str = "There are no entries to display in this table.",
        action_text: str = "",
    ):
        """Initialize empty table widget."""
        try:
            super().__init__(
                message, detail, action_text, "SP_DialogApplyButton", parent
            )

            logger.debug("Empty table widget initialized")

        except Exception as e:
            logger.error(f"Error initializing empty table widget: {e}", exc_info=True)
            raise
