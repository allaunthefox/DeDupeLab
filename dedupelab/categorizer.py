# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Allaun

import re

def categorize_file(mime: str, name: str):
    """Return dict with category, subtype, topic inferred from MIME and filename (lightweight heuristics)."""
    cat = "other"; subtype = "other"; topic = None
    if mime.startswith("image/"):
        cat, subtype = "image", "photo"
    elif mime.startswith("video/"):
        cat, subtype = "video", "clip"
    elif mime.startswith("audio/"):
        cat, subtype = "audio", "track"
    elif mime.startswith("application/pdf"):
        cat, subtype = "document", "pdf"
    elif mime.startswith("text/"):
        cat, subtype = "document", "text"
    elif mime.endswith("zip") or "zip" in mime or "x-7z" in mime or "rar" in mime:
        cat, subtype = "archive", "compressed"

    n = name.lower()
    if re.search(r"(invoice|receipt|tax)", n):
        topic = "finance"
    elif re.search(r"(vacation|travel|trip)", n):
        topic = "travel"
    elif re.search(r"(wedding|birthday|family)", n):
        topic = "family"
    elif re.search(r"(project|report|proposal)", n):
        topic = "work"
    elif re.search(r"(camera|img_|dsc_)", n):
        topic = "camera_uploads"
    return {"category": cat, "subtype": subtype, "topic": topic}
