# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Allaun

"""
Environment detection and automatic configuration tuning.
Optimizes settings for Desktop, NAS, Cloud, and Container deployments.
"""

import os
import platform
from pathlib import Path
from typing import Dict
from .deps import check_dep


class Environment:
    """
    Detect deployment environment and provide optimized settings.
    
    Environment types:
    - desktop: Personal computer (optimize for responsiveness)
    - nas: Network-attached storage (optimize for network I/O)
    - cloud: Cloud VM/instance (optimize for throughput)
    - container: Docker/Kubernetes (conservative defaults)
    """
    
    def __init__(self):
        """Initialize environment detection."""
        self.type = self._detect_type()
        self.resources = self._get_resources()
        self.optimizations = self._get_optimizations()
    
    def _detect_type(self) -> str:
        """
        Detect deployment environment type.
        
        Detection heuristics:
        1. Container: Check for /.dockerenv or /run/.containerenv
        2. Cloud: Check DMI product name for cloud provider markers
        3. NAS: Check for NAS-specific paths and markers
        4. Desktop: Fallback default
        
        Returns:
            One of: 'container', 'cloud', 'nas', 'desktop'
        """
        # Check for containerization
        container_markers = [
            Path('/.dockerenv'),
            Path('/run/.containerenv')
        ]
        if any(marker.exists() for marker in container_markers):
            return "container"
        
        # Check for cloud VM markers (Linux-specific)
        if platform.system() == 'Linux':
            cloud_files = {
                '/sys/class/dmi/id/product_name': [
                    'Google Compute Engine',
                    'Amazon EC2',
                    'Microsoft Corporation',
                    'DigitalOcean',
                    'Linode'
                ],
                '/sys/class/dmi/id/sys_vendor': [
                    'Google',
                    'Amazon EC2',
                    'Microsoft Corporation',
                    'DigitalOcean',
                    'Linode'
                ],
                '/sys/hypervisor/type': ['xen', 'kvm']
            }
            
            for marker_file, patterns in cloud_files.items():
                if Path(marker_file).exists():
                    try:
                        content = Path(marker_file).read_text().strip()
                        if any(p in content for p in patterns):
                            return "cloud"
                    except:
                        pass
        
        # Check for NAS-like environments
        nas_markers = [
            # Synology
            Path('/usr/syno'),
            Path('/volume1'),
            Path('/volume2'),
            # QNAP
            Path('/share/CACHEDEV1_DATA'),
            Path('/mnt/HDA_ROOT'),
            # Generic NAS paths
            Path('/shares'),
            Path('/mnt/user'),  # Unraid
        ]
        
        if any(marker.exists() for marker in nas_markers):
            return "nas"
        
        # Check home directory for NAS indicators
        home_lower = str(Path.home()).lower()
        nas_keywords = ['synology', 'qnap', 'nas', 'volume', 'share']
        if any(keyword in home_lower for keyword in nas_keywords):
            return "nas"
        
        # Default to desktop
        return "desktop"
    
    def _get_resources(self) -> Dict:
        """
        Get available system resources.
        
        Returns:
            Dictionary with:
            - cpu_count: Number of CPU cores
            - memory_gb: Total RAM in gigabytes
            - disk_type: 'ssd' or 'hdd' (best guess)
        """
        resources = {
            'cpu_count': os.cpu_count() or 4,
            'memory_gb': 4.0,  # Safe default
            'disk_type': 'ssd'  # Modern systems assume SSD
        }
        
        # Try to get accurate memory info
        if check_dep("psutil"):
            try:
                import psutil
                resources['memory_gb'] = psutil.virtual_memory().total / (1024**3)
                resources['disk_type'] = self._detect_disk_type()
            except Exception:
                pass
        
        return resources
    
    def _detect_disk_type(self) -> str:
        """
        Detect if primary storage is SSD or HDD.
        
        Method (Linux-specific):
        Check /sys/block/*/queue/rotational flag
        - 0 = SSD (non-rotational)
        - 1 = HDD (rotational)
        
        Returns:
            'ssd' or 'hdd'
        """
        if platform.system() != 'Linux':
            return 'ssd'  # Assume SSD for non-Linux
        
        try:
            for dev_path in Path('/sys/block').iterdir():
                dev_name = dev_path.name
                
                # Only check physical drives (sd*, nvme*, vd*)
                if not (dev_name.startswith('sd') or 
                        dev_name.startswith('nvme') or 
                        dev_name.startswith('vd')):
                    continue
                
                rotational_file = dev_path / 'queue' / 'rotational'
                if rotational_file.exists():
                    is_rotational = int(rotational_file.read_text().strip())
                    return "hdd" if is_rotational else "ssd"
        except Exception:
            pass
        
        return "ssd"  # Default assumption
    
    def _get_optimizations(self) -> Dict:
        """
        Get environment-specific optimization settings.
        
        Returns:
            Dictionary with recommended configuration values:
            - parallelism: Number of worker threads
            - chunk_size: I/O buffer size in bytes
            - batch_size: Database batch insert size
        """
        cpu_count = self.resources['cpu_count']
        memory_gb = self.resources['memory_gb']
        disk_type = self.resources['disk_type']
        
        # Base defaults
        opts = {
            'parallelism': min(cpu_count, 8),
            'chunk_size': 1024 * 1024,  # 1MB
            'batch_size': 1000,
        }
        
        # Environment-specific tuning
        if self.type == "nas":
            # NAS: Limited CPU, network bottleneck, optimize for I/O
            opts['parallelism'] = max(2, cpu_count // 2)
            opts['chunk_size'] = 2 * 1024 * 1024  # 2MB chunks for network I/O
            opts['batch_size'] = 500  # Smaller batches to avoid network timeouts
            
        elif self.type == "cloud":
            # Cloud VM: Optimize for throughput, assume fast I/O
            opts['parallelism'] = cpu_count
            if disk_type == 'ssd':
                opts['chunk_size'] = 4 * 1024 * 1024  # 4MB for fast SSDs
            else:
                opts['chunk_size'] = 2 * 1024 * 1024  # 2MB for slower disks
            opts['batch_size'] = 2000  # Larger batches for throughput
            
        elif self.type == "container":
            # Container: Conservative defaults, may have resource limits
            opts['parallelism'] = max(2, cpu_count // 2)
            opts['chunk_size'] = 1024 * 1024  # 1MB
            opts['batch_size'] = 500  # Smaller batches
            
        elif self.type == "desktop":
            # Desktop: Balance performance with system responsiveness
            opts['parallelism'] = max(4, cpu_count - 1)  # Leave 1 core for OS
            if disk_type == 'ssd':
                opts['chunk_size'] = 2 * 1024 * 1024  # 2MB
            else:
                opts['chunk_size'] = 512 * 1024  # 512KB for HDD
            opts['batch_size'] = 1000
        
        # Adjust for available memory
        if memory_gb < 2:
            # Low memory: reduce parallelism and batch size
            opts['parallelism'] = min(opts['parallelism'], 2)
            opts['batch_size'] = 500
        elif memory_gb > 16:
            # High memory: increase batch size
            opts['batch_size'] = 5000
        
        return opts
    
    def apply_to_config(self, cfg: Dict) -> Dict:
        """
        Apply environment optimizations to configuration.
        
        Only overrides values that are set to defaults.
        User-specified values are preserved.
        
        Args:
            cfg: Configuration dictionary
            
        Returns:
            Updated configuration dictionary
        """
        cfg = cfg.copy()
        
        # Override parallelism only if using default value
        if cfg.get('parallelism', 0) in [0, 4]:  # 0 or default 4
            cfg['parallelism'] = self.optimizations['parallelism']
        
        # Add environment metadata for diagnostics
        cfg['_environment'] = {
            'type': self.type,
            'cpu_count': self.resources['cpu_count'],
            'memory_gb': round(self.resources['memory_gb'], 1),
            'disk_type': self.resources['disk_type'],
            'optimizations_applied': True,
            'detected_optimizations': self.optimizations
        }
        
        return cfg
    
    def print_info(self):
        """Print human-readable environment information."""
        print(f"[env] Environment Type: {self.type}")
        print(f"[env] Resources:")
        print(f"      CPU Cores: {self.resources['cpu_count']}")
        print(f"      Memory: {self.resources['memory_gb']:.1f} GB")
        print(f"      Disk Type: {self.resources['disk_type'].upper()}")
        print(f"[env] Optimizations:")
        print(f"      Parallelism: {self.optimizations['parallelism']} workers")
        print(f"      Chunk Size: {self.optimizations['chunk_size'] // 1024} KB")
        print(f"      Batch Size: {self.optimizations['batch_size']} records")