#!/usr/bin/env python3
"""
Snapshot with mechanically enforced hash scope.

Hash scope is structurally guaranteed via HashableManifest dataclass.
"""

import json
import hashlib
import copy
from pathlib import Path
from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass


VERSION = "2.1"


class SourceType(Enum):
    """Where files came from."""
    POSIX = "posix"
    CONTAINER = "container"
    DRIVE = "drive"


def canonical_json(obj: Any) -> str:
    """
    Canonical JSON for deterministic hashing.
    
    Rules (see spec/canonical-json-v1.yaml):
    - Keys sorted lexicographically
    - Compact serialization (no whitespace)
    - Separators: ',' between items, ':' between key-value
    - UTF-8 encoding
    """
    return json.dumps(obj, sort_keys=True, separators=(',', ':'))


@dataclass
class HashableManifest:
    """
    The ONLY object that gets hashed to produce content_hash.
    
    Mechanical enforcement: By construction, this excludes annotations.
    """
    version: str
    source_type: str
    files: List[Dict[str, Any]]
    
    def to_hashable_dict(self) -> Dict[str, Any]:
        """Convert to dict in canonical order."""
        return {
            "version": self.version,
            "source_type": self.source_type,
            "files": self.files
        }
    
    def compute_hash(self) -> str:
        """
        Compute SHA-256 hash of this manifest.
        
        Excludes (by construction):
        - annotations
        - created_at
        - any future metadata
        """
        manifest_dict = self.to_hashable_dict()
        canonical = canonical_json(manifest_dict)
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


class Snapshot:
    """
    Cryptographic snapshot with mechanically enforced hash scope.
    
    Design guarantees:
    1. HashableManifest contains ONLY hashed fields
    2. Annotations stored separately
    3. Files sorted canonically before hashing
    4. Manifest deep-copied to prevent mutation
    """
    
    def __init__(self, source_type: SourceType):
        self.source_type = source_type
        self.files: List[Dict[str, Any]] = []
        self.created_at: Optional[float] = None
        self.annotations: Dict[str, Any] = {}
        
        self._hashable_manifest: Optional[HashableManifest] = None
        self._content_hash: Optional[str] = None
    
    def add_file(self, path: str, sha256: str, size: int):
        """Add file to snapshot."""
        if self._content_hash:
            raise RuntimeError(
                "Cannot modify snapshot after finalization.\n"
                "REASON: Hash is already computed and immutable."
            )
        
        self.files.append({
            "path": path,
            "sha256": sha256,
            "size": size
        })
    
    def finalize(self) -> str:
        """
        Compute content_hash from ONLY the hashable manifest.
        
        Enforcement:
        1. Files sorted canonically (deterministic ordering)
        2. Manifest deep-copied (prevents mutation)
        3. Hash computed from manifest only (excludes annotations)
        """
        if self._content_hash:
            raise RuntimeError("Snapshot already finalized")
        
        # Sort files canonically (UTF-8 bytewise comparison)
        sorted_files = sorted(self.files, key=lambda f: f["path"])
        
        # Deep copy to prevent mutation
        immutable_files = copy.deepcopy(sorted_files)
        
        # Create hashable manifest
        self._hashable_manifest = HashableManifest(
            version=VERSION,
            source_type=self.source_type.value,
            files=immutable_files
        )
        
        # Compute hash
        self._content_hash = self._hashable_manifest.compute_hash()
        
        return self._content_hash
    
    @property
    def content_hash(self) -> str:
        """Get content hash. Must call finalize() first."""
        if not self._content_hash:
            raise RuntimeError(
                "Snapshot not finalized. Call finalize() first.\n"
                "REASON: Hash scope must be explicit before use."
            )
        return self._content_hash
    
    def add_annotation(self, key: str, value: Any):
        """Add annotation AFTER finalization."""
        if not self._content_hash:
            raise RuntimeError(
                "Cannot add annotations before finalization.\n"
                "REASON: Ensures annotations are added after hash is fixed."
            )
        
        self.annotations[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Export snapshot."""
        if not self._content_hash:
            raise RuntimeError("Snapshot must be finalized before export")
        
        hashable = self._hashable_manifest.to_hashable_dict()
        
        return {
            "hashable_manifest": hashable,
            "content_hash": self._content_hash,
            "created_at": self.created_at,
            "annotations": self.annotations,
            "hash_scope": {
                "hashed_fields": ["version", "source_type", "files"],
                "not_hashed": ["created_at", "annotations"],
                "verification": "content_hash = SHA256(canonical_json(hashable_manifest))",
                "determinism": "Files canonically sorted by path (UTF-8 bytewise) before hashing",
                "note": "Scope mechanically enforced within reference implementation via HashableManifest dataclass"
            }
        }
    
    def verify_hash(self) -> bool:
        """Verify content_hash matches manifest."""
        if not self._hashable_manifest or not self._content_hash:
            return False
        
        recomputed = self._hashable_manifest.compute_hash()
        return recomputed == self._content_hash


def create_snapshot(directory: str, source_type: SourceType = SourceType.POSIX) -> Snapshot:
    """Create snapshot with strict hash scope enforcement."""
    import time
    
    snapshot = Snapshot(source_type)
    snapshot.created_at = time.time()
    
    # Add files
    for path in Path(directory).rglob("*"):
        if path.is_file():
            with open(path, "rb") as f:
                content = f.read()
                sha256 = hashlib.sha256(content).hexdigest()
            
            rel_path = str(path.relative_to(directory))
            snapshot.add_file(rel_path, sha256, len(content))
    
    # Finalize before annotations
    snapshot.finalize()
    
    # Add annotations if needed
    if source_type == SourceType.DRIVE:
        snapshot.add_annotation("note", 
            "Drive metadata is archival annotation only. "
            "POSIX-based verification is authoritative."
        )
    
    return snapshot
