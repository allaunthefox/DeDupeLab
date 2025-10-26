# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Allaun

from __future__ import annotations
import json, shutil
from pathlib import Path
from .planner import ensure_unique

def rollback_from_checkpoint(checkpoint: Path):
    manifest = json.loads(checkpoint.read_text(encoding="utf-8"))
    moves = manifest.get("moves", [])
    restored = 0
    errors = 0
    for mv in reversed(moves):
        src_now = Path(mv["dst"])
        dst_restore = Path(mv["src"])
        try:
            dst_restore.parent.mkdir(parents=True, exist_ok=True)
            if dst_restore.exists():
                dst_restore = ensure_unique(dst_restore)
            if src_now.exists():
                shutil.move(str(src_now), str(dst_restore))
                restored += 1
        except Exception:
            errors += 1
    return {"restored": restored, "errors": errors}
