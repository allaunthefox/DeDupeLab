# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Allaun

from __future__ import annotations
import shutil, os, hashlib, time, json
from pathlib import Path
from typing import List, Dict
from .planner import ensure_unique

CHUNK = 1024 * 1024

def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()

def copy_verify_delete(src: Path, dst: Path) -> int:
    # Returns bytes moved; 0 if nothing
    if src.resolve().anchor != dst.resolve().anchor:
        # Cross-device likely; do copy-verify-delete
        size = src.stat().st_size
        with src.open("rb") as s, dst.open("wb") as d:
            shutil.copyfileobj(s, d, length=CHUNK)
        # fsync destination
        with dst.open("rb+") as d2:
            d2.flush(); os.fsync(d2.fileno())
        if _sha256_file(src) != _sha256_file(dst):
            dst.unlink(missing_ok=True)
            raise RuntimeError("hash mismatch after copy")
        src.unlink()
        return size
    else:
        # Same device; rename is atomic
        shutil.move(str(src), str(dst))
        return src.stat().st_size if src.exists() else 0

def apply_moves(rows: List[Dict[str,str]], checkpoint: Path, dry_run: bool):
    applied = []
    attempted = 0
    skipped = 0
    errors = 0
    bytes_moved = 0
    for row in rows:
        if row.get("op") != "move" or row.get("status") != "planned":
            continue
        src = Path(row["src_path"])
        dst = Path(row["dst_path"])
        attempted += 1
        try:
            if not src.exists():
                skipped += 1
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                dst = ensure_unique(dst)
            if dry_run:
                pass
            else:
                bytes_moved += copy_verify_delete(src, dst)
                applied.append({"src": str(src), "dst": str(dst)})
        except Exception as e:
            errors += 1
    # write checkpoint
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    checkpoint.write_text(json.dumps({"ts": time.time(), "moves": applied}, indent=2), encoding="utf-8")
    return {"attempted": attempted, "succeeded": len(applied), "skipped": skipped, "errors": errors, "bytes_moved": bytes_moved}
