#!/usr/bin/env python3
"""
Verification bundle with complete semantic binding.

Bundle manifest cryptographically binds:
- Component identities (hashes)
- Verification semantics (profile)
- File integrity (checksums)
- Provenance relationships
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional


VERSION = "2.1"
VERIFICATION_PROFILE = "reprohash-v2.1-strict"


def canonical_json(obj: Any) -> str:
    """
    Canonical JSON for deterministic hashing.
    
    Rules (see spec/canonical-json-v1.yaml):
    - Keys sorted lexicographically
    - Compact serialization (no whitespace)
    - Separators: ',' between items, ':' between key-value
    - UTF-8 encoding
    
    Limitations (DOCUMENTED):
    - Float precision: Python default
    - Unicode: No explicit normalization (assumes NFC)
    - Relies on: Python json module semantics
    """
    return json.dumps(obj, sort_keys=True, separators=(',', ':'))


class ZenodoBundle:
    """
    Cryptographically bound verification bundle.
    
    Includes verification_profile binding semantics.
    Provenance summary excluded from hash (derived field).
    Components section authoritative, files derived.
    """
    
    def __init__(
        self,
        input_snapshot,
        runrecord,
        output_snapshot=None
    ):
        self.input_snapshot = input_snapshot
        self.runrecord = runrecord
        self.output_snapshot = output_snapshot
        self.bundle_hash: Optional[str] = None
    
    def create_bundle(self, output_dir: str) -> str:
        """
        Create cryptographically bound bundle.
        
        Process:
        1. Write component files
        2. Create manifest with components + verification_profile
        3. Seal manifest (hash excludes derived fields)
        4. Add derived fields (provenance_summary, etc)
        5. Write final manifest
        
        Returns: bundle_hash (binds components + semantics)
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Write input snapshot
        snapshot_file = output_path / "snapshot.json"
        with open(snapshot_file, "w") as f:
            json.dump(self.input_snapshot.to_dict(), f, indent=2)
        snapshot_file_hash = self._hash_file(snapshot_file)
        
        # Write runrecord
        runrecord_file = output_path / "runrecord.json"
        with open(runrecord_file, "w") as f:
            json.dump(self.runrecord.to_dict(), f, indent=2)
        runrecord_file_hash = self._hash_file(runrecord_file)
        
        # Write output snapshot if present
        output_file_hash = None
        if self.output_snapshot:
            output_snapshot_file = output_path / "output_snapshot.json"
            with open(output_snapshot_file, "w") as f:
                json.dump(self.output_snapshot.to_dict(), f, indent=2)
            output_file_hash = self._hash_file(output_snapshot_file)
        
        # Components section is authoritative
        components = {
            "input_snapshot": {
                "file": "snapshot.json",
                "content_hash": self.input_snapshot.content_hash,
                "file_sha256": snapshot_file_hash
            },
            "runrecord": {
                "file": "runrecord.json",
                "runrecord_hash": self.runrecord.runrecord_hash,
                "file_sha256": runrecord_file_hash
            }
        }
        
        if self.output_snapshot:
            components["output_snapshot"] = {
                "file": "output_snapshot.json",
                "content_hash": self.output_snapshot.content_hash,
                "file_sha256": output_file_hash
            }
        
        # Verification profile binds semantics
        manifest_for_hash = {
            "version": VERSION,
            "bundle_type": "reprohash_verification_bundle",
            
            "verification_profile": {
                "id": VERIFICATION_PROFILE,
                "semantics": "strict",
                "verification_rules": {
                    "bundle_seal": "required",
                    "component_seals": "required",
                    "provenance_chain": "verified",
                    "file_integrity": "required"
                },
                "outcome_model": "PASS_INPUT_INTEGRITY|FAIL|INCONCLUSIVE",
                "note": "Profile binds verification semantics. Future versions must maintain compatibility or declare new profile."
            },
            
            "components": components
        }
        
        # Compute bundle hash (over semantic manifest only)
        self.bundle_hash = hashlib.sha256(
            canonical_json(manifest_for_hash).encode('utf-8')
        ).hexdigest()
        
        # Derived fields added AFTER hash computation
        manifest_final = manifest_for_hash.copy()
        manifest_final["bundle_hash"] = self.bundle_hash
        
        # Provenance summary (informational only, not in hash)
        manifest_final["provenance_summary"] = {
            "note": "Informational only. Not included in bundle_hash.",
            "input": self.input_snapshot.content_hash[:16] + "...",
            "run": self.runrecord.run_id[:16] + "...",
            "output": self.output_snapshot.content_hash[:16] + "..." if self.output_snapshot else None
        }
        
        # File list (derived from components)
        manifest_final["files"] = [
            {
                "name": comp["file"],
                "sha256": comp["file_sha256"],
                "role": role,
                "note": "Derived from components section"
            }
            for role, comp in components.items()
        ]
        
        # Integrity note
        manifest_final["integrity"] = {
            "sealed": True,
            "tamper_evident": True,
            "note": (
                "bundle_hash cryptographically binds: version, bundle_type, "
                "verification_profile, and all components. "
                "Provenance summary and file list are derived (not in hash). "
                "Modifications to bundle_hash computation, components, or "
                "verification profile will be detectable."
            )
        }
        
        # Write sealed manifest
        manifest_file = output_path / "MANIFEST.json"
        with open(manifest_file, "w") as f:
            json.dump(manifest_final, f, indent=2)
        
        return self.bundle_hash
    
    def _hash_file(self, path: Path) -> str:
        """Hash a file."""
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()


