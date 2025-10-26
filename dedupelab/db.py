# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Allaun

from __future__ import annotations
import sqlite3, os, time
from pathlib import Path
from typing import Iterable, Dict, Any, Tuple

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
CREATE TABLE IF NOT EXISTS files(
  path TEXT PRIMARY KEY,
  size INTEGER NOT NULL,
  mtime INTEGER NOT NULL,
  sha256 TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sha ON files(sha256);
CREATE TABLE IF NOT EXISTS runs(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL,
  note TEXT
);
"""

class DB:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path.as_posix(), timeout=30)
        self.conn.executescript(SCHEMA)

    def close(self):
        self.conn.close()

    def upsert_files(self, records: Iterable[Tuple[str,int,int,str]]):
        cur = self.conn.cursor()
        cur.executemany(
            "INSERT INTO files(path,size,mtime,sha256) VALUES(?,?,?,?) "
            "ON CONFLICT(path) DO UPDATE SET size=excluded.size, mtime=excluded.mtime, sha256=excluded.sha256",
            records
        )
        self.conn.commit()

    def get_duplicates(self):
        q = ("SELECT sha256, GROUP_CONCAT(path) FROM files GROUP BY sha256 HAVING COUNT(*)>1")
        return list(self.conn.execute(q))

    def get_all(self):
        return list(self.conn.execute("SELECT path,size,mtime,sha256 FROM files"))
