# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Allaun

from __future__ import annotations
import os
import time
import hashlib
import mimetypes
import sys
from pathlib import Path
from typing import Iterable, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from .deps import check_dep

CHUNK = 1024 * 1024  # 1MB chunks for I/O

# Archive and extraction detection
ARCHIVE_EXTENSIONS = {'.zip', '.7z', '.tar', '.gz', '.bz2', '.xz', '.rar', 
                      '.tar.gz', '.tar.bz2', '.tar.xz', '.tgz', '.tbz2'}

EXTRACTION_MARKERS = {'extracted', 'unzipped', 'unpacked', 'unarchived', 
                      'decompressed', 'unrar', 'untar'}


def _should_skip(p: Path, ignore: List[str]) -> bool:
    """Check if path should be skipped based on ignore patterns."""
    parts = set(p.parts)
    return any(ig in parts for ig in ignore)


def _sha256_file(p: Path) -> str:
    """Compute SHA-256 hash of file."""
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_archive(path: Path) -> bool:
    """Check if file is an archive by extension."""
    return any(str(path).lower().endswith(ext) for ext in ARCHIVE_EXTENSIONS)


def _is_inside_archive(path: Path) -> bool:
    """
    Check if path is inside an extracted archive folder.
    
    Detection methods:
    1. Parent folder name matches archive without extension
    2. Path contains extraction marker keywords
    3. Adjacent archive file with same name exists
    """
    for parent in path.parents:
        parent_str = str(parent).lower()
        parent_name = parent.name.lower()
        
        # Check extraction markers
        if any(marker in parent_name for marker in EXTRACTION_MARKERS):
            return True
        
        # Check for adjacent archive
        for ext in ARCHIVE_EXTENSIONS:
            archive_candidate = parent.with_name(parent.name + ext)
            if archive_candidate.exists() and archive_candidate.is_file():
                return True
        
        # Check for archive-like folder names
        for ext in ARCHIVE_EXTENSIONS:
            if ext.replace('.', '_') in parent_name or ext.replace('.', '') in parent_name:
                return True
    
    return False


def _detect_context(p: Path) -> str:
    """
    Determine context tag for file.
    
    Returns:
        'archived' - file is inside an extracted archive
        'unarchived' - regular filesystem file
    
    Examples:
        /data/extracted/file.txt -> 'archived'
        /data/backup.zip.extracted/file.txt -> 'archived'
        /data/file.txt -> 'unarchived'
        /data/archive.zip -> 'unarchived' (the archive itself)
    """
    if _is_inside_archive(p):
        return "archived"
    
    # The archive file itself is 'unarchived' (not inside another archive)
    return "unarchived"


def _init_mime_types():
    """Register modern file format MIME types."""
    custom_types = {
        # Modern image formats
        '.webp': 'image/webp',
        '.avif': 'image/avif',
        '.heic': 'image/heic',
        '.heif': 'image/heif',
        '.jxl': 'image/jxl',
        
        # Modern video formats
        '.mkv': 'video/x-matroska',
        '.webm': 'video/webm',
        '.m4v': 'video/x-m4v',
        
        # Modern audio formats
        '.opus': 'audio/opus',
        '.flac': 'audio/flac',
        '.m4a': 'audio/mp4',
        '.aac': 'audio/aac',
        
        # Modern document formats
        '.epub': 'application/epub+zip',
        '.mobi': 'application/x-mobipocket-ebook',
        
        # Archive formats
        '.7z': 'application/x-7z-compressed',
        '.rar': 'application/vnd.rar',
        '.zst': 'application/zstd',
        '.br': 'application/x-brotli',
    }
    
    for ext, mime in custom_types.items():
        mimetypes.add_type(mime, ext)


# Initialize MIME types at module load
_init_mime_types()


