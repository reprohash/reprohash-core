#!/usr/bin/env python3
"""
Complete CLI with prospective-only runrecord creation.

Design principle: CLI enforces prospective recording via 'run' command only.
Retroactive creation requires programmatic API (explicit bypass of safeguards).
"""

import sys
import argparse
import json
import subprocess
import time
from pathlib import Path


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="ReproHash - Cryptographic Input State Verification",
        epilog="Complete documentation: https://docs.reprohash.org"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Snapshot command
    snapshot_parser = subparsers.add_parser('snapshot', help='Create snapshot')
    snapshot_parser.add_argument('directory', help='Directory to snapshot')
    snapshot_parser.add_argument('-o', '--output', required=True, help='Output file')
    snapshot_parser.add_argument('--source', choices=['posix', 'container', 'drive'], 
                                default='posix', help='Source type')
    
    # Run command (ONLY way to create runrecords via CLI)
    run_parser = subparsers.add_parser('run', 
                                       help='Execute command and create sealed runrecord (prospective recording only)')
    run_parser.add_argument('--input-hash', required=True,
                           help='Input snapshot hash')
    run_parser.add_argument('--exec', required=True,
                           help='Shell command to execute')
    run_parser.add_argument('-o', '--output', required=True,
                           help='Output runrecord JSON file')
    run_parser.add_argument('--reproducibility-class',
                           choices=['deterministic', 'stochastic', 'unknown'],
                           default='unknown',
                           help='Reproducibility class (default: unknown)')
    
    # Verify snapshot command
    verify_parser = subparsers.add_parser('verify', help='Verify snapshot')
    verify_parser.add_argument('snapshot', help='Snapshot file')
    verify_parser.add_argument('-d', '--directory', required=True, help='Data directory')
    
    # Verify runrecord command
    verify_rr_parser = subparsers.add_parser('verify-runrecord', 
                                             help='Verify runrecord seal')
    verify_rr_parser.add_argument('runrecord', help='RunRecord file')
    
    # Verify bundle command
    verify_bundle_parser = subparsers.add_parser('verify-bundle',
                                                 help='Verify complete bundle')
    verify_bundle_parser.add_argument('bundle_dir', help='Bundle directory')
    verify_bundle_parser.add_argument('-d', '--data-dir', 
                                     help='Data directory for snapshot verification (optional)')
    
    # Create bundle command
    bundle_parser = subparsers.add_parser('create-bundle', 
                                         help='Create complete verification bundle')
    bundle_parser.add_argument('--input-snapshot', required=True, 
                              help='Input snapshot JSON file')
    bundle_parser.add_argument('--runrecord', required=True, 
                              help='RunRecord JSON file')
    bundle_parser.add_argument('--output-snapshot', 
                              help='Output snapshot JSON file (optional)')
    bundle_parser.add_argument('-o', '--output', required=True, 
                              help='Output bundle directory')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Handle commands
    if args.command == 'snapshot':
        from reprohash import create_snapshot, SourceType
        
        source_type = SourceType[args.source.upper()]
        snapshot = create_snapshot(args.directory, source_type)
        
        with open(args.output, 'w') as f:
            json.dump(snapshot.to_dict(), f, indent=2)
        
        print(f"✓ Snapshot created: {args.output}")
        print(f"  Content hash: {snapshot.content_hash}")
    
    elif args.command == 'run':
        from reprohash import RunRecord, ReproducibilityClass
        
        print(f"🚀 Executing: {args.exec}")
        print(f"   Input hash: {args.input_hash[:16]}...")
        print()
        
        # Create runrecord
        repro_class = ReproducibilityClass[args.reproducibility_class.upper()]
        runrecord = RunRecord(args.input_hash, args.exec, repro_class)
        
        # Execute command and capture timing
        runrecord.started = time.time()
        try:
            result = subprocess.run(args.command, shell=True)
            exit_code = result.returncode
        except Exception as e:
            print(f"✗ Execution failed: {e}")
            exit_code = 1
        
        runrecord.ended = time.time()
        runrecord.exit_code = exit_code
        
        # Seal immediately (prospective recording)
        seal_hash = runrecord.seal()
        
        # Export to JSON
        with open(args.output, 'w') as f:
            json.dump(runrecord.to_dict(), f, indent=2)
        
        print()
        print(f"✓ RunRecord created and sealed: {args.output}")
        print(f"  Run ID: {runrecord.run_id}")
        print(f"  Seal hash: {seal_hash}")
        print(f"  Exit code: {exit_code}")
        print(f"  Duration: {runrecord.ended - runrecord.started:.2f}s")
        print()
        print("ℹ  Note: Output snapshot binding requires programmatic API")
        print("   See: https://docs.reprohash.org/advanced-workflows")
        
        # Exit with same code as the executed command
        sys.exit(exit_code)
    
    elif args.command == 'verify':
        from reprohash import verify_snapshot
        
        result = verify_snapshot(args.snapshot, args.directory)
        _print_result(result)
        sys.exit(0 if result.outcome.value == "PASS_INPUT_INTEGRITY" else 1)
    
    elif args.command == 'verify-runrecord':
        from reprohash import verify_runrecord
        
        result = verify_runrecord(args.runrecord)
        _print_result(result)
        sys.exit(0 if result.outcome.value == "PASS_INPUT_INTEGRITY" else 1)
    
    elif args.command == 'verify-bundle':
        from reprohash.bundle import verify_bundle
        
        result = verify_bundle(args.bundle_dir, args.data_dir)
        _print_result(result)
        sys.exit(0 if result.outcome.value == "PASS_INPUT_INTEGRITY" else 1)
    
    elif args.command == 'create-bundle':
        # Full implementation
        from reprohash import Snapshot, RunRecord, SourceType
        from reprohash.bundle import ZenodoBundle
        
        # Load input snapshot
        with open(args.input_snapshot) as f:
            input_snap_data = json.load(f)
        
        # Reconstruct Snapshot object
        input_snapshot = Snapshot(SourceType.POSIX)
        for file_info in input_snap_data['hashable_manifest']['files']:
            input_snapshot.add_file(
                file_info['path'],
                file_info['sha256'],
                file_info['size']
            )
        input_snapshot.finalize()
        
        # Load runrecord
        with open(args.runrecord) as f:
            rr_data = json.load(f)
        
        # Reconstruct RunRecord object
        from reprohash import ReproducibilityClass
        runrecord = RunRecord(
            rr_data['provenance']['input_snapshot'],
            rr_data['execution']['command'],
            ReproducibilityClass[rr_data['reproducibility_class'].upper()]
        )
        runrecord.run_id = rr_data['run_id']
        runrecord.runrecord_hash = rr_data['runrecord_hash']
        runrecord.exit_code = rr_data['execution'].get('exit_code')
        runrecord.started = rr_data['execution'].get('started_timestamp')
        runrecord.ended = rr_data['execution'].get('ended_timestamp')
        
        if rr_data['provenance'].get('output_snapshot'):
            runrecord.output_snapshot_hash = rr_data['provenance']['output_snapshot']
        
        # Load output snapshot if provided
        output_snapshot = None
        if args.output_snapshot:
            with open(args.output_snapshot) as f:
                output_snap_data = json.load(f)
            
            output_snapshot = Snapshot(SourceType.POSIX)
            for file_info in output_snap_data['hashable_manifest']['files']:
                output_snapshot.add_file(
                    file_info['path'],
                    file_info['sha256'],
                    file_info['size']
                )
            output_snapshot.finalize()
        
        # Create bundle
        bundle = ZenodoBundle(input_snapshot, runrecord, output_snapshot)
        bundle_hash = bundle.create_bundle(args.output)
        
        print(f"✓ Bundle created: {args.output}")
        print(f"  Bundle hash: {bundle_hash}")
        print(f"  Verification: reprohash verify-bundle {args.output}")


def _print_result(result):
    """Print verification result."""
    print(f"\n{'='*60}")
    print(f"Outcome: {result.outcome.value}")
    print(f"{'='*60}")
    
    if result.errors:
        print("\n✗ Errors:")
        for err in result.errors:
            print(f"  • {err}")
    
    if result.inconclusive_reasons:
        print("\n⚠ Inconclusive:")
        for reason in result.inconclusive_reasons:
            print(f"  • {reason}")
    
    if result.warnings:
        print("\n⚠ Warnings:")
        for warn in result.warnings:
            print(f"  • {warn}")
    
    if result.outcome.value == "PASS_INPUT_INTEGRITY":
        print("\n✓ All checks passed")


if __name__ == "__main__":
    main()
