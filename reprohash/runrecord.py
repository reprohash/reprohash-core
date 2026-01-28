#!/usr/bin/env python3
"""
Run record with cryptographic sealing and enforced linear provenance.

TERMINOLOGY:
- "Tamper-evident" (correct): Modifications are detectable
- NOT "Immutable": Files can be modified, seal breaks

AUTHENTICATION:
- Seal provides INTEGRITY (detects tampering)
- Seal does NOT provide AUTHENTICITY (no author binding)
"""

import sys
import json
import time
import uuid
import platform
import hashlib
from typing import Dict, Any, Optional, List
from pathlib import Path
from reprohash.env_plugins import (
    EnvironmentCapture,
    EnvironmentMetadata,
    update_runrecord_with_environment
)
from enum import Enum


VERSION = "2.1"


def canonical_json(obj: Any) -> str:
    """Canonical JSON for deterministic hashing."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'))


class ReproducibilityClass(Enum):
    """
    Reproducibility expectations.
    Informational only - not enforced by verifier.
    """
    DETERMINISTIC = "deterministic"
    STOCHASTIC = "stochastic"
    UNKNOWN = "unknown"


class RunRecord:
    """
    Cryptographically sealed run record with enforced linear provenance.
    
    Linearity enforced by design:
    - ONE input_snapshot_hash (required)
    - ONE output_snapshot_hash (optional)
    - NO multi-parent or multi-output structures
    """
    
    def __init__(
        self,
        input_snapshot_hash: str,
        command: str,
        reproducibility_class: ReproducibilityClass = ReproducibilityClass.UNKNOWN,
        env_plugins: Optional[List[str]] = None
    ):
        # Single input only (enforced by constructor signature)
        self.run_id = str(uuid.uuid4())
        self.input_snapshot_hash = input_snapshot_hash
        
        # Single output only (enforced by attribute, not list)
        self.output_snapshot_hash: Optional[str] = None
        
        self.command = command
        self.reproducibility_class = reproducibility_class
        
        self.exit_code = None
        self.started = None
        self.ended = None
        
        self.environment = self._capture_minimal_environment()
        
        # Seal hash - MUST be set via seal() before archival
        self.runrecord_hash = None
        self.env_metadata: Optional[EnvironmentMetadata] = None
        if env_plugins:
            try:
                self.env_metadata = EnvironmentCapture.capture_environment(env_plugins)
                if self.env_metadata:
                    print(f" Environment captured via {self.env_metadata.plugin_name} plugin", 
                          file=sys.stderr)
            except Exception as e:
                print(f"Warning: Environment capture failed: {e}", file=sys.stderr)

    def _capture_minimal_environment(self) -> Dict[str, Any]:
        """Minimal, reliable environment capture."""
        return {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "note": "Minimal environment. Host details affect reproducibility but are not controlled."
        }
    
    def bind_output(self, output_snapshot_hash: str):
        """
        Bind output snapshot to this run.
        
        Single output only (overwrites if called multiple times).
        """
        if not isinstance(output_snapshot_hash, str):
            raise TypeError("output_snapshot_hash must be a string (single hash)")
        
        self.output_snapshot_hash = output_snapshot_hash
    
    def seal(self) -> str:
        """
        Cryptographically seal the runrecord.
        
        EFFECT: Makes record tamper-evident (not immutable).
        Any modification will be detectable via verify_seal().
        
        DOES NOT: Authenticate author or prevent fabrication.
        
        REQUIRED BEFORE:
        - Citing in paper
        - Exporting to Zenodo
        - Archival storage
        """
        if self.runrecord_hash:
            raise RuntimeError("RunRecord already sealed")
        
        record = {
            "run_id": self.run_id,
            "input_snapshot_hash": self.input_snapshot_hash,
            "output_snapshot_hash": self.output_snapshot_hash,
            "command": self.command,
            "reproducibility_class": self.reproducibility_class.value,
            "exit_code": self.exit_code,
            "started": self.started,
            "ended": self.ended,
            "environment": self.environment
        }
        
        self.runrecord_hash = hashlib.sha256(
            canonical_json(record).encode('utf-8')
        ).hexdigest()
        
        return self.runrecord_hash
    
    def verify_seal(self) -> bool:
        """Verify seal integrity."""
        if not self.runrecord_hash:
            return False
        
        record = {
            "run_id": self.run_id,
            "input_snapshot_hash": self.input_snapshot_hash,
            "output_snapshot_hash": self.output_snapshot_hash,
            "command": self.command,
            "reproducibility_class": self.reproducibility_class.value,
            "exit_code": self.exit_code,
            "started": self.started,
            "ended": self.ended,
            "environment": self.environment
        }
        
        computed = hashlib.sha256(
            canonical_json(record).encode('utf-8')
        ).hexdigest()
        
        return computed == self.runrecord_hash
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Export sealed runrecord.
        
        CRITICAL: RunRecord must be sealed before export.
        Unsealed records MUST NOT be cited or archived.
        """
        if not self.runrecord_hash:
            raise RuntimeError(
                "RunRecord must be sealed before export. Call seal() first.\n\n"
                "NORMATIVE REQUIREMENT: Unsealed RunRecords MUST NOT be cited, "
                "exported, or archived.\n\n"
                "REASON: Only sealed records provide tamper-evidence."
            )
            
        base_dict =  {
            "version": VERSION,
            "run_id": self.run_id,
            "runrecord_hash": self.runrecord_hash,
            
            "provenance": {
                "input_snapshot": self.input_snapshot_hash,
                "output_snapshot": self.output_snapshot_hash,
                "provenance_summary": f"{self.input_snapshot_hash[:8]} → {self.run_id[:8]} → {self.output_snapshot_hash[:8] if self.output_snapshot_hash else 'pending'}",
                "note": "provenance_summary is informational only and not part of the cryptographic seal",
                "linearity": "Single input, single output. Multi-parent structures not supported by design."
            },
            
            "execution": {
                "command": self.command,
                "exit_code": self.exit_code,
                "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.started)) if self.started else None,
                "ended_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.ended)) if self.ended else None,
                "duration_seconds": round(self.ended - self.started, 2) if self.started and self.ended else None,
                # FIX: Store raw timestamps for verification
                "started_timestamp": self.started,
                "ended_timestamp": self.ended
            },
            
            "reproducibility_class": self.reproducibility_class.value,
            "reproducibility_note": "Class is informational. Not enforced by verifier.",
            
            "environment": self.environment,
            
            "integrity": {
                "sealed": True,
                "tamper_evident": True,
                "authenticated": False,
                "archival_status": "archival_object",
                "note": (
                    "RunRecord hash binds all fields. Modifications are detectable. "
                    "Seal provides INTEGRITY (tamper-evidence), not AUTHENTICITY (author binding). "
                    "Only sealed RunRecords are archival objects."
                )
            }
        }
        if self.env_metadata:
            base_dict = update_runrecord_with_environment(base_dict, self.env_metadata)

        return base_dict

    def save_environment_to_bundle(self, bundle_dir: Path):
        """
        Save full environment data to bundle directory.
        
        Args:
            bundle_dir: Path to bundle directory
        """
        if self.env_metadata:
            from reprohash.env_plugins import EnvironmentCapture
            EnvironmentCapture.save_full_environment(self.env_metadata, bundle_dir)
