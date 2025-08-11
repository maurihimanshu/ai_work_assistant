"""Configuration layout for managing categories and app mappings."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QMessageBox,
    QSizePolicy,
)
from PySide6.QtCore import Qt

from ..utils.config_store import ConfigStore, AppMapping, DEFAULT_CATEGORIES
from datetime import timedelta


class ConfigurationLayout(QWidget):
    def __init__(self, service_connector, parent=None):
        super().__init__(parent)
        self.service_connector = service_connector
        self.config = ConfigStore()
        self._init_ui()
        self._load_data()
        self._refresh_unknowns()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Categories card
        cat_card = QFrame()
        cat_card.setObjectName("card")
        cat_box = QVBoxLayout(cat_card)
        cat_title = QLabel("Categories")
        self.cat_input = QLineEdit()
        self.cat_input.setPlaceholderText("Add new category (e.g., Development)")
        cat_actions = QHBoxLayout()
        cat_add = QPushButton("Add Category")
        cat_add.clicked.connect(self._add_category)
        cat_save = QPushButton("Save Categories")
        cat_save.clicked.connect(self._save_categories)
        cat_actions.addWidget(cat_add)
        cat_actions.addWidget(cat_save)
        cat_box.addWidget(cat_title)
        cat_box.addWidget(self.cat_input)
        cat_box.addLayout(cat_actions)

        # App mappings card
        map_card = QFrame()
        map_card.setObjectName("card")
        map_box = QVBoxLayout(map_card)
        map_title = QLabel("Application Mappings")
        self.map_table = QTableWidget(0, 3)
        self.map_table.setHorizontalHeaderLabels(
            ["App Executable", "Software Name", "Category"]
        )
        self.map_table.horizontalHeader().setStretchLastSection(True)
        self.map_table.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.map_table.setMinimumHeight(300)
        map_actions = QHBoxLayout()
        self.map_add_btn = QPushButton("Add Mapping")
        self.map_add_btn.clicked.connect(self._add_mapping_row)
        self.map_save_btn = QPushButton("Save Mappings")
        self.map_save_btn.clicked.connect(self._save_mappings)
        map_actions.addWidget(self.map_add_btn)
        map_actions.addWidget(self.map_save_btn)
        map_box.addWidget(map_title)
        map_box.addWidget(self.map_table)
        map_box.addLayout(map_actions)

        layout.addWidget(cat_card)
        layout.addWidget(map_card)

        # Unknowns card (unmapped apps and uncategorized apps)
        unknown_card = QFrame()
        unknown_card.setObjectName("card")
        unknown_box = QVBoxLayout(unknown_card)
        unknown_title = QLabel("Unmapped & Uncategorized")
        unknown_title.setStyleSheet("font-weight: bold;")
        unknown_box.addWidget(unknown_title)

        # Controls
        controls = QHBoxLayout()
        self.refresh_unknown_btn = QPushButton("Refresh Unknowns")
        self.refresh_unknown_btn.clicked.connect(self._refresh_unknowns)
        self.add_selected_btn = QPushButton("Add Selected to Mappings")
        self.add_selected_btn.clicked.connect(self._add_selected_unknowns_to_mappings)
        controls.addWidget(self.refresh_unknown_btn)
        controls.addWidget(self.add_selected_btn)
        controls.addStretch()
        unknown_box.addLayout(controls)

        # Side-by-side tables with equal width and height
        tables_row = QHBoxLayout()
        tables_row.setSpacing(12)

        # Left panel: Unmapped Applications
        left_panel = QVBoxLayout()
        left_label = QLabel("Unmapped Applications")
        self.unknown_apps_table = QTableWidget(0, 3)
        self.unknown_apps_table.setHorizontalHeaderLabels(
            ["Executable", "Occurrences", "Last Seen"]
        )
        self.unknown_apps_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.unknown_apps_table.setSelectionMode(
            QTableWidget.SelectionMode.ExtendedSelection
        )
        self.unknown_apps_table.horizontalHeader().setStretchLastSection(True)
        self.unknown_apps_table.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.unknown_apps_table.setMinimumHeight(360)
        left_panel.addWidget(left_label)
        left_panel.addWidget(self.unknown_apps_table)

        # Right panel: Uncategorized Applications
        right_panel = QVBoxLayout()
        right_label = QLabel("Uncategorized Applications")
        self.unknown_cats_table = QTableWidget(0, 2)
        self.unknown_cats_table.setHorizontalHeaderLabels(
            ["Application", "Occurrences"]
        )
        self.unknown_cats_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.unknown_cats_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.unknown_cats_table.horizontalHeader().setStretchLastSection(True)
        self.unknown_cats_table.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.unknown_cats_table.setMinimumHeight(360)
        right_panel.addWidget(right_label)
        right_panel.addWidget(self.unknown_cats_table)

        # Add panels with equal stretch so widths match
        tables_row.addLayout(left_panel, 1)
        tables_row.addLayout(right_panel, 1)
        unknown_box.addLayout(tables_row)

        layout.addWidget(unknown_card)
        layout.addStretch()

    def _load_data(self):
        # Load categories for category column
        self._categories = self.config.load_categories()
        # Populate existing mappings
        mappings = self.config.load_mappings()
        for m in mappings:
            self._append_mapping_row(m.executable, m.name, m.category)

    # Handlers
    def _add_category(self):
        text = self.cat_input.text().strip()
        if not text:
            return
        if text not in self._categories:
            self._categories.append(text)
            QMessageBox.information(self, "Category Added", f"Added category: {text}")
        self.cat_input.clear()

    def _save_categories(self):
        self.config.save_categories(self._categories)
        QMessageBox.information(self, "Saved", "Categories saved.")
        # Refresh category combos to include any new categories
        for r in range(self.map_table.rowCount()):
            combo = self.map_table.cellWidget(r, 2)
            if isinstance(combo, QComboBox):
                current = combo.currentText()
                combo.clear()
                combo.addItems(self._categories)
                if current in self._categories:
                    combo.setCurrentText(current)

    def _append_mapping_row(self, exe: str, name: str, category: str):
        r = self.map_table.rowCount()
        self.map_table.insertRow(r)
        self.map_table.setItem(r, 0, QTableWidgetItem(exe))
        self.map_table.setItem(r, 1, QTableWidgetItem(name))
        combo = QComboBox()
        combo.addItems(self._categories or DEFAULT_CATEGORIES)
        if category and category in self._categories:
            combo.setCurrentText(category)
        self.map_table.setCellWidget(r, 2, combo)

    def _add_mapping_row(self):
        self._append_mapping_row(
            "", "", self._categories[0] if self._categories else "Unknown"
        )

    def _save_mappings(self):
        rows = self.map_table.rowCount()
        mappings = []
        for r in range(rows):
            exe_item = self.map_table.item(r, 0)
            name_item = self.map_table.item(r, 1)
            combo = self.map_table.cellWidget(r, 2)
            exe = exe_item.text().strip() if exe_item else ""
            name = name_item.text().strip() if name_item else ""
            category = (
                combo.currentText().strip()
                if isinstance(combo, QComboBox)
                else "Unknown"
            )
            if exe and name:
                mappings.append(
                    AppMapping(executable=exe, name=name, category=category)
                )
        self.config.save_mappings(mappings)
        QMessageBox.information(self, "Saved", "Application mappings saved.")

    # Unknowns helpers
    def _refresh_unknowns(self):
        """Populate unknown applications and uncategorized apps from recent data."""
        try:
            data = self.service_connector.get_dashboard_data(timedelta(days=30))
        except Exception:
            data = {}
        activities = (data or {}).get("activities", {}).get("list", [])
        # Build mapping key set for quick check
        mapping_keys = {m.executable.lower() for m in self.config.load_mappings()}
        # Aggregate unknown executables by occurrences and last seen
        stats = {}
        for a in activities:
            exe_path = a.get("executable_path") or a.get("app_name") or ""
            exe = exe_path.split("\\")[-1].split("/")[-1]
            if not exe:
                continue
            if exe.lower() in mapping_keys:
                continue
            # Consider unmapped
            s = stats.setdefault(exe, {"count": 0, "last": "N/A"})
            s["count"] += 1
            last = a.get("start_time") or "N/A"
            s["last"] = max(s["last"], last) if isinstance(s["last"], str) else last
        # Fill table
        self.unknown_apps_table.setRowCount(0)
        for exe, s in sorted(stats.items(), key=lambda x: x[1]["count"], reverse=True):
            r = self.unknown_apps_table.rowCount()
            self.unknown_apps_table.insertRow(r)
            self.unknown_apps_table.setItem(r, 0, QTableWidgetItem(exe))
            self.unknown_apps_table.setItem(r, 1, QTableWidgetItem(str(s["count"])))
            self.unknown_apps_table.setItem(r, 2, QTableWidgetItem(str(s["last"])))
        # Uncategorized apps (category == Unknown)
        by_app = {}
        for a in activities:
            name = a.get("display_name") or a.get("app_name") or "Unknown"
            category = a.get("category") or "Unknown"
            if category != "Unknown":
                continue
            by_app[name] = by_app.get(name, 0) + 1
        self.unknown_cats_table.setRowCount(0)
        for name, cnt in sorted(by_app.items(), key=lambda x: x[1], reverse=True):
            r = self.unknown_cats_table.rowCount()
            self.unknown_cats_table.insertRow(r)
            self.unknown_cats_table.setItem(r, 0, QTableWidgetItem(name))
            self.unknown_cats_table.setItem(r, 1, QTableWidgetItem(str(cnt)))

    def _add_selected_unknowns_to_mappings(self):
        """Append selected unknown executables into mappings table for quick editing."""
        selected_rows = {idx.row() for idx in self.unknown_apps_table.selectedIndexes()}
        if not selected_rows:
            QMessageBox.information(
                self, "No Selection", "Select one or more unknown executables to add."
            )
            return
        for r in sorted(selected_rows):
            exe_item = self.unknown_apps_table.item(r, 0)
            exe = exe_item.text().strip() if exe_item else ""
            if exe:
                self._append_mapping_row(
                    exe, "", self._categories[0] if self._categories else "Unknown"
                )
        QMessageBox.information(
            self, "Added", "Selected executables added to mappings for editing."
        )
