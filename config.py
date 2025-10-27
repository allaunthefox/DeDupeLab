# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Allaun

import yaml
from pathlib import Path

DEFAULTS = {
    "hash_algo": "sha256",
    "dedup_strategy": "content_hash",
    "parallelism": 0,  # 0 = auto-detect
    "dry_run": True,
    "overwrite": False,
    "checkpoint": True,
    "ignore_patterns": [".git", "node_modules", "__pycache__", ".deduplab_duplicates"],
    "nsfw": {"enabled": False, "threshold": 2, "auto_quarantine": False},
    "logging": {"rotate_mb": 10, "keep": 7, "level": "INFO"},
    "db_path": "output/index.db",
    "log_dir": "output/logs",
    "metrics_path": "output/metrics.json",
    "export_folder_meta": True,
    "meta_format": "deduplab_meta_v4",
    "meta_pretty": False,
    "meta_validate_schema": True,
    "meta_auto_validate_startup": True,
    "meta_auto_validate_shutdown": True,
    "auto_install_deps": True
}


def ensure_config(path="deduplab.yml"):
    """Create default configuration file if it doesn't exist."""
    p = Path(path)
    if not p.exists():
        p.write_text(
            "# Auto-generated config. Edit as needed.\n" +
            yaml.safe_dump(DEFAULTS, sort_keys=False),
            encoding="utf-8"
        )


def load_config(path="deduplab.yml"):
    """
    Load configuration with environment auto-tuning.
    
    Args:
        path: Path to configuration file
        
    Returns:
        Configuration dictionary with environment optimizations applied
    """
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
    
    # Apply environment auto-tuning
    try:
        from .environment import Environment
        env = Environment()
        cfg = env.apply_to_config(cfg)
    except Exception as e:
        print(f"[config][WARN] Environment detection failed: {e}")
    
    return cfg