# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Allaun

"""
Deduplab package initialization.
Single source of truth for version from pyproject.toml.
"""

__license__ = "Apache-2.0"
__author__ = "Allaun"

# Version is read from installed package metadata
try:
    from importlib.metadata import version, PackageNotFoundError
    __version__ = version("deduplab")
except PackageNotFoundError:
    # Package not installed, try reading from pyproject.toml
    try:
        from pathlib import Path
        import tomllib  # Python 3.11+
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        if pyproject_path.exists():
            with open(pyproject_path, "rb") as f:
                pyproject = tomllib.load(f)
                __version__ = pyproject.get("project", {}).get("version", "unknown")
        else:
            __version__ = "unknown"
    except ImportError:
        # Python < 3.11, try tomli
        try:
            import tomli
            pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
            if pyproject_path.exists():
                with open(pyproject_path, "rb") as f:
                    pyproject = tomli.load(f)
                    __version__ = pyproject.get("project", {}).get("version", "unknown")
            else:
                __version__ = "unknown"
        except ImportError:
            __version__ = "unknown"
except Exception:
    __version__ = "unknown"