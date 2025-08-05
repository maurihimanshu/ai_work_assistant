"""Settings dialog for configuring application preferences."""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """Dialog for configuring application settings."""

    def __init__(self, config_path: str = "./config/settings.json", parent=None):
        """Initialize settings dialog.

        Args:
            config_path: Path to settings file
            parent: Parent widget
        """
        super().__init__(parent)

        self.config_path = Path(config_path)
        self.settings: Dict = {}

        # Create config directory if it doesn't exist
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Load settings
        self._load_settings()

        # Set up UI
        self._setup_ui()

        # Set window properties
        self.setWindowTitle("Settings")
        self.setMinimumWidth(400)
        self.setModal(True)

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout()

        # Create tab widget
        tab_widget = QTabWidget()

        # General settings tab
        general_tab = QWidget()
        general_layout = QVBoxLayout()

        # Session settings
        session_group = QGroupBox("Session Settings")
        session_layout = QFormLayout()

        self.inactivity_timeout = QSpinBox()
        self.inactivity_timeout.setRange(1, 120)
        self.inactivity_timeout.setValue(
            self.settings.get("session", {}).get("inactivity_timeout", 30)
        )
        self.inactivity_timeout.setSuffix(" minutes")
        session_layout.addRow("Inactivity Timeout:", self.inactivity_timeout)

        self.auto_start_session = QCheckBox()
        self.auto_start_session.setChecked(
            self.settings.get("session", {}).get("auto_start", False)
        )
        session_layout.addRow("Auto-start Session:", self.auto_start_session)

        session_group.setLayout(session_layout)
        general_layout.addWidget(session_group)

        # Notification settings
        notification_group = QGroupBox("Notification Settings")
        notification_layout = QFormLayout()

        self.show_productivity_alerts = QCheckBox()
        self.show_productivity_alerts.setChecked(
            self.settings.get("notifications", {}).get("show_productivity_alerts", True)
        )
        notification_layout.addRow(
            "Show Productivity Alerts:", self.show_productivity_alerts
        )

        self.show_suggestions = QCheckBox()
        self.show_suggestions.setChecked(
            self.settings.get("notifications", {}).get("show_suggestions", True)
        )
        notification_layout.addRow("Show Task Suggestions:", self.show_suggestions)

        self.notification_duration = QSpinBox()
        self.notification_duration.setRange(1, 30)
        self.notification_duration.setValue(
            self.settings.get("notifications", {}).get("duration", 5)
        )
        self.notification_duration.setSuffix(" seconds")
        notification_layout.addRow("Notification Duration:", self.notification_duration)

        notification_group.setLayout(notification_layout)
        general_layout.addWidget(notification_group)

        # Privacy settings
        privacy_group = QGroupBox("Privacy Settings")
        privacy_layout = QFormLayout()

        self.data_retention = QSpinBox()
        self.data_retention.setRange(1, 365)
        self.data_retention.setValue(
            self.settings.get("privacy", {}).get("data_retention_days", 30)
        )
        self.data_retention.setSuffix(" days")
        privacy_layout.addRow("Data Retention Period:", self.data_retention)

        self.collect_app_usage = QCheckBox()
        self.collect_app_usage.setChecked(
            self.settings.get("privacy", {}).get("collect_app_usage", True)
        )
        privacy_layout.addRow("Collect App Usage Data:", self.collect_app_usage)

        self.collect_window_titles = QCheckBox()
        self.collect_window_titles.setChecked(
            self.settings.get("privacy", {}).get("collect_window_titles", False)
        )
        privacy_layout.addRow("Collect Window Titles:", self.collect_window_titles)

        privacy_group.setLayout(privacy_layout)
        general_layout.addWidget(privacy_group)

        general_tab.setLayout(general_layout)
        tab_widget.addTab(general_tab, "General")

        # Analytics settings tab
        analytics_tab = QWidget()
        analytics_layout = QVBoxLayout()

        # Productivity settings
        productivity_group = QGroupBox("Productivity Settings")
        productivity_layout = QFormLayout()

        self.productivity_threshold = QSpinBox()
        self.productivity_threshold.setRange(1, 100)
        self.productivity_threshold.setValue(
            int(self.settings.get("analytics", {}).get("productivity_threshold", 70))
        )
        self.productivity_threshold.setSuffix("%")
        productivity_layout.addRow(
            "Productivity Threshold:", self.productivity_threshold
        )

        self.analysis_window = QSpinBox()
        self.analysis_window.setRange(1, 60)
        self.analysis_window.setValue(
            self.settings.get("analytics", {}).get("analysis_window_days", 7)
        )
        self.analysis_window.setSuffix(" days")
        productivity_layout.addRow("Analysis Window:", self.analysis_window)

        productivity_group.setLayout(productivity_layout)
        analytics_layout.addWidget(productivity_group)

        # ML settings
        ml_group = QGroupBox("Machine Learning Settings")
        ml_layout = QFormLayout()

        self.enable_predictions = QCheckBox()
        self.enable_predictions.setChecked(
            self.settings.get("ml", {}).get("enable_predictions", True)
        )
        ml_layout.addRow("Enable Activity Predictions:", self.enable_predictions)

        self.prediction_confidence = QSpinBox()
        self.prediction_confidence.setRange(1, 100)
        self.prediction_confidence.setValue(
            int(self.settings.get("ml", {}).get("prediction_confidence", 80))
        )
        self.prediction_confidence.setSuffix("%")
        ml_layout.addRow("Prediction Confidence Threshold:", self.prediction_confidence)

        ml_group.setLayout(ml_layout)
        analytics_layout.addWidget(ml_group)

        analytics_tab.setLayout(analytics_layout)
        tab_widget.addTab(analytics_tab, "Analytics")

        layout.addWidget(tab_widget)

        # Buttons
        button_layout = QHBoxLayout()

        save_button = QPushButton("Save")
        save_button.clicked.connect(self._save_settings)
        button_layout.addWidget(save_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _load_settings(self) -> None:
        """Load settings from file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r") as f:
                    self.settings = json.load(f)
            else:
                self._create_default_settings()

        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            self._create_default_settings()

    def _create_default_settings(self) -> None:
        """Create default settings."""
        self.settings = {
            "session": {"inactivity_timeout": 30, "auto_start": False},
            "notifications": {
                "show_productivity_alerts": True,
                "show_suggestions": True,
                "duration": 5,
            },
            "privacy": {
                "data_retention_days": 30,
                "collect_app_usage": True,
                "collect_window_titles": False,
            },
            "analytics": {"productivity_threshold": 70, "analysis_window_days": 7},
            "ml": {"enable_predictions": True, "prediction_confidence": 80},
        }

        self._save_settings()

    def _save_settings(self) -> None:
        """Save settings to file."""
        try:
            # Update settings from UI
            self.settings["session"] = {
                "inactivity_timeout": self.inactivity_timeout.value(),
                "auto_start": self.auto_start_session.isChecked(),
            }

            self.settings["notifications"] = {
                "show_productivity_alerts": (self.show_productivity_alerts.isChecked()),
                "show_suggestions": self.show_suggestions.isChecked(),
                "duration": self.notification_duration.value(),
            }

            self.settings["privacy"] = {
                "data_retention_days": self.data_retention.value(),
                "collect_app_usage": self.collect_app_usage.isChecked(),
                "collect_window_titles": self.collect_window_titles.isChecked(),
            }

            self.settings["analytics"] = {
                "productivity_threshold": self.productivity_threshold.value(),
                "analysis_window_days": self.analysis_window.value(),
            }

            self.settings["ml"] = {
                "enable_predictions": self.enable_predictions.isChecked(),
                "prediction_confidence": self.prediction_confidence.value(),
            }

            # Save to file
            with open(self.config_path, "w") as f:
                json.dump(self.settings, f, indent=2)

            self.accept()

        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            QMessageBox.critical(
                self, "Error", "Failed to save settings. Please try again."
            )

    def get_settings(self) -> Dict:
        """Get current settings.

        Returns:
            dict: Current settings
        """
        return self.settings.copy()


def load_settings(config_path: str = "./config/settings.json") -> Dict:
    """Load settings from file.

    Args:
        config_path: Path to settings file

    Returns:
        dict: Loaded settings
    """
    try:
        config_path = Path(config_path)
        if config_path.exists():
            with open(config_path, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading settings: {e}")

    # Return default settings if loading fails
    return SettingsDialog(config_path=config_path).get_settings()
