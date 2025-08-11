"""Service to manage workspace save/restore/close actions."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from infrastructure.os.app_controller import AppController, RunningApp

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceApp:
    executable_path: str
    args: List[str]
    window_title: Optional[str]
    last_seen: Optional[str]


@dataclass
class WorkspaceSnapshot:
    id: str
    created_at: str
    apps: List[WorkspaceApp]
    metadata: dict


class WorkspaceService:
    def __init__(self, base_dir: str = "data/workspaces") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.controller = AppController()

    def _snapshot_path(self, snapshot_id: str) -> Path:
        return self.base_dir / f"workspace_{snapshot_id}.json"

    def create_snapshot(self, note: str = "auto") -> WorkspaceSnapshot:
        now = datetime.now()
        snapshot_id = now.strftime("%Y%m%d_%H%M%S")
        apps: List[WorkspaceApp] = []
        seen = set()
        for app in self.controller.list_visible_apps():
            if not app.exe:
                continue
            key = (app.exe.lower(), (app.window_title or ""))
            if key in seen:
                continue
            seen.add(key)
            apps.append(
                WorkspaceApp(
                    executable_path=app.exe,
                    args=app.cmdline[1:] if len(app.cmdline) > 1 else [],
                    window_title=app.window_title,
                    last_seen=now.isoformat(),
                )
            )
        snapshot = WorkspaceSnapshot(
            id=snapshot_id,
            created_at=now.isoformat(),
            apps=apps,
            metadata={"note": note},
        )
        self._save_snapshot(snapshot)
        logger.info(f"Saved workspace snapshot {snapshot_id} with {len(apps)} apps")
        return snapshot

    def _save_snapshot(self, snapshot: WorkspaceSnapshot) -> None:
        try:
            path = self._snapshot_path(snapshot.id)
            data = asdict(snapshot)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving workspace snapshot: {e}")

    def load_last_snapshot(self) -> Optional[WorkspaceSnapshot]:
        try:
            files = sorted(self.base_dir.glob("workspace_*.json"), reverse=True)
            if not files:
                return None
            with open(files[0], "r", encoding="utf-8") as f:
                data = json.load(f)
            return WorkspaceSnapshot(
                id=data["id"],
                created_at=data["created_at"],
                apps=[WorkspaceApp(**a) for a in data.get("apps", [])],
                metadata=data.get("metadata", {}),
            )
        except Exception as e:
            logger.error(f"Error loading last workspace snapshot: {e}")
            return None

    def restore_snapshot(self, snapshot: WorkspaceSnapshot) -> int:
        """Start applications from snapshot. Returns count of launch attempts."""
        count = 0
        for app in snapshot.apps:
            if app.executable_path:
                if self.controller.start_app(app.executable_path, app.args):
                    count += 1
        logger.info(f"Restored {count} apps from snapshot {snapshot.id}")
        return count

    def close_workspace(self, exclude: Optional[List[str]] = None) -> int:
        exclude = exclude or []
        closed = 0
        # Close all apps except exclusions by exe name
        for running in self.controller.list_running_apps():
            if any((running.name or "").lower() == e.lower() for e in exclude):
                continue
            if running.name and self.controller.close_app_by_exe(running.name):
                closed += 1
        logger.info(f"Closed {closed} apps (exclude={exclude})")
        return closed
