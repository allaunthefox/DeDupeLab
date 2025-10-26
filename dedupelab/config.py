# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Allaun

import yaml, json
from pathlib import Path

DEFAULTS = {
    "hash_algo": "sha256",
    "dedup_strategy": "content_hash",
    "parallelism": 4,
    "dry_run": True,
    "overwrite": False,
    "checkpoint": True,
    "ignore_patterns": [".git", "node_modules", "__pycache__", ".deduplab_duplicates"],
    "nsfw": {"enabled": False},
    "logging": {"rotate_mb": 10, "keep": 7, "level": "INFO"},
    "db_path": "output/index.db",
    "log_dir": "output/logs",
    "metrics_path": "output/metrics.json",
    "export_folder_meta": True,
    "meta_format": "deduplab_meta_v3",
    "meta_pretty": False,
    "meta_validate_schema": True,
    "meta_auto_validate_startup": True,
    "meta_auto_validate_shutdown": True
}

def ensure_config(path="dedupelab.yml"):
    p = Path(path)
    if not p.exists():
        p.write_text(
            "# Auto-generated config. Edit as needed.\n" +
            yaml.safe_dump(DEFAULTS, sort_keys=False),
            encoding="utf-8"
        )

def load_config(path="dedupelab.yml"):
    ensure_config(path)
    p = Path(path)
    cfg = DEFAULTS.copy()
    if p.exists():
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                cfg.update(data)
        except Exception as e:
            print(f"[config][WARN] Failed to load {path}: {e}")
    return cfg
