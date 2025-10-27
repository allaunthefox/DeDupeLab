# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Allaun

"""
Automatic dependency installation with graceful degradation.
Attempts pip install, falls back to reduced functionality if unavailable.
"""

import subprocess
import sys
import importlib.util
from typing import Dict, Optional, Set


OPTIONAL_DEPS = {
    "jsonschema": {
        "package": "jsonschema",
        "feature": "JSON Schema validation",
        "fallback": "Basic structural validation only"
    },
    "tqdm": {
        "package": "tqdm",
        "feature": "Progress bars with ETA",
        "fallback": "Periodic text progress updates"
    },
    "pandas": {
        "package": "pandas",
        "feature": "CPU-accelerated data processing",
        "fallback": "Pure Python data structures"
    },
    "cudf": {
        "package": "cudf",
        "feature": "GPU-accelerated data processing",
        "fallback": "CPU-based processing (pandas or builtin)"
    },
    "pillow": {
        "package": "Pillow",
        "feature": "Image metadata analysis for NSFW detection",
        "fallback": "Filename-based classification only"
    },
    "psutil": {
        "package": "psutil",
        "feature": "System resource detection",
        "fallback": "Conservative defaults for CPU/memory"
    }
}


class DependencyManager:
    """
    Manages optional dependencies with automatic installation and fallback.
    
    Features:
    - Auto-detection of available dependencies
    - Automatic pip install attempt (with timeout)
    - Graceful fallback when dependencies unavailable
    - Caching to avoid repeated checks
    """
    
    def __init__(self, auto_install: bool = True, silent: bool = False):
        """
        Initialize dependency manager.
        
        Args:
            auto_install: If True, attempt to install missing dependencies
            silent: If True, suppress informational messages
        """
        self.auto_install = auto_install
        self.silent = silent
        self.available: Dict[str, bool] = {}
        self.attempted_install: Set[str] = set()
    
    def check_and_install(self, module_name: str) -> bool:
        """
        Check if module is available, attempt install if not.
        
        Args:
            module_name: Name of Python module to check
            
        Returns:
            True if module is available, False otherwise
        """
        # Check cache first
        if module_name in self.available:
            return self.available[module_name]
        
        # Try direct import
        spec = importlib.util.find_spec(module_name)
        if spec is not None:
            self.available[module_name] = True
            return True
        
        # Module not available - try to install if enabled
        if not self.auto_install:
            self.available[module_name] = False
            self._warn_missing(module_name)
            return False
        
        # Attempt installation (only once per module)
        if module_name not in self.attempted_install:
            self.attempted_install.add(module_name)
            success = self._try_install(module_name)
            self.available[module_name] = success
            
            if success and not self.silent:
                print(f"[deps] ✓ Successfully installed {module_name}")
            elif not success:
                self._warn_missing(module_name)
            
            return success
        
        # Already attempted install and failed
        self.available[module_name] = False
        return False
    
    def _try_install(self, module_name: str) -> bool:
        """
        Attempt to install package via pip.
        
        Args:
            module_name: Python module name
            
        Returns:
            True if installation succeeded, False otherwise
        """
        pkg_name = OPTIONAL_DEPS.get(module_name, {}).get("package", module_name)
        
        try:
            # Run pip install with timeout
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-q", pkg_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=60,
                check=False
            )
            
            if result.returncode != 0:
                if not self.silent:
                    stderr_msg = result.stderr.decode()[:100]
                    print(
                        f"[deps] ⚠ pip install {pkg_name} failed: {stderr_msg}",
                        file=sys.stderr
                    )
                return False
            
            # Verify import now works
            spec = importlib.util.find_spec(module_name)
            return spec is not None
            
        except subprocess.TimeoutExpired:
            if not self.silent:
                print(
                    f"[deps] ⚠ pip install {pkg_name} timed out (>60s)",
                    file=sys.stderr
                )
            return False
        except Exception as e:
            if not self.silent:
                print(
                    f"[deps] ⚠ pip install {pkg_name} error: {e}",
                    file=sys.stderr
                )
            return False
    
    def _warn_missing(self, module_name: str):
        """Print warning about missing dependency."""
        if self.silent:
            return
        
        info = OPTIONAL_DEPS.get(module_name, {})
        feature = info.get("feature", module_name)
        fallback = info.get("fallback", "Limited functionality")
        
        print(
            f"[deps] ⚠ {module_name} unavailable\n"
            f"       Feature disabled: {feature}\n"
            f"       Fallback: {fallback}",
            file=sys.stderr
        )
    
    def get_summary(self) -> Dict[str, bool]:
        """Get availability status of all checked dependencies."""
        return self.available.copy()
    
    def print_summary(self):
        """Print human-readable summary of dependency status."""
        if not self.available:
            print("[deps] No dependencies checked yet")
            return
        
        print("[deps] Dependency Status:")
        for module_name, is_available in sorted(self.available.items()):
            status = "✓ Available" if is_available else "✗ Unavailable"
            feature = OPTIONAL_DEPS.get(module_name, {}).get("feature", "")
            print(f"  {module_name:12} {status:15} {feature}")


# Global singleton instance
_dep_manager: Optional[DependencyManager] = None


def init_deps(auto_install: bool = True, silent: bool = False) -> DependencyManager:
    """
    Initialize global dependency manager.
    
    Args:
        auto_install: If True, attempt to install missing dependencies
        silent: If True, suppress informational messages
        
    Returns:
        DependencyManager instance
    """
    global _dep_manager
    _dep_manager = DependencyManager(auto_install, silent)
    return _dep_manager


def check_dep(module_name: str) -> bool:
    """
    Check if dependency is available (auto-installs if configured).
    
    Args:
        module_name: Name of Python module to check
        
    Returns:
        True if module is available, False otherwise
    """
    global _dep_manager
    if _dep_manager is None:
        _dep_manager = DependencyManager()
    return _dep_manager.check_and_install(module_name)


def get_dep_summary() -> Dict[str, bool]:
    """Get summary of all checked dependencies."""
    global _dep_manager
    if _dep_manager is None:
        return {}
    return _dep_manager.get_summary()