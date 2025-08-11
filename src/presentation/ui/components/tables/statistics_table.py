"""Statistics table module."""

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal as pyqtSignal
from PySide6.QtGui import QColor, QBrush, QPalette, QFont, QIcon
from PySide6.QtWidgets import (
    QTableView,
    QFrame,
    QMenu,
    QHeaderView,
    QStyledItemDelegate,
    QStyle,
    QWidget,
)
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class Column:
    """Column definition."""

    def __init__(
        self,
        name: str,
        title: str,
        width: int = None,
        align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft,
        visible: bool = True,
        formatter=str,
    ):
        """Initialize column.

        Args:
            name: Column identifier
            title: Column display title
            width: Fixed width in pixels (None for auto)
            align: Text alignment
            visible: Whether column is visible
            formatter: Function to format cell value
        """
        self.name = name
        self.title = title
        self.width = width
        self.align = align
        self.visible = visible
        self.formatter = formatter


class PercentageDelegate(QStyledItemDelegate):
    """Delegate for rendering percentage cells with color bars."""

    def __init__(self, parent=None):
        """Initialize percentage delegate."""
        super().__init__(parent)

        # Color gradient for percentages
        self.colors = [
            (0, QColor("#FF5252")),  # Red (0%)
            (25, QColor("#FFA726")),  # Orange (25%)
            (50, QColor("#FFEB3B")),  # Yellow (50%)
            (75, QColor("#66BB6A")),  # Light green (75%)
            (100, QColor("#4CAF50")),  # Green (100%)
        ]

    def paint(self, painter, option, index):
        """Paint the percentage cell."""
        try:
            # Get percentage value
            value = index.data(Qt.ItemDataRole.DisplayRole)
            if not value:
                super().paint(painter, option, index)
                return

            try:
                percentage = float(value.strip("%"))
            except (ValueError, AttributeError):
                super().paint(painter, option, index)
                return

            # Draw background
            if option.state & QStyle.StateFlag.State_Selected:
                painter.fillRect(option.rect, option.palette.highlight())
            else:
                painter.fillRect(option.rect, option.palette.base())

            # Calculate bar width
            bar_width = int(option.rect.width() * (percentage / 100))
            bar_rect = option.rect
            bar_rect.setWidth(bar_width)

            # Get color for percentage
            color = self._get_color(percentage)
            painter.fillRect(bar_rect, color)

            # Draw text
            text_rect = option.rect
            text_rect.setLeft(text_rect.left() + 4)  # Add padding
            painter.drawText(
                text_rect,
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                f"{percentage:.1f}%",
            )

        except Exception as e:
            logger.error(f"Error painting percentage cell: {e}", exc_info=True)
            super().paint(painter, option, index)

    def _get_color(self, percentage: float) -> QColor:
        """Get color for percentage value using gradient."""
        try:
            # Find color range
            for i in range(len(self.colors) - 1):
                if self.colors[i][0] <= percentage <= self.colors[i + 1][0]:
                    # Calculate interpolation factor
                    range_start = self.colors[i][0]
                    range_end = self.colors[i + 1][0]
                    factor = (percentage - range_start) / (range_end - range_start)

                    # Interpolate colors
                    c1 = self.colors[i][1]
                    c2 = self.colors[i + 1][1]

                    return QColor(
                        int(c1.red() + factor * (c2.red() - c1.red())),
                        int(c1.green() + factor * (c2.green() - c1.green())),
                        int(c1.blue() + factor * (c2.blue() - c1.blue())),
                        int(c1.alpha() + factor * (c2.alpha() - c1.alpha())),
                    )

            return self.colors[-1][1]  # Default to last color

        except Exception as e:
            logger.error(f"Error getting percentage color: {e}", exc_info=True)
            return QColor("#4CAF50")  # Default to green