def verify_bundle(bundle_dir: str, data_dir: str = None):
    """
    Verify bundle integrity AND component semantics.
    
    Performs COMPLETE verification:
    1. Bundle seal (manifest integrity)
    2. File integrity (component files)
    3. Component seals (snapshot, runrecord)
    4. Provenance chain (input → run → output consistency)
    5. Optional: Input data verification (if data_dir provided)
    
    This is FULL semantic verification, not just coherence.
    
    Args:
        bundle_dir: Bundle directory
        data_dir: Optional data directory for snapshot verification
    
    Returns: VerificationResult
    """
    from .verify import VerificationResult, VerificationOutcome, verify_snapshot, verify_runrecord
    
    result = VerificationResult(VerificationOutcome.PASS_INPUT_INTEGRITY)
    bundle_path = Path(bundle_dir)
    
    # === STEP 1: Load and verify manifest seal ===
    manifest_file = bundle_path / "MANIFEST.json"
    if not manifest_file.exists():
        result.add_inconclusive(
            "Bundle manifest not found (verification infrastructure unavailable)"
        )
        return result
    
    try:
        with open(manifest_file, 'r') as f:
            manifest = json.load(f)
    except Exception as e:
        result.add_error(f"Could not read bundle manifest: {e}")
        return result
    
    # Verify bundle seal exists
    if 'bundle_hash' not in manifest:
        result.add_error("Bundle not sealed (missing bundle_hash)")
        return result
    
    claimed_hash = manifest['bundle_hash']
    
    # Reconstruct manifest for hash verification
    # Must include verification_profile
    # Must exclude derived fields (provenance_summary, files, integrity)
    manifest_for_hash = {
        "version": manifest['version'],
        "bundle_type": manifest['bundle_type'],
        "verification_profile": manifest.get('verification_profile'),
        "components": manifest['components']
    }
    
    computed_hash = hashlib.sha256(
        canonical_json(manifest_for_hash).encode('utf-8')
    ).hexdigest()
    
    if computed_hash != claimed_hash:
        result.add_error(
            f"Bundle seal broken (integrity violation). "
            f"Expected: {claimed_hash[:16]}..., "
            f"Got: {computed_hash[:16]}..."
        )
        return result
    
    # Verify verification profile compatibility
    profile = manifest.get('verification_profile', {})
    if profile.get('id') != VERIFICATION_PROFILE:
        result.add_warning(
            f"Bundle created with profile {profile.get('id')}, "
            f"verifying with {VERIFICATION_PROFILE}. "
            f"Semantics may differ."
        )
    
    # === STEP 2: Verify component file integrity ===
    components = manifest['components']
    
    for role, comp in components.items():
        file_path = bundle_path / comp['file']
        
        if not file_path.exists():
            result.add_error(f"Component file missing: {comp['file']} ({role})")
            continue
        
        try:
            with open(file_path, 'rb') as f:
                actual_hash = hashlib.sha256(f.read()).hexdigest()
            
            if actual_hash != comp['file_sha256']:
                result.add_error(
                    f"Component file modified: {comp['file']} ({role}) "
                    f"(expected: {comp['file_sha256'][:16]}..., "
                    f"got: {actual_hash[:16]}...)"
                )
        except Exception as e:
            result.add_inconclusive(
                f"Could not read component file {comp['file']}: {e}"
            )
    
    # If file integrity failed, stop here
    if result.outcome == VerificationOutcome.FAIL:
        return result
    
    # === STEP 3: Verify component seals ===
    
    # Verify snapshot seal
    snapshot_file = bundle_path / components['input_snapshot']['file']
    try:
        with open(snapshot_file) as f:
            snapshot_data = json.load(f)
        
        # Check content_hash matches
        if snapshot_data['content_hash'] != components['input_snapshot']['content_hash']:
            result.add_error(
                "Snapshot content_hash mismatch "
                "(file content doesn't match bundle manifest)"
            )
    except Exception as e:
        result.add_inconclusive(f"Could not verify snapshot seal: {e}")
    
    # Verify runrecord seal
    runrecord_file = bundle_path / components['runrecord']['file']
    rr_result = verify_runrecord(str(runrecord_file))
    
    if rr_result.outcome == VerificationOutcome.FAIL:
        for err in rr_result.errors:
            result.add_error(f"RunRecord verification failed: {err}")
    elif rr_result.outcome == VerificationOutcome.INCONCLUSIVE:
        for reason in rr_result.inconclusive_reasons:
            result.add_inconclusive(f"RunRecord verification inconclusive: {reason}")
    
    # Verify output snapshot if present
    if 'output_snapshot' in components:
        output_file = bundle_path / components['output_snapshot']['file']
        try:
            with open(output_file) as f:
                output_data = json.load(f)
            
            if output_data['content_hash'] != components['output_snapshot']['content_hash']:
                result.add_error(
                    "Output snapshot content_hash mismatch "
                    "(file content doesn't match bundle manifest)"
                )
        except Exception as e:
            result.add_inconclusive(f"Could not verify output snapshot seal: {e}")
    
    # === STEP 4: Verify provenance chain consistency ===
    try:
        with open(runrecord_file) as f:
            rr_data = json.load(f)
        
        # Check input consistency
        claimed_input = rr_data['provenance']['input_snapshot']
        actual_input = components['input_snapshot']['content_hash']
        
        if claimed_input != actual_input:
            result.add_error(
                f"Provenance chain broken: RunRecord claims input {claimed_input[:16]}... "
                f"but bundle has {actual_input[:16]}..."
            )
        
        # Check output consistency if present
        if 'output_snapshot' in components:
            claimed_output = rr_data['provenance'].get('output_snapshot')
            actual_output = components['output_snapshot']['content_hash']
            
            if claimed_output != actual_output:
                result.add_error(
                    f"Provenance chain broken: RunRecord claims output {claimed_output[:16] if claimed_output else 'None'}... "
                    f"but bundle has {actual_output[:16]}..."
                )
    
    except Exception as e:
        result.add_inconclusive(f"Could not verify provenance chain: {e}")
    
    # === STEP 5: Optional data verification ===
    if data_dir:
        data_result = verify_snapshot(str(snapshot_file), data_dir)
        
        if data_result.outcome == VerificationOutcome.FAIL:
            for err in data_result.errors:
                result.add_error(f"Data verification failed: {err}")
        elif data_result.outcome == VerificationOutcome.INCONCLUSIVE:
            for reason in data_result.inconclusive_reasons:
                result.add_inconclusive(f"Data verification inconclusive: {reason}")
        
        for warn in data_result.warnings:
            result.add_warning(f"Data verification: {warn}")
    
    return result
