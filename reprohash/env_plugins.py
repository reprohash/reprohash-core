#!/usr/bin/env python3
"""
ReproHash Environment Plugin System v1.0

Complete standalone module for environment metadata capture.
Can be imported without affecting existing reprohash functionality.
"""

import sys
import json
import time
import hashlib
import importlib.metadata
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


VERSION = "2.1"
ENV_SCHEMA_VERSION = "reprohash.env.v1"


def canonical_json(obj: Any) -> str:
    """Canonical JSON for deterministic hashing."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'))


# ============================================================
# Base Plugin Interface
# ============================================================

class EnvironmentPlugin(ABC):
    """
    Base class for environment metadata capture plugins.
    
    Design invariants:
    1. Plugins never affect PASS/FAIL outcomes
    2. Plugins cannot veto verification
    3. Plugin output is immutable once sealed
    4. Core verification logic is unaware of plugin semantics
    5. Absence of environment metadata is always valid
    """
    
    PLUGIN_NAME: str = "base"
    PLUGIN_VERSION: str = "1.0"
    SCHEMA_VERSION: str = ENV_SCHEMA_VERSION
    
    @abstractmethod
    def capture(self) -> Dict[str, Any]:
        """
        Capture environment metadata.
        
        Must return JSON-serializable data.
        Must not execute user code.
        Must not modify environment.
        
        Returns:
            Dictionary with plugin-specific metadata
        """
        raise NotImplementedError
    
    def get_envelope(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wrap plugin data in standard envelope.
        
        Args:
            data: Plugin-specific metadata
            
        Returns:
            Standardized envelope with metadata
        """
        return {
            "schema": self.SCHEMA_VERSION,
            "captured_by": {
                "plugin": self.PLUGIN_NAME,
                "plugin_version": self.PLUGIN_VERSION
            },
            "timestamp": time.time(),
            "data": data
        }
    
    def get_hashable_data(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract only the hashable portion of envelope.
        
        Excludes timestamp to make hash deterministic for same environment.
        
        Args:
            envelope: Full plugin output with envelope
            
        Returns:
            Hashable portion (schema, plugin info, data only)
        """
        return {
            "schema": envelope["schema"],
            "captured_by": envelope["captured_by"],
            "data": envelope["data"]
        }
    
    def capture_with_envelope(self) -> Dict[str, Any]:
        """Capture and wrap in envelope."""
        data = self.capture()
        return self.get_envelope(data)
    
    def get_fingerprint_hash(self, envelope: Dict[str, Any]) -> str:
        """
        Compute cryptographic fingerprint of environment.
        
        Excludes timestamp to ensure same environment = same hash.
        
        Args:
            envelope: Full plugin output with envelope
            
        Returns:
            SHA-256 hash of canonical JSON (without timestamp)
        """
        hashable = self.get_hashable_data(envelope)
        canonical = canonical_json(hashable)
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


# ============================================================
# Reference Plugin: Python/pip
# ============================================================

class PipEnvironmentPlugin(EnvironmentPlugin):
    """
    Captures Python and pip package environment.
    
    What it captures:
    - Python version and implementation
    - Installed packages and versions
    
    What it does NOT capture:
    - CUDA versions
    - System libraries
    - Compiler versions
    - Hardware details
    
    This is intentionally minimal and deterministic.
    """
    
    PLUGIN_NAME = "pip"
    PLUGIN_VERSION = "1.0"
    
    def capture(self) -> Dict[str, Any]:
        """Capture Python/pip environment."""
        
        # Python info
        python_info = {
            "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "implementation": sys.implementation.name.title()
        }
        
        # Get installed packages
        packages = {}
        try:
            # Use importlib.metadata (Python 3.8+)
            for dist in importlib.metadata.distributions():
                packages[dist.name] = dist.version
        except Exception as e:
            # Fallback: note the error
            packages["_error"] = f"Could not enumerate packages: {str(e)}"
        
        return {
            "python": python_info,
            "packages": dict(sorted(packages.items())),  # Deterministic ordering
            "capture_method": "importlib.metadata"
        }
    
    def get_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract human-readable summary.
        
        Args:
            data: Full plugin data
            
        Returns:
            Condensed summary for display
        """
        packages = data.get("packages", {})
        
        # Key packages for ML/scientific computing
        key_package_names = [
            "torch", "torchvision", "tensorflow", 
            "numpy", "scipy", "pandas", "scikit-learn",
            "jax", "mxnet"
        ]
        
        key_packages = {
            name: version 
            for name, version in packages.items() 
            if name.lower() in key_package_names
        }
        
        return {
            "python": data.get("python", {}).get("version"),
            "key_packages": key_packages,
            "total_packages": len(packages)
        }


# ============================================================
# Plugin Registry
# ============================================================

class PluginRegistry:
    """Registry of available environment plugins."""
    
    _plugins: Dict[str, type] = {}
    
    @classmethod
    def register(cls, plugin_class: type):
        """Register a plugin."""
        plugin_name = plugin_class.PLUGIN_NAME
        cls._plugins[plugin_name] = plugin_class
        return plugin_class
    
    @classmethod
    def get(cls, plugin_name: str) -> Optional[type]:
        """Get plugin class by name."""
        return cls._plugins.get(plugin_name)
    
    @classmethod
    def list_plugins(cls) -> List[str]:
        """List available plugin names."""
        return list(cls._plugins.keys())


# Register built-in plugins
PluginRegistry.register(PipEnvironmentPlugin)


# ============================================================
# Environment Metadata Container
# ============================================================

@dataclass
class EnvironmentMetadata:
    """
    Container for environment metadata attached to RunRecords.
    
    This is what gets stored in the RunRecord JSON.
    """
    
    fingerprint_hash: str
    plugin_name: str
    plugin_version: str
    schema_version: str
    summary: Dict[str, Any]
    full_data_file: Optional[str] = None  # Path to full JSON in bundle
    
    def to_dict(self) -> Dict[str, Any]:
        """Export for RunRecord."""
        return {
            "schema": self.schema_version,
            "fingerprint_hash": self.fingerprint_hash,
            "captured_by": self.plugin_name,
            "plugin_version": self.plugin_version,
            "summary": self.summary,
            "full_data_file": self.full_data_file,
            "note": "Informational only. Not part of cryptographic verification."
        }
    
    @classmethod
    def from_plugin_output(
        cls,
        envelope: Dict[str, Any],
        fingerprint_hash: str,
        summary: Dict[str, Any]
    ) -> 'EnvironmentMetadata':
        """Create from plugin output."""
        return cls(
            fingerprint_hash=fingerprint_hash,
            plugin_name=envelope["captured_by"]["plugin"],
            plugin_version=envelope["captured_by"]["plugin_version"],
            schema_version=envelope["schema"],
            summary=summary
        )


# ============================================================
# Environment Capture Orchestrator
# ============================================================

class EnvironmentCapture:
    """
    Orchestrates environment plugin execution.
    
    Called during `reprohash run` before command execution.
    """
    
    @staticmethod
    def capture_environment(
        plugin_names: List[str]
    ) -> Optional[EnvironmentMetadata]:
        """
        Capture environment using specified plugins.
        
        Args:
            plugin_names: List of plugin names to execute
            
        Returns:
            EnvironmentMetadata if successful, None otherwise
        """
        if not plugin_names:
            return None
        
        # For now, we only support single plugin
        # (multiple plugins can be added later if needed)
        if len(plugin_names) > 1:
            raise ValueError(
                "Multiple environment plugins not yet supported. "
                "Use --env-plugin once."
            )
        
        plugin_name = plugin_names[0]
        
        # Get plugin class
        plugin_class = PluginRegistry.get(plugin_name)
        if not plugin_class:
            available = PluginRegistry.list_plugins()
            raise ValueError(
                f"Unknown plugin: {plugin_name}. "
                f"Available: {', '.join(available)}"
            )
        
        # Instantiate and capture
        plugin = plugin_class()
        
        try:
            envelope = plugin.capture_with_envelope()
            fingerprint_hash = plugin.get_fingerprint_hash(envelope)
            
            # Get summary (plugin-specific)
            if hasattr(plugin, 'get_summary'):
                summary = plugin.get_summary(envelope["data"])
            else:
                # Generic summary
                summary = {"captured": True}
            
            # Create metadata object
            metadata = EnvironmentMetadata.from_plugin_output(
                envelope,
                fingerprint_hash,
                summary
            )
            
            # Store full envelope for bundle
            metadata._full_envelope = envelope
            
            return metadata
            
        except Exception as e:
            print(f"Warning: Environment capture failed: {e}", file=sys.stderr)
            return None
    
    @staticmethod
    def save_full_environment(
        metadata: EnvironmentMetadata,
        output_dir: Path
    ):
        """
        Save full environment data to bundle.
        
        Args:
            metadata: Environment metadata with full envelope
            output_dir: Bundle directory
        """
        if not hasattr(metadata, '_full_envelope'):
            return
        
        env_file = output_dir / f"environment_{metadata.plugin_name}.json"
        
        with open(env_file, 'w') as f:
            json.dump(metadata._full_envelope, f, indent=2)
        
        metadata.full_data_file = env_file.name


# ============================================================
# Integration Helper Functions
# ============================================================

def update_runrecord_with_environment(
    runrecord_dict: Dict[str, Any],
    env_metadata: Optional[EnvironmentMetadata]
) -> Dict[str, Any]:
    """
    Add environment metadata to RunRecord.
    
    Args:
        runrecord_dict: RunRecord as dict
        env_metadata: Environment metadata (or None)
        
    Returns:
        Updated RunRecord dict
    """
    if env_metadata is None:
        return runrecord_dict
    
    runrecord_dict["environment_metadata"] = env_metadata.to_dict()
    
    return runrecord_dict


# ============================================================
# Verification Support
# ============================================================

def verify_environment_metadata(
    runrecord_dict: Dict[str, Any],
    bundle_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Verify environment metadata integrity.
    
    Args:
        runrecord_dict: RunRecord as dict
        bundle_dir: Bundle directory (to check full data file)
        
    Returns:
        Verification result dict
    """
    result = {
        "verified": False,
        "errors": [],
        "warnings": []
    }
    
    env_meta = runrecord_dict.get("environment_metadata")
    
    if not env_meta:
        result["warnings"].append(
            "No environment metadata present (this is valid)"
        )
        result["verified"] = True
        return result
    
    # Check schema version
    if env_meta.get("schema") != ENV_SCHEMA_VERSION:
        result["warnings"].append(
            f"Environment schema version mismatch: "
            f"{env_meta.get('schema')} vs {ENV_SCHEMA_VERSION}"
        )
    
    # If bundle directory provided, verify full data file
    if bundle_dir and env_meta.get("full_data_file"):
        full_file = bundle_dir / env_meta["full_data_file"]
        
        if not full_file.exists():
            result["errors"].append(
                f"Environment data file missing: {env_meta['full_data_file']}"
            )
            return result
        
        try:
            with open(full_file) as f:
                full_envelope = json.load(f)
            
            # Recompute hash
            plugin_class = PluginRegistry.get(env_meta["captured_by"])
            if plugin_class:
                plugin = plugin_class()
                recomputed_hash = plugin.get_fingerprint_hash(full_envelope)
                
                if recomputed_hash != env_meta["fingerprint_hash"]:
                    result["errors"].append(
                        "Environment fingerprint hash mismatch "
                        "(data file may have been modified)"
                    )
                    return result
        except Exception as e:
            result["errors"].append(f"Could not verify environment data: {e}")
            return result
    
    result["verified"] = True
    return result


def compare_environment_metadata(
    runrecord_a: Dict[str, Any],
    runrecord_b: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compare environment metadata between two RunRecords.
    
    This is informational only - does not affect verification outcomes.
    
    Args:
        runrecord_a: First RunRecord
        runrecord_b: Second RunRecord
        
    Returns:
        Comparison result
    """
    env_a = runrecord_a.get("environment_metadata")
    env_b = runrecord_b.get("environment_metadata")
    
    if not env_a or not env_b:
        return {
            "comparable": False,
            "reason": "One or both RunRecords lack environment metadata"
        }
    
    hash_a = env_a.get("fingerprint_hash")
    hash_b = env_b.get("fingerprint_hash")
    
    result = {
        "comparable": True,
        "identical": hash_a == hash_b,
        "fingerprint_a": hash_a[:16] + "...",
        "fingerprint_b": hash_b[:16] + "...",
    }
    
    if not result["identical"]:
        # Extract differences from summaries
        summary_a = env_a.get("summary", {})
        summary_b = env_b.get("summary", {})
        
        differences = []
        
        # Compare Python versions
        py_a = summary_a.get("python")
        py_b = summary_b.get("python")
        if py_a != py_b:
            differences.append(f"Python: {py_a} vs {py_b}")
        
        # Compare key packages
        pkg_a = summary_a.get("key_packages", {})
        pkg_b = summary_b.get("key_packages", {})
        
        all_packages = set(pkg_a.keys()) | set(pkg_b.keys())
        for pkg in all_packages:
            ver_a = pkg_a.get(pkg, "not installed")
            ver_b = pkg_b.get(pkg, "not installed")
            if ver_a != ver_b:
                differences.append(f"{pkg}: {ver_a} vs {ver_b}")
        
        result["differences"] = differences
    
    return result


__all__ = [
    'EnvironmentPlugin',
    'PipEnvironmentPlugin',
    'PluginRegistry',
    'EnvironmentCapture',
    'EnvironmentMetadata',
    'update_runrecord_with_environment',
    'verify_environment_metadata',
    'compare_environment_metadata',
]
