"""Analytics dashboard for visualizing productivity data."""

import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
from PyQt6.QtCore import (
    Qt,
    QTimer,
    pyqtSlot,
    QSortFilterProxyModel,
    QAbstractTableModel,
    pyqtSignal,
    QSettings,
    QThread,
    QModelIndex,
)
from PyQt6.QtGui import QColor, QPainter, QStandardItemModel, QStandardItem
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QVBoxLayout,
    QWidget,
    QMessageBox,
    QTableView,
    QTabWidget,
    QTextEdit,
    QScrollArea,
)

# Add the parent directory to Python path to make the src package importable
parent_dir = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from core.services.analytics_service import AnalyticsService
from core.services.session_service import SessionService
from core.services.task_suggestion_service import TaskSuggestionService
from presentation.ui.charts import (
    ActivityBarChart,
    ActivityPieChart,
    ProductivityLineChart,
    TimeHeatmap,
)

logger = logging.getLogger(__name__)


class LogHandler(logging.Handler):
    """Custom logging handler that emits signals for log messages."""

    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

    def emit(self, record):
        msg = self.format(record)
        self.callback(msg, record.levelno)


class ActivityTableModel(QAbstractTableModel):
    """Model for activity data table with sorting support."""

    def __init__(self):
        super().__init__()
        self.activities = []
        self.headers = ["Time", "Application", "Window Title", "Duration", "Status"]
        self._sort_column = 0
        self._sort_order = Qt.SortOrder.AscendingOrder

    def rowCount(self, parent=None):
        return len(self.activities)

    def columnCount(self, parent=None):
        return len(self.headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            activity = self.activities[index.row()]
            column = index.column()

            if column == 0:  # Time
                return activity.get("time", "").strftime("%H:%M:%S")
            elif column == 1:  # Application
                return activity.get("app_name", "")
            elif column == 2:  # Window Title
                return activity.get("window_title", "")
            elif column == 3:  # Duration
                duration = activity.get("duration", 0)
                return f"{duration:.1f}s"
            elif column == 4:  # Status
                return activity.get("status", "")
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if index.column() in [0, 3, 4]:  # Time, Duration, Status
                return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
        ):
            return self.headers[section]
        return None

    def sort(self, column, order=Qt.SortOrder.AscendingOrder):
        """Sort table by given column number."""
        try:
            self.layoutAboutToBeChanged.emit()
            self._sort_column = column
            self._sort_order = order

            if column == 0:  # Time
                self.activities.sort(
                    key=lambda x: x.get("time", datetime.min),
                    reverse=(order == Qt.SortOrder.DescendingOrder),
                )
            elif column == 3:  # Duration
                self.activities.sort(
                    key=lambda x: float(x.get("duration", 0)),
                    reverse=(order == Qt.SortOrder.DescendingOrder),
                )
            else:  # Other columns
                self.activities.sort(
                    key=lambda x: str(
                        self.data(self.index(0, column), Qt.ItemDataRole.DisplayRole)
                    ).lower(),
                    reverse=(order == Qt.SortOrder.DescendingOrder),
                )

            self.layoutChanged.emit()
        except Exception as e:
            logger.error(f"Error sorting activities: {e}")

    def update_activities(self, activities):
        """Update activities with efficient change handling."""
        try:
            if not activities:
                self.beginResetModel()
                self.activities = []
                self.endResetModel()
                return

            # Only update changed rows
            old_count = len(self.activities)
            new_count = len(activities)

            if new_count < old_count:
                self.beginRemoveRows(QModelIndex(), new_count, old_count - 1)
                self.activities = activities
                self.endRemoveRows()
            elif new_count > old_count:
                self.beginInsertRows(QModelIndex(), old_count, new_count - 1)
                self.activities = activities
                self.endInsertRows()
            else:
                self.activities = activities
                self.dataChanged.emit(
                    self.index(0, 0), self.index(new_count - 1, self.columnCount() - 1)
                )

            # Re-sort if needed
            if self._sort_column >= 0:
                self.sort(self._sort_column, self._sort_order)

        except Exception as e:
            logger.error(f"Error updating activities: {e}")
            # Fall back to full reset if update fails
            self.beginResetModel()
            self.activities = activities
            self.endResetModel()


class UpdateWorker(QThread):
    """Worker thread for async data updates."""

    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, analytics_service, time_window):
        """Initialize update worker.

        Args:
            analytics_service: Analytics service instance
            time_window: Time window for report
        """
        super().__init__()
        self.analytics_service = analytics_service
        self.time_window = time_window

    def run(self):
        """Run the worker thread."""
        try:
            self.progress.emit("Fetching analytics data...")
            report = self.analytics_service.get_productivity_report(
                time_window=self.time_window
            )
            self.finished.emit(report)
        except Exception as e:
            logger.error(f"Error in update worker: {e}", exc_info=True)
            self.error.emit(str(e))


class Dashboard(QMainWindow):
    """Analytics dashboard window."""

    # Add signals
    log_signal = pyqtSignal(str, int)
    update_started = pyqtSignal()
    update_finished = pyqtSignal()

    @pyqtSlot()
    def update_data(self) -> None:
        """Update all dashboard data asynchronously."""
        try:
            # Don't start new update if one is already running
            if (
                hasattr(self, "update_worker")
                and self.update_worker
                and self.update_worker.isRunning()
            ):
                logger.debug("Update already in progress, skipping")
                return

            self.update_started.emit()
            self.statusBar().showMessage("Updating data...")

            # Get time range for analytics
            start_time, end_time = self._get_time_range()
            logger.info(
                f"Fetching analytics report for time window: {end_time - start_time}"
            )

            # Create and start worker
            self.update_worker = UpdateWorker(
                self.analytics_service, end_time - start_time
            )
            self.update_worker.finished.connect(self._handle_update_finished)
            self.update_worker.error.connect(self._handle_update_error)
            self.update_worker.progress.connect(self._handle_update_progress)
            self.update_worker.start()

        except Exception as e:
            logger.error(f"Error starting update: {e}", exc_info=True)
            self.statusBar().showMessage("Update failed")
            self.update_finished.emit()

    def __init__(
        self,
        analytics_service: AnalyticsService,
        suggestion_service: TaskSuggestionService,
        session_service: SessionService,
        parent=None,
    ):
        """Initialize dashboard.

        Args:
            analytics_service: Service for analytics
            suggestion_service: Service for task suggestions
            session_service: Service for managing sessions
            parent: Parent widget
        """
        super().__init__(parent)

        # Services
        self.analytics_service = analytics_service
        self.suggestion_service = suggestion_service
        self.session_service = session_service

        # Connect log signal
        self.log_signal.connect(self._handle_log_message_gui)

        # Data
        self.current_report: Optional[Dict] = None
        self.current_suggestions: List[str] = []
        self.current_productivity: float = 0.0

        # Load settings
        self.settings = QSettings("AIWorkAssistant", "Dashboard")
        self.default_settings = {
            "session_timeout": 30,
            "productivity_threshold": 0.7,
            "notification_interval": 60,
            "dark_mode": False,
        }
        self._load_settings()

        # Activity tracking
        self.activity_model = ActivityTableModel()
        self.recent_activities = []

        # Add update worker
        self.update_worker = None

        # Set up UI
        self._setup_ui()

        # Set up update timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_data)
        self.update_timer.start(60000)  # Update every minute

        # Set up log handler
        self.log_handler = LogHandler(self._handle_log_message)
        logging.getLogger().addHandler(self.log_handler)

        # Initial data load
        self.update_data()

        # Set window properties
        self.setWindowTitle("AI Work Assistant Dashboard")
        self.resize(1400, 900)

        # Create status bar
        self.statusBar().showMessage("Ready")

    def _load_settings(self) -> None:
        """Load settings from QSettings."""
        try:
            # Load each setting with proper type conversion
            self.default_settings["session_timeout"] = int(
                self.settings.value(
                    "session_timeout",
                    self.default_settings["session_timeout"],
                    type=int,
                )
            )
            self.default_settings["productivity_threshold"] = float(
                self.settings.value(
                    "productivity_threshold",
                    self.default_settings["productivity_threshold"],
                    type=float,
                )
            )
            self.default_settings["notification_interval"] = int(
                self.settings.value(
                    "notification_interval",
                    self.default_settings["notification_interval"],
                    type=int,
                )
            )
            self.default_settings["dark_mode"] = self.settings.value(
                "dark_mode", self.default_settings["dark_mode"], type=bool
            )

            # Apply theme
            self._apply_theme()

        except Exception as e:
            logger.error(f"Error loading settings: {e}", exc_info=True)
            # Use defaults if loading fails
            self.default_settings = {
                "session_timeout": 30,
                "productivity_threshold": 0.7,
                "notification_interval": 60,
                "dark_mode": False,
            }

    def _handle_log_message(self, message: str, level: int) -> None:
        """Handle incoming log message by emitting signal.

        Args:
            message: Log message
            level: Log level
        """
        self.log_signal.emit(message, level)

    def _handle_log_message_gui(self, message: str, level: int) -> None:
        """Handle log message in GUI thread.

        Args:
            message: Log message
            level: Log level
        """
        try:
            # Check if message should be shown based on current filter
            current_level = getattr(logging, self.log_level_combo.currentText())
            if level >= current_level:
                # Add color based on level
                color = self._get_log_level_color(level)
                self.log_viewer.append(f'<font color="{color}">{message}</font>')
        except Exception as e:
            # Avoid recursive logging here
            print(f"Error handling log message: {e}")

    def _setup_ui(self) -> None:
        """Set up the dashboard UI."""
        try:
            # Create central widget and main layout
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            main_layout = QVBoxLayout()
            central_widget.setLayout(main_layout)

            # Create tab widget
            tab_widget = QTabWidget()
            tab_widget.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            main_layout.addWidget(tab_widget)

            # Overview tab
            overview_tab = QWidget()
            overview_layout = QVBoxLayout()
            overview_tab.setLayout(overview_layout)

            # Top controls layout
            controls_layout = QHBoxLayout()
            controls_layout.setContentsMargins(0, 0, 0, 10)

            # Add session controls
            session_group = QGroupBox("Session Control")
            session_group.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
            )
            session_layout = QGridLayout()
            self._create_session_widget(session_layout)
            session_group.setLayout(session_layout)
            controls_layout.addWidget(session_group)

            # Add settings
            settings_group = QGroupBox("Settings")
            settings_group.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
            )
            settings_layout = QGridLayout()
            self._create_settings_widget(settings_layout)
            settings_group.setLayout(settings_layout)
            controls_layout.addWidget(settings_group)

            # Add time period selector
            period_group = QGroupBox("Time Period")
            period_group.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
            )
            period_layout = QHBoxLayout()
            self.period_combo = QComboBox()
            self.period_combo.addItems(["Today", "Last 7 Days", "Last 30 Days"])
            self.period_combo.currentIndexChanged.connect(self.update_data)
            period_layout.addWidget(self.period_combo)
            period_group.setLayout(period_layout)
            controls_layout.addWidget(period_group)

            # Add controls to overview layout
            overview_layout.addLayout(controls_layout)

            # Create scrollable area for overview content
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            scroll_widget = QWidget()
            scroll_layout = QVBoxLayout()
            scroll_widget.setLayout(scroll_layout)

            # Add overview widgets to scroll area
            self._create_overview_widget(scroll_layout)
            self._create_productivity_widget(scroll_layout)
            self._create_activity_widget(scroll_layout)
            self._create_suggestions_widget(scroll_layout)

            scroll_area.setWidget(scroll_widget)
            overview_layout.addWidget(scroll_area)

            # Activity Log tab
            activity_tab = QWidget()
            activity_layout = QVBoxLayout()
            activity_tab.setLayout(activity_layout)
            self._create_activity_table(activity_layout)

            # Statistics tab
            stats_tab = QWidget()
            stats_layout = QVBoxLayout()  # Changed to QVBoxLayout
            stats_tab.setLayout(stats_layout)
            self._create_statistics_tables(stats_layout)

            # System Log tab
            log_tab = QWidget()
            log_layout = QVBoxLayout()
            log_tab.setLayout(log_layout)
            self._create_log_viewer(log_layout)

            # Add tabs
            tab_widget.addTab(overview_tab, "Overview")
            tab_widget.addTab(activity_tab, "Activity Log")
            tab_widget.addTab(stats_tab, "Statistics")
            tab_widget.addTab(log_tab, "System Log")

            # Set minimum size for better initial appearance
            self.setMinimumSize(800, 600)

            # Store tab widget reference
            self.tab_widget = tab_widget

            # Initial update
            self.update_data()

        except Exception as e:
            logger.error(f"Error setting up UI: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", "Failed to set up dashboard UI")

    def _create_session_widget(self, layout: QGridLayout) -> None:
        """Create session control widget.

        Args:
            layout: Parent layout
        """
        session_group = QGroupBox("Session Control")
        session_layout = QHBoxLayout()

        # Session status
        self.session_status_label = QLabel("No active session")
        session_layout.addWidget(self.session_status_label)

        # Start button
        self.start_session_btn = QPushButton("Start Session")
        self.start_session_btn.clicked.connect(self._start_session)
        session_layout.addWidget(self.start_session_btn)

        # End button
        self.end_session_btn = QPushButton("End Session")
        self.end_session_btn.clicked.connect(self._end_session)
        self.end_session_btn.setEnabled(False)
        session_layout.addWidget(self.end_session_btn)

        session_group.setLayout(session_layout)
        layout.addWidget(session_group, 0, 0, 1, 2)

    def _create_settings_widget(self, layout: QGridLayout) -> None:
        """Create settings widget.

        Args:
            layout: Layout to add settings to
        """
        try:
            # Session timeout
            timeout_label = QLabel("Session Timeout (minutes):")
            self.timeout_spin = QSpinBox()
            self.timeout_spin.setRange(1, 120)
            self.timeout_spin.setValue(
                int(
                    self.settings.value(
                        "session_timeout", self.default_settings["session_timeout"]
                    )
                )
            )
            layout.addWidget(timeout_label, 0, 0)
            layout.addWidget(self.timeout_spin, 0, 1)

            # Productivity threshold
            threshold_label = QLabel("Productivity Threshold:")
            self.threshold_spin = QDoubleSpinBox()
            self.threshold_spin.setRange(0.1, 1.0)
            self.threshold_spin.setSingleStep(0.1)
            self.threshold_spin.setValue(
                float(
                    self.settings.value(
                        "productivity_threshold",
                        self.default_settings["productivity_threshold"],
                    )
                )
            )
            layout.addWidget(threshold_label, 1, 0)
            layout.addWidget(self.threshold_spin, 1, 1)

            # Notification interval
            interval_label = QLabel("Notification Interval (seconds):")
            self.interval_spin = QSpinBox()
            self.interval_spin.setRange(30, 3600)
            self.interval_spin.setValue(
                int(
                    self.settings.value(
                        "notification_interval",
                        self.default_settings["notification_interval"],
                    )
                )
            )
            layout.addWidget(interval_label, 2, 0)
            layout.addWidget(self.interval_spin, 2, 1)

            # Dark mode
            dark_mode_label = QLabel("Dark Mode:")
            self.dark_mode_check = QCheckBox()
            self.dark_mode_check.setChecked(
                self.settings.value(
                    "dark_mode", self.default_settings["dark_mode"], type=bool
                )
            )
            layout.addWidget(dark_mode_label, 3, 0)
            layout.addWidget(self.dark_mode_check, 3, 1)

            # Apply button
            apply_button = QPushButton("Apply Settings")
            apply_button.clicked.connect(self._save_settings)
            layout.addWidget(apply_button, 4, 0, 1, 2)

        except Exception as e:
            logger.error(f"Error creating settings widget: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", "Failed to create settings widget")

    def _save_settings(self) -> None:
        """Save current settings."""
        try:
            # Save settings
            self.settings.setValue("session_timeout", self.timeout_spin.value())
            self.settings.setValue(
                "productivity_threshold", self.threshold_spin.value()
            )
            self.settings.setValue("notification_interval", self.interval_spin.value())
            self.settings.setValue("dark_mode", self.dark_mode_check.isChecked())
            self.settings.sync()  # Ensure settings are written to disk

            # Apply dark mode if needed
            self._apply_theme()

            # Show confirmation
            self.statusBar().showMessage("Settings saved successfully", 3000)

        except Exception as e:
            logger.error(f"Error saving settings: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", "Failed to save settings")

    def _apply_theme(self) -> None:
        """Apply dark/light theme."""
        try:
            if self.settings.value(
                "dark_mode", self.default_settings["dark_mode"], type=bool
            ):
                # Dark theme
                self.setStyleSheet(
                    """
                    QMainWindow, QWidget {
                        background-color: #2b2b2b;
                        color: #ffffff;
                    }
                    QGroupBox {
                        border: 1px solid #555555;
                        margin-top: 0.5em;
                        padding-top: 0.5em;
                    }
                    QGroupBox::title {
                        color: #ffffff;
                    }
                    QTableView {
                        background-color: #3b3b3b;
                        alternate-background-color: #333333;
                        gridline-color: #555555;
                    }
                    QHeaderView::section {
                        background-color: #2b2b2b;
                        color: #ffffff;
                        border: 1px solid #555555;
                    }
                    QPushButton {
                        background-color: #4a4a4a;
                        border: 1px solid #555555;
                        color: #ffffff;
                        padding: 5px;
                    }
                    QPushButton:hover {
                        background-color: #5a5a5a;
                    }
                    QComboBox, QSpinBox, QDoubleSpinBox {
                        background-color: #3b3b3b;
                        color: #ffffff;
                        border: 1px solid #555555;
                    }
                    QScrollBar {
                        background-color: #2b2b2b;
                        border: 1px solid #555555;
                    }
                    QScrollBar::handle {
                        background-color: #4a4a4a;
                    }
                    QScrollBar::add-line, QScrollBar::sub-line {
                        background-color: #2b2b2b;
                    }
                """
                )
            else:
                # Light theme (default)
                self.setStyleSheet("")

        except Exception as e:
            logger.error(f"Error applying theme: {e}", exc_info=True)
            self.setStyleSheet("")  # Fallback to default theme

    @pyqtSlot()
    def _start_session(self) -> None:
        """Start a new work session."""
        try:
            session_id = self.session_service.start_session()
            if session_id:
                self.start_session_btn.setEnabled(False)
                self.end_session_btn.setEnabled(True)
                self.session_status_label.setText(f"Session active (ID: {session_id})")
                self.update_data()  # Refresh data immediately
        except Exception as e:
            logger.error(f"Error starting session: {e}")
            QMessageBox.warning(self, "Error", "Failed to start session")

    @pyqtSlot()
    def _end_session(self) -> None:
        """End the current work session."""
        try:
            self.session_service.end_session()
            self.start_session_btn.setEnabled(True)
            self.end_session_btn.setEnabled(False)
            self.session_status_label.setText("No active session")
            self.update_data()  # Refresh data immediately
        except Exception as e:
            logger.error(f"Error ending session: {e}")
            QMessageBox.warning(self, "Error", "Failed to end session")

    def _create_overview_widget(self, layout: QVBoxLayout) -> None:
        """Create overview section of dashboard.

        Args:
            layout: Layout to add overview to
        """
        try:
            # Create overview group
            overview_group = QGroupBox("Overview")
            overview_group.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            overview_layout = QGridLayout()
            overview_group.setLayout(overview_layout)

            # Time Period section
            time_group = QGroupBox("Time Period")
            time_group.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            time_layout = QGridLayout()

            # Current time period
            time_layout.addWidget(QLabel("Current Period:"), 0, 0)
            self.current_period_label = QLabel("Today")
            time_layout.addWidget(self.current_period_label, 0, 1)

            # Start time
            time_layout.addWidget(QLabel("Start Time:"), 1, 0)
            self.start_time_label = QLabel("--")
            time_layout.addWidget(self.start_time_label, 1, 1)

            # End time
            time_layout.addWidget(QLabel("End Time:"), 2, 0)
            self.end_time_label = QLabel("--")
            time_layout.addWidget(self.end_time_label, 2, 1)

            time_group.setLayout(time_layout)
            overview_layout.addWidget(time_group, 0, 0)

            # Time Statistics section
            stats_group = QGroupBox("Time Statistics")
            stats_group.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            stats_layout = QGridLayout()

            # Total time
            stats_layout.addWidget(QLabel("Total Time:"), 0, 0)
            self.total_time_label = QLabel("0:00:00")
            stats_layout.addWidget(self.total_time_label, 0, 1)

            # Active time
            stats_layout.addWidget(QLabel("Active Time:"), 1, 0)
            self.active_time_label = QLabel("0:00:00")
            stats_layout.addWidget(self.active_time_label, 1, 1)

            # Idle time
            stats_layout.addWidget(QLabel("Idle Time:"), 2, 0)
            self.idle_time_label = QLabel("0:00:00")
            stats_layout.addWidget(self.idle_time_label, 2, 1)

            stats_group.setLayout(stats_layout)
            overview_layout.addWidget(stats_group, 0, 1)

            # Activity Statistics section
            activity_group = QGroupBox("Activity Statistics")
            activity_group.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            activity_layout = QGridLayout()

            # Productivity score
            activity_layout.addWidget(QLabel("Productivity Score:"), 0, 0)
            self.productivity_score_label = QLabel("0%")
            activity_layout.addWidget(self.productivity_score_label, 0, 1)

            # Active applications
            activity_layout.addWidget(QLabel("Active Applications:"), 1, 0)
            self.active_apps_label = QLabel("0")
            activity_layout.addWidget(self.active_apps_label, 1, 1)

            # Activity categories
            activity_layout.addWidget(QLabel("Activity Categories:"), 2, 0)
            self.categories_label = QLabel("0")
            activity_layout.addWidget(self.categories_label, 2, 1)

            activity_group.setLayout(activity_layout)
            overview_layout.addWidget(activity_group, 0, 2)

            # Add overview group to main layout
            layout.addWidget(overview_group)

        except Exception as e:
            logger.error(f"Error creating overview widget: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", "Failed to create overview widget")

    def _create_productivity_widget(self, layout: QVBoxLayout) -> None:
        """Create productivity widget.

        Args:
            layout: Layout to add widget to
        """
        try:
            # Create productivity group
            productivity_group = QGroupBox("Productivity")
            productivity_group.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            productivity_layout = QVBoxLayout()
            productivity_group.setLayout(productivity_layout)

            # Add productivity chart
            self.productivity_chart = ProductivityLineChart()
            self.productivity_chart.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            self.productivity_chart.setMinimumHeight(200)
            productivity_layout.addWidget(self.productivity_chart)

            # Add time heatmap
            self.time_heatmap = TimeHeatmap()
            self.time_heatmap.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            self.time_heatmap.setMinimumHeight(200)
            productivity_layout.addWidget(self.time_heatmap)

            # Add to main layout
            layout.addWidget(productivity_group)

        except Exception as e:
            logger.error(f"Error creating productivity widget: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", "Failed to create productivity widget")

    def _create_activity_widget(self, layout: QVBoxLayout) -> None:
        """Create activity widget.

        Args:
            layout: Layout to add widget to
        """
        try:
            # Create activity group
            activity_group = QGroupBox("Recent Activities")
            activity_group.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            activity_layout = QVBoxLayout()
            activity_group.setLayout(activity_layout)

            # Create table view
            table_view = QTableView()
            table_view.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            table_view.setMinimumHeight(200)
            table_view.setModel(self.activity_model)
            table_view.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.ResizeToContents
            )
            table_view.setAlternatingRowColors(True)
            activity_layout.addWidget(table_view)

            # Add to main layout
            layout.addWidget(activity_group)

        except Exception as e:
            logger.error(f"Error creating activity widget: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", "Failed to create activity widget")

    def _create_suggestions_widget(self, layout: QVBoxLayout) -> None:
        """Create suggestions widget.

        Args:
            layout: Layout to add widget to
        """
        try:
            # Create suggestions group
            suggestions_group = QGroupBox("Task Suggestions")
            suggestions_group.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            suggestions_layout = QVBoxLayout()
            suggestions_group.setLayout(suggestions_layout)

            # Create suggestions scroll area
            suggestions_scroll = QScrollArea()
            suggestions_scroll.setWidgetResizable(True)
            suggestions_scroll.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
            suggestions_scroll.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
            suggestions_scroll.setMinimumHeight(300)  # Set minimum height

            # Create suggestions container
            suggestions_container = QWidget()
            self.suggestions_layout = QVBoxLayout()
            suggestions_container.setLayout(self.suggestions_layout)
            suggestions_scroll.setWidget(suggestions_container)

            # Add scroll area to suggestions group
            suggestions_layout.addWidget(suggestions_scroll)

            # Add suggestions group to main layout
            layout.addWidget(suggestions_group)

        except Exception as e:
            logger.error(f"Error creating suggestions widget: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", "Failed to create suggestions widget")

    def _create_suggestion_widget(self, suggestion: str, priority: float) -> QWidget:
        """Create a widget for a single suggestion.

        Args:
            suggestion: Suggestion text
            priority: Suggestion priority (0-1)

        Returns:
            QWidget: Suggestion widget
        """
        try:
            # Create container widget
            container = QWidget()
            container.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            container_layout = QHBoxLayout()
            container.setLayout(container_layout)

            # Add suggestion text
            text_label = QLabel(suggestion)
            text_label.setWordWrap(True)
            text_label.setStyleSheet(f"color: {self._get_priority_color(priority)}")
            container_layout.addWidget(text_label, stretch=1)

            # Add feedback buttons
            accept_btn = QPushButton("✓")
            accept_btn.setFixedSize(24, 24)
            accept_btn.clicked.connect(
                lambda: self._handle_suggestion_feedback(suggestion, True)
            )
            container_layout.addWidget(accept_btn)

            reject_btn = QPushButton("✗")
            reject_btn.setFixedSize(24, 24)
            reject_btn.clicked.connect(
                lambda: self._handle_suggestion_feedback(suggestion, False)
            )
            container_layout.addWidget(reject_btn)

            return container

        except Exception as e:
            logger.error(f"Error creating suggestion widget: {e}", exc_info=True)
            return QWidget()  # Return empty widget on error

    def _get_priority_color(self, priority: float) -> str:
        """Get color for suggestion priority.

        Args:
            priority: Priority value (0-1)

        Returns:
            str: Color in hex format
        """
        try:
            if priority >= 0.8:
                return "#F44336"  # Red for high priority
            elif priority >= 0.5:
                return "#FFC107"  # Yellow for medium priority
            else:
                return "#4CAF50"  # Green for low priority
        except Exception as e:
            logger.error(f"Error getting priority color: {e}", exc_info=True)
            return "#000000"  # Black as fallback

    def _handle_suggestion_feedback(self, suggestion: str, accepted: bool) -> None:
        """Handle user feedback on suggestions.

        Args:
            suggestion: Suggestion text
            accepted: Whether suggestion was accepted
        """
        try:
            # Log feedback
            logger.info(
                f"Suggestion feedback - {'Accepted' if accepted else 'Rejected'}: {suggestion}"
            )

            # Update suggestions
            self._update_suggestions()

            # Show feedback message
            self.statusBar().showMessage(
                f"Suggestion {'accepted' if accepted else 'rejected'}", 3000
            )

        except Exception as e:
            logger.error(f"Error handling suggestion feedback: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", "Failed to process suggestion feedback")

    def _clear_layout(self, layout) -> None:
        """Recursively clear a layout and its children.

        Args:
            layout: Layout to clear
        """
        if layout is None:
            return

        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
                item.layout().deleteLater()

    def _update_suggestions(self) -> None:
        """Update task suggestions."""
        try:
            # Clear existing suggestions
            self._clear_layout(self.suggestions_layout)

            # Get new suggestions
            suggestions = self.suggestion_service.get_current_suggestions(
                time_window=self._get_time_range()[1] - self._get_time_range()[0]
            )

            # Add new suggestions
            if suggestions:
                for i, suggestion in enumerate(suggestions):
                    # Calculate priority based on position (higher priority for first suggestions)
                    priority = 1.0 - (i / len(suggestions))
                    suggestion_widget = self._create_suggestion_widget(
                        suggestion, priority
                    )
                    self.suggestions_layout.addWidget(suggestion_widget)
            else:
                # Add placeholder when no suggestions
                placeholder = QLabel("No suggestions available")
                placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.suggestions_layout.addWidget(placeholder)

        except Exception as e:
            logger.error(f"Error updating suggestions: {e}", exc_info=True)
            # Add error message
            error_label = QLabel("Error loading suggestions")
            error_label.setStyleSheet("color: red")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.suggestions_layout.addWidget(error_label)

    def _format_time(self, seconds: float) -> str:
        """Format time in seconds to hours and minutes with validation.

        Args:
            seconds: Time in seconds

        Returns:
            str: Formatted time string
        """
        try:
            seconds = float(seconds)  # Convert to float
            if seconds < 0:
                logger.warning(f"Negative time value: {seconds}, using 0")
                return "0h 0m"
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
        except (TypeError, ValueError) as e:
            logger.error(f"Invalid time value: {seconds} - {e}")
            return "0h 0m"

    def _validate_report_data(self, report: Dict) -> bool:
        """Validate analytics report data.

        Args:
            report: Analytics report dictionary

        Returns:
            bool: True if data is valid
        """
        try:
            if not isinstance(report, dict):
                logger.error(f"Invalid report type: {type(report)}")
                return False

            required_keys = [
                "daily_metrics",
                "app_patterns",
                "productivity_trends",
                "activities",
            ]
            missing_keys = [key for key in required_keys if key not in report]
            if missing_keys:
                logger.error(f"Missing required keys in report: {missing_keys}")
                return False

            # Validate daily metrics
            daily_metrics = report.get("daily_metrics", {})
            if not isinstance(daily_metrics, dict):
                logger.error(f"Invalid daily_metrics type: {type(daily_metrics)}")
                return False

            required_metrics = ["total_time", "active_time", "idle_time"]
            missing_metrics = [
                key for key in required_metrics if key not in daily_metrics
            ]
            if missing_metrics:
                logger.error(f"Missing required metrics: {missing_metrics}")
                return False

            for key in required_metrics:
                if not isinstance(daily_metrics[key], (int, float)):
                    logger.error(
                        f"Invalid metric type for {key}: {type(daily_metrics[key])}"
                    )
                    return False

            # Validate app patterns
            app_patterns = report.get("app_patterns", {})
            if not isinstance(app_patterns, dict):
                logger.error(f"Invalid app_patterns type: {type(app_patterns)}")
                return False

            for app_name, stats in app_patterns.items():
                if not isinstance(stats, dict):
                    logger.error(f"Invalid stats type for {app_name}: {type(stats)}")
                    return False
                required_stats = [
                    "total_time",
                    "active_time",
                    "idle_time",
                    "usage_percentage",
                ]
                missing_stats = [key for key in required_stats if key not in stats]
                if missing_stats:
                    logger.error(
                        f"Missing required stats for {app_name}: {missing_stats}"
                    )
                    return False

            # Validate productivity trends
            trends = report.get("productivity_trends", {})
            if not isinstance(trends, dict):
                logger.error(f"Invalid trends type: {type(trends)}")
                return False

            hourly = trends.get("hourly", [])
            daily = trends.get("daily", [])
            if not isinstance(hourly, list) or not isinstance(daily, list):
                logger.error("Invalid trends data structure")
                return False

            if len(hourly) != 24:
                logger.error(f"Invalid hourly trends length: {len(hourly)}")
                return False
            if len(daily) != 7:
                logger.error(f"Invalid daily trends length: {len(daily)}")
                return False

            # Validate activities
            activities = report.get("activities", [])
            if not isinstance(activities, list):
                logger.error(f"Invalid activities type: {type(activities)}")
                return False

            for activity in activities:
                if not isinstance(activity, dict):
                    logger.error(f"Invalid activity type: {type(activity)}")
                    return False
                required_activity_keys = [
                    "start_time",
                    "app_name",
                    "window_title",
                    "duration",
                    "active_time",
                    "idle_time",
                ]
                missing_activity_keys = [
                    key for key in required_activity_keys if key not in activity
                ]
                if missing_activity_keys:
                    logger.error(
                        f"Missing required keys in activity: {missing_activity_keys}"
                    )
                    return False

            return True

        except Exception as e:
            logger.error(f"Error validating report data: {e}", exc_info=True)
            return False

    def _get_time_range(self) -> Tuple[datetime, datetime]:
        """Get selected time range.

        Returns:
            tuple: Start and end time
        """
        end_time = datetime.now()

        if self.period_combo.currentText() == "Today":
            start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
        elif self.period_combo.currentText() == "Last 7 Days":
            start_time = end_time - timedelta(days=7)
        else:  # Last 30 Days
            start_time = end_time - timedelta(days=30)

        return start_time, end_time

    def _handle_update_finished(self, report: Dict) -> None:
        """Handle completion of async update with validation.

        Args:
            report: Analytics report data
        """
        try:
            logger.info("Received analytics update")

            # Validate report data
            if not self._validate_report_data(report):
                logger.error("Invalid report data received")
                self.statusBar().showMessage(
                    "Failed to update dashboard - invalid data"
                )
                return

            # Store report
            self.current_report = report

            # Update UI components
            self._update_ui_components()

            # Update activity table
            activities = []
            for activity in report.get("activities", []):
                if isinstance(activity, dict):
                    activities.append(
                        {
                            "time": activity.get("start_time"),
                            "app_name": activity.get("app_name", "Unknown"),
                            "window_title": activity.get("window_title", ""),
                            "duration": activity.get("duration", 0),
                            "status": "Active"
                            if activity.get("active_time", 0) > 0
                            else "Idle",
                        }
                    )
            self.activity_model.update_activities(activities)

            # Get suggestions
            try:
                suggestions = self.suggestion_service.get_current_suggestions(
                    time_window=self._get_time_range()[1] - self._get_time_range()[0]
                )
                self._update_suggestions()
            except Exception as e:
                logger.error(f"Error updating suggestions: {e}", exc_info=True)

            # Update status
            self.statusBar().showMessage("Dashboard updated successfully", 3000)
            self.update_finished.emit()

        except Exception as e:
            logger.error(f"Error handling update completion: {e}", exc_info=True)
            self.statusBar().showMessage("Failed to update dashboard")
            self.update_finished.emit()

    def _handle_update_error(self, error_msg: str) -> None:
        """Handle error in async update.

        Args:
            error_msg: Error message
        """
        logger.error(f"Update error: {error_msg}")
        self.statusBar().showMessage(f"Update failed: {error_msg}", 5000)
        QMessageBox.warning(self, "Error", f"Failed to update data: {error_msg}")
        self.update_finished.emit()

        # Clean up worker
        if self.update_worker:
            self.update_worker.deleteLater()
            self.update_worker = None

    def _handle_update_progress(self, message: str) -> None:
        """Handle progress update from worker.

        Args:
            message: Progress message
        """
        self.statusBar().showMessage(message)

    def _update_ui_components(self) -> None:
        """Update all UI components with current data."""
        try:
            if not self.current_report:
                return

            # Update statistics tables
            self._update_statistics_tables()

            # Update charts
            self._update_productivity_chart()
            self._update_time_heatmap()
            self._update_activity_charts()

            # Update time period
            start_time, end_time = self._get_time_range()
            self.current_period_label.setText(self.period_combo.currentText())
            self.start_time_label.setText(start_time.strftime("%Y-%m-%d %H:%M"))
            self.end_time_label.setText(end_time.strftime("%Y-%m-%d %H:%M"))

        except Exception as e:
            logger.error(f"Error updating UI components: {e}", exc_info=True)
            raise  # Re-raise to be caught by caller

    def _update_productivity_chart(self) -> None:
        """Update productivity chart with data validation."""
        try:
            trends = self.current_report.get("productivity_trends", {})
            daily_trends = trends.get("daily", [])

            if not daily_trends:
                logger.warning("No daily trends data available")
                return

            # Validate and normalize data
            if not all(isinstance(x, (int, float)) for x in daily_trends):
                logger.error("Invalid data type in daily trends")
                return

            normalized_trends = [max(0.0, min(1.0, float(x))) for x in daily_trends]
            self.productivity_chart.update_data(normalized_trends)

        except Exception as e:
            logger.error(f"Error updating productivity chart: {e}", exc_info=True)

    def _update_time_heatmap(self) -> None:
        """Update time heatmap with data validation."""
        try:
            trends = self.current_report.get("productivity_trends", {})
            hourly_trends = trends.get("hourly", [])

            if not hourly_trends:
                logger.warning("No hourly trends data available")
                return

            # Validate data length
            if len(hourly_trends) != 24:
                logger.error(f"Invalid hourly trends length: {len(hourly_trends)}")
                return

            # Validate and normalize data
            if not all(isinstance(x, (int, float)) for x in hourly_trends):
                logger.error("Invalid data type in hourly trends")
                return

            data = np.zeros((7, 24))  # days x hours
            for hour, productivity in enumerate(hourly_trends):
                normalized_value = max(0.0, min(1.0, float(productivity)))
                for day in range(7):
                    data[day, hour] = normalized_value

            self.time_heatmap.update_data(data)

        except Exception as e:
            logger.error(f"Error updating time heatmap: {e}", exc_info=True)

    def _update_activity_charts(self) -> None:
        """Update activity-related charts."""
        try:
            if not self.current_report:
                return

            # Update activity table
            activities = []
            for activity in self.current_report.get("activities", []):
                if isinstance(activity, dict):
                    activities.append(
                        {
                            "time": activity.get("start_time"),
                            "app_name": activity.get("app_name", "Unknown"),
                            "window_title": activity.get("window_title", ""),
                            "duration": activity.get("duration", 0),
                            "status": "Active"
                            if activity.get("active_time", 0) > 0
                            else "Idle",
                        }
                    )
            self.activity_model.update_activities(activities)

        except Exception as e:
            logger.error(f"Error updating activity charts: {e}", exc_info=True)

    def _update_statistics_tables(self) -> None:
        """Update statistics tables with current data."""
        try:
            if not self.current_report:
                return

            # Get daily metrics
            daily_metrics = self.current_report.get("daily_metrics", {})
            total_time, active_time, idle_time = self._calculate_time_metrics(
                daily_metrics
            )

            # Update time statistics
            self.total_time_label.setText(
                f"Total Time: {self._format_time(total_time)}"
            )
            self.active_time_label.setText(
                f"Active Time: {self._format_time(active_time)}"
            )
            self.idle_time_label.setText(f"Idle Time: {self._format_time(idle_time)}")

            # Calculate and update productivity score
            productivity_score = (
                (active_time / total_time * 100) if total_time > 0 else 0.0
            )
            self.productivity_score_label.setText(f"{productivity_score:.1f}%")

            # Update application statistics
            self.app_stats_model.setRowCount(0)
            app_patterns = self.current_report.get("app_patterns", {})
            for app_name, stats in app_patterns.items():
                total_time = stats.get("total_time", 0)
                usage_percentage = stats.get("usage_percentage", 0)

                row = [
                    QStandardItem(app_name),
                    QStandardItem(self._format_time(total_time)),
                    QStandardItem(f"{usage_percentage:.1%}"),
                ]
                self.app_stats_model.appendRow(row)

            # Update category statistics
            self.category_stats_model.setRowCount(0)
            category_patterns = self.current_report.get("category_patterns", {})
            for category_name, stats in category_patterns.items():
                total_time = stats.get("total_time", 0)
                usage_percentage = stats.get("usage_percentage", 0)

                row = [
                    QStandardItem(category_name),
                    QStandardItem(self._format_time(total_time)),
                    QStandardItem(f"{usage_percentage:.1%}"),
                ]
                self.category_stats_model.appendRow(row)

            # Update hourly statistics
            self.hourly_stats_model.setRowCount(0)
            hourly_trends = self.current_report.get("productivity_trends", {}).get(
                "hourly", []
            )
            for hour, productivity in enumerate(hourly_trends):
                row = [
                    QStandardItem(f"{hour:02d}:00"),
                    QStandardItem(self._format_time(3600)),  # 1 hour in seconds
                    QStandardItem(f"{productivity:.1%}"),
                ]
                self.hourly_stats_model.appendRow(row)

            # Update overview counts
            self.active_apps_label.setText(str(len(app_patterns)))
            self.categories_label.setText(str(len(category_patterns)))

            # Update time period labels
            start_time, end_time = self._get_time_range()
            self.current_period_label.setText(self.period_combo.currentText())
            self.start_time_label.setText(start_time.strftime("%Y-%m-%d %H:%M"))
            self.end_time_label.setText(end_time.strftime("%Y-%m-%d %H:%M"))

        except Exception as e:
            logger.error(f"Error updating statistics tables: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", "Failed to update statistics")

    def _create_activity_table(self, layout: QVBoxLayout) -> None:
        """Create activity log table with sorting support.

        Args:
            layout: Parent layout
        """
        # Create table view
        table_view = QTableView()

        # Add proxy model for sorting
        proxy_model = QSortFilterProxyModel()
        proxy_model.setSourceModel(self.activity_model)
        table_view.setModel(proxy_model)

        # Enable sorting
        table_view.setSortingEnabled(True)
        table_view.horizontalHeader().setSectionsClickable(True)

        # Configure columns
        header = table_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )  # Window Title column

        # Style
        table_view.setAlternatingRowColors(True)
        table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)

        # Add to layout
        layout.addWidget(table_view)

    def _create_statistics_tables(self, layout: QVBoxLayout) -> None:
        """Create statistics tables.

        Args:
            layout: Layout to add tables to
        """
        try:
            # Create statistics group boxes
            time_stats_group = QGroupBox("Time Statistics")
            time_stats_group.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            time_stats_layout = QVBoxLayout()
            time_stats_group.setLayout(time_stats_layout)

            # Time statistics labels
            self.total_time_label = QLabel("Total Time: 0:00:00")
            self.active_time_label = QLabel("Active Time: 0:00:00")
            self.idle_time_label = QLabel("Idle Time: 0:00:00")
            self.productivity_score_label = QLabel("Productivity Score: 0%")

            # Add labels to time stats layout
            time_stats_layout.addWidget(self.total_time_label)
            time_stats_layout.addWidget(self.active_time_label)
            time_stats_layout.addWidget(self.idle_time_label)
            time_stats_layout.addWidget(self.productivity_score_label)

            # Create tables group box
            tables_group = QGroupBox("Activity Statistics")
            tables_group.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            tables_layout = QVBoxLayout()  # Changed to QVBoxLayout
            tables_group.setLayout(tables_layout)

            # Application statistics
            app_stats_label = QLabel("Top Applications")
            self.app_stats_model = QStandardItemModel()
            self.app_stats_model.setHorizontalHeaderLabels(
                ["Application", "Time", "Percentage"]
            )
            app_stats_view = QTableView()
            app_stats_view.setModel(self.app_stats_model)
            app_stats_view.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            app_stats_view.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.ResizeToContents
            )
            app_stats_view.setAlternatingRowColors(True)
            tables_layout.addWidget(app_stats_label)
            tables_layout.addWidget(app_stats_view)

            # Category statistics
            cat_stats_label = QLabel("Top Categories")
            self.category_stats_model = QStandardItemModel()
            self.category_stats_model.setHorizontalHeaderLabels(
                ["Category", "Time", "Percentage"]
            )
            category_stats_view = QTableView()
            category_stats_view.setModel(self.category_stats_model)
            category_stats_view.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            category_stats_view.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.ResizeToContents
            )
            category_stats_view.setAlternatingRowColors(True)
            tables_layout.addWidget(cat_stats_label)
            tables_layout.addWidget(category_stats_view)

            # Hourly statistics
            hour_stats_label = QLabel("Hourly Distribution")
            self.hourly_stats_model = QStandardItemModel()
            self.hourly_stats_model.setHorizontalHeaderLabels(
                ["Hour", "Time", "Percentage"]
            )
            hourly_stats_view = QTableView()
            hourly_stats_view.setModel(self.hourly_stats_model)
            hourly_stats_view.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            hourly_stats_view.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.ResizeToContents
            )
            hourly_stats_view.setAlternatingRowColors(True)
            tables_layout.addWidget(hour_stats_label)
            tables_layout.addWidget(hourly_stats_view)

            # Add groups to main layout
            layout.addWidget(time_stats_group)
            layout.addWidget(tables_group)

        except Exception as e:
            logger.error(f"Error creating statistics tables: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", "Failed to create statistics tables")

    def _create_log_viewer(self, layout: QVBoxLayout) -> None:
        """Create log viewer widget.

        Args:
            layout: Parent layout
        """
        # Log level filter
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Log Level:")
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.log_level_combo.setCurrentText("INFO")
        self.log_level_combo.currentTextChanged.connect(self._filter_logs)
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.log_level_combo)
        filter_layout.addStretch()

        # Clear button
        clear_btn = QPushButton("Clear Logs")
        clear_btn.clicked.connect(self._clear_logs)
        filter_layout.addWidget(clear_btn)

        layout.addLayout(filter_layout)

        # Log viewer
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.log_viewer)

    def _get_log_level_color(self, level: int) -> str:
        """Get color for log level.

        Args:
            level: Log level

        Returns:
            str: Color in hex format
        """
        if level >= logging.CRITICAL:
            return "#ff0000"  # Red
        elif level >= logging.ERROR:
            return "#ff4444"  # Light red
        elif level >= logging.WARNING:
            return "#ffaa00"  # Orange
        elif level >= logging.INFO:
            return "#000000"  # Black
        else:
            return "#666666"  # Gray

    def _filter_logs(self) -> None:
        """Filter log messages based on selected level."""
        self.log_viewer.clear()
        # Re-apply all logs with current filter
        # (This would need storing of all logs, which we'll skip for now)

    def _clear_logs(self) -> None:
        """Clear log viewer."""
        self.log_viewer.clear()

    def closeEvent(self, event) -> None:
        """Handle window close event with proper cleanup."""
        try:
            # Stop and cleanup timer
            if hasattr(self, "update_timer"):
                self.update_timer.stop()
                self.update_timer.deleteLater()

            # Remove log handler
            if hasattr(self, "log_handler"):
                logging.getLogger().removeHandler(self.log_handler)

            # Clean up layouts
            if hasattr(self, "layout"):
                self._clear_layout(self.layout())

            # Clean up worker
            if hasattr(self, "update_worker") and self.update_worker:
                self.update_worker.quit()
                self.update_worker.wait()
                self.update_worker.deleteLater()

            # Save settings
            if hasattr(self, "settings"):
                self.settings.sync()

            # Clean up widgets
            for attr in [
                "period_combo",
                "productivity_chart",
                "time_heatmap",
                "tab_widget",
            ]:
                if hasattr(self, attr):
                    widget = getattr(self, attr)
                    if widget and not widget.isHidden():
                        widget.hide()
                        widget.deleteLater()

            # Accept the event
            event.accept()

        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
            event.accept()  # Still close even if cleanup fails

    def _calculate_time_metrics(
        self, daily_metrics: Dict
    ) -> Tuple[float, float, float]:
        """Calculate time metrics from daily metrics.

        Args:
            daily_metrics: Daily metrics dictionary

        Returns:
            tuple: Total time, active time, idle time
        """
        try:
            total_time = float(daily_metrics.get("total_time", 0))
            active_time = float(daily_metrics.get("active_time", 0))
            idle_time = float(daily_metrics.get("idle_time", 0))

            # Validate values
            if total_time < 0:
                logger.warning("Negative total time, using 0")
                total_time = 0
            if active_time < 0:
                logger.warning("Negative active time, using 0")
                active_time = 0
            if idle_time < 0:
                logger.warning("Negative idle time, using 0")
                idle_time = 0

            # Ensure consistency
            if total_time < active_time + idle_time:
                total_time = active_time + idle_time
                logger.warning("Adjusted total time to match active + idle time")

            return total_time, active_time, idle_time

        except (TypeError, ValueError) as e:
            logger.error(f"Error calculating time metrics: {e}", exc_info=True)
            return 0.0, 0.0, 0.0
