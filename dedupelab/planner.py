# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Allaun

from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any
import csv

def ensure_unique(dst: Path) -> Path:
    if not dst.exists():
        return dst
    stem, suf = dst.stem, dst.suffix
    parent = dst.parent
    i = 1
    while True:
        cand = parent / f"{stem} ({i}){suf}"
        if not cand.exists():
            return cand
        i += 1

def write_plan_csv(rows: List[Dict[str,str]], out: Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["status","op","src_path","dst_path","content_id","reason","rollback_key","ts"]
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)