class StatisticsTableModel(QAbstractTableModel):
    """Model for statistics table data."""

    def __init__(self, parent=None):
        """Initialize statistics table model."""
        super().__init__(parent)

        # Data
        self.statistics = []  # List of statistics rows

        # Settings
        self.columns = [
            Column(
                "name",
                "Name",
                width=None,
                align=Qt.AlignmentFlag.AlignLeft,
                formatter=str,
            ),
            Column(
                "time",
                "Time",
                width=120,
                align=Qt.AlignmentFlag.AlignHCenter,
                formatter=lambda x: str(x),
            ),
            Column(
                "percentage",
                "Usage %",
                width=140,
                align=Qt.AlignmentFlag.AlignHCenter,
                formatter=lambda x: f"{float(x):.1f}%" if x is not None else "0.0%",
            ),
        ]

        logger.debug("Statistics table model initialized")

    def rowCount(self, parent=QModelIndex()):
        """Get number of rows."""
        if not parent.isValid():
            return len(self.statistics)
        return 0

    def columnCount(self, parent=QModelIndex()):
        """Get number of columns."""
        return len([col for col in self.columns if col.visible])

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        """Get header data."""
        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Horizontal
        ):
            visible_columns = [col for col in self.columns if col.visible]
            if 0 <= section < len(visible_columns):
                return visible_columns[section].title
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """Get cell data."""
        try:
            if not index.isValid():
                return None

            if not (0 <= index.row() < len(self.statistics)):
                return None

            # Get row data and column
            row_data = self.statistics[index.row()]
            visible_columns = [col for col in self.columns if col.visible]
            if not (0 <= index.column() < len(visible_columns)):
                return None
            column = visible_columns[index.column()]

            # Handle different roles
            if role == Qt.ItemDataRole.DisplayRole:
                value = row_data.get(column.name)
                return column.formatter(value) if value is not None else ""

            elif role == Qt.ItemDataRole.TextAlignmentRole:
                return int(column.align | Qt.AlignmentFlag.AlignVCenter)

            elif role == Qt.ItemDataRole.ToolTipRole:
                if column.name == "name":
                    return row_data.get("name", "")
                elif column.name == "time":
                    return f"Total time: {row_data.get('time', '0s')}"
                elif column.name == "percentage":
                    return f"Usage: {row_data.get('percentage', 0):.1f}%"
                return None

        except Exception as e:
            logger.error(f"Error getting table data: {e}", exc_info=True)
            return None

        return None

    def flags(self, index):
        """Get item flags."""
        try:
            flags = super().flags(index)
            flags |= Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
            return flags

        except Exception as e:
            logger.error(f"Error getting item flags: {e}", exc_info=True)
            return super().flags(index)

    def sort(self, column, order=Qt.SortOrder.AscendingOrder):
        """Sort table by column."""
        try:
            self.layoutAboutToBeChanged.emit()

            visible_columns = [col for col in self.columns if col.visible]
            if not (0 <= column < len(visible_columns)):
                return
            column_name = visible_columns[column].name

            # Sort statistics
            reverse = order == Qt.SortOrder.DescendingOrder

            if column_name == "name":
                self.statistics.sort(
                    key=lambda x: x.get("name", "").lower(), reverse=reverse
                )
            elif column_name == "time":
                self.statistics.sort(
                    key=lambda x: self._parse_duration(x.get("time", "0s")),
                    reverse=reverse,
                )
            elif column_name == "percentage":
                self.statistics.sort(
                    key=lambda x: float(x.get("percentage", 0)), reverse=reverse
                )

            self.layoutChanged.emit()

        except Exception as e:
            logger.error(f"Error sorting statistics: {e}", exc_info=True)

    def _parse_duration(self, duration_str: str) -> float:
        """Parse duration string to seconds for sorting."""
        try:
            if "h" in duration_str:
                parts = duration_str.split("h")
                hours = float(parts[0].strip())
                minutes = float(parts[1].strip("m").strip()) if "m" in parts[1] else 0
                return hours * 3600 + minutes * 60
            elif "m" in duration_str:
                minutes = float(duration_str.strip("m").strip())
                return minutes * 60
            elif "s" in duration_str:
                seconds = float(duration_str.strip("s").strip())
                return seconds
            return 0
        except (ValueError, TypeError):
            return 0

    def set_column_visible(self, column_name: str, visible: bool):
        """Set column visibility."""
        try:
            for column in self.columns:
                if column.name == column_name:
                    self.beginResetModel()
                    column.visible = visible
                    self.endResetModel()
                    logger.debug(f"Column {column_name} visibility set to {visible}")
                    return

        except Exception as e:
            logger.error(f"Error setting column visibility: {e}", exc_info=True)

    def set_column_width(self, column_name: str, width: int):
        """Set column width."""
        try:
            for column in self.columns:
                if column.name == column_name:
                    column.width = width
                    logger.debug(f"Column {column_name} width set to {width}")
                    return

        except Exception as e:
            logger.error(f"Error setting column width: {e}", exc_info=True)

    def update_statistics(self, statistics: List[List[str]]):
        """Update statistics data.

        Args:
            statistics: List of [name, time, percentage] lists
        """
        try:
            if not statistics:
                self.beginResetModel()
                self.statistics = []
                self.endResetModel()
                return

            # Transform list format to dictionary format
            validated_stats = []
            for stat in statistics:
                try:
                    if len(stat) != 3:
                        logger.warning(f"Invalid statistic data format: {stat}")
                        continue

                    validated_stat = {
                        "name": str(stat[0]),
                        "time": str(stat[1]),
                        "percentage": float(str(stat[2]).rstrip("%")),
                    }
                    validated_stats.append(validated_stat)
                except (ValueError, TypeError, IndexError) as e:
                    logger.warning(f"Invalid statistic data: {e}")
                    continue

            # Update model
            self.beginResetModel()
            self.statistics = validated_stats
            self.endResetModel()

            logger.debug(f"Updated with {len(validated_stats)} statistics")

        except Exception as e:
            logger.error(f"Error updating statistics: {e}", exc_info=True)
            # Fall back to full reset
            self.beginResetModel()
            self.statistics = []
            self.endResetModel()


