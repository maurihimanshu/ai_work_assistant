"""Named workspaces store (presentation layer, JSON-backed)."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any


@dataclass
class WorkspaceRecord:
    id: str
    name: str
    created_at: str
    updated_at: str
    favorite: bool
    color: Optional[str]
    icon: Optional[str]
    template: bool
    # apps: list of entries like
    #   {
    #     "executable": str,
    #     "args": List[str],
    #     "title": str,
    #     "order": Optional[int],
    #     "delay_ms": Optional[int],
    #     "position": Optional[Dict[str, int]]  # {x,y,w,h}
    #   }
    apps: List[Dict[str, Any]]

    @staticmethod
    def new(
        name: str, apps: List[Dict[str, Any]], template: bool = False
    ) -> "WorkspaceRecord":
        ts = datetime.now().isoformat(timespec="seconds")
        return WorkspaceRecord(
            id=str(uuid.uuid4()),
            name=name,
            created_at=ts,
            updated_at=ts,
            favorite=False,
            color=None,
            icon=None,
            template=template,
            apps=apps,
        )


class WorkspacesStore:
    def __init__(self, base_dir: str = "data/workspaces") -> None:
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self._path = os.path.join(self.base_dir, "workspaces.json")
        if not os.path.exists(self._path):
            self._write({"workspaces": []})

    def _read(self) -> Dict[str, Any]:
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                return json.load(f) or {"workspaces": []}
        except Exception:
            return {"workspaces": []}

    def _write(self, data: Dict[str, Any]) -> None:
        os.makedirs(self.base_dir, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def list(self) -> List[WorkspaceRecord]:
        data = self._read()
        recs: List[WorkspaceRecord] = []
        for w in data.get("workspaces", []):
            try:
                recs.append(WorkspaceRecord(**w))
            except Exception:
                continue
        return recs

    def save_new(
        self, name: str, apps: List[Dict[str, Any]], template: bool = False
    ) -> WorkspaceRecord:
        rec = WorkspaceRecord.new(name=name, apps=apps, template=template)
        all_ws = self.list()
        all_ws.append(rec)
        self._write({"workspaces": [asdict(w) for w in all_ws]})
        return rec

    def update(self, rec_id: str, **fields) -> Optional[WorkspaceRecord]:
        all_ws = self.list()
        updated = None
        for i, w in enumerate(all_ws):
            if w.id == rec_id:
                for k, v in fields.items():
                    if hasattr(w, k):
                        setattr(w, k, v)
                w.updated_at = datetime.now().isoformat(timespec="seconds")
                all_ws[i] = w
                updated = w
                break
        if updated:
            self._write({"workspaces": [asdict(w) for w in all_ws]})
        return updated

    def delete(self, rec_id: str) -> bool:
        all_ws = self.list()
        new_ws = [w for w in all_ws if w.id != rec_id]
        if len(new_ws) == len(all_ws):
            return False
        self._write({"workspaces": [asdict(w) for w in new_ws]})
        return True

    def duplicate(self, rec_id: str, new_name: str) -> Optional[WorkspaceRecord]:
        w = self.get(rec_id)
        if not w:
            return None
        return self.save_new(new_name, apps=w.apps, template=w.template)

    def get(self, rec_id: str) -> Optional[WorkspaceRecord]:
        for w in self.list():
            if w.id == rec_id:
                return w
        return None

    def find_by_name(self, name: str) -> Optional[WorkspaceRecord]:
        name_lower = (name or "").strip().lower()
        for w in self.list():
            if w.name.strip().lower() == name_lower:
                return w
        return None

    def set_favorite(self, rec_id: str, favorite: bool) -> Optional[WorkspaceRecord]:
        return self.update(rec_id, favorite=favorite)

    def set_template(self, rec_id: str, template: bool) -> Optional[WorkspaceRecord]:
        return self.update(rec_id, template=template)

    # Export/Import
    def export_to(self, file_path: str) -> int:
        """Export all workspaces to a JSON file. Returns count exported."""
        ws = [asdict(w) for w in self.list()]
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({"workspaces": ws}, f, indent=2)
        return len(ws)

    def import_from(self, file_path: str, merge: bool = True) -> int:
        """Import workspaces from file. If merge, appends; else replaces. Returns count imported."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
        except Exception:
            return 0
        imported = data.get("workspaces", [])
        if not isinstance(imported, list):
            return 0
        if not merge:
            self._write({"workspaces": imported})
            return len(imported)
        # merge
        current = [asdict(w) for w in self.list()]
        current.extend(imported)
        # optional: de-dup by (name, apps signature)
        self._write({"workspaces": current})
        return len(imported)
