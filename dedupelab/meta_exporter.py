# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Allaun

import json, time, mimetypes
from pathlib import Path
from collections import Counter, defaultdict
from .categorizer import categorize_file
from .accelerator import DataFrameWrapper
from .validator import validate_meta_dict

def _iso_now():
    import datetime
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def write_folder_meta(folder_path: Path, file_records: list, root_path: Path, pretty: bool=False, silent: bool=True):
    """Write deduplab_meta_v3 meta.json for a folder. file_records: list of dicts with name,size,mtime,sha256,mime"""
    cats = Counter([categorize_file(r["mime"], r["name"])["category"] for r in file_records])
    topics = []
    keywords = set()
    for r in file_records:
        c = categorize_file(r["mime"], r["name"])
        if c.get("topic"): topics.append(c["topic"])
        # Keywords from filename tokens
        for tok in Path(r["name"]).stem.replace("_"," ").replace("-"," ").split():
            if tok and tok.isascii() and tok[0].isalpha() and len(tok) >= 3:
                keywords.add(tok[:32])
    topics = sorted({t for t in topics if t})[:8]
    keywords = sorted(list(keywords))[:16]

    meta = {
        "spec": "deduplab_meta_v3",
        "generated_at": _iso_now(),
        "folder_rel": str(folder_path.relative_to(root_path)) if folder_path != root_path else ".",
        "parent_rel": (str(folder_path.parent.relative_to(root_path)) if folder_path != root_path else None),
        "summary": {
            "files_total": len(file_records),
            "bytes_total": sum(int(r["size"]) for r in file_records),
            "categories": dict(cats),
            "topics": topics,
            "keywords": keywords
        },
        "entries": []
    }
    for r in file_records:
        c = categorize_file(r["mime"], r["name"])
        meta["entries"].append({
            "name": r["name"],
            "size": int(r["size"]),
            "mtime": int(r["mtime"]),
            "sha256": r["sha256"],
            "mime": r["mime"],
            "category": c["category"],
            "subtype": c["subtype"],
            "topic": c["topic"]
        })

    ok, err = validate_meta_dict(meta)
    meta_path = folder_path / "meta.json"
    if ok:
        tmp = meta_path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8", newline="\\n") as f:
            if pretty:
                json.dump(meta, f, ensure_ascii=False, sort_keys=True, indent=2)
            else:
                json.dump(meta, f, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            f.write("\\n")
        tmp.replace(meta_path)
    else:
        bad = meta_path.with_suffix(".invalid.json")
        with open(bad, "w", encoding="utf-8", newline="\\n") as f:
            json.dump(meta, f, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            f.write("\\n")
        # Silent unless needed; if not silent, print error
        if not silent:
            print(f"[meta][INVALID] {folder_path}: {err}")
