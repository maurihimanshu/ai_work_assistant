"""System tray application for the AI Work Assistant."""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Optional

from PyQt6.QtCore import QTimer, Qt, pyqtSlot
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (QApplication, QMenu, QMessageBox, QStyle,
                            QSystemTrayIcon)

from ...core.events.event_dispatcher import EventDispatcher
from ...core.events.event_types import ProductivityAlertEvent, SessionEvent
from ...core.services.analytics_service import AnalyticsService
from ...core.services.session_service import SessionService
from ...core.services.task_suggestion_service import TaskSuggestionService
from .dashboard import Dashboard
from .settings_dialog import SettingsDialog

logger = logging.getLogger(__name__)


class SystemTrayApp(QSystemTrayIcon):
    """System tray application for the AI Work Assistant."""

    def __init__(
        self,
        session_service: SessionService,
        analytics_service: AnalyticsService,
        suggestion_service: TaskSuggestionService,
        event_dispatcher: EventDispatcher,
        icon_path: Optional[str] = None,
        parent=None
    ):
        """Initialize system tray application.

        Args:
            session_service: Service for managing work sessions
            analytics_service: Service for analytics
            suggestion_service: Service for task suggestions
            event_dispatcher: Event dispatcher
            icon_path: Path to tray icon
            parent: Parent widget
        """
        super().__init__(parent)

        # Services
        self.session_service = session_service
        self.analytics_service = analytics_service
        self.suggestion_service = suggestion_service
        self.event_dispatcher = event_dispatcher

        # State
        self.current_session_id: Optional[str] = None
        self.dashboard: Optional[Dashboard] = None
        self.settings_dialog: Optional[SettingsDialog] = None

        # Set up UI
        self._setup_ui(icon_path)
        self._setup_event_handlers()
        self._setup_timers()

        # Show initial message
        self.showMessage(
            "AI Work Assistant",
            "Assistant is running in the background",
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )

    def _setup_ui(self, icon_path: Optional[str]) -> None:
        """Set up system tray UI.

        Args:
            icon_path: Path to tray icon
        """
        # Set icon
        if icon_path and Path(icon_path).exists():
            self.setIcon(QIcon(icon_path))
        else:
            # Use default app icon
            app = QApplication.instance()
            if app:
                self.setIcon(
                    app.style().standardIcon(
                        QStyle.StandardPixmap.SP_ComputerIcon
                    )
                )
            else:
                # Fallback to a simple icon
                self.setIcon(QIcon())

        # Create menu
        menu = QMenu()

        # Session actions
        self.start_session_action = QAction("Start Session", self)
        self.start_session_action.triggered.connect(self._start_session)
        menu.addAction(self.start_session_action)

        self.end_session_action = QAction("End Session", self)
        self.end_session_action.triggered.connect(self._end_session)
        self.end_session_action.setEnabled(False)
        menu.addAction(self.end_session_action)

        menu.addSeparator()

        # Dashboard action
        self.show_dashboard_action = QAction("Show Dashboard", self)
        self.show_dashboard_action.triggered.connect(self._show_dashboard)
        menu.addAction(self.show_dashboard_action)

        # Settings action
        self.show_settings_action = QAction("Settings", self)
        self.show_settings_action.triggered.connect(self._show_settings)
        menu.addAction(self.show_settings_action)

        menu.addSeparator()

        # Quit action
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit_application)
        menu.addAction(quit_action)

        self.setContextMenu(menu)

        # Enable tray icon
        self.setVisible(True)

    def _setup_event_handlers(self) -> None:
        """Set up event handlers."""
        # Subscribe to events
        self.event_dispatcher.subscribe(
            self._handle_productivity_alert,
            "productivity_alert"
        )
        self.event_dispatcher.subscribe(
            self._handle_session_event,
            "session_start"
        )
        self.event_dispatcher.subscribe(
            self._handle_session_event,
            "session_end"
        )

        # Connect tray icon signals
        self.activated.connect(self._handle_tray_activation)
        self.messageClicked.connect(self._handle_message_click)

    def _setup_timers(self) -> None:
        """Set up update timers."""
        # Timer for checking session timeout
        self.session_timer = QTimer(self)
        self.session_timer.timeout.connect(self._check_session_timeout)
        self.session_timer.start(60000)  # Check every minute

        # Timer for updating analytics
        self.analytics_timer = QTimer(self)
        self.analytics_timer.timeout.connect(self._update_analytics)
        self.analytics_timer.start(300000)  # Update every 5 minutes

    @pyqtSlot()
    def _start_session(self) -> None:
        """Start a new work session."""
        try:
            session_id = self.session_service.start_session()
            self.current_session_id = session_id

            # Update UI
            self.start_session_action.setEnabled(False)
            self.end_session_action.setEnabled(True)

            # Show notification
            self.showMessage(
                "Session Started",
                "Work session has been started",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )

        except Exception as e:
            logger.error(f"Error starting session: {e}")
            QMessageBox.critical(
                None,
                "Error",
                "Failed to start session. Please try again."
            )

    @pyqtSlot()
    def _end_session(self) -> None:
        """End current work session."""
        try:
            self.session_service.end_session()
            self.current_session_id = None

            # Update UI
            self.start_session_action.setEnabled(True)
            self.end_session_action.setEnabled(False)

            # Show notification
            self.showMessage(
                "Session Ended",
                "Work session has been ended",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )

        except Exception as e:
            logger.error(f"Error ending session: {e}")
            QMessageBox.critical(
                None,
                "Error",
                "Failed to end session. Please try again."
            )

    @pyqtSlot()
    def _show_dashboard(self) -> None:
        """Show analytics dashboard."""
        try:
            if not self.dashboard:
                self.dashboard = Dashboard(
                    self.analytics_service,
                    self.suggestion_service,
                    self.session_service
                )

            self.dashboard.show()
            self.dashboard.activateWindow()

        except Exception as e:
            logger.error(f"Error showing dashboard: {e}")
            QMessageBox.critical(
                None,
                "Error",
                "Failed to open dashboard. Please try again."
            )

    @pyqtSlot()
    def _show_settings(self) -> None:
        """Show settings dialog."""
        try:
            if not self.settings_dialog:
                self.settings_dialog = SettingsDialog()

            self.settings_dialog.show()
            self.settings_dialog.activateWindow()

        except Exception as e:
            logger.error(f"Error showing settings: {e}")
            QMessageBox.critical(
                None,
                "Error",
                "Failed to open settings. Please try again."
            )

    @pyqtSlot()
    def _quit_application(self) -> None:
        """Quit the application."""
        try:
            # End session if active
            if self.current_session_id:
                self.session_service.end_session()

            # Close windows
            if self.dashboard:
                self.dashboard.close()
            if self.settings_dialog:
                self.settings_dialog.close()

            # Quit application
            QApplication.quit()

        except Exception as e:
            logger.error(f"Error quitting application: {e}")
            QMessageBox.critical(
                None,
                "Error",
                "Failed to quit properly. Force closing."
            )
            sys.exit(1)

    def _handle_productivity_alert(
        self,
        event: ProductivityAlertEvent
    ) -> None:
        """Handle productivity alert events.

        Args:
            event: Productivity alert event
        """
        try:
            # Show notification with suggestions
            message = (
                f"Productivity Score: {event.productivity_score:.2f}\n"
                "Suggestions:\n" +
                "\n".join(f"- {s}" for s in event.suggestions[:3])
            )

            self.showMessage(
                "Productivity Alert",
                message,
                QSystemTrayIcon.MessageIcon.Information,
                5000
            )

        except Exception as e:
            logger.error(f"Error handling productivity alert: {e}")

    def _handle_session_event(self, event: SessionEvent) -> None:
        """Handle session events.

        Args:
            event: Session event
        """
        try:
            # Update UI based on event type
            if event.event_type == "session_start":
                self.current_session_id = event.session_id
                self.start_session_action.setEnabled(False)
                self.end_session_action.setEnabled(True)

            elif event.event_type == "session_end":
                self.current_session_id = None
                self.start_session_action.setEnabled(True)
                self.end_session_action.setEnabled(False)

        except Exception as e:
            logger.error(f"Error handling session event: {e}")

    def _handle_tray_activation(
        self,
        reason: QSystemTrayIcon.ActivationReason
    ) -> None:
        """Handle tray icon activation.

        Args:
            reason: Activation reason
        """
        try:
            if reason == QSystemTrayIcon.ActivationReason.Trigger:
                # Single click - show current status
                if self.current_session_id:
                    suggestions, score = (
                        self.suggestion_service.get_current_suggestions()
                    )
                    message = (
                        f"Current Productivity: {score:.2f}\n"
                        "Suggestions:\n" +
                        "\n".join(f"- {s}" for s in suggestions[:3])
                    )
                else:
                    message = "No active session"

                self.showMessage(
                    "Status",
                    message,
                    QSystemTrayIcon.MessageIcon.Information,
                    3000
                )

            elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
                # Double click - show dashboard
                self._show_dashboard()

        except Exception as e:
            logger.error(f"Error handling tray activation: {e}")

    def _handle_message_click(self) -> None:
        """Handle tray message click."""
        # Show dashboard when notification is clicked
        self._show_dashboard()

    @pyqtSlot()
    def _check_session_timeout(self) -> None:
        """Check for session timeout."""
        try:
            if (
                self.current_session_id and
                self.session_service.check_session_timeout()
            ):
                # Show warning
                self.showMessage(
                    "Session Timeout",
                    "Session has been inactive for too long",
                    QSystemTrayIcon.MessageIcon.Warning,
                    5000
                )

        except Exception as e:
            logger.error(f"Error checking session timeout: {e}")

    @pyqtSlot()
    def _update_analytics(self) -> None:
        """Update analytics data."""
        try:
            if self.current_session_id:
                self.analytics_service.update_analytics()

                # Update dashboard if open
                if self.dashboard and self.dashboard.isVisible():
                    self.dashboard.update_data()

        except Exception as e:
            logger.error(f"Error updating analytics: {e}")


def run_system_tray(
    session_service: SessionService,
    analytics_service: AnalyticsService,
    suggestion_service: TaskSuggestionService,
    event_dispatcher: EventDispatcher,
    icon_path: Optional[str] = None
) -> None:
    """Run the system tray application.

    Args:
        session_service: Service for managing work sessions
        analytics_service: Service for analytics
        suggestion_service: Service for task suggestions
        event_dispatcher: Event dispatcher
        icon_path: Path to tray icon
    """
    try:
        # Create application
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)

        # Create system tray
        tray = SystemTrayApp(
            session_service,
            analytics_service,
            suggestion_service,
            event_dispatcher,
            icon_path,
            parent=app
        )

        # Run application
        sys.exit(app.exec())
    except Exception as e:
        logger.error(f"Error running system tray application: {e}")
        sys.exit(1)