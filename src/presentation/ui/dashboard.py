"""Dashboard window module."""

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QStackedWidget,
    QScrollArea,
    QFrame,
    QSizePolicy,
    QLabel,
    QComboBox,
)
from PySide6.QtCore import (
    Qt,
    QSettings,
    QPropertyAnimation,
    QEasingCurve,
    QPoint,
    QRect,
    QSize,
    QTimer,
)
from PySide6.QtGui import QIcon
from datetime import datetime, timedelta
import logging

from .layouts.overview_layout import OverviewLayout
from .layouts.statistics_layout import StatisticsLayout
from .layouts.activity_log_layout import ActivityLogLayout
from .layouts.system_log_layout import SystemLogLayout
from .layouts.workspace_layout import WorkspaceLayout
from .layouts.configuration_layout import ConfigurationLayout
from .utils.log_handler import QtLogHandler

logger = logging.getLogger(__name__)


class Dashboard(QMainWindow):
    """Main dashboard window."""

    def __init__(self, service_connector, parent=None):
        """Initialize dashboard window."""
        try:
            super().__init__(parent)
            self.service_connector = service_connector

            # Date range selection state (persisted)
            self.settings = QSettings("AIWorkAssistant", "Dashboard")
            self.time_window_key = "time_window_days"  # backwards-compat key
            self.time_range_index_key = "time_range_index"
            saved_index = self.settings.value(self.time_range_index_key, None)
            try:
                saved_index = int(saved_index) if saved_index is not None else None
            except Exception:
                saved_index = None
            # Fallback to days mapping if index not present
            if saved_index is None:
                default_days = int(self.settings.value(self.time_window_key, 1))
                saved_index = {1: 0, 7: 1, 15: 2, 30: 3}.get(default_days, 0)
            self.current_range_index = saved_index
            self.current_time_window = self._compute_time_window_for_index(
                self.current_range_index
            )

            # Window setup
            self.setWindowTitle("AI Work Assistant")
            self.setMinimumSize(1200, 800)

            # Create central widget and main layout
            central_widget = QWidget()
            self.setCentralWidget(central_widget)

            main_layout = QVBoxLayout()
            main_layout.setContentsMargins(12, 12, 12, 12)
            main_layout.setSpacing(12)
            central_widget.setLayout(main_layout)

            # Header bar
            header = QFrame()
            header.setObjectName("headerBar")
            header_layout = QHBoxLayout()
            header_layout.setContentsMargins(12, 8, 12, 8)
            header_layout.setSpacing(8)
            header.setLayout(header_layout)
            title = QLabel("AI Work Assistant")
            title.setObjectName("appTitleLabel")
            self.subtitle_label = QLabel(self._format_current_range_label())
            self.subtitle_label.setObjectName("subtitleLabel")
            header_layout.addWidget(title)
            header_layout.addStretch()
            header_layout.addWidget(self.subtitle_label)

            # Body area: horizontal split with side panel + content
            body = QHBoxLayout()
            body.setContentsMargins(0, 0, 0, 0)
            body.setSpacing(12)

            # Create side panel
            self.side_panel = QFrame()
            self.side_panel.setObjectName("sidePanel")
            self.side_panel.setFixedWidth(220)
            side_layout = QVBoxLayout()
            side_layout.setContentsMargins(12, 16, 12, 16)
            side_layout.setSpacing(10)
            self.side_panel.setLayout(side_layout)

            # Create date range selector
            range_label = QLabel("Date Range")
            range_label.setStyleSheet("color: #9ca3af; padding-left: 4px;")
            self.range_combo = QComboBox()
            self.range_combo.addItems(
                ["Today", "Last 7 days", "Last 15 days", "Last 30 days"]
            )
            # Set initial index from saved selection
            self.range_combo.setCurrentIndex(self.current_range_index)
            self.range_combo.currentIndexChanged.connect(self._on_range_changed)
            side_layout.addWidget(range_label)
            side_layout.addWidget(self.range_combo)

            # Create navigation buttons
            self.nav_buttons = []

            overview_btn = self._create_nav_button("Overview")
            statistics_btn = self._create_nav_button("Statistics")
            activity_btn = self._create_nav_button("Activity Log")
            system_btn = self._create_nav_button("System Log")
            workspace_btn = self._create_nav_button("Workspace")
            config_btn = self._create_nav_button("Configuration")

            side_layout.addWidget(overview_btn)
            side_layout.addWidget(statistics_btn)
            side_layout.addWidget(activity_btn)
            side_layout.addWidget(system_btn)
            side_layout.addWidget(workspace_btn)
            side_layout.addWidget(config_btn)
            side_layout.addStretch()

            # Create stacked widget for content
            self.content_stack = QStackedWidget()

            # Create scroll area
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setWidget(self.content_stack)

            # Add layouts to stack
            self.overview = OverviewLayout()
            # Show current date range in overview header if supported
            try:
                if hasattr(self.overview, "set_header_subtitle"):
                    self.overview.set_header_subtitle(
                        self._format_current_range_label()
                    )
            except Exception:
                pass
            self.statistics = StatisticsLayout()
            self.activity_log = ActivityLogLayout()
            self.system_log = SystemLogLayout()
            self.workspace = WorkspaceLayout(service_connector=self.service_connector)
            self.configuration = ConfigurationLayout(
                service_connector=self.service_connector
            )

            self.content_stack.addWidget(self.overview)
            self.content_stack.addWidget(self.statistics)
            self.content_stack.addWidget(self.activity_log)
            self.content_stack.addWidget(self.system_log)
            self.content_stack.addWidget(self.workspace)
            self.content_stack.addWidget(self.configuration)

            # Assemble body and main layout
            body.addWidget(self.side_panel)
            body.addWidget(scroll)
            main_layout.addWidget(header)
            main_layout.addLayout(body)

            # Connect signals
            overview_btn.clicked.connect(lambda: self._switch_page(0))
            statistics_btn.clicked.connect(lambda: self._switch_page(1))
            activity_btn.clicked.connect(lambda: self._switch_page(2))
            system_btn.clicked.connect(lambda: self._switch_page(3))
            workspace_btn.clicked.connect(lambda: self._switch_page(4))
            config_btn.clicked.connect(lambda: self._switch_page(5))

            # Connect log handler
            self._connect_log_handler()

            # Style is applied globally via theme

            # Setup update timer
            self.update_timer = QTimer(self)
            self.update_timer.timeout.connect(self._update_data)
            self.update_timer.start(30000)  # Update every 30 seconds

            # Initial update
            self._update_data()

            # Set initial page
            overview_btn.setChecked(True)
            self._switch_page(0)

            logger.debug("Dashboard initialized")

        except Exception as e:
            logger.error(f"Error initializing dashboard: {e}", exc_info=True)
            raise

    def _create_nav_button(self, text: str) -> QPushButton:
        """Create a navigation button."""
        try:
            button = QPushButton(text)
            button.setCheckable(True)
            button.setFixedHeight(40)
            self.nav_buttons.append(button)
            return button

        except Exception as e:
            logger.error(f"Error creating nav button: {e}", exc_info=True)
            raise

    def _switch_page(self, index: int):
        """Switch to page at index."""
        try:
            # Update button states
            for i, button in enumerate(self.nav_buttons):
                button.setChecked(i == index)

            # Switch page with animation
            self.content_stack.setCurrentIndex(index)

        except Exception as e:
            logger.error(f"Error switching page: {e}", exc_info=True)

    def _on_range_changed(self, index: int) -> None:
        # Persist selection (index) and a backwards-compatible days value
        self.current_range_index = index
        days_map = {0: 1, 1: 7, 2: 15, 3: 30}
        self.settings.setValue(self.time_range_index_key, index)
        self.settings.setValue(self.time_window_key, days_map.get(index, 1))
        # Recompute anchored time window and update labels
        self.current_time_window = self._compute_time_window_for_index(index)
        try:
            if hasattr(self.overview, "set_header_subtitle"):
                self.overview.set_header_subtitle(self._format_current_range_label())
        except Exception:
            pass
        try:
            if hasattr(self, "subtitle_label") and self.subtitle_label is not None:
                self.subtitle_label.setText(self._format_current_range_label())
        except Exception:
            pass
        self._update_data()

    def _update_data(self):
        """Update dashboard data."""
        try:
            # Use selected time window
            time_window = self.current_time_window
            data = self.service_connector.get_dashboard_data(time_window)

            # Update layouts
            if data:
                # Update activity log with activity list
                if "activities" in data:
                    self.activity_log.update_data(data["activities"].get("list", []))

                # Update overview with productivity metrics and trends
                if "productivity" in data:
                    productivity = data["productivity"]
                    overview_payload = {
                        # Time metrics
                        "total_time": productivity["metrics"].get("total_time", 0),
                        "active_time": productivity["metrics"].get("active_time", 0),
                        "idle_time": productivity["metrics"].get("idle_time", 0),
                        "focus_time": productivity["metrics"].get("focus_time", 0),
                        "break_time": productivity["metrics"].get("break_time", 0),
                        # Performance metrics
                        "productivity_score": productivity["metrics"].get(
                            "productivity_score", 0
                        ),
                        "efficiency_score": productivity["metrics"].get(
                            "efficiency_score", 0
                        ),
                        "avg_session_time": productivity["metrics"].get(
                            "avg_session_time", 0
                        ),
                        # Trends and distribution
                        "productivity_trends": productivity["trends"].get(
                            "productivity_trends", {}
                        ),
                        "hourly_distribution": productivity.get(
                            "hourly_distribution", {}
                        ),
                    }
                    if "suggestions" in data:
                        overview_payload["suggestions"] = data.get("suggestions", [])
                    self.overview.update_data(overview_payload)

                # Update statistics with app and category data
                if "productivity" in data:
                    productivity = data["productivity"]
                    statistics = productivity.get("statistics", {})
                    self.statistics.update_data(
                        {
                            "app_data": statistics.get("app_data", []),
                            "category_data": statistics.get("category_data", []),
                        }
                    )

                # Update system log
                if "system_logs" in data:
                    self.system_log.update_data(data["system_logs"])

            logger.debug("Dashboard data updated")

        except Exception as e:
            logger.error(f"Error updating dashboard data: {e}", exc_info=True)

    def _connect_log_handler(self):
        """Connect Qt log handler to system log layout."""
        try:
            # Find Qt log handler
            for handler in logging.getLogger().handlers:
                if isinstance(handler, QtLogHandler):
                    handler.connect_to_widget(self.system_log.handle_log_message)
                    logger.debug("Connected Qt log handler to system log layout")
                    break
        except Exception as e:
            logger.error(f"Error connecting log handler: {e}", exc_info=True)

    def closeEvent(self, event):
        """Handle window close event."""
        try:
            # Stop update timer
            self.update_timer.stop()

            # Disconnect log handler
            for handler in logging.getLogger().handlers:
                if isinstance(handler, QtLogHandler):
                    handler.disconnect_from_widget(self.system_log.handle_log_message)
                    break

            event.accept()

        except Exception as e:
            logger.error(f"Error handling close event: {e}", exc_info=True)
            event.accept()

    def _format_current_range_label(self) -> str:
        # Use the current selection to generate a stable label
        idx = getattr(self, "current_range_index", 0)
        if idx == 0:
            return "Viewing: Today"
        elif idx == 1:
            return "Viewing: Last 7 days"
        elif idx == 2:
            return "Viewing: Last 15 days"
        else:
            return "Viewing: Last 30 days"

    def _compute_time_window_for_index(self, index: int) -> timedelta:
        """Compute a midnight-anchored time window based on selection index."""
        now = datetime.now()
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if index == 0:  # Today
            start = start_of_today
        elif index == 1:  # Last 7 days (including today)
            start = start_of_today - timedelta(days=6)
        elif index == 2:  # Last 15 days (including today)
            start = start_of_today - timedelta(days=14)
        else:  # Last 30 days (including today)
            start = start_of_today - timedelta(days=29)
        return now - start
