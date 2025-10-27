# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Allaun

import argparse
import json
import sys
import time
import csv
import atexit
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from .config import load_config
from .db import DB
from .scanner import threaded_hash
from .meta_exporter import write_folder_meta
from .accelerator import DataFrameWrapper
from .planner import ensure_unique, write_plan_csv
from .applier import apply_moves
from .rollback import rollback_from_checkpoint
from .logger import JsonlLogger
from .metrics import Metrics
from .bootstrap import lint_tree
from .deps import init_deps
from . import __version__


def _iso_now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def cmd_scan(args, cfg):
    """
    Scan command: discover files, compute hashes, export metadata.
    
    Complete implementation with meta export integration.
    """
    db = DB(Path(cfg["db_path"]))
    logger = JsonlLogger(
        Path(cfg["log_dir"]), 
        rotate_mb=cfg["logging"]["rotate_mb"], 
        keep=cfg["logging"]["keep"]
    )
    metrics = Metrics(Path(cfg["metrics_path"]))
    
    # Log scan start
    logger.log("INFO", "scan_start", 
               roots=list(args.root), 
               parallelism=cfg["parallelism"],
               export_meta=cfg.get("export_folder_meta", False))
    
    # Execute scan
    records, dur, total = threaded_hash(
        args.root, 
        cfg["ignore_patterns"], 
        workers=cfg["parallelism"]
    )
    
    # Store in database
    db.upsert_files(records)
    
    # Calculate metrics
    dfw = DataFrameWrapper([{
        "path": r[0], 
        "size": r[1], 
        "mtime": r[2], 
        "sha256": r[3], 
        "mime": r[4],
        "context_tag": r[5]
    } for r in records])
    
    bytes_scanned = dfw.sum("size")
    
    metrics.data["files_scanned"] = total
    metrics.data["bytes_scanned"] = int(bytes_scanned)
    metrics.data["durations"]["scan_s"] = round(dur, 3)
    
    # META EXPORT INTEGRATION
    if cfg.get("export_folder_meta", False):
        logger.log("INFO", "meta_export_start", directories="calculating")
        
        # Group files by directory
        by_dir = defaultdict(list)
        
        for rec in records:
            path_obj = Path(rec[0])
            dir_path = path_obj.parent
            
            file_record = {
                "name": path_obj.name,
                "size": rec[1],
                "mtime": rec[2],
                "sha256": rec[3],
                "mime": rec[4],
                "context_tag": rec[5]
            }
            
            by_dir[dir_path].append(file_record)
        
        # Export meta.json for each directory
        meta_count = 0
        meta_errors = 0
        
        for dir_path, file_recs in by_dir.items():
            try:
                write_folder_meta(
                    folder_path=dir_path,
                    file_records=file_recs,
                    root_path=Path(args.root[0]),
                    pretty=cfg.get("meta_pretty", False),
                    silent=True
                )
                meta_count += 1
            except Exception as e:
                meta_errors += 1
                logger.log("ERROR", "meta_export_failed", 
                          directory=str(dir_path), 
                          error=str(e))
        
        metrics.data["meta_exported"] = meta_count
        metrics.data["meta_errors"] = meta_errors
        
        logger.log("INFO", "meta_export_done", 
                  directories=meta_count, 
                  errors=meta_errors)
    
    # Save metrics
    metrics.save()
    
    # Final log
    logger.log("INFO", "scan_done", 
              files=total, 
              bytes=bytes_scanned, 
              duration_s=round(dur, 3))
    
    # Console output
    print(f"[scan] files={total} bytes={bytes_scanned} dur_s={round(dur,3)} → {cfg['db_path']}")
    
    if cfg.get("export_folder_meta", False):
        print(f"[scan] meta.json exported to {metrics.data.get('meta_exported', 0)} directories")
    
    return 0


def cmd_plan(args, cfg):
    """Plan command - compute duplicate moves (context-aware)."""
    db = DB(Path(cfg["db_path"]))
    logger = JsonlLogger(
        Path(cfg["log_dir"]), 
        rotate_mb=cfg["logging"]["rotate_mb"], 
        keep=cfg["logging"]["keep"]
    )
    metrics = Metrics(Path(cfg["metrics_path"]))

    dups = db.get_duplicates()
    ts = _iso_now()
    rows = []
    rbk = 0
    
    for sha, context_tag, paths_csv in dups:
        paths = sorted(paths_csv.split("|"))
        keeper = paths[0]
        
        for src in paths[1:]:
            srcp = Path(src)
            dup_dir = srcp.parent / ".deduplab_duplicates"
            dst = ensure_unique(dup_dir / srcp.name)
            
            rows.append({
                "status": "planned",
                "op": "move",
                "src_path": src,
                "dst_path": str(dst),
                "content_id": f"b3:sha256:{sha}:ctx:{context_tag}",
                "reason": "dedup",
                "rollback_key": f"rbk:{rbk:06d}",
                "ts": ts
            })
            rbk += 1
    
    write_plan_csv(rows, Path(args.out))
    metrics.data["duplicates_found"] = len(dups)
    metrics.data["planned_ops"] = len(rows)
    metrics.save()
    
    logger.log("INFO", "plan_done", duplicates=len(dups), planned=len(rows), out=str(args.out))
    print(f"[plan] duplicate_groups={len(dups)} planned_ops={len(rows)} → {args.out}")
    return 0


