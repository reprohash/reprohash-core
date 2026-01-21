#!/usr/bin/env python3
"""
Test suite for environment plugin system.

Run with: pytest test_env_plugins.py -v
"""

import pytest
import json
import tempfile
from pathlib import Path

from reprohash.env_plugins import (
    EnvironmentPlugin,
    PipEnvironmentPlugin,
    PluginRegistry,
    EnvironmentCapture,
    EnvironmentMetadata,
    verify_environment_metadata,
    compare_environment_metadata
)
from reprohash import RunRecord, ReproducibilityClass


class TestPluginBase:
    """Test base plugin functionality."""
    
    def test_pip_plugin_capture(self):
        """Test that pip plugin captures environment."""
        plugin = PipEnvironmentPlugin()
        
        data = plugin.capture()
        
        # Should have Python info
        assert 'python' in data
        assert 'version' in data['python']
        assert 'implementation' in data['python']
        
        # Should have packages
        assert 'packages' in data
        assert isinstance(data['packages'], dict)
        
        # Should have capture method
        assert data['capture_method'] == 'importlib.metadata'
    
    def test_plugin_envelope(self):
        """Test that plugin wraps data in standard envelope."""
        plugin = PipEnvironmentPlugin()
        
        envelope = plugin.capture_with_envelope()
        
        # Check envelope structure
        assert envelope['schema'] == 'reprohash.env.v1'
        assert envelope['captured_by']['plugin'] == 'pip'
        assert envelope['captured_by']['plugin_version'] == '1.0'
        assert 'timestamp' in envelope
        assert 'data' in envelope
    
    def test_plugin_fingerprint_hash(self):
        """Test fingerprint hash computation."""
        plugin = PipEnvironmentPlugin()
        
        envelope = plugin.capture_with_envelope()
        hash1 = plugin.get_fingerprint_hash(envelope)
        
        # Should be SHA-256 (64 hex chars)
        assert len(hash1) == 64
        assert all(c in '0123456789abcdef' for c in hash1)
        
        # Should be deterministic
        hash2 = plugin.get_fingerprint_hash(envelope)
        assert hash1 == hash2
    
    def test_pip_plugin_summary(self):
        """Test summary extraction."""
        plugin = PipEnvironmentPlugin()
        
        data = plugin.capture()
        summary = plugin.get_summary(data)
        
        assert 'python' in summary
        assert 'key_packages' in summary
        assert 'total_packages' in summary


class TestPluginRegistry:
    """Test plugin registry."""
    
    def test_registry_has_pip(self):
        """Test that pip plugin is registered."""
        assert 'pip' in PluginRegistry.list_plugins()
    
    def test_registry_get_plugin(self):
        """Test getting plugin by name."""
        plugin_class = PluginRegistry.get('pip')
        
        assert plugin_class is not None
        assert plugin_class.PLUGIN_NAME == 'pip'
    
    def test_registry_get_nonexistent(self):
        """Test getting nonexistent plugin."""
        plugin_class = PluginRegistry.get('nonexistent')
        assert plugin_class is None


class TestEnvironmentCapture:
    """Test environment capture orchestrator."""
    
    def test_capture_with_pip_plugin(self):
        """Test capturing environment with pip plugin."""
        metadata = EnvironmentCapture.capture_environment(['pip'])
        
        assert metadata is not None
        assert isinstance(metadata, EnvironmentMetadata)
        assert metadata.plugin_name == 'pip'
        assert len(metadata.fingerprint_hash) == 64
        assert metadata.summary is not None
    
    def test_capture_without_plugins(self):
        """Test that no plugins returns None."""
        metadata = EnvironmentCapture.capture_environment([])
        assert metadata is None
    
    def test_capture_with_invalid_plugin(self):
        """Test that invalid plugin raises error."""
        with pytest.raises(ValueError, match="Unknown plugin"):
            EnvironmentCapture.capture_environment(['nonexistent'])
    
    def test_multiple_plugins_not_supported(self):
        """Test that multiple plugins raise error."""
        with pytest.raises(ValueError, match="Multiple environment plugins"):
            EnvironmentCapture.capture_environment(['pip', 'conda'])


