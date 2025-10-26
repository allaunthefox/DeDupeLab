
---
title: "Deduplab v5.4 Manual"
description: "Autonomous Caretaker Mode — fully unattended file organization and deduplication tool."
---

# 🧭 Deduplab v5.4 — Autonomous Caretaker Manual

[TOC]

## Overview
Deduplab automates file reorganization with confidence scoring, fuzzy classification, and safety-first defaults.

### Highlights
- Automatic defaults and self-healing
- Atomic writes + file locks
- 60s live heartbeat
- 7-day rotating logs
- Crash-safe, container-friendly

## Installation & Usage
```bash
pip install -e .
deduplab scan
deduplab analyze
deduplab reorg-plan
deduplab rename-apply
```

Logs are written to `output/deduplab_watchdog_<date>.log`.

## Configuration
| Priority | Path | Notes |
|-----------|------|--------|
| 1 | `$DE_DUPLAB_CONFIG` | environment override |
| 2 | `~/.config/deduplab/config.json` | global |
| 3 | `.deduplab_config.json` | project-local |

Defaults:
```json
{ "defaults": { "min_conf": 0.65, "nsfw_threshold": 2 } }
```

## Watchdog
Heartbeats every 60s:
```json
{"status":"running","processed":15321,"total":26890}
```
Completion:
```json
{"status":"ok","processed":26890,"total":26890}
```
Logs auto-rotate daily and prune older than 7 days.

## Safety & Recovery
- Atomic writes prevent corruption
- `.lock` ensures exclusive writes
- Buffered I/O extends disk life
- Silent repair on error

## Commands
| Command | Action |
|----------|--------|
| `scan` | build file index |
| `analyze` | deduplicate & tag |
| `reorg-plan` | plan renames |
| `rename-apply` | execute plan safely |

## Output
```
output/
├── rename_plan.csv
├── normalization_log.jsonl
├── deduplab_watchdog_<date>.log
└── meta_index.json
```

## Philosophy
> Designed to endure neglect.  
> Deduplab runs quietly, cleans methodically, and logs faithfully.
