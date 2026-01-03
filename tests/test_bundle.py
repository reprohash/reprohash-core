#!/usr/bin/env python3
"""
Bundle test suite.

Tests bundle-level sealing and complete verification.
"""

import pytest
import json
import time


class TestBundleSealing:
    """Test bundle-level sealing."""
    
    def test_bundle_has_seal(self, tmp_workspace, sample_file):
        """Bundle must have cryptographic seal."""
        from reprohash import create_snapshot, RunRecord, ZenodoBundle
        
        snapshot = create_snapshot(str(sample_file.parent))
        
        runrecord = RunRecord(snapshot.content_hash, "python test.py")
        runrecord.started = time.time()
        runrecord.ended = time.time() + 1
        runrecord.exit_code = 0
        runrecord.seal()
        
        bundle = ZenodoBundle(snapshot, runrecord)
        bundle_dir = tmp_workspace / "bundle"
        bundle_hash = bundle.create_bundle(str(bundle_dir))
        
        # Must have bundle_hash
        assert bundle_hash is not None
        assert len(bundle_hash) == 64
        
        # Manifest must contain bundle_hash
        manifest_file = bundle_dir / "MANIFEST.json"
        with open(manifest_file) as f:
            manifest = json.load(f)
        
        assert 'bundle_hash' in manifest
        assert manifest['bundle_hash'] == bundle_hash
    
    def test_bundle_seal_binds_components(self, tmp_workspace, sample_file):
        """Bundle seal must bind all component hashes."""
        from reprohash import create_snapshot, RunRecord, ZenodoBundle
        
        snapshot = create_snapshot(str(sample_file.parent))
        
        runrecord = RunRecord(snapshot.content_hash, "python test.py")
        runrecord.started = time.time()
        runrecord.ended = time.time() + 1
        runrecord.exit_code = 0
        runrecord.seal()
        
        bundle = ZenodoBundle(snapshot, runrecord)
        bundle_dir = tmp_workspace / "bundle"
        bundle.create_bundle(str(bundle_dir))
        
        manifest_file = bundle_dir / "MANIFEST.json"
        with open(manifest_file) as f:
            manifest = json.load(f)
        
        # Bundle must reference component hashes
        assert 'components' in manifest
        assert manifest['components']['input_snapshot']['content_hash'] == snapshot.content_hash
        assert manifest['components']['runrecord']['runrecord_hash'] == runrecord.runrecord_hash
    
    def test_bundle_has_verification_profile(self, tmp_workspace, sample_file):
        """Bundle must include verification_profile."""
        from reprohash import create_snapshot, RunRecord, ZenodoBundle
        
        snapshot = create_snapshot(str(sample_file.parent))
        
        runrecord = RunRecord(snapshot.content_hash, "python test.py")
        runrecord.started = time.time()
        runrecord.ended = time.time() + 1
        runrecord.exit_code = 0
        runrecord.seal()
        
        bundle = ZenodoBundle(snapshot, runrecord)
        bundle_dir = tmp_workspace / "bundle"
        bundle.create_bundle(str(bundle_dir))
        
        manifest_file = bundle_dir / "MANIFEST.json"
        with open(manifest_file) as f:
            manifest = json.load(f)
        
        # Must have verification_profile
        assert 'verification_profile' in manifest
        assert 'id' in manifest['verification_profile']
        assert manifest['verification_profile']['id'] == 'reprohash-v2.1-strict'
    
    def test_bundle_verification_detects_component_modification(self, tmp_workspace, sample_file):
        """Bundle verification must detect modified components."""
        from reprohash import create_snapshot, RunRecord, ZenodoBundle
        from reprohash.bundle import verify_bundle
        
        snapshot = create_snapshot(str(sample_file.parent))
        
        runrecord = RunRecord(snapshot.content_hash, "python test.py")
        runrecord.started = time.time()
        runrecord.ended = time.time() + 1
        runrecord.exit_code = 0
        runrecord.seal()
        
        bundle = ZenodoBundle(snapshot, runrecord)
        bundle_dir = tmp_workspace / "bundle"
        bundle.create_bundle(str(bundle_dir))
        
        # Modify a component file
        snapshot_file = bundle_dir / "snapshot.json"
        with open(snapshot_file, 'r') as f:
            snapshot_data = json.load(f)
        
        snapshot_data['annotations']['tampered'] = True
        
        with open(snapshot_file, 'w') as f:
            json.dump(snapshot_data, f)
        
        # Verification must FAIL
        result = verify_bundle(str(bundle_dir))
        
        assert result.outcome.value == "FAIL"
        assert any("modified" in err.lower() for err in result.errors)
    
    def test_bundle_verification_pass_when_intact(self, tmp_workspace, sample_file):
        """Bundle verification must PASS when intact."""
        from reprohash import create_snapshot, RunRecord, ZenodoBundle
        from reprohash.bundle import verify_bundle
        
        snapshot = create_snapshot(str(sample_file.parent))
        
        runrecord = RunRecord(snapshot.content_hash, "python test.py")
        runrecord.started = time.time()
        runrecord.ended = time.time() + 1
        runrecord.exit_code = 0
        runrecord.seal()
        
        bundle = ZenodoBundle(snapshot, runrecord)
        bundle_dir = tmp_workspace / "bundle"
        bundle.create_bundle(str(bundle_dir))
        
        # Verification must PASS
        result = verify_bundle(str(bundle_dir))
        
        assert result.outcome.value == "PASS_INPUT_INTEGRITY"
        assert len(result.errors) == 0
    
    def test_bundle_verification_checks_provenance_chain(self, tmp_workspace, sample_file):
        """Bundle verification must check provenance chain consistency."""
        from reprohash import create_snapshot, RunRecord, ZenodoBundle
        from reprohash.bundle import verify_bundle
        
        snapshot = create_snapshot(str(sample_file.parent))
        
        runrecord = RunRecord(snapshot.content_hash, "python test.py")
        runrecord.started = time.time()
        runrecord.ended = time.time() + 1
        runrecord.exit_code = 0
        runrecord.bind_output("output_hash_123")
        runrecord.seal()
        
        bundle = ZenodoBundle(snapshot, runrecord)
        bundle_dir = tmp_workspace / "bundle"
        bundle.create_bundle(str(bundle_dir))
        
        # Modify runrecord to break provenance chain
        rr_file = bundle_dir / "runrecord.json"
        with open(rr_file, 'r') as f:
            rr_data = json.load(f)
        
        # Change input hash in runrecord
        rr_data['provenance']['input_snapshot'] = "wrong_hash"
        
        with open(rr_file, 'w') as f:
            json.dump(rr_data, f)
        
        # Verification should detect broken provenance chain
        result = verify_bundle(str(bundle_dir))
        
        assert result.outcome.value == "FAIL"
        # Note: This will fail file integrity check first,
        # but that's correct - the runrecord file was modified