class TestRunRecordIntegration:
    """Test RunRecord integration with environment plugins."""
    
    def test_runrecord_without_env_plugin(self):
        """Test RunRecord without environment capture (backwards compatible)."""
        rr = RunRecord(
            input_snapshot_hash='abc123',
            command='python test.py',
            env_plugins=None
        )
        
        rr.started = 1234567890.0
        rr.ended = 1234567900.0
        rr.exit_code = 0
        rr.seal()
        
        rr_dict = rr.to_dict()
        
        # Should NOT have environment_metadata
        assert 'environment_metadata' not in rr_dict
    
    def test_runrecord_with_env_plugin(self):
        """Test RunRecord with environment capture."""
        rr = RunRecord(
            input_snapshot_hash='abc123',
            command='python test.py',
            env_plugins=['pip']
        )
        
        rr.started = 1234567890.0
        rr.ended = 1234567900.0
        rr.exit_code = 0
        rr.seal()
        
        rr_dict = rr.to_dict()
        
        # Should have environment_metadata
        assert 'environment_metadata' in rr_dict
        
        env_meta = rr_dict['environment_metadata']
        assert env_meta['captured_by'] == 'pip'
        assert 'fingerprint_hash' in env_meta
        assert 'summary' in env_meta
    
    def test_seal_unchanged_by_environment(self):
        """Test that environment does NOT affect seal hash."""
        # Create two RunRecords with IDENTICAL execution but different env plugins
        rr1 = RunRecord('abc123', 'python test.py', env_plugins=None)
        rr1.started = 1234567890.0
        rr1.ended = 1234567900.0
        rr1.exit_code = 0
        
        rr2 = RunRecord('abc123', 'python test.py', env_plugins=['pip'])
        rr2.started = 1234567890.0
        rr2.ended = 1234567900.0
        rr2.exit_code = 0
        
        # CRITICAL: Make run_ids identical (they're normally unique UUIDs)
        # This simulates the same execution, just with/without env metadata
        rr2.run_id = rr1.run_id
        
        # Now seal both
        seal1 = rr1.seal()
        seal2 = rr2.seal()
        
        # Seals should be IDENTICAL (environment metadata does not affect seal)
        # This is the critical invariant: env_metadata is informational only
        assert seal1 == seal2


class TestEnvironmentVerification:
    """Test environment metadata verification."""
    
    def test_verify_runrecord_without_env(self):
        """Test verifying RunRecord without environment metadata."""
        rr = RunRecord('abc123', 'python test.py', env_plugins=None)
        rr.started = 1234567890.0
        rr.ended = 1234567900.0
        rr.exit_code = 0
        rr.seal()
        
        rr_dict = rr.to_dict()
        
        result = verify_environment_metadata(rr_dict)
        
        assert result['verified'] is True
        assert len(result['errors']) == 0
        assert any('No environment metadata' in w for w in result['warnings'])
    
    def test_verify_runrecord_with_env(self):
        """Test verifying RunRecord with environment metadata."""
        rr = RunRecord('abc123', 'python test.py', env_plugins=['pip'])
        rr.started = 1234567890.0
        rr.ended = 1234567900.0
        rr.exit_code = 0
        rr.seal()
        
        rr_dict = rr.to_dict()
        
        result = verify_environment_metadata(rr_dict)
        
        assert result['verified'] is True
        assert len(result['errors']) == 0
    
    def test_verify_with_tampered_fingerprint(self):
        """Test that tampering with fingerprint is detected."""
        rr = RunRecord('abc123', 'python test.py', env_plugins=['pip'])
        rr.started = 1234567890.0
        rr.ended = 1234567900.0
        rr.exit_code = 0
        rr.seal()
        
        rr_dict = rr.to_dict()
        
        # Tamper with fingerprint
        rr_dict['environment_metadata']['fingerprint_hash'] = 'tampered'
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(rr_dict, f)
            temp_file = f.name
        
        # Create fake environment file
        temp_dir = Path(temp_file).parent
        env_file = temp_dir / 'environment_pip.json'
        
        with open(env_file, 'w') as f:
            # Write valid environment data
            env_data = rr.env_metadata._full_envelope
            json.dump(env_data, f)
        
        # Update path in RunRecord
        rr_dict['environment_metadata']['full_data_file'] = 'environment_pip.json'
        
        with open(temp_file, 'w') as f:
            json.dump(rr_dict, f)
        
        # Verify with bundle directory
        result = verify_environment_metadata(rr_dict, temp_dir)
        
        # Should detect mismatch
        assert result['verified'] is False
        assert any('hash mismatch' in e.lower() for e in result['errors'])
        
        # Cleanup
        Path(temp_file).unlink()
        env_file.unlink()


