# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Allaun

import ast, sys
from pathlib import Path

def lint_tree(root: Path):
    for f in root.rglob("*.py"):
        try:
            ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError as e:
            print(f"[lint][ERROR] {f}: {e}", file=sys.stderr)
            raise
