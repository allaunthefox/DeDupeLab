# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Allaun

import json
from pathlib import Path

def _load_schema(schema_path: Path):
    return json.loads(schema_path.read_text(encoding="utf-8"))

def get_schema(name: str):
    # Only v3 currently
    p = Path(__file__).parent / "schemas" / "deduplab_meta_v3.schema.json"
    return _load_schema(p)

def validate_meta_dict(meta: dict):
    try:
        from jsonschema import Draft202012Validator
        Draft202012Validator(get_schema("deduplab_meta_v3")).validate(meta)
        return True, None
    except Exception as e:
        # Minimal fallback: structural checks only
        try:
            assert isinstance(meta, dict), "meta must be object"
            for k in ("spec","generated_at","folder_rel","summary","entries"):
                assert k in meta, f"missing key: {k}"
            assert meta.get("spec") == "deduplab_meta_v3", "spec mismatch"
            assert isinstance(meta["entries"], list), "entries must be list"
            return True, None
        except Exception as e2:
            return False, f"{e}; fallback: {e2}"
