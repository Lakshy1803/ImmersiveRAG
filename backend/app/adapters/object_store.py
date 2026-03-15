from __future__ import annotations

from pathlib import Path
from uuid import uuid4


class LocalObjectStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, filename: str, payload: bytes) -> str:
        target = self.root / f"{uuid4().hex}_{filename}"
        target.write_bytes(payload)
        return str(target)