class StatisticsTable(QTableView):
    """Table view for statistics data."""

    # Signals
    columnVisibilityChanged = pyqtSignal(str, bool)  # Column name, visible

    def __init__(self, parent=None):
        """Initialize statistics table."""
        try:
            super().__init__(parent)

            # Create model
            self.model = StatisticsTableModel()
            self.setModel(self.model)

            # Set delegate for percentage column
            self.percentage_delegate = PercentageDelegate(self)
            self.setItemDelegateForColumn(2, self.percentage_delegate)

            # Setup UI
            self.setup_ui()

            logger.debug("Statistics table initialized")

        except Exception as e:
            logger.error(f"Error initializing statistics table: {e}", exc_info=True)
            raise

    def setup_ui(self):
        """Set up the table UI."""
        try:
            # Set frame style
            self.setFrameStyle(QFrame.Shape.NoFrame)
            self.setStyleSheet(
                """
                QTableView {
                    background-color: white;
                    border: none;
                    gridline-color: #f5f5f5;
                }
                QTableView::item {
                    padding: 10px 8px;
                    border-bottom: 1px solid #f5f5f5;
                }
                QTableView::item:selected {
                    background-color: #e3f2fd;
                    color: black;
                }
                QHeaderView::section {
                    background-color: white;
                    padding: 10px 8px;
                    border: none;
                    border-bottom: 2px solid #e0e0e0;
                    font-weight: bold;
                    color: #424242;
                }
                QHeaderView::section:hover {
                    background-color: #f5f5f5;
                }
            """
            )

            # Set selection behavior
            self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
            self.setSelectionMode(QTableView.SelectionMode.SingleSelection)

            # Enable sorting
            self.setSortingEnabled(True)

            # Set column sizes
            header = self.horizontalHeader()
            header.setStretchLastSection(True)

            for i, column in enumerate(self.model.columns):
                if not column.visible:
                    self.hideColumn(i)
                    continue

                if column.width:
                    self.setColumnWidth(i, column.width)
                    header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
                else:
                    header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

            # Set row height
            self.verticalHeader().setDefaultSectionSize(44)
            self.verticalHeader().hide()

            # Enable hover
            self.setMouseTracking(True)

            # Create context menu
            self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.customContextMenuRequested.connect(self._show_context_menu)

            logger.debug("Statistics table UI setup complete")

        except Exception as e:
            logger.error(f"Error setting up statistics table UI: {e}", exc_info=True)
            raise

    def _show_context_menu(self, pos):
        """Show context menu."""
        try:
            menu = QMenu(self)

            # Add columns submenu
            columns_menu = menu.addMenu("Columns")

            for column in self.model.columns:
                action = columns_menu.addAction(column.title)
                action.setCheckable(True)
                action.setChecked(column.visible)
                action.triggered.connect(
                    lambda checked, col=column: self.set_column_visible(
                        col.name, checked
                    )
                )

            # Show menu
            menu.exec(self.mapToGlobal(pos))

        except Exception as e:
            logger.error(f"Error showing context menu: {e}", exc_info=True)

    def set_column_visible(self, column_name: str, visible: bool):
        """Set column visibility."""
        try:
            self.model.set_column_visible(column_name, visible)
            self.columnVisibilityChanged.emit(column_name, visible)
        except Exception as e:
            logger.error(f"Error setting column visibility: {e}", exc_info=True)

    def update_data(self, statistics: List[Dict[str, Any]]):
        """Update table with new data."""
        try:
            self.model.update_statistics(statistics)
        except Exception as e:
            logger.error(f"Error updating statistics table: {e}", exc_info=True)
