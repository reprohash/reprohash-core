#!/usr/bin/env python3
"""
Verification with epistemically honest semantics.

Three outcomes:
- PASS_INPUT_INTEGRITY: All checks passed
- FAIL: Integrity violated
- INCONCLUSIVE: Could not complete verification
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List
from enum import Enum


VERSION = "2.1"


class VerificationOutcome(Enum):
    """
    Verification outcomes (scientifically precise).
    
    PASS_INPUT_INTEGRITY: All checks passed within stated scope
    FAIL: Verification found problems (integrity violated)
    INCONCLUSIVE: Verification could not be completed
    """
    PASS_INPUT_INTEGRITY = "PASS_INPUT_INTEGRITY" # nosec
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"


class VerificationResult:
    """Verification result with proper epistemic categories."""
    
    def __init__(self, outcome: VerificationOutcome):
        self.outcome = outcome
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.inconclusive_reasons: List[str] = []
    
    def add_error(self, msg: str):
        """Add error (triggers FAIL - integrity violated)."""
        self.errors.append(msg)
        self.outcome = VerificationOutcome.FAIL
    
    def add_inconclusive(self, msg: str):
        """Add inconclusive reason (verification not possible)."""
        self.inconclusive_reasons.append(msg)
        if self.outcome != VerificationOutcome.FAIL:
            self.outcome = VerificationOutcome.INCONCLUSIVE
    
    def add_warning(self, msg: str):
        """Add warning (informational only)."""
        self.warnings.append(msg)
    
    def to_dict(self) -> Dict[str, Any]:
        """Export result."""
        return {
            "outcome": self.outcome.value,
            "errors": self.errors,
            "inconclusive_reasons": self.inconclusive_reasons,
            "warnings": self.warnings,
            "scope": "input_integrity_only",
            "does_not_verify": [
                "numerical_reproducibility",
                "environment_equivalence",
                "execution_correctness",
                "author_authenticity"
            ]
        }


def verify_snapshot(snapshot_file: str, data_dir: str) -> VerificationResult:
    """
    Verify snapshot against data directory.
    
    Returns:
    - PASS_INPUT_INTEGRITY: All files match hashes
    - FAIL: Files missing, changed, or manifest corrupted
    - INCONCLUSIVE: Cannot read snapshot or data directory
    """
    result = VerificationResult(VerificationOutcome.PASS_INPUT_INTEGRITY)
    
    # Load snapshot
    try:
        with open(snapshot_file, 'r') as f:
            snapshot = json.load(f)
    except FileNotFoundError:
        result.add_inconclusive(
            f"Snapshot file not found: {snapshot_file} "
            "(verification infrastructure unavailable)"
        )
        return result
    except json.JSONDecodeError as e:
        result.add_error(f"Snapshot file corrupted (invalid JSON): {e}")
        return result
    except PermissionError:
        result.add_inconclusive(
            f"Permission denied reading snapshot: {snapshot_file}"
        )
        return result
    except Exception as e:
        result.add_inconclusive(f"Could not read snapshot file: {e}")
        return result
    
    # Verify required fields
    if 'content_hash' not in snapshot:
        result.add_error("Snapshot missing content_hash field")
        return result
    
    if 'hashable_manifest' not in snapshot:
        result.add_error("Snapshot missing hashable_manifest field")
        return result
    
    # Verify manifest hash
    try:
        from .snapshot import canonical_json
        manifest = snapshot['hashable_manifest']
        computed_hash = hashlib.sha256(
            canonical_json(manifest).encode('utf-8')
        ).hexdigest()
        
        if computed_hash != snapshot['content_hash']:
            result.add_error(
                f"Manifest hash mismatch (integrity violation). "
                f"Expected: {snapshot['content_hash'][:16]}..., "
                f"Got: {computed_hash[:16]}..."
            )
            return result
    except Exception as e:
        result.add_error(f"Could not verify manifest hash: {e}")
        return result
    
    # Verify files
    data_path = Path(data_dir)
    if not data_path.exists():
        result.add_inconclusive(
            f"Data directory not found: {data_dir} "
            "(verification infrastructure unavailable)"
        )
        return result
    
    manifest_files = {f['path']: f for f in manifest.get('files', [])}
    
    # Check all manifest files
    for file_path, file_info in manifest_files.items():
        full_path = data_path / file_path
        
        if not full_path.exists():
            result.add_error(f"File MISSING (integrity violation): {file_path}")
            continue
        
        try:
            with open(full_path, 'rb') as f:
                content = f.read()
                actual_hash = hashlib.sha256(content).hexdigest()
            
            if actual_hash != file_info['sha256']:
                result.add_error(
                    f"File CHANGED (integrity violation): {file_path} "
                    f"(expected: {file_info['sha256'][:16]}..., "
                    f"got: {actual_hash[:16]}...)"
                )
        except PermissionError:
            result.add_inconclusive(
                f"Permission denied reading {file_path}"
            )
        except Exception as e:
            result.add_inconclusive(f"Could not read file {file_path}: {e}")
    
    # Extra files are warnings only
    actual_files = set()
    for path in data_path.rglob("*"):
        if path.is_file():
            actual_files.add(str(path.relative_to(data_path)))
    
    extra_files = actual_files - set(manifest_files.keys())
    if extra_files:
        result.add_warning(
            f"Found {len(extra_files)} files not in snapshot"
        )
    
    return result


def verify_runrecord(runrecord_file: str) -> VerificationResult:
    """
    Verify runrecord seal integrity.
    
    Returns:
    - PASS_INPUT_INTEGRITY: Seal verified cryptographically
    - FAIL: Seal broken
    - INCONCLUSIVE: Cannot read runrecord
    """
    result = VerificationResult(VerificationOutcome.PASS_INPUT_INTEGRITY)
    
    # Load runrecord
    try:
        with open(runrecord_file, 'r') as f:
            runrecord = json.load(f)
    except FileNotFoundError:
        result.add_inconclusive(
            f"RunRecord file not found: {runrecord_file}"
        )
        return result
    except json.JSONDecodeError as e:
        result.add_error(f"RunRecord file corrupted (invalid JSON): {e}")
        return result
    except PermissionError:
        result.add_inconclusive(
            f"Permission denied reading runrecord: {runrecord_file}"
        )
        return result
    except Exception as e:
        result.add_inconclusive(f"Could not read RunRecord file: {e}")
        return result
    
    # Verify seal exists
    if 'runrecord_hash' not in runrecord:
        result.add_error("RunRecord missing seal")
        return result
    
    if not runrecord.get('integrity', {}).get('sealed', False):
        result.add_error("RunRecord is not sealed")
        return result
    
    # Full cryptographic seal verification
    try:
        from .snapshot import canonical_json
        
        # FIX: Use raw timestamps from execution section
        started = runrecord['execution'].get('started_timestamp')
        ended = runrecord['execution'].get('ended_timestamp')
        
        sealed_record = {
            "run_id": runrecord.get('run_id'),
            "input_snapshot_hash": runrecord['provenance']['input_snapshot'],
            "output_snapshot_hash": runrecord['provenance'].get('output_snapshot'),
            "command": runrecord['execution']['command'],
            "reproducibility_class": runrecord.get('reproducibility_class'),
            "exit_code": runrecord['execution'].get('exit_code'),
            "started": started,
            "ended": ended,
            "environment": runrecord.get('environment', {})
        }
        
        computed_hash = hashlib.sha256(
            canonical_json(sealed_record).encode('utf-8')
        ).hexdigest()
        
        claimed_hash = runrecord['runrecord_hash']
        
        if computed_hash != claimed_hash:
            result.add_error(
                f"Seal broken (integrity violation). "
                f"Expected: {claimed_hash[:16]}..., "
                f"Got: {computed_hash[:16]}..."
            )
    except KeyError as e:
        result.add_error(f"RunRecord malformed (missing field: {e})")
    except Exception as e:
        result.add_inconclusive(f"Could not verify seal: {e}")
    
    return result
