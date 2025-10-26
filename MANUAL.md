# Dedupelab v6.0 Specification (spec_v1)

## 0. Metadata
- Spec-Version: 1.0
- Software-Version: 6.0
- License: Apache-2.0
- Author: Allaun
- Document-Type: Machine-readable operational specification

## 1. Overview
Dedupelab is a safety-first deduplication and file-organization engine.
It performs scanning, planning, application, rollback, and verification in discrete, auditable stages.
All operations are resumable, idempotent, and logged.
No system-specific assumptions are made regarding filesystem layout or path separators.

## 2. Safety Principles
| Key | Description |
|-----|--------------|
| Isolation | All file mutations occur only after explicit planning. |
| Dry-Run Default | All operations simulate behavior unless a --force flag overrides. |
| No Overwrite | Destination conflicts create uniquely suffixed paths. |
| Checkpoints | Every apply operation emits a manifest for rollback. |
| Verification | Copy operations verify content hashes before deletion. |
| Observability | All runs produce structured logs and metrics. |
| Idempotency | Re-running with unchanged data yields identical results. |
| Non-Destructive | Deletions never occur without verified backups or checkpoints. |

## 3. Configuration Specification

File: deduplab.yml  
Type: YAML key-value document.  
Autogeneration: If missing, created automatically with defaults.

| Key | Type | Default | Description |
|-----|------|----------|-------------|
| hash_algo | string | sha256 | Algorithm used for hashing. |
| dedup_strategy | string | content_hash | Strategy for detecting duplicates. |
| parallelism | integer | 4 | Worker threads for hashing. |
| dry_run | boolean | true | Prevents filesystem modification by default. |
| overwrite | boolean | false | Disables overwriting; always suffixes duplicates. |
| checkpoint | boolean | true | Enables checkpoint manifest creation. |
| ignore_patterns | list[string] | [ .git, node_modules, __pycache__, .deduplab_duplicates ] | Directories or files ignored during scans. |
| nsfw.enabled | boolean | false | Classification system toggle (currently inactive). |
| logging.rotate_mb | integer | 10 | Log rotation threshold (megabytes). |
| logging.keep | integer | 7 | Number of logs retained. |
| logging.level | string | INFO | Logging verbosity. |
| db_path | string | output/index.db | Path to SQLite index database. |
| log_dir | string | output/logs | Directory for JSONL logs. |
| metrics_path | string | output/metrics.json | File path for metrics output. |

All paths are logical and relative to the execution context unless explicitly absolute.

## 4. Command Specification

### 4.1 scan
Purpose: Traverse directories, hash files, and store metadata in the index database.  
Inputs: --root (repeatable string path)  
Outputs: Updated SQLite database at db_path.  
Side-Effects: Writes log entry and updates metrics file.  
Defaults: Uses parallel hashing as defined in parallelism.  
Error Codes: 0 success, 5 partial, 10 fatal.

### 4.2 plan
Purpose: Identify duplicate content in index and generate a move plan.  
Inputs: --out (string path to CSV).  
Outputs: rename_plan.csv containing planned moves.  
Side-Effects: Updates metrics (duplicates_found, planned_ops).  
Error Codes: 0 success, 5 partial, 10 fatal.

### 4.3 rename-apply
Purpose: Execute planned moves using copy-verify-delete or atomic rename.  
Inputs: --plan (CSV), --checkpoint (JSON manifest), optional --force.  
Outputs: apply_status.json, checkpoint manifest.  
Side-Effects: Moves or copies files when --force is set.  
Verification: Compares hash of source and destination before deletion.  
Error Codes: 0 all succeeded, 5 partial, 10 fatal.  
Default Behavior: Dry-run (dry_run: true) unless --force provided.

### 4.4 rollback
Purpose: Restore files to original locations using a checkpoint manifest.  
Inputs: --checkpoint (path to manifest).  
Outputs: Restored files and updated logs.  
Error Codes: 0 success, 5 partial, 10 fatal.  
Behavior: Processes checkpoint entries in reverse order.

### 4.5 verify
Purpose: Validate that all applied moves from a checkpoint still exist.  
Inputs: --checkpoint (path).  
Outputs: JSON summary of checked vs. missing paths.  
Error Codes: 0 success, 5 missing entries, 10 fatal.

### 4.6 metrics
Purpose: Display metrics summary from the last run.  
Inputs: None.  
Outputs: Contents of metrics.json.  
Error Codes: 0 success, 10 missing file.

## 5. File Artifact Specification

### 5.1 SQLite Index (output/index.db)
Columns: path (string), size (integer), mtime (integer), sha256 (string)

### 5.2 Plan CSV (rename_plan.csv)
Columns: status, op, src_path, dst_path, content_id, reason, rollback_key, ts

### 5.3 Checkpoint Manifest (*.json)
Keys: ts (float epoch), moves (list[src,dst])

### 5.4 Apply Status (apply_status.json)
Keys: attempted, succeeded, skipped, errors, bytes_moved, dry_run

### 5.5 Metrics (metrics.json)
Keys: ts, files_scanned, bytes_scanned, duplicates_found, planned_ops, apply, durations

### 5.6 Logs (output/logs/run_*.log.jsonl)
Each line: JSON object with keys ts, level, event, and arbitrary fields.

## 6. Runtime Behavior
1. Configuration is loaded or auto-generated.  
2. scan populates or updates the index database.  
3. plan computes duplicate groups using the database.  
4. rename-apply performs atomic or verified moves, creating a checkpoint manifest.  
5. rollback reverts based on manifest if errors or command invoked.  
6. Logs and metrics are written for every run.  
7. Exit codes follow POSIX: 0 success, 5 partial, 10 fatal.

## 7. Version History
| Version | Changes |
|----------|----------|
| 5.4 | Initial scaffold with docs-only manual. |
| 6.0 | Threaded scanner, SQLite index, structured logs, copy-verify-delete, checkpoints, verify & metrics commands, spec_v1 manual. |

## 8. License Reference
Licensed under Apache License 2.0.  
See LICENSE for full terms.  
All file paths and environment behaviors are declarative, not prescriptive.
