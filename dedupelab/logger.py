# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Allaun

from __future__ import annotations
import json, os, time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

def _iso_now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

class JsonlLogger:
    def __init__(self, log_dir: Path, rotate_mb: int = 10, keep: int = 7):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self.path = self.log_dir / f"run_{stamp}.log.jsonl"
        self.rotate_bytes = rotate_mb * 1024 * 1024
        self.keep = keep

    def _maybe_rotate(self):
        logs = sorted(self.log_dir.glob("run_*.log.jsonl"))
        if len(logs) > self.keep:
            for p in logs[:-self.keep]:
                try: p.unlink()
                except: pass

    def log(self, level: str, event: str, **fields):
        rec = {"ts": _iso_now(), "level": level, "event": event}
        rec.update(fields)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if self.path.exists() and self.path.stat().st_size > self.rotate_bytes:
            # create a new file on next write by renaming current with .1 suffix
            rotated = self.path.with_suffix(".1")
            try:
                if rotated.exists(): rotated.unlink()
                self.path.rename(rotated)
            except: pass
        self._maybe_rotate()
