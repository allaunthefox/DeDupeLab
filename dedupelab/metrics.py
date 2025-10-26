# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Allaun

from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime

def _iso_now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

class Metrics:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.data = {
            "ts": _iso_now(),
            "files_scanned": 0,
            "bytes_scanned": 0,
            "duplicates_found": 0,
            "planned_ops": 0,
            "apply": {"attempted": 0, "succeeded": 0, "skipped": 0, "errors": 0, "bytes_moved": 0},
            "durations": {}
        }

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