class TestEnvironmentComparison:
    """Test comparing environments between RunRecords."""
    
    def test_compare_identical_environments(self):
        """Test comparing two RunRecords with identical environments."""
        # Create two RunRecords with same environment
        # Capture environment once and reuse it to ensure identical hashes
        env_metadata = EnvironmentCapture.capture_environment(['pip'])
        
        # Create first RunRecord and manually attach the environment
        rr1 = RunRecord('abc123', 'python test.py', env_plugins=None)
        rr1.env_metadata = env_metadata
        rr1.started = 1234567890.0
        rr1.ended = 1234567900.0
        rr1.exit_code = 0
        rr1.seal()
        
        # Create second RunRecord and attach the SAME environment metadata
        rr2 = RunRecord('abc123', 'python test.py', env_plugins=None)
        rr2.env_metadata = env_metadata  # Same object = same hash
        rr2.started = 1234567890.0
        rr2.ended = 1234567900.0
        rr2.exit_code = 0
        rr2.seal()
        
        # Compare
        result = compare_environment_metadata(rr1.to_dict(), rr2.to_dict())
        
        assert result['comparable'] is True
        assert result['identical'] is True
    
    def test_compare_without_environment(self):
        """Test comparing RunRecords without environment metadata."""
        rr1 = RunRecord('abc123', 'python test.py', env_plugins=None)
        rr1.started = 1234567890.0
        rr1.ended = 1234567900.0
        rr1.exit_code = 0
        rr1.seal()
        
        rr2 = RunRecord('abc123', 'python test.py', env_plugins=None)
        rr2.started = 1234567890.0
        rr2.ended = 1234567900.0
        rr2.exit_code = 0
        rr2.seal()
        
        result = compare_environment_metadata(rr1.to_dict(), rr2.to_dict())
        
        assert result['comparable'] is False


class TestEndToEnd:
    """End-to-end integration tests."""
    
    def test_full_workflow_with_environment(self):
        """Test complete workflow with environment capture."""
        # 1. Create RunRecord with environment
        rr = RunRecord(
            input_snapshot_hash='abc123',
            command='python train.py',
            reproducibility_class=ReproducibilityClass.STOCHASTIC,
            env_plugins=['pip']
        )
        
        # 2. Simulate execution
        rr.started = 1234567890.0
        rr.ended = 1234567900.0
        rr.exit_code = 0
        
        # 3. Seal
        seal_hash = rr.seal()
        assert len(seal_hash) == 64
        
        # 4. Export to JSON
        rr_dict = rr.to_dict()
        
        # 5. Verify structure
        assert 'environment_metadata' in rr_dict
        assert 'runrecord_hash' in rr_dict
        
        # 6. Save to temp directory (simulating bundle)
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_dir = Path(tmpdir)
            
            # Save RunRecord
            rr_file = bundle_dir / 'runrecord.json'
            with open(rr_file, 'w') as f:
                json.dump(rr_dict, f)
            
            # Save environment data
            rr.save_environment_to_bundle(bundle_dir)
            
            # Verify environment file was created
            env_file = bundle_dir / rr.env_metadata.full_data_file
            assert env_file.exists()
            
            # 7. Verify
            result = verify_environment_metadata(rr_dict, bundle_dir)
            assert result['verified'] is True
            assert len(result['errors']) == 0


# ============================================================
# Run Tests
# ============================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
