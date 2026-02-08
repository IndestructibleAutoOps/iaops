from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import ensure_dir, write_text


class Patcher:
    def __init__(self, project_root: Path, allow_writes: bool):
        self.root = project_root
        self.allow_writes = allow_writes

    def apply(self, plan: dict[str, Any]) -> dict[str, Any]:
        actions = plan.get("actions", [])
        applied: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        for a in actions:
            kind = a.get("kind")
            if kind == "write_file_if_missing":
                rel = a["path"]
                p = self.root / rel
                if p.exists():
                    skipped.append({"action": a, "reason": "exists"})
                    continue
                if not self.allow_writes:
                    skipped.append({"action": a, "reason": "writes_disabled"})
                    continue
                ensure_dir(p.parent)
                write_text(p, f"# generated placeholder: {rel}\n")
                applied.append({"action": a})
                continue
            skipped.append({"action": a, "reason": "unsupported"})
        return {
            "ok": True,
            "allowWrites": self.allow_writes,
            "applied": applied,
            "skipped": skipped,
        }
