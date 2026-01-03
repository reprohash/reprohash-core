#!/usr/bin/env python3
"""
RunRecord test suite.

Tests sealing enforcement and linear provenance.
"""

import pytest
import time


class TestRunRecord:
    """Test run record creation and sealing."""
    
    def test_unsealed_cannot_export(self):
        """Unsealed RunRecords MUST NOT be exported."""
        from reprohash import RunRecord
        
        runrecord = RunRecord("abc123", "python train.py")
        
        # Must raise error on export
        with pytest.raises(RuntimeError, match="must be sealed"):
            runrecord.to_dict()
    
    def test_seal_required_before_export(self):
        """Seal is required before export."""
        from reprohash import RunRecord
        
        runrecord = RunRecord("abc123", "python train.py")
        runrecord.started = time.time()
        runrecord.ended = time.time() + 10
        runrecord.exit_code = 0
        
        # Seal
        seal_hash = runrecord.seal()
        
        # Now export should work
        runrecord_dict = runrecord.to_dict()
        
        assert runrecord_dict['runrecord_hash'] == seal_hash
        assert runrecord_dict['integrity']['tamper_evident'] is True
        assert runrecord_dict['integrity']['authenticated'] is False
    
    def test_seal_prevents_mutation(self):
        """Sealed record detects mutation."""
        from reprohash import RunRecord
        
        runrecord = RunRecord("abc123", "python train.py")
        runrecord.started = time.time()
        runrecord.ended = time.time() + 10
        runrecord.exit_code = 0
        
        runrecord.seal()
        
        # Verify seal
        assert runrecord.verify_seal() is True
        
        # Mutate
        runrecord.command = "python train_modified.py"
        
        # Seal verification MUST fail
        assert runrecord.verify_seal() is False
    
    def test_seal_integrity_after_any_field_modification(self):
        """Modifying ANY field after sealing invalidates seal."""
        from reprohash import RunRecord
        
        runrecord = RunRecord("abc123", "python train.py")
        runrecord.started = 1234567890.0
        runrecord.ended = 1234567900.0
        runrecord.exit_code = 0
        runrecord.bind_output("output_xyz")
        
        # Seal
        runrecord.seal()
        assert runrecord.verify_seal() is True
        
        # Test each field mutation
        original_command = runrecord.command
        runrecord.command = "modified"
        assert runrecord.verify_seal() is False
        runrecord.command = original_command
        
        original_exit = runrecord.exit_code
        runrecord.exit_code = 1
        assert runrecord.verify_seal() is False
        runrecord.exit_code = original_exit
        
        original_output = runrecord.output_snapshot_hash
        runrecord.output_snapshot_hash = "tampered"
        assert runrecord.verify_seal() is False
        runrecord.output_snapshot_hash = original_output
        
        # Should pass again with original values
        assert runrecord.verify_seal() is True
    
    def test_double_seal_fails(self):
        """Cannot seal twice."""
        from reprohash import RunRecord
        
        runrecord = RunRecord("abc123", "python train.py")
        runrecord.started = time.time()
        runrecord.ended = time.time() + 1
        runrecord.exit_code = 0
        runrecord.seal()
        
        with pytest.raises(RuntimeError, match="already sealed"):
            runrecord.seal()
    
    def test_provenance_summary_informational(self):
        """provenance_summary is informational, not cryptographic."""
        from reprohash import RunRecord
        
        runrecord = RunRecord("input_abc", "python train.py")
        runrecord.started = time.time()
        runrecord.ended = time.time() + 1
        runrecord.exit_code = 0
        runrecord.bind_output("output_xyz")
        runrecord.seal()
        
        rr_dict = runrecord.to_dict()
        
        # Must have provenance_summary
        assert "provenance_summary" in rr_dict["provenance"]
        
        # Must have note that it's informational
        assert "note" in rr_dict["provenance"]
        assert "informational only" in rr_dict["provenance"]["note"]
    
    def test_linear_provenance_enforced(self):
        """Linear provenance: single input, single output."""
        from reprohash import RunRecord
        
        # Constructor enforces single input
        runrecord = RunRecord("input_abc", "python train.py")
        
        # bind_output enforces single output (overwrites)
        runrecord.bind_output("output_1")
        assert runrecord.output_snapshot_hash == "output_1"
        
        runrecord.bind_output("output_2")  # Overwrites
        assert runrecord.output_snapshot_hash == "output_2"
