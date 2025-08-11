"""Presentation-layer configuration store for categories and app mappings."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

DEFAULT_CATEGORIES = [
    "Development",
    "Communication",
    "Office Work",
    "Web Browsing",
    "Entertainment",
    "System",
    "Unknown",
]


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


@dataclass
class AppMapping:
    executable: str
    name: str
    category: str

    def to_dict(self) -> Dict:
        return {
            "executable": self.executable,
            "name": self.name,
            "category": self.category,
        }


class ConfigStore:
    """Manages reading/writing categories and app mappings to JSON files."""

    def __init__(self, base_dir: str = "data/config") -> None:
        self.base_dir = base_dir
        _ensure_dir(self.base_dir)
        self._categories_path = os.path.join(self.base_dir, "categories.json")
        self._mappings_path = os.path.join(self.base_dir, "app_mappings.json")

    # Categories
    def load_categories(self) -> List[str]:
        if not os.path.exists(self._categories_path):
            self.save_categories(DEFAULT_CATEGORIES)
            return list(DEFAULT_CATEGORIES)
        try:
            with open(self._categories_path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            cats = data.get("categories", [])
            if not cats:
                cats = list(DEFAULT_CATEGORIES)
                self.save_categories(cats)
            return cats
        except Exception:
            return list(DEFAULT_CATEGORIES)

    def save_categories(self, categories: List[str]) -> None:
        payload = {"categories": [c for c in categories if c and c.strip()]}
        with open(self._categories_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    # App mappings
    def load_mappings(self) -> List[AppMapping]:
        if not os.path.exists(self._mappings_path):
            self.save_mappings([])
            return []
        try:
            with open(self._mappings_path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            mappings = data.get("mappings", [])
            result: List[AppMapping] = []
            for m in mappings:
                exe = (m.get("executable") or "").strip()
                name = (m.get("name") or "").strip()
                category = (m.get("category") or "Unknown").strip() or "Unknown"
                if exe and name:
                    result.append(
                        AppMapping(executable=exe, name=name, category=category)
                    )
            return result
        except Exception:
            return []

    def save_mappings(self, mappings: List[AppMapping | Dict]) -> None:
        serializable = []
        for m in mappings:
            if isinstance(m, AppMapping):
                serializable.append(m.to_dict())
            else:
                # Assume dict-like
                exe = (m.get("executable") or "").strip()
                name = (m.get("name") or "").strip()
                category = (m.get("category") or "Unknown").strip() or "Unknown"
                if exe and name:
                    serializable.append(
                        {"executable": exe, "name": name, "category": category}
                    )
        with open(self._mappings_path, "w", encoding="utf-8") as f:
            json.dump({"mappings": serializable}, f, indent=2)

    # Helpers
    def mapping_lookup(self) -> Dict[str, Tuple[str, str]]:
        """Return dict: exe_lower -> (name, category)."""
        table: Dict[str, Tuple[str, str]] = {}
        for m in self.load_mappings():
            table[m.executable.lower()] = (m.name, m.category)
        return table
