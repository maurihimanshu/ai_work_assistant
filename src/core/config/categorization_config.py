"""Core configuration for activity categorization."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, Optional


DEFAULT_CONFIG_DIR = os.path.join("data", "config")


@dataclass
class CategorizationConfig:
    """Holds application-to-category mappings and optional category weights."""

    exe_to_category: Dict[str, str]
    category_weights: Dict[str, float]

    @staticmethod
    def _basename_lower(path_or_name: str) -> str:
        base = (path_or_name or "").split("\\")[-1].split("/")[-1]
        return base.lower()

    @classmethod
    def load(cls, base_dir: str = DEFAULT_CONFIG_DIR) -> "CategorizationConfig":
        """Load config from JSON files under base_dir.

        - app_mappings.json: { "mappings": [ {"executable","name","category"}, ... ] }
        - categories.json:   { "categories": [...], "weights": {category: float} }
        """
        mappings_path = os.path.join(base_dir, "app_mappings.json")
        categories_path = os.path.join(base_dir, "categories.json")

        exe_to_category: Dict[str, str] = {}
        category_weights: Dict[str, float] = {}

        # Load mappings
        try:
            if os.path.exists(mappings_path):
                with open(mappings_path, "r", encoding="utf-8") as f:
                    payload = json.load(f) or {}
                for m in payload.get("mappings", []) or []:
                    exe = cls._basename_lower(m.get("executable") or "")
                    category = (m.get("category") or "").strip()
                    if exe and category:
                        exe_to_category[exe] = category
        except Exception:
            # Keep defaults on read error
            pass

        # Load optional weights
        try:
            if os.path.exists(categories_path):
                with open(categories_path, "r", encoding="utf-8") as f:
                    payload = json.load(f) or {}
                weights = payload.get("weights") or {}
                if isinstance(weights, dict):
                    # Only keep valid [0,1] floats
                    for k, v in weights.items():
                        try:
                            fv = float(v)
                            if 0.0 <= fv <= 1.0:
                                category_weights[str(k)] = fv
                        except Exception:
                            continue
        except Exception:
            pass

        return cls(exe_to_category=exe_to_category, category_weights=category_weights)

    def category_for_executable(self, path_or_name: str) -> Optional[str]:
        """Return configured category for executable path or name, if present."""
        return self.exe_to_category.get(self._basename_lower(path_or_name))
