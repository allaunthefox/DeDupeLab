# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Allaun

from __future__ import annotations
import shutil
import os
import hashlib
import time
import json
import sys
from pathlib import Path
from typing import List, Dict

CHUNK = 1024 * 1024  # 1MB chunks for I/O


def _sha256_file(p: Path) -> str:
    """
    Compute SHA-256 hash of file.
    
    Args:
        p: Path to file
        
    Returns:
        Lowercase hex digest (64 characters)
    """
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_verify_delete(src: Path, dst: Path) -> int:
    """
    Three-phase commit for safe file moves across devices.
    
    Phase 1: Copy to temporary destination
    Phase 2: Verify hash integrity
    Phase 3: Atomic rename and delete source
    
    This ensures:
    - No data loss if verification fails
    - No orphaned files if process crashes
    - Atomic final commit
    
    Args:
        src: Source file path
        dst: Destination file path
        
    Returns:
        Number of bytes moved
        
    Raises:
        RuntimeError: If copy fails, verification fails, or cleanup fails
    """
    # Generate temporary destination name
    dst_tmp = dst.with_suffix(dst.suffix + '.tmp')
    size = 0
    
    try:
        # Ensure destination directory exists
        dst.parent.mkdir(parents=True, exist_ok=True)
        
        # Get source file size before copy
        size = src.stat().st_size
        
        # PHASE 1: Copy to temporary file
        try:
            with src.open("rb") as s, dst_tmp.open("wb") as d:
                shutil.copyfileobj(s, d, length=CHUNK)
        except Exception as e:
            raise RuntimeError(f"Copy failed: {src} → {dst_tmp}: {e}")
        
        # Force fsync to ensure data is on disk
        try:
            with dst_tmp.open("rb+") as f:
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            dst_tmp.unlink(missing_ok=True)
            raise RuntimeError(f"Fsync failed for {dst_tmp}: {e}")
        
        # PHASE 2: Verify hash integrity
        src_hash = _sha256_file(src)
        dst_hash = _sha256_file(dst_tmp)
        
        if src_hash != dst_hash:
            # Verification failed - cleanup temp file
            dst_tmp.unlink(missing_ok=True)
            raise RuntimeError(
                f"Hash mismatch after copy:\n"
                f"  Source: {src} ({src_hash})\n"
                f"  Dest:   {dst_tmp} ({dst_hash})"
            )
        
        # PHASE 3: Commit - atomic rename then delete source
        try:
            # Atomic rename (on same filesystem this is guaranteed atomic)
            dst_tmp.rename(dst)
        except Exception as e:
            # Rename failed - cleanup temp file
            dst_tmp.unlink(missing_ok=True)
            raise RuntimeError(f"Atomic rename failed: {dst_tmp} → {dst}: {e}")
        
        # Now safe to delete source (destination is verified and committed)
        try:
            src.unlink()
        except Exception as e:
            # Source deletion failed, but destination is safe
            # Log warning but don't raise - user can manually delete source
            print(
                f"[applier][WARN] Source deletion failed (destination is safe): {src}: {e}",
                file=sys.stderr
            )
        
        return size
        
    except Exception as e:
        # Ensure no temporary files are left behind
        if dst_tmp.exists():
            try:
                dst_tmp.unlink()
            except:
                pass  # Best effort cleanup
        raise


def apply_moves(rows: List[Dict[str, str]], checkpoint: Path, dry_run: bool) -> Dict[str, int]:
    """
    Apply planned file moves with checkpoint creation.
    
    Args:
        rows: List of plan records from CSV (must have 'op', 'status', 'src_path', 'dst_path')
        checkpoint: Path to write checkpoint manifest
        dry_run: If True, simulate moves without actual filesystem changes
        
    Returns:
        Dictionary with execution statistics:
        {
            'attempted': int,
            'succeeded': int,
            'skipped': int,
            'errors': int,
            'bytes_moved': int,
            'dry_run': bool
        }
    """
    from .planner import ensure_unique
    
    applied = []
    attempted = 0
    skipped = 0
    errors = 0
    bytes_moved = 0
    
    for row in rows:
        # Only process 'move' operations that are 'planned'
        if row.get("op") != "move" or row.get("status") != "planned":
            continue
        
        src = Path(row["src_path"])
        dst = Path(row["dst_path"])
        attempted += 1
        
        try:
            # Skip if source doesn't exist
            if not src.exists():
                skipped += 1
                print(f"[applier][WARN] Source not found: {src}", file=sys.stderr)
                continue
            
            # Ensure destination directory exists
            dst.parent.mkdir(parents=True, exist_ok=True)
            
            # Handle destination conflicts
            if dst.exists():
                original_dst = dst
                dst = ensure_unique(dst)
                print(
                    f"[applier][INFO] Destination exists, using unique name:\n"
                    f"  Original: {original_dst}\n"
                    f"  New:      {dst}",
                    file=sys.stderr
                )
            
            if dry_run:
                # Simulate move
                size = src.stat().st_size
                print(f"[applier][DRY-RUN] Would move: {src} → {dst} ({size} bytes)")
            else:
                # Execute actual move
                size = copy_verify_delete(src, dst)
                bytes_moved += size
                
                # Record successful move
                applied.append({
                    "src": str(src),
                    "dst": str(dst),
                    "size": size,
                    "timestamp": time.time()
                })
                
                print(f"[applier][OK] Moved: {src} → {dst} ({size} bytes)")
                
        except Exception as e:
            errors += 1
            print(
                f"[applier][ERROR] Failed to move {src} → {dst}: {e}",
                file=sys.stderr
            )
    
    # Write checkpoint manifest
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    
    manifest = {
        "timestamp": time.time(),
        "dry_run": dry_run,
        "statistics": {
            "attempted": attempted,
            "succeeded": len(applied),
            "skipped": skipped,
            "errors": errors,
            "bytes_moved": bytes_moved
        },
        "moves": applied
    }
    
    checkpoint.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    
    return {
        "attempted": attempted,
        "succeeded": len(applied),
        "skipped": skipped,
        "errors": errors,
        "bytes_moved": bytes_moved,
        "dry_run": dry_run
    }