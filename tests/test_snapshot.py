#!/usr/bin/env python3
"""
Snapshot test suite.

Tests mechanical enforcement of hash scope.
"""

import pytest
import json


class TestSnapshot:
    """Test snapshot creation and hashing."""
    
    def test_create_basic_snapshot(self, sample_file):
        """Basic snapshot creation."""
        from reprohash import create_snapshot
        
        snapshot = create_snapshot(str(sample_file.parent))
        
        assert snapshot.content_hash is not None
        assert len(snapshot.content_hash) == 64  # SHA-256
        assert len(snapshot.to_dict()['hashable_manifest']['files']) == 1
    
    def test_hash_scope_explicit(self, sample_file):
        """Hash scope must be explicit."""
        from reprohash import create_snapshot
        
        snapshot = create_snapshot(str(sample_file.parent))
        snapshot_dict = snapshot.to_dict()
        
        # Must have explicit hash scope documentation
        assert 'hash_scope' in snapshot_dict
        assert 'hashed_fields' in snapshot_dict['hash_scope']
        assert 'version' in snapshot_dict['hash_scope']['hashed_fields']
        assert 'source_type' in snapshot_dict['hash_scope']['hashed_fields']
        assert 'files' in snapshot_dict['hash_scope']['hashed_fields']
    
    def test_annotations_excluded_from_hash(self, sample_file):
        """Annotations must not affect hash."""
        from reprohash import create_snapshot
        
        # Snapshot without annotations
        snap1 = create_snapshot(str(sample_file.parent))
        hash1 = snap1.content_hash
        
        # Add annotation
        snap1.add_annotation('test_key', 'test_value')
        
        # Hash MUST be unchanged
        assert snap1.content_hash == hash1
    
    def test_file_ordering_deterministic(self, tmp_workspace):
        """Files must be sorted canonically."""
        from reprohash import create_snapshot
        
        # Create files in non-alphabetical order
        (tmp_workspace / "z.txt").write_text("last")
        (tmp_workspace / "a.txt").write_text("first")
        (tmp_workspace / "m.txt").write_text("middle")
        
        snapshot = create_snapshot(str(tmp_workspace))
        manifest = snapshot.to_dict()['hashable_manifest']
        
        paths = [f['path'] for f in manifest['files']]
        
        # Must be sorted
        assert paths == sorted(paths)
        assert paths == ["a.txt", "m.txt", "z.txt"]
    
    def test_finalization_required(self, sample_file):
        """Cannot access hash before finalization."""
        from reprohash import Snapshot, SourceType
        
        snapshot = Snapshot(SourceType.POSIX)
        snapshot.add_file("test.txt", "abc123", 100)
        
        # Must fail before finalization
        with pytest.raises(RuntimeError, match="not finalized"):
            _ = snapshot.content_hash
        
        # Finalize
        snapshot.finalize()
        
        # Now works
        assert snapshot.content_hash is not None
    
    def test_cannot_modify_after_finalization(self, sample_file):
        """Cannot add files after finalization."""
        from reprohash import Snapshot, SourceType
        
        snapshot = Snapshot(SourceType.POSIX)
        snapshot.add_file("test.txt", "abc123", 100)
        snapshot.finalize()
        
        # Must fail after finalization
        with pytest.raises(RuntimeError, match="after finalization"):
            snapshot.add_file("test2.txt", "def456", 200)
    
    def test_annotations_after_finalization_only(self, sample_file):
        """Annotations can only be added after finalization."""
        from reprohash import Snapshot, SourceType
        
        snapshot = Snapshot(SourceType.POSIX)
        snapshot.add_file("test.txt", "abc123", 100)
        
        # Must fail before finalization
        with pytest.raises(RuntimeError, match="before finalization"):
            snapshot.add_annotation("key", "value")
        
        # Finalize
        snapshot.finalize()
        
        # Now works
        snapshot.add_annotation("key", "value")
        assert "key" in snapshot.annotations
