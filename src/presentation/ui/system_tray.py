"""System tray application."""

from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication, QMessageBox, QWidget
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Qt, QTimer, QObject
import logging
import sys
import os

from .dashboard import Dashboard
from .utils.service_connector import ServiceConnector

logger = logging.getLogger(__name__)


class SystemTrayApp(QObject):
    """System tray application."""

    def __init__(self, service_connector: ServiceConnector, parent: QWidget = None):
        """Initialize system tray application.

        Args:
            service_connector: Service connector instance
            parent: Parent widget
        """
        try:
            super().__init__(parent)
            logger.info("Initializing system tray application...")

            self.service_connector = service_connector
            self.dashboard = None
            self.setup_ui()

            # Show dashboard after a delay
            QTimer.singleShot(2000, self._show_dashboard)

        except Exception as e:
            logger.error(f"Error initializing system tray: {e}", exc_info=True)
            QMessageBox.critical(
                None, "Error", f"Failed to initialize system tray: {str(e)}"
            )
            raise

    def setup_ui(self):
        """Set up the system tray UI."""
        try:
            logger.info("Setting up system tray UI...")

            # Create system tray icon
            if not QSystemTrayIcon.isSystemTrayAvailable():
                raise RuntimeError("System tray is not available")

            self.tray_icon = QSystemTrayIcon()

            # Set icon with fallback options
            icon_set = False
            try:
                # Try custom icon
                icon_path = os.path.join("assets", "icons", "tray_icon.png")
                if os.path.exists(icon_path):
                    self.tray_icon.setIcon(QIcon(icon_path))
                    icon_set = True
                    logger.info("Using custom icon")
            except Exception as e:
                logger.warning(f"Error setting custom icon: {e}")

            if not icon_set:
                try:
                    # Try system theme icon
                    theme_icon = QIcon.fromTheme("computer")
                    if not theme_icon.isNull():
                        self.tray_icon.setIcon(theme_icon)
                        icon_set = True
                        logger.info("Using system theme icon")
                except Exception as e:
                    logger.warning(f"Error setting theme icon: {e}")

            if not icon_set:
                # Create a simple default icon
                from PySide6.QtGui import QPixmap, QPainter, QColor

                pixmap = QPixmap(32, 32)
                pixmap.fill(QColor(0, 0, 0, 0))
                painter = QPainter(pixmap)
                painter.setPen(QColor(0, 120, 215))  # Windows blue color
                painter.setBrush(QColor(0, 120, 215))
                painter.drawEllipse(4, 4, 24, 24)
                painter.end()
                self.tray_icon.setIcon(QIcon(pixmap))
                logger.info("Using fallback icon")

            # Create tray menu
            tray_menu = QMenu()

            # Add menu items
            show_action = QAction("Show Dashboard", self)
            show_action.triggered.connect(self._show_dashboard)
            tray_menu.addAction(show_action)

            quit_action = QAction("Quit", self)
            quit_action.triggered.connect(self._quit_application)
            tray_menu.addAction(quit_action)

            # Set menu
            self.tray_icon.setContextMenu(tray_menu)

            # Connect activation signal (single click)
            self.tray_icon.activated.connect(self._handle_tray_activation)

            # Show tray icon
            self.tray_icon.show()

            # Show startup notification
            self.tray_icon.showMessage(
                "AI Work Assistant",
                "Application is running in the background",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )

            logger.info("System tray UI setup complete")
            logger.info("System tray icon is visible")

        except Exception as e:
            logger.error(f"Error setting up system tray UI: {e}", exc_info=True)
            raise

    def _show_dashboard(self):
        """Show the dashboard window."""
        try:
            logger.info("Attempting to show dashboard...")

            if not self.dashboard:
                logger.info("Creating new dashboard instance...")
                try:
                    self.dashboard = Dashboard(service_connector=self.service_connector)
                    logger.info("Dashboard instance created successfully")
                except Exception as e:
                    logger.error(
                        f"Error creating dashboard instance: {e}", exc_info=True
                    )
                    QMessageBox.critical(
                        None, "Error", f"Failed to create dashboard: {str(e)}"
                    )
                    return

            # Show and activate window
            try:
                self.dashboard.show()
                self.dashboard.raise_()
                self.dashboard.activateWindow()
                logger.info("Dashboard shown successfully")
            except Exception as e:
                logger.error(f"Error showing dashboard window: {e}", exc_info=True)
                QMessageBox.critical(
                    None, "Error", f"Failed to show dashboard window: {str(e)}"
                )

        except Exception as e:
            logger.error(f"Error in _show_dashboard: {e}", exc_info=True)
            QMessageBox.critical(
                None, "Error", "Failed to open dashboard. Please try again."
            )

    def _handle_tray_activation(self, reason):
        """Handle tray icon activation."""
        try:
            if reason in [
                QSystemTrayIcon.ActivationReason.Trigger,  # Single click
                QSystemTrayIcon.ActivationReason.DoubleClick,  # Double click
            ]:
                self._show_dashboard()
        except Exception as e:
            logger.error(f"Error handling tray activation: {e}", exc_info=True)

    def _quit_application(self):
        """Quit the application."""
        try:
            # Ask for confirmation
            reply = QMessageBox.question(
                None,
                "Confirm Exit",
                "Are you sure you want to exit AI Work Assistant?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                logger.info("User confirmed application exit")

                # Close dashboard if open
                if self.dashboard:
                    try:
                        self.dashboard.close()
                        logger.info("Dashboard closed")
                    except Exception as e:
                        logger.error(f"Error closing dashboard: {e}", exc_info=True)

                # Hide tray icon
                self.tray_icon.hide()
                logger.info("System tray icon hidden")

                # Quit application
                QApplication.quit()
                logger.info("Application quit requested")
            else:
                logger.info("User cancelled application exit")

        except Exception as e:
            logger.error(f"Error quitting application: {e}", exc_info=True)
            QMessageBox.critical(
                None, "Error", "Failed to quit properly. Force closing."
            )
            sys.exit(1)
