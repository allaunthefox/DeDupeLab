# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Allaun

import json
from pathlib import Path
from .deps import check_dep


def _load_schema(schema_path: Path):
    return json.loads(schema_path.read_text(encoding="utf-8"))


def get_schema(name: str):
    """
    Load schema by name.
    
    Args:
        name: Schema name (e.g., "deduplab_meta_v4")
        
    Returns:
        Schema dictionary
    """
    # Default to v4, fallback to v3 if v4 not found
    if name == "deduplab_meta_v4" or name == "v4":
        p = Path(__file__).parent / "schemas" / "deduplab_meta_v4.schema.json"
        if p.exists():
            return _load_schema(p)
    
    # Fallback to v3
    p = Path(__file__).parent / "schemas" / "deduplab_meta_v3.schema.json"
    return _load_schema(p)


def validate_meta_dict(meta: dict):
    """
    Validate metadata dictionary against schema.
    
    Uses jsonschema if available, falls back to structural checks.
    
    Args:
        meta: Metadata dictionary to validate
        
    Returns:
        Tuple of (is_valid: bool, error_message: str or None)
    """
    spec = meta.get("spec", "deduplab_meta_v3")
    
    # Try jsonschema validation
    if check_dep("jsonschema"):
        try:
            from jsonschema import Draft202012Validator
            Draft202012Validator(get_schema(spec)).validate(meta)
            return True, None
        except Exception as e:
            return False, str(e)
    
    # Fallback: structural checks only
    try:
        assert isinstance(meta, dict), "meta must be object"
        
        for k in ("spec", "generated_at", "folder_rel", "summary", "entries"):
            assert k in meta, f"missing key: {k}"
        
        assert meta.get("spec") in ["deduplab_meta_v3", "deduplab_meta_v4"], "spec mismatch"
        assert isinstance(meta["entries"], list), "entries must be list"
        
        # Validate entries structure
        for entry in meta["entries"]:
            assert isinstance(entry, dict), "entry must be object"
            for k in ("name", "size", "sha256", "mime", "category"):
                assert k in entry, f"entry missing key: {k}"
            
            # Validate sha256 format
            assert len(entry["sha256"]) == 64, "sha256 must be 64 chars"
            assert all(c in "0123456789abcdefABCDEF" for c in entry["sha256"]), "sha256 must be hex"
        
        return True, None
        
    except Exception as e2:
        return False, f"Structural validation failed: {e2}"