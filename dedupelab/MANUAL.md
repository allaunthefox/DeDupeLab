# Dedupelab v6.3 — Contextual Hashing Edition

## Overview
Dedupelab is a self-contained, autonomous file cataloging and deduplication engine.
It creates validated, RFC 8259–compliant `meta.json` manifests for every folder, summarizing structure and meaning.
It is self-linting, self-validating, and portable.

## 🔒 Hashing and Deduplication Policy

### Default Algorithm
- **SHA-256** is the only hash algorithm used.
- Hashes are stored as lowercase hex (64 characters).
- All operations—integrity, deduplication, and export—use the same hash.

### Context Tags
To prevent cross-context confusion, every file includes a `context_tag`:
- `unarchived` → regular file in the filesystem
- `archived` → file contained within an archive (`.zip`, `.7z`, `.tar`, `.rar`, etc.)

Dedupelab treats `(sha256, context_tag)` as its unique identity key.

| Example | sha256 | context_tag | Result |
|----------|---------|-------------|---------|
| same file on disk | `abc123...` | `unarchived` | duplicate |
| same file inside ZIP | `abc123...` | `archived` | separate entity |

### Database Schema
The internal database now uses:
```sql
CREATE TABLE files (
    path TEXT PRIMARY KEY,
    size INTEGER,
    mtime INTEGER,
    sha256 TEXT,
    mime TEXT,
    context_tag TEXT DEFAULT 'unarchived'
);
CREATE UNIQUE INDEX idx_files_hash_ctx ON files (sha256, context_tag);
```

## 📄 Metadata Schema (`meta_v4`)

A new field, `context_tag`, extends the manifest specification.

```json
{
  "name": "IMG_1204.JPG",
  "size": 2837423,
  "mtime": 1730090400,
  "sha256": "1f3cbe02b1a5a73d9b8b8a2c248a693a2c6bbf2aeb8ecbb92b09db4a6c420e19",
  "mime": "image/jpeg",
  "category": "image",
  "subtype": "photo",
  "topic": "beach",
  "context_tag": "unarchived"
}
```

The corresponding JSON Schema lives at:
```
deduplab/schemas/deduplab_meta_v4.schema.json
```
and conforms to JSON Schema Draft 2020-12.

## ⚡ Acceleration Layer

If detected, Dedupelab automatically uses:
1. **cuDF (GPU acceleration)**
2. **pandas (CPU dataframe acceleration)**
3. **builtin (pure Python fallback)**

No configuration required.

## 🧪 Validation & Linting

Every manifest is validated before being written.
- If invalid → written as `meta.invalid.json`
- Syntax of all Python modules is re-linted on startup and shutdown
- Runs even in minimal Python (no extra dependencies)

## 📜 Example Manifest

```json
{
  "spec": "deduplab_meta_v4",
  "generated_at": "2025-10-25T20:45:00Z",
  "folder_rel": "Photos/2022_Vacation",
  "summary": {
    "files_total": 248,
    "bytes_total": 1348723982,
    "categories": {"image":236,"video":8,"document":4},
    "topics": ["vacation","beach","family"],
    "keywords": ["Hawaii","Canon","IMG_","sunset"]
  },
  "entries": [
    {
      "name": "IMG_1204.JPG",
      "size": 2837423,
      "mtime": 1730090400,
      "sha256": "1f3cbe02b1a5a73d9b8b8a2c248a693a2c6bbf2aeb8ecbb92b09db4a6c420e19",
      "mime": "image/jpeg",
      "category": "image",
      "subtype": "photo",
      "topic": "beach",
      "context_tag": "unarchived"
    }
  ]
}
```

## ⚙️ Configuration Defaults (`deduplab.yml`)
```yaml
export_folder_meta: true
meta_format: deduplab_meta_v4
meta_pretty: false
meta_validate_schema: true
meta_auto_validate_startup: true
meta_auto_validate_shutdown: true
```

## 🚀 Usage

### Basic scan
```bash
deduplab scan --root /path/to/archive
```

### Rebuild DB from metas
```bash
deduplab rebuild --root /path/to/archive
```

### Validate all manifests
```bash
deduplab validate --root /path/to/archive
```

## 🧭 Philosophy
Dedupelab is designed for **autonomy and recoverability**:
- Every folder describes itself.
- Every meta.json is schema-valid and human-readable.
- If the code is lost, the metadata remains a map of meaning.