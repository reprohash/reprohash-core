#!/usr/bin/env python3
"""
Complete CLI update to add compare-environments command.

This is the exact code to add to your reprohash/cli.py file.
"""

import sys
import argparse
import json
import subprocess # nosec
import time
from pathlib import Path


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="ReproHash - Cryptographic Input State Verification",
        epilog="Complete documentation: https://github.com/reprohash/reprohash-core"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # ============================================================
    # Existing commands (snapshot, verify, run, etc.)
    # ============================================================
    
    # Snapshot command
    snapshot_parser = subparsers.add_parser('snapshot', help='Create snapshot')
    snapshot_parser.add_argument('directory', help='Directory to snapshot')
    snapshot_parser.add_argument('-o', '--output', required=True, help='Output file')
    snapshot_parser.add_argument('--source', choices=['posix', 'container', 'drive'], 
                                default='posix', help='Source type')
    
    # Run command
    run_parser = subparsers.add_parser(
        'run', 
        help='Execute command and create sealed runrecord (prospective recording only)'
    )
    run_parser.add_argument('--input-hash', required=True, help='Input snapshot hash')
    run_parser.add_argument('--exec', required=True, help='Shell command to execute')
    run_parser.add_argument('-o', '--output', required=True, help='Output runrecord JSON file')
    run_parser.add_argument(
        '--reproducibility-class',
        choices=['deterministic', 'stochastic', 'unknown'],
        default='unknown',
        help='Reproducibility class (default: unknown)'
    )
    run_parser.add_argument(
        '--env-plugin',
        action='append',
        help='Environment capture plugin (e.g., pip). Can be specified multiple times.'
    )
    
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
    
    # ============================================================
    # NEW: Compare environments command
    # ============================================================
    
    compare_parser = subparsers.add_parser(
        'compare-environments',
        help='Compare environment metadata between two RunRecords'
    )
    compare_parser.add_argument(
        'runrecord1',
        help='First RunRecord JSON file'
    )
    compare_parser.add_argument(
        'runrecord2',
        help='Second RunRecord JSON file'
    )
    compare_parser.add_argument(
        '--json',
        action='store_true',
        help='Output in JSON format'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # ============================================================
    # Handle commands
    # ============================================================
    
    if args.command == 'snapshot':
        from reprohash import create_snapshot, SourceType
        
        source_type = SourceType[args.source.upper()]
        snapshot = create_snapshot(args.directory, source_type)
        
        with open(args.output, 'w') as f:
            json.dump(snapshot.to_dict(), f, indent=2)
        
        print(f" Snapshot created: {args.output}")
        print(f"  Content hash: {snapshot.content_hash}")
    
    elif args.command == 'run':
        from reprohash import RunRecord, ReproducibilityClass
        
        print(f" Executing: {args.exec}")
        print(f"   Input hash: {args.input_hash[:16]}...")
        
        if args.env_plugin:
            print(f"   Environment: Capturing via {', '.join(args.env_plugin)} plugin(s)")
        
        print()
        
        # Create runrecord with optional environment plugins
        repro_class = ReproducibilityClass[args.reproducibility_class.upper()]
        
        runrecord = RunRecord(
            input_snapshot_hash=args.input_hash,
            command=args.exec,
            reproducibility_class=repro_class,
            env_plugins=args.env_plugin
        )
        
        # Execute command
        runrecord.started = time.time()
        try:
            result = subprocess.run(args.exec, shell=True)
            exit_code = result.returncode
        except Exception as e:
            print(f" Execution failed: {e}")
            exit_code = 1
        
        runrecord.ended = time.time()
        runrecord.exit_code = exit_code
        
        # Seal
        seal_hash = runrecord.seal()
        
        # Export to JSON
        runrecord_dict = runrecord.to_dict()
        
        with open(args.output, 'w') as f:
            json.dump(runrecord_dict, f, indent=2)
        
        # Save environment data if captured
        if runrecord.env_metadata:
            runrecord.save_environment_to_bundle(Path(args.output).parent)
            print(f" Environment data saved")
        
        print(f" RunRecord created and sealed: {args.output}")
        print(f"  Run ID: {runrecord.run_id}")
        print(f"  Seal hash: {seal_hash}")
        
        if runrecord.env_metadata:
            print(f"  Environment fingerprint: {runrecord.env_metadata.fingerprint_hash[:16]}...")
        
        print(f"  Exit code: {exit_code}")
        print(f"  Duration: {runrecord.ended - runrecord.started:.2f}s")
        
        if not runrecord.output_snapshot_hash:
            print()
            print("ℹ  Note: Output snapshot binding requires programmatic API")
            print("   See: https://github.com/reprohash/reprohash-core#advanced-workflows")
        
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
        
        print(f" Bundle created: {args.output}")
        print(f"  Bundle hash: {bundle_hash}")
        print(f"  Verification: reprohash verify-bundle {args.output}")
    
    # ============================================================
    # NEW: Handle compare-environments command
    # ============================================================
    
    elif args.command == 'compare-environments':
        from reprohash.env_plugins import compare_environment_metadata
        
        # Load both RunRecords
        try:
            with open(args.runrecord1) as f:
                rr1 = json.load(f)
        except Exception as e:
            print(f" Could not load {args.runrecord1}: {e}")
            sys.exit(1)
        
        try:
            with open(args.runrecord2) as f:
                rr2 = json.load(f)
        except Exception as e:
            print(f" Could not load {args.runrecord2}: {e}")
            sys.exit(1)
        
        # Compare environments
        comparison = compare_environment_metadata(rr1, rr2)
        
        if args.json:
            # JSON output
            print(json.dumps(comparison, indent=2))
            sys.exit(0)
        
        # Human-readable output
        print("=" * 60)
        print("Environment Comparison")
        print("=" * 60)
        
        if not comparison['comparable']:
            print(f"\n {comparison['reason']}")
            print("\nTo compare environments, both RunRecords must have")
            print("been created with --env-plugin flag.")
            print("\nExample:")
            print("  reprohash run --env-plugin pip ... -o runrecord.json")
            sys.exit(1)
        
        print(f"\nRunRecord 1: {args.runrecord1}")
        print(f"  Run ID: {rr1.get('run_id', 'unknown')[:16]}...")
        print(f"  Environment fingerprint: {comparison['fingerprint_a']}")
        
        print(f"\nRunRecord 2: {args.runrecord2}")
        print(f"  Run ID: {rr2.get('run_id', 'unknown')[:16]}...")
        print(f"  Environment fingerprint: {comparison['fingerprint_b']}")
        
        print("\n" + "-" * 60)
        
        if comparison['identical']:
            print(" Environments are IDENTICAL")
            print("\nBoth RunRecords used the same:")
            
            env1 = rr1.get('environment_metadata', {})
            summary = env1.get('summary', {})
            
            if 'python' in summary:
                print(f"  • Python: {summary['python']}")
            
            if 'key_packages' in summary:
                print("  • Key packages:")
                for pkg, ver in summary['key_packages'].items():
                    print(f"      {pkg}: {ver}")
            
            sys.exit(0)
        else:
            print(" Environments DIFFER")
            print("\nDifferences detected:")
            
            for diff in comparison.get('differences', []):
                print(f"  • {diff}")
            
            # Impact analysis
            print("\n" + "=" * 60)
            print("Impact Analysis")
            print("=" * 60)
            
            diffs = comparison.get('differences', [])
            
            critical = []
            moderate = []
            minor = []
            
            for diff in diffs:
                lower_diff = diff.lower()
                
                # Check for critical differences
                if 'numpy' in lower_diff:
                    # Check for NumPy 1.x -> 2.x (ABI break)
                    if '1.' in lower_diff and '2.' in lower_diff:
                        critical.append(f"{diff} [ABI INCOMPATIBILITY LIKELY]")
                    else:
                        moderate.append(diff)
                elif 'torch' in lower_diff:
                    # Check for major version change
                    parts = diff.split('vs')
                    if len(parts) == 2:
                        try:
                            v1 = parts[0].split(':')[1].strip().split('.')[0]
                            v2 = parts[1].strip().split('.')[0]
                            if v1 != v2:
                                critical.append(f"{diff} [MAJOR VERSION CHANGE]")
                            else:
                                moderate.append(diff)
                        except:
                            moderate.append(diff)
                    else:
                        moderate.append(diff)
                elif 'python' in lower_diff:
                    moderate.append(diff)
                else:
                    minor.append(diff)
            
            if critical:
                print("\n🔴 CRITICAL differences (likely to affect results):")
                for item in critical:
                    print(f"   {item}")
            
            if moderate:
                print("\n🟡 MODERATE differences (may affect results):")
                for item in moderate:
                    print(f"   {item}")
            
            if minor:
                print("\n🟢 MINOR differences (unlikely to affect results):")
                for item in minor:
                    print(f"   {item}")
            
            print("\n" + "=" * 60)
            print("Note")
            print("=" * 60)
            print("Input integrity is verified separately.")
            print("Environment differences are informational only.")
            print("Re-execution is required to confirm reproducibility.")
            
            sys.exit(1)  # Exit with code 1 to indicate differences


def _print_result(result):
    """Print verification result."""
    print(f"\n{'='*60}")
    print(f"Outcome: {result.outcome.value}")
    print(f"{'='*60}")
    
    if result.errors:
        print("\n Errors:")
        for err in result.errors:
            print(f"  • {err}")
    
    if result.inconclusive_reasons:
        print("\n Inconclusive:")
        for reason in result.inconclusive_reasons:
            print(f"  • {reason}")
    
    if result.warnings:
        print("\n Warnings:")
        for warn in result.warnings:
            print(f"  • {warn}")
    
    if result.outcome.value == "PASS_INPUT_INTEGRITY":
        print("\n All checks passed")


if __name__ == "__main__":
    main()