def _get_mime_safe(p: Path) -> str:
    """
    Get MIME type with comprehensive fallback.
    
    Strategy:
    1. Try standard mimetypes.guess_type()
    2. Check custom mappings
    3. Fallback to application/octet-stream
    
    Args:
        p: Path to file
        
    Returns:
        MIME type string (never None)
    """
    # Primary method
    mime, encoding = mimetypes.guess_type(str(p))
    
    if mime:
        return mime
    
    # Fallback: check by extension directly
    suffix_lower = p.suffix.lower()
    
    # Additional manual mappings for edge cases
    extension_map = {
        '.md': 'text/markdown',
        '.yaml': 'text/yaml',
        '.yml': 'text/yaml',
        '.toml': 'text/toml',
        '.ini': 'text/plain',
        '.log': 'text/plain',
        '.conf': 'text/plain',
        '.cfg': 'text/plain',
        '.sh': 'application/x-sh',
        '.bash': 'application/x-sh',
        '.zsh': 'application/x-sh',
        '.py': 'text/x-python',
        '.js': 'application/javascript',
        '.ts': 'application/typescript',
        '.jsx': 'text/jsx',
        '.tsx': 'text/tsx',
        '.rs': 'text/x-rust',
        '.go': 'text/x-go',
        '.c': 'text/x-c',
        '.cpp': 'text/x-c++',
        '.h': 'text/x-c',
        '.hpp': 'text/x-c++',
    }
    
    if suffix_lower in extension_map:
        return extension_map[suffix_lower]
    
    # Ultimate fallback
    return "application/octet-stream"


def iter_files(roots: Iterable[str], ignore: List[str]) -> Iterable[Path]:
    """Generate all files to be scanned."""
    for r in roots:
        rp = Path(r)
        if not rp.exists():
            continue
        for p in rp.rglob("*"):
            if p.is_file() and not _should_skip(p, ignore):
                yield p


def threaded_hash(roots: Iterable[str], ignore: List[str], workers: int = 4):
    """
    Scan files and compute hashes with progress indicators.
    
    Features:
    - Parallel hashing with ThreadPoolExecutor
    - Progress bar with tqdm (if available) or text fallback
    - MIME type detection
    - Context detection (archived vs unarchived)
    
    Args:
        roots: List of root directories to scan
        ignore: List of directory/file patterns to skip
        workers: Number of parallel worker threads
        
    Returns:
        Tuple of (results, duration, total_files)
        where results is List[Tuple[path, size, mtime, sha256, mime, context_tag]]
    """
    files = list(iter_files(roots, ignore))
    results: List[Tuple[str, int, int, str, str, str]] = []
    start = time.time()
    
    # Check for tqdm availability
    has_tqdm = check_dep("tqdm")
    
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futs = {}
        for p in files:
            futs[ex.submit(_sha256_file, p)] = p
        
        # Progress tracking
        if has_tqdm:
            # Use tqdm progress bar
            from tqdm import tqdm
            
            pbar = tqdm(
                total=len(futs),
                desc="Hashing files",
                unit="file",
                unit_scale=False,
                ncols=80
            )
            
            for fut in as_completed(futs):
                p = futs[fut]
                try:
                    sha = fut.result()
                    st = p.stat()
                    mime = _get_mime_safe(p)
                    context = _detect_context(p)
                    results.append((
                        str(p),
                        st.st_size,
                        int(st.st_mtime),
                        sha,
                        mime,
                        context
                    ))
                except Exception as e:
                    # Log error but continue
                    print(f"[scanner][WARN] Failed to process {p}: {e}", file=sys.stderr)
                finally:
                    pbar.update(1)
            
            pbar.close()
        
        else:
            # Fallback: text-based progress updates
            processed = 0
            last_update = 0
            update_interval = max(1, len(futs) // 100)  # Update every 1%
            
            print(f"[scanner] Processing {len(futs)} files (no tqdm, using text updates)...", 
                  file=sys.stderr)
            
            for fut in as_completed(futs):
                p = futs[fut]
                try:
                    sha = fut.result()
                    st = p.stat()
                    mime = _get_mime_safe(p)
                    context = _detect_context(p)
                    results.append((
                        str(p),
                        st.st_size,
                        int(st.st_mtime),
                        sha,
                        mime,
                        context
                    ))
                except Exception as e:
                    print(f"[scanner][WARN] Failed to process {p}: {e}", file=sys.stderr)
                finally:
                    processed += 1
                    
                    # Print periodic updates
                    if processed - last_update >= update_interval or processed == len(futs):
                        percent = 100 * processed / len(futs)
                        print(
                            f"[scanner] Progress: {processed}/{len(futs)} "
                            f"({percent:.1f}%)...",
                            file=sys.stderr
                        )
                        last_update = processed
    
    dur = time.time() - start
    return results, dur, len(files)