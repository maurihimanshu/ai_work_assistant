"""Workspace layout providing Save/Restore/Close controls and named workspace management."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QInputDialog,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHeaderView,
)
from PySide6.QtCore import Qt
from typing import List


class WorkspaceLayout(QWidget):
    def __init__(self, service_connector, parent=None):
        super().__init__(parent)
        self.service_connector = service_connector
        self._init_ui()
        self._load_named_workspaces()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Header
        header = QFrame()
        header.setObjectName("card")
        hbox = QHBoxLayout(header)
        title = QLabel("Workspace")
        subtitle = QLabel("Manage named workspaces, save/restore/close apps.")
        subtitle.setStyleSheet("color: #6b7280")
        hbox.addWidget(title)
        hbox.addStretch()
        hbox.addWidget(subtitle)

        # Named workspaces panel
        named_panel = QFrame()
        named_panel.setObjectName("card")
        np_box = QVBoxLayout(named_panel)
        np_title = QLabel("Named Workspaces")

        # Filters row
        filters_row = QHBoxLayout()
        self.filter_favorites = QCheckBox("Favorites only")
        self.filter_templates = QCheckBox("Templates only")
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Updated (desc)", "Name (A-Z)", "Created (desc)"])
        self.filter_favorites.stateChanged.connect(self._load_named_workspaces)
        self.filter_templates.stateChanged.connect(self._load_named_workspaces)
        self.sort_combo.currentIndexChanged.connect(self._load_named_workspaces)
        filters_row.addWidget(self.filter_favorites)
        filters_row.addWidget(self.filter_templates)
        filters_row.addStretch()
        filters_row.addWidget(QLabel("Sort:"))
        filters_row.addWidget(self.sort_combo)

        # Workspaces list
        self.ws_list = QListWidget()
        self.ws_list.setSelectionMode(self.ws_list.SelectionMode.SingleSelection)

        # Controls
        controls_row1 = QHBoxLayout()
        controls_row2 = QHBoxLayout()
        self.save_current_btn = QPushButton("Save Current…")
        self.save_current_btn.clicked.connect(self._save_current_named)
        self.restore_named_btn = QPushButton("Restore Selected")
        self.restore_named_btn.clicked.connect(self._restore_selected_named)
        self.duplicate_btn = QPushButton("Duplicate…")
        self.duplicate_btn.clicked.connect(self._duplicate_selected_named)
        self.rename_btn = QPushButton("Rename…")
        self.rename_btn.clicked.connect(self._rename_selected_named)
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._delete_selected_named)
        self.capture_pos_btn = QPushButton("Capture Window Positions")
        self.capture_pos_btn.clicked.connect(self._capture_positions_into_selected)
        self.toggle_fav_btn = QPushButton("★ Favorite")
        self.toggle_fav_btn.clicked.connect(self._toggle_favorite)
        self.toggle_tpl_btn = QPushButton("Set as Template")
        self.toggle_tpl_btn.clicked.connect(self._toggle_template)
        self.edit_apps_btn = QPushButton("Edit Apps…")
        self.edit_apps_btn.clicked.connect(self._edit_apps)
        self.export_btn = QPushButton("Export…")
        self.export_btn.clicked.connect(self._export_workspaces)
        self.import_btn = QPushButton("Import…")
        self.import_btn.clicked.connect(self._import_workspaces)

        # First row
        controls_row1.addWidget(self.save_current_btn)
        controls_row1.addWidget(self.restore_named_btn)
        controls_row1.addWidget(self.duplicate_btn)
        controls_row1.addWidget(self.rename_btn)
        controls_row1.addWidget(self.delete_btn)
        controls_row1.addStretch()

        # Second row
        controls_row2.addWidget(self.capture_pos_btn)
        controls_row2.addWidget(self.toggle_fav_btn)
        controls_row2.addWidget(self.toggle_tpl_btn)
        controls_row2.addWidget(self.edit_apps_btn)
        controls_row2.addStretch()
        controls_row2.addWidget(self.export_btn)
        controls_row2.addWidget(self.import_btn)

        # Stack rows vertically
        controls_box = QVBoxLayout()
        controls_box.setSpacing(8)
        controls_box.addLayout(controls_row1)
        controls_box.addLayout(controls_row2)

        np_box.addWidget(np_title)
        np_box.addLayout(filters_row)
        np_box.addWidget(self.ws_list)
        np_box.addLayout(controls_box)

        # Quick actions for current session
        actions = QFrame()
        abox = QHBoxLayout(actions)
        save_btn = QPushButton("Save Snapshot")
        restore_btn = QPushButton("Restore Last")
        close_btn = QPushButton("Close Workspace")
        save_btn.clicked.connect(self._save)
        restore_btn.clicked.connect(self._restore)
        close_btn.clicked.connect(self._close)
        abox.addWidget(save_btn)
        abox.addWidget(restore_btn)
        abox.addWidget(close_btn)
        abox.addStretch()

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #6b7280")

        # Table for app details (with status)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Action", "Executable", "Args", "Result", "Status"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        layout.addWidget(header)
        layout.addWidget(named_panel)
        layout.addWidget(actions)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table)
        layout.addStretch()

    def _apply_filters(self, items: List[dict]) -> List[dict]:
        fav_only = self.filter_favorites.isChecked()
        tpl_only = self.filter_templates.isChecked()
        filtered = [
            it
            for it in items
            if (not fav_only or it.get("favorite"))
            and (not tpl_only or it.get("template"))
        ]
        idx = self.sort_combo.currentIndex()
        if idx == 0:  # Updated desc
            filtered.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        elif idx == 1:  # Name A-Z
            filtered.sort(key=lambda x: (x.get("name", "") or "").lower())
        elif idx == 2:  # Created desc
            filtered.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return filtered

    def _populate_ws_list(self, recs: List[dict]) -> None:
        self.ws_list.clear()
        for rec in recs:
            label = rec.get("name", "")
            if rec.get("favorite"):
                label = "★ " + label
            if rec.get("template"):
                label = label + "  (Template)"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, rec.get("id"))
            self.ws_list.addItem(item)

    def _load_named_workspaces(self) -> None:
        items = self.service_connector.named_workspace_list()
        self._populate_ws_list(self._apply_filters(items))

    def _populate_table(self, rows):
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(row.get("action", "")))
            self.table.setItem(r, 1, QTableWidgetItem(row.get("executable", "")))
            self.table.setItem(r, 2, QTableWidgetItem(row.get("args", "")))
            self.table.setItem(r, 3, QTableWidgetItem(row.get("result", "")))
            status_text = (
                "OK" if row.get("result") in ("launched", "saved", "closed") else "-"
            )
            self.table.setItem(r, 4, QTableWidgetItem(status_text))

    # Quick actions
    def _save(self) -> None:
        ok, payload = self.service_connector.workspace_save_details()
        if ok:
            snap_id = payload.get("snapshot_id")
            self.status_label.setText(f"Saved snapshot: {snap_id}")
            self._populate_table(payload.get("apps", []))
        else:
            self.status_label.setText("Failed to save workspace")
            self._populate_table([])

    def _restore(self) -> None:
        ok, payload = self.service_connector.workspace_restore_details()
        if ok:
            snap_id = payload.get("snapshot_id")
            self.status_label.setText(f"Restored from snapshot: {snap_id}")
            self._populate_table(payload.get("apps", []))
        else:
            self.status_label.setText("Failed to restore workspace")
            self._populate_table([])

    def _close(self) -> None:
        ok, payload = self.service_connector.workspace_close_details()
        if ok:
            self.status_label.setText("Closed running applications")
            self._populate_table(payload.get("apps", []))
        else:
            self.status_label.setText("Failed to close workspace")
            self._populate_table([])

    # Named workspace handlers
    def _save_current_named(self) -> None:
        name, ok = QInputDialog.getText(
            self, "Save Current Workspace", "Workspace name:"
        )
        if not ok or not name.strip():
            return
        res = self.service_connector.named_workspace_save_current(
            name=name.strip(), as_template=False
        )
        if res:
            self.status_label.setText(f"Saved named workspace: {res.get('name')}")
            self._load_named_workspaces()
        else:
            QMessageBox.warning(self, "Error", "Failed to save named workspace.")

    def _restore_selected_named(self) -> None:
        it = self.ws_list.currentItem()
        if not it:
            QMessageBox.information(
                self, "No Selection", "Select a workspace to restore."
            )
            return
        ws_id = it.data(Qt.ItemDataRole.UserRole)
        payload = self.service_connector.named_workspace_restore(ws_id)
        self.status_label.setText(f"Restored named workspace: {it.text()}")
        self._populate_table(payload.get("apps", []))

    def _duplicate_selected_named(self) -> None:
        it = self.ws_list.currentItem()
        if not it:
            QMessageBox.information(
                self, "No Selection", "Select a workspace to duplicate."
            )
            return
        new_name, ok = QInputDialog.getText(self, "Duplicate Workspace", "New name:")
        if not ok or not new_name.strip():
            return
        res = self.service_connector.named_workspace_duplicate(
            it.data(Qt.ItemDataRole.UserRole), new_name.strip()
        )
        if res:
            self.status_label.setText(f"Duplicated workspace as: {res.get('name')}")
            self._load_named_workspaces()

    def _rename_selected_named(self) -> None:
        it = self.ws_list.currentItem()
        if not it:
            QMessageBox.information(
                self, "No Selection", "Select a workspace to rename."
            )
            return
        new_name, ok = QInputDialog.getText(
            self, "Rename Workspace", "New name:", text=it.text()
        )
        if not ok or not new_name.strip():
            return
        ok2 = self.service_connector.named_workspace_rename(
            it.data(Qt.ItemDataRole.UserRole), new_name.strip()
        )
        if ok2:
            self.status_label.setText(f"Renamed workspace to: {new_name.strip()}")
            self._load_named_workspaces()

    def _delete_selected_named(self) -> None:
        it = self.ws_list.currentItem()
        if not it:
            QMessageBox.information(
                self, "No Selection", "Select a workspace to delete."
            )
            return
        if (
            QMessageBox.question(
                self, "Confirm Delete", f"Delete workspace '{it.text()}'?"
            )
            == QMessageBox.StandardButton.Yes
        ):
            ok = self.service_connector.named_workspace_delete(
                it.data(Qt.ItemDataRole.UserRole)
            )
            if ok:
                self.status_label.setText("Workspace deleted.")
                self._load_named_workspaces()
            else:
                QMessageBox.warning(self, "Error", "Failed to delete workspace.")

    def _capture_positions_into_selected(self) -> None:
        it = self.ws_list.currentItem()
        if not it:
            QMessageBox.information(
                self, "No Selection", "Select a workspace to capture positions into."
            )
            return
        ws_id = it.data(Qt.ItemDataRole.UserRole)
        # Fetch current saved record
        recs = {r.get("id"): r for r in self.service_connector.named_workspace_list()}
        rec = recs.get(ws_id)
        if not rec:
            QMessageBox.warning(self, "Error", "Failed to load workspace record.")
            return
        # Build updated apps with positions from currently running windows (placeholder; best-effort)
        updated_apps = []
        from core.services.workspace_service import WorkspaceService

        current = WorkspaceService().create_snapshot(note="capture-pos")
        live = {}
        for a in current.apps:
            exe_tail = (a.executable_path or "").split("\\")[-1].split("/")[-1]
            live_key = (exe_tail.lower(), (a.window_title or ""))
            live[live_key] = {"title": a.window_title or "", "exe": exe_tail}
        for app in rec.get("apps", []):
            exe_tail = (
                app.get("executable", "").split("\\")[-1].split("/")[-1]
            ).lower()
            title = app.get("title", "")
            key = (exe_tail, title)
            pos = app.get("position") or {}
            delay_ms = app.get("delay_ms")
            order = app.get("order")
            args = app.get("args", [])
            if key in live:
                updated_apps.append(
                    {
                        "executable": app.get("executable", ""),
                        "args": args,
                        "title": title,
                        "order": order,
                        "delay_ms": delay_ms,
                        "position": pos,
                    }
                )
            else:
                updated_apps.append(app)
        from ..utils.workspaces_store import WorkspacesStore

        store = WorkspacesStore()
        store.update(ws_id, apps=updated_apps)
        self.status_label.setText(
            "Captured window positions placeholders for selected workspace."
        )

    def _edit_apps(self) -> None:
        it = self.ws_list.currentItem()
        if not it:
            QMessageBox.information(
                self, "No Selection", "Select a workspace to edit apps."
            )
            return
        ws_id = it.data(Qt.ItemDataRole.UserRole)
        recs = {r.get("id"): r for r in self.service_connector.named_workspace_list()}
        rec = recs.get(ws_id)
        if not rec:
            QMessageBox.warning(self, "Error", "Failed to load workspace record.")
            return
        from ..components.app_editor_dialog import AppEditorDialog

        dlg = AppEditorDialog(rec.get("apps", []), self)
        if dlg.exec() == dlg.DialogCode.Accepted:
            new_apps = dlg.edited_apps()
            from ..utils.workspaces_store import WorkspacesStore

            store = WorkspacesStore()
            store.update(ws_id, apps=new_apps)
            self.status_label.setText("Updated workspace applications.")
            self._load_named_workspaces()

    def _toggle_favorite(self) -> None:
        it = self.ws_list.currentItem()
        if not it:
            QMessageBox.information(
                self, "No Selection", "Select a workspace to toggle favorite."
            )
            return
        ws_id = it.data(Qt.ItemDataRole.UserRole)
        recs = {r.get("id"): r for r in self.service_connector.named_workspace_list()}
        current = recs.get(ws_id)
        if not current:
            return
        new_state = not bool(current.get("favorite"))
        if self.service_connector.named_workspace_set_favorite(ws_id, new_state):
            self._load_named_workspaces()

    def _toggle_template(self) -> None:
        it = self.ws_list.currentItem()
        if not it:
            QMessageBox.information(
                self, "No Selection", "Select a workspace to toggle template."
            )
            return
        ws_id = it.data(Qt.ItemDataRole.UserRole)
        recs = {r.get("id"): r for r in self.service_connector.named_workspace_list()}
        current = recs.get(ws_id)
        if not current:
            return
        new_state = not bool(current.get("template"))
        if self.service_connector.named_workspace_set_template(ws_id, new_state):
            self._load_named_workspaces()

    def _export_workspaces(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Workspaces", "workspaces.json", "JSON Files (*.json)"
        )
        if not file_path:
            return
        count = self.service_connector.export_workspaces(file_path)
        self.status_label.setText(f"Exported {count} workspaces to {file_path}")

    def _import_workspaces(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Workspaces", "", "JSON Files (*.json)"
        )
        if not file_path:
            return
        count = self.service_connector.import_workspaces(file_path, merge=True)
        self.status_label.setText(f"Imported {count} workspaces from {file_path}")
        self._load_named_workspaces()
