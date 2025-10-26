# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Allaun

from __future__ import annotations
import os, time, hashlib, mimetypes
from pathlib import Path
from typing import Iterable, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

CHUNK = 1024 * 1024

def _should_skip(p: Path, ignore: List[str]) -> bool:
    parts = set(p.parts)
    return any(ig in parts for ig in ignore)

def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()

def iter_files(roots: Iterable[str], ignore: List[str]) -> Iterable[Path]:
    for r in roots:
        rp = Path(r)
        if not rp.exists(): continue
        for p in rp.rglob("*"):
            if p.is_file() and not _should_skip(p, ignore):
                yield p

def threaded_hash(roots: Iterable[str], ignore: List[str], workers: int = 4):
    files = list(iter_files(roots, ignore))
    results: List[Tuple[str,int,int,str]] = []
    start = time.time()
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futs = {}
        for p in files:
            futs[ex.submit(_sha256_file, p)] = p
        for fut in as_completed(futs):
            p = futs[fut]
            try:
                sha = fut.result()
                st = p.stat()
                results.append((str(p), st.st_size, int(st.st_mtime), sha))
            except Exception as e:
                # Skip file on error
                pass
    dur = time.time() - start
    return results, dur, len(files)
