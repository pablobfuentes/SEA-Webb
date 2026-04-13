from __future__ import annotations

import json
import os
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


class JsonRepository:
    """Local JSON persistence with atomic replace on write."""

    def __init__(self, base_path: str | Path) -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def exists(self, relative_path: str) -> bool:
        return (self.base_path / relative_path).is_file()

    def write(self, relative_path: str, payload: Any) -> Path:
        """Write JSON atomically (temp file in target directory, then os.replace)."""
        target = self.base_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        serializable = asdict(payload) if is_dataclass(payload) else payload
        text = json.dumps(serializable, indent=2, ensure_ascii=False)
        tmp = target.with_name(target.name + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, target)
        return target

    def read_json(self, relative_path: str) -> Any:
        """Load JSON (object or array). Malformed files raise ValueError."""
        path = self.base_path / relative_path
        raw = path.read_text(encoding="utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {relative_path}: {e}") from e

    def read(self, relative_path: str) -> dict[str, Any]:
        """Load a JSON object. Raises if root is not an object."""
        data = self.read_json(relative_path)
        if not isinstance(data, dict):
            raise ValueError(f"Expected JSON object in {relative_path}, got {type(data).__name__}")
        return data
