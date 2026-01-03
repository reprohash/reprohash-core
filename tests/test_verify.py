#!/usr/bin/env python3
"""
Verification test suite.

Tests epistemic outcomes (PASS/FAIL/INCONCLUSIVE).
"""

import pytest
import json


class TestEpistemicOutcomes:
    """Test proper epistemic categories."""
    
    def test_pass_when_all_checks_succeed(self, tmp_workspace, sample_file):
        """PASS_INPUT_INTEGRITY when verification succeeds."""
        from reprohash import create_snapshot, verify_snapshot
        
        snapshot = create_snapshot(str(sample_file.parent))
        snapshot_file = tmp_workspace / "snapshot.json"
        with open(snapshot_file, "w") as f:
            json.dump(snapshot.to_dict(), f)
        
        result = verify_snapshot(str(snapshot_file), str(sample_file.parent))
        
        assert result.outcome.value == "PASS_INPUT_INTEGRITY"
        assert len(result.errors) == 0
        assert len(result.inconclusive_reasons) == 0
    
    def test_fail_when_file_changed(self, tmp_workspace, sample_file):
        """FAIL when integrity violated (file changed)."""
        from reprohash import create_snapshot, verify_snapshot
        
        snapshot = create_snapshot(str(sample_file.parent))
        snapshot_file = tmp_workspace / "snapshot.json"
        with open(snapshot_file, "w") as f:
            json.dump(snapshot.to_dict(), f)
        
        # Modify file
        sample_file.write_text("CHANGED")
        
        result = verify_snapshot(str(snapshot_file), str(sample_file.parent))
        
        assert result.outcome.value == "FAIL"
        assert any("CHANGED" in err for err in result.errors)
    
    def test_inconclusive_when_snapshot_missing(self, tmp_workspace):
        """INCONCLUSIVE when verification infrastructure unavailable."""
        from reprohash import verify_snapshot
        
        result = verify_snapshot(
            str(tmp_workspace / "nonexistent.json"),
            str(tmp_workspace)
        )
        
        assert result.outcome.value == "INCONCLUSIVE"
        assert len(result.inconclusive_reasons) > 0
        assert "not found" in result.inconclusive_reasons[0]
    
    def test_inconclusive_when_directory_missing(self, tmp_workspace, sample_file):
        """INCONCLUSIVE when data directory unavailable."""
        from reprohash import create_snapshot, verify_snapshot
        
        snapshot = create_snapshot(str(sample_file.parent))
        snapshot_file = tmp_workspace / "snapshot.json"
        with open(snapshot_file, "w") as f:
            json.dump(snapshot.to_dict(), f)
        
        result = verify_snapshot(
            str(snapshot_file),
            str(tmp_workspace / "nonexistent_dir")
        )
        
        assert result.outcome.value == "INCONCLUSIVE"
        assert any("not found" in r for r in result.inconclusive_reasons)
    
    def test_fail_on_missing_file(self, tmp_workspace, sample_file):
        """Missing file causes FAIL."""
        from reprohash import create_snapshot, verify_snapshot
        
        snapshot = create_snapshot(str(sample_file.parent))
        snapshot_file = tmp_workspace / "snapshot.json"
        with open(snapshot_file, "w") as f:
            json.dump(snapshot.to_dict(), f)
        
        # Delete file
        sample_file.unlink()
        
        result = verify_snapshot(str(snapshot_file), str(sample_file.parent))
        
        assert result.outcome.value == "FAIL"
        assert any("MISSING" in err for err in result.errors)
    
    def test_fail_on_corrupted_manifest(self, tmp_workspace, sample_file):
        """Corrupted manifest causes FAIL."""
        from reprohash import create_snapshot, verify_snapshot
        
        snapshot = create_snapshot(str(sample_file.parent))
        snapshot_dict = snapshot.to_dict()
        
        # Corrupt manifest
        snapshot_dict['hashable_manifest']['files'][0]['sha256'] = 'corrupted'
        
        snapshot_file = tmp_workspace / "snapshot.json"
        with open(snapshot_file, "w") as f:
            json.dump(snapshot_dict, f)
        
        result = verify_snapshot(str(snapshot_file), str(sample_file.parent))
        
        assert result.outcome.value == "FAIL"


class TestSpecConformance:
    """Test suite verifying spec matches implementation."""
    
    def test_canonical_json_matches_spec(self):
        """Canonical JSON must match spec/canonical-json-v1.yaml rules."""
        from reprohash.snapshot import canonical_json
        
        # Test case from spec
        obj = {
            "version": "2.1",
            "source_type": "posix",
            "files": [
                {"path": "a.txt", "sha256": "abc123", "size": 100}
            ]
        }
        
        result = canonical_json(obj)
        
        # Spec requirements:
        # 1. Keys sorted
        assert result.startswith('{"files":[')
        
        # 2. No whitespace
        assert ' ' not in result
        assert '\n' not in result
        
        # 3. Correct separators
        assert ',' in result
        assert ':' in result
        assert ', ' not in result  # No space after comma
        assert ': ' not in result  # No space after colon
    
    def test_hash_computation_deterministic(self):
        """Hash computation must be deterministic."""
        from reprohash.snapshot import HashableManifest
        
        # Test vector
        manifest = HashableManifest(
            version="2.1",
            source_type="posix",
            files=[
                {"path": "test.txt", "sha256": "abc123", "size": 100}
            ]
        )
        
        # Compute hash multiple times
        hash1 = manifest.compute_hash()
        hash2 = manifest.compute_hash()
        
        # Must be identical
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256
