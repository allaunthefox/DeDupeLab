# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Allaun

from __future__ import annotations
import sqlite3
import sys
import time
from pathlib import Path
from typing import Iterable, Tuple, List

# Migration system
MIGRATIONS = {
    1: """
        -- Add mime column with default value
        ALTER TABLE files ADD COLUMN mime TEXT DEFAULT 'application/octet-stream';
    """,
    2: """
        -- Add context_tag column with default value
        ALTER TABLE files ADD COLUMN context_tag TEXT DEFAULT 'unarchived';
    """,
    3: """
        -- Create composite index for hash+context deduplication
        CREATE INDEX IF NOT EXISTS idx_files_hash_ctx 
        ON files (sha256, context_tag);
    """,
    4: """
        -- Create schema version tracking table
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at INTEGER NOT NULL,
            description TEXT
        );
    """
}

# Base schema (v0 - original)
BASE_SCHEMA = """
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
    """
    SQLite database with automatic schema migrations.
    
    Schema Evolution:
    - v0: Original (path, size, mtime, sha256)
    - v1: Add mime column
    - v2: Add context_tag column
    - v3: Add composite index
    - v4: Add schema_version table
    """
    
    def __init__(self, path: Path):
        """
        Initialize database with automatic migration.
        
        Args:
            path: Path to SQLite database file
        """
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path.as_posix(), timeout=30)
        
        # Create base schema if new database
        self._init_base_schema()
        
        # Apply pending migrations
        self._migrate()

    def _init_base_schema(self):
        """Create base schema if tables don't exist."""
        try:
            self.conn.executescript(BASE_SCHEMA)
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"[db][ERROR] Failed to initialize base schema: {e}", file=sys.stderr)
            raise

    def _get_schema_version(self) -> int:
        """
        Get current schema version from database.
        
        Returns:
            Current version number, or 0 if schema_version table doesn't exist
        """
        try:
            cursor = self.conn.execute("SELECT MAX(version) FROM schema_version")
            result = cursor.fetchone()
            return result[0] if result[0] is not None else 0
        except sqlite3.OperationalError:
            # Table doesn't exist yet - this is a fresh or v0 database
            return 0

    def _migrate(self):
        """
        Apply all pending migrations in order.
        
        Process:
        1. Get current schema version
        2. For each migration > current version:
           a. Execute migration SQL
           b. Record migration in schema_version table
           c. Commit transaction
        3. If any migration fails, rollback and raise
        """
        current = self._get_schema_version()
        
        for version in sorted(MIGRATIONS.keys()):
            if version > current:
                try:
                    print(f"[db] Applying migration v{version}...")
                    
                    # Execute migration
                    self.conn.executescript(MIGRATIONS[version])
                    
                    # Record successful migration
                    # Note: schema_version table is created in migration 4
                    if version >= 4:
                        self.conn.execute(
                            "INSERT INTO schema_version (version, applied_at, description) VALUES (?, ?, ?)",
                            (version, int(time.time()), f"Migration v{version}")
                        )
                    
                    # Commit
                    self.conn.commit()
                    
                    print(f"[db] Migration v{version} applied successfully")
                    
                except sqlite3.Error as e:
                    print(f"[db][ERROR] Migration v{version} failed: {e}", file=sys.stderr)
                    self.conn.rollback()
                    raise RuntimeError(f"Database migration failed at version {version}: {e}")

    def close(self):
        """Close database connection."""
        self.conn.close()

    def upsert_files(self, records: Iterable[Tuple[str, int, int, str, str, str]]):
        """
        Insert or update file records.
        
        Args:
            records: Iterable of (path, size, mtime, sha256, mime, context_tag) tuples
        """
        cur = self.conn.cursor()
        cur.executemany(
            """INSERT INTO files(path, size, mtime, sha256, mime, context_tag) 
               VALUES(?, ?, ?, ?, ?, ?) 
               ON CONFLICT(path) DO UPDATE SET 
                   size=excluded.size, 
                   mtime=excluded.mtime, 
                   sha256=excluded.sha256,
                   mime=excluded.mime,
                   context_tag=excluded.context_tag""",
            records
        )
        self.conn.commit()

    def get_duplicates(self) -> List[Tuple[str, str, str]]:
        """
        Get duplicate file groups (context-aware).
        
        Returns same hash + same context_tag as duplicates.
        Same hash + different context_tag are NOT duplicates.
        
        Returns:
            List of (sha256, context_tag, pipe-separated paths) tuples
        """
        query = """
            SELECT sha256, context_tag, GROUP_CONCAT(path, '|') 
            FROM files 
            GROUP BY sha256, context_tag 
            HAVING COUNT(*) > 1
        """
        return list(self.conn.execute(query))

    def get_all(self):
        """Get all file records."""
        return list(self.conn.execute(
            "SELECT path, size, mtime, sha256, mime, context_tag FROM files"
        ))