def cmd_apply(args, cfg):
    """Apply command - execute moves with three-phase commit."""
    logger = JsonlLogger(
        Path(cfg["log_dir"]), 
        rotate_mb=cfg["logging"]["rotate_mb"], 
        keep=cfg["logging"]["keep"]
    )
    metrics = Metrics(Path(cfg["metrics_path"]))

    rows = []
    with Path(args.plan).open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)

    dry = cfg["dry_run"] and (not args.force)
    res = apply_moves(rows, Path(args.checkpoint), dry_run=dry)
    
    metrics.data["apply"].update(res)
    metrics.save()

    logger.log("INFO", "apply_done", **res, dry_run=dry, checkpoint=str(args.checkpoint))
    print(f"[apply] {res} dry_run={dry} checkpoint={args.checkpoint}")
    
    return 0 if res["errors"] == 0 else 5


def cmd_rollback(args, cfg):
    """Rollback command - restore from checkpoint."""
    out = rollback_from_checkpoint(Path(args.checkpoint))
    print(f"[rollback] {out}")
    return 0 if out["errors"] == 0 else 5


def cmd_verify(args, cfg):
    """Verify command - check checkpoint integrity."""
    cp = Path(args.checkpoint)
    if not cp.exists():
        print(f"[verify] checkpoint not found: {cp}")
        return 5
    
    manifest = json.loads(cp.read_text(encoding="utf-8"))
    moves = manifest.get("moves", [])
    missing = []
    
    for mv in moves:
        if not Path(mv["dst"]).exists():
            missing.append(mv["dst"])
    
    result = {"checked": len(moves), "missing": missing}
    print(json.dumps(result, indent=2))
    
    return 0 if not missing else 5


def cmd_metrics(args, cfg):
    """Metrics command - display last run statistics."""
    mp = Path(cfg["metrics_path"])
    if mp.exists():
        print(mp.read_text(encoding="utf-8"))
        return 0
    print("{}")
    return 0


def main(argv=None):
    """
    Main entry point with complete startup/shutdown linting.
    
    Process:
    1. Initialize dependency manager
    2. Lint Python files at startup
    3. Register shutdown linting via atexit
    4. Load configuration
    5. Parse arguments and execute command
    """
    # Initialize dependency auto-installer
    dep_mgr = init_deps(auto_install=True, silent=False)
    
    # Startup linting
    module_dir = Path(__file__).parent
    try:
        lint_tree(module_dir)
    except SyntaxError as e:
        print(f"[fatal] Startup linting failed: {e}", file=sys.stderr)
        return 10
    
    # Register shutdown linting
    def shutdown_lint():
        try:
            lint_tree(module_dir)
        except Exception as e:
            print(f"[warn] Shutdown linting failed: {e}", file=sys.stderr)
    
    atexit.register(shutdown_lint)
    
    # Load configuration
    cfg = load_config()
    
    # Argument parsing
    parser = argparse.ArgumentParser(
        prog="deduplab",
        description="Context-aware file deduplication and organization system"
    )
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    
    sub = parser.add_subparsers(dest="cmd", required=True)

    # Scan command
    p_scan = sub.add_parser("scan", help="Discover files, compute hashes, detect context")
    p_scan.add_argument("--root", action="append", required=True, 
                        help="Root directory to scan (repeatable)")
    p_scan.set_defaults(_run=cmd_scan)

    # Plan command
    p_plan = sub.add_parser("plan", help="Compute duplicate moves (context-aware)")
    p_plan.add_argument("--out", required=True, help="CSV plan output path")
    p_plan.set_defaults(_run=cmd_plan)

    # Apply command
    p_apply = sub.add_parser("rename-apply", 
                             help="Apply plan with three-phase commit")
    p_apply.add_argument("--plan", required=True, help="Path to plan CSV")
    p_apply.add_argument("--checkpoint", required=True, 
                         help="Checkpoint manifest output path")
    p_apply.add_argument("--force", action="store_true", 
                         help="Override dry-run and execute filesystem changes")
    p_apply.set_defaults(_run=cmd_apply)

    # Rollback command
    p_rb = sub.add_parser("rollback", help="Restore files from checkpoint")
    p_rb.add_argument("--checkpoint", required=True, help="Checkpoint file path")
    p_rb.set_defaults(_run=cmd_rollback)

    # Verify command
    p_vf = sub.add_parser("verify", help="Verify checkpoint integrity")
    p_vf.add_argument("--checkpoint", required=True, help="Checkpoint to verify")
    p_vf.set_defaults(_run=cmd_verify)

    # Metrics command
    p_mt = sub.add_parser("metrics", help="Display last run metrics")
    p_mt.set_defaults(_run=cmd_metrics)

    # Parse and execute
    args = parser.parse_args(argv)
    
    try:
        rc = args._run(args, cfg)
    except KeyboardInterrupt:
        print("\n[fatal] Interrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"[fatal] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 10
    
    return rc


if __name__ == "__main__":
    sys.exit(main())