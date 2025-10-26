# Schemas

## rename_plan.csv
status,op,src_path,dst_path,content_id,reason,rollback_key,ts

## normalization_log.jsonl (one JSON per line)
{"ts":"2025-10-25T18:00:12Z","level":"INFO","event":"rename","content_id":"b3:sha256:...","src":"/a","dst":"/b","plan_row":1,"attempt":1,"dur_ms":37}

## apply_status.json
{"ts":"2025-10-25T18:05:00Z","attempted":0,"succeeded":0,"skipped":0,"errors":0}


## metrics.json
```
{
  "ts": "...",
  "files_scanned": 0,
  "bytes_scanned": 0,
  "duplicates_found": 0,
  "planned_ops": 0,
  "apply": {"attempted":0,"succeeded":0,"skipped":0,"errors":0,"bytes_moved":0},
  "durations": {"scan_s": 0.0}
}
```
