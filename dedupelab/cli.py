# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Allaun

import argparse, json, sys, time, csv, mimetypes
from pathlib import Path
from datetime import datetime

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

def _iso_now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def cmd_scan(args, cfg):
    db = DB(Path(cfg["db_path"]))
    logger = JsonlLogger(Path(cfg["log_dir"]), rotate_mb=cfg["logging"]["rotate_mb"], keep=cfg["logging"]["keep"])
    metrics = Metrics(Path(cfg["metrics_path"]))

    logger.log("INFO", "scan_start", roots=list(args.root), parallelism=cfg["parallelism"])
    records, dur, total = threaded_hash(args.root, cfg["ignore_patterns"], workers=cfg["parallelism"])
    db.upsert_files(records)
    dfw = DataFrameWrapper([{"path": r[0], "size": r[1], "mtime": r[2], "sha256": r[3], "mime": r[4]} for r in records])
    bytes_scanned = dfw.sum("size")
    metrics.data["files_scanned"] = total
    metrics.data["bytes_scanned"] = int(bytes_scanned)
    metrics.data["durations"]["scan_s"] = round(dur, 3)
    metrics.save()
    logger.log("INFO", "scan_done", files=total, bytes=bytes_scanned, duration_s=round(dur,3))
    print(f"[scan] files={total} bytes={bytes_scanned} dur_s={round(dur,3)} → {cfg['db_path']}")
    return 0

def cmd_plan(args, cfg):
    db = DB(Path(cfg["db_path"]))
    logger = JsonlLogger(Path(cfg["log_dir"]), rotate_mb=cfg["logging"]["rotate_mb"], keep=cfg["logging"]["keep"])
    metrics = Metrics(Path(cfg["metrics_path"]))

    dups = db.get_duplicates()
    ts = _iso_now()
    rows = []
    rbk = 0
    for sha, paths_csv in dups:
        paths = sorted(paths_csv.split(","))
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
                "content_id": f"b3:sha256:{sha}",
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
    print(f"[plan] duplicates_groups={len(dups)} planned_ops={len(rows)} → {args.out}")
    return 0

def cmd_apply(args, cfg):
    logger = JsonlLogger(Path(cfg["log_dir"]), rotate_mb=cfg["logging"]["rotate_mb"], keep=cfg["logging"]["keep"])
    metrics = Metrics(Path(cfg["metrics_path"]))

    rows = []
    with Path(args.plan).open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r: rows.append(row)

    dry = cfg["dry_run"] and (not args.force)
    res = apply_moves(rows, Path(args.checkpoint), dry_run=dry)
    metrics.data["apply"].update(res)
    metrics.save()

    logger.log("INFO", "apply_done", **res, dry_run=dry, checkpoint=str(args.checkpoint))
    print(f"[apply] {res} dry_run={dry} checkpoint={args.checkpoint}")
    return 0 if res["errors"] == 0 else 5

def cmd_rollback(args, cfg):
    out = rollback_from_checkpoint(Path(args.checkpoint))
    print(f"[rollback] {out}")
    return 0 if out["errors"] == 0 else 5

def cmd_verify(args, cfg):
    # Minimal verify: check that all moves in the last checkpoint still exist at dst
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
    print(json.dumps({"checked": len(moves), "missing": missing}, indent=2))
    return 0 if not missing else 5

def cmd_metrics(args, cfg):
    mp = Path(cfg["metrics_path"])
    if mp.exists():
        print(mp.read_text(encoding="utf-8"))
        return 0
    print("{}")
    return 0

def main(argv=None):
    cfg = load_config()
    parser = argparse.ArgumentParser(prog="dedupelab")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_scan = sub.add_parser("scan", help="Discover files and compute content IDs (threaded).")
    p_scan.add_argument("--root", action="append", required=True, help="Root directory to scan.")
    p_scan.set_defaults(_run=cmd_scan)

    p_plan = sub.add_parser("plan", help="Compute moves for duplicates and write CSV plan.")
    p_plan.add_argument("--out", required=True, help="CSV plan path to write.")
    p_plan.set_defaults(_run=cmd_plan)

    p_apply = sub.add_parser("rename-apply", help="Apply a CSV plan with checkpointing (copy-verify-delete).")
    p_apply.add_argument("--plan", required=True, help="Path to the plan CSV.")
    p_apply.add_argument("--checkpoint", required=True, help="Checkpoint file path to write.")
    p_apply.add_argument("--force", action="store_true", help="Override default dry-run and actually mutate the filesystem.")
    p_apply.set_defaults(_run=cmd_apply)

    p_rb = sub.add_parser("rollback", help="Rollback a previous apply using its checkpoint manifest.")
    p_rb.add_argument("--checkpoint", required=True, help="Checkpoint file to use.")
    p_rb.set_defaults(_run=cmd_rollback)

    p_vf = sub.add_parser("verify", help="Verify that applied moves still exist and are consistent.")
    p_vf.add_argument("--checkpoint", required=True, help="Checkpoint manifest to verify.")
    p_vf.set_defaults(_run=cmd_verify)

    p_mt = sub.add_parser("metrics", help="Show last run metrics JSON.")
    p_mt.set_defaults(_run=cmd_metrics)

    args = parser.parse_args(argv)
    try:
        rc = args._run(args, cfg)
    except Exception as e:
        print(f"[fatal] {e}", file=sys.stderr)
        return 10
        lint_tree(Path(__file__).parent)  # lint end
    return rc

if __name__ == "__main__":
    sys.exit(main())
