# ReproHash - Cryptographic Input State Verification

## What ReproHash Does

Creates cryptographic snapshots of computational input states and enables 
verification without re-execution.

### Verifies 
- Input file integrity (SHA-256 hashes)
- Snapshot manifest consistency (mechanically enforced scope)
- Run record tamper-evidence (sealed provenance)
- Bundle coherence (component binding)

### Does NOT Verify 
- Numerical reproducibility (requires re-execution)
- Environment equivalence (minimal capture only)
- Execution correctness (not validated)
- Author authenticity (provides integrity, not authentication)

See [docs/WHAT_THIS_IS_NOT.md](docs/WHAT_THIS_IS_NOT.md) for complete boundaries.

---

## Quick Start

### Installation

```bash
pip install reprohash-core
```

### Basic Usage

```bash
# Create snapshot of input data
reprohash snapshot data/ -o snapshot.json

# Verify snapshot against data
reprohash verify snapshot.json -d data/

# Output: PASS_INPUT_INTEGRITY, FAIL, or INCONCLUSIVE
```

### Complete Workflow

```bash
# 1. Snapshot inputs
reprohash snapshot input_data/ -o input_snapshot.json

# 2. Run your computation
python analysis.py

# 3. Create RunRecord (programmatically in your script)
# See examples/ for details

# 4. Snapshot outputs  
reprohash snapshot output_data/ -o output_snapshot.json

# 5. Create complete bundle
reprohash create-bundle \
  --input-snapshot input_snapshot.json \
  --runrecord runrecord.json \
  --output-snapshot output_snapshot.json \
  -o bundle/

# 6. Verify complete bundle
reprohash verify-bundle bundle/ -d input_data/
```

---

## Design Principles

### Fail-Fast with Epistemic Precision
- **PASS_INPUT_INTEGRITY**: All checks passed
- **FAIL**: Integrity violated
- **INCONCLUSIVE**: Could not complete verification

Three outcomes distinguish "claim is false" from "claim not evaluated."

### Mechanical Enforcement
Correctness enforced by code structure within reference implementation:
- Hash scope via `HashableManifest` dataclass
- Finalization via `RuntimeError` barriers
- Sealing via cryptographic binding

### Honest Boundaries
Explicitly states what it does NOT do:
- Not a workflow manager
- Not reproducibility guarantee  
- Not authentication system
- Not defending against fraud

### Governance
- perpetual free verification guarantee (OSS)
- Verification profile stability
- Documented versioning and compatibility

See [docs/PHILOSOPHY.md](docs/PHILOSOPHY.md) and [docs/GOVERNANCE.md](docs/GOVERNANCE.md)

---

## Guarantees and Constraints

### What We Guarantee (Within Declared Constraints)

✅ **Offline verification forever** - No internet required  
✅ **Open source** - Apache 2.0, zero dependencies  
✅ **Verification profile stability** - Same profile = same semantics  
✅ **Service-independent** - Verification never requires paid service

### What We Cannot Guarantee

⚠️ **Language-independent implementation** - Python-specific semantics documented  
⚠️ **Semantic enforcement via profile parsing** - Declarative profile, not executable  
⚠️ **Future-proof against all changes** - Breaking changes require new profile

See [docs/GOVERNANCE.md](docs/GOVERNANCE.md) for complete versioning commitments.

---

## For Reviewers

**You don't need to pay anything.**

ReproHash is fully functional as open source. CLI has no restrictions.
Verification works offline, forever.

### Quick Verification (< 5 minutes)

```bash
# Install once
pip install reprohash-core

# Download bundle from paper's Zenodo link
wget https://zenodo.org/record/XXX/bundle.zip
unzip bundle.zip

# Verify everything
reprohash verify-bundle bundle/ -d input_data/

# Output: PASS_INPUT_INTEGRITY, FAIL, or INCONCLUSIVE
```

See [docs/FOR_REVIEWERS.md](docs/FOR_REVIEWERS.md) for detailed guidance.

---

## Optional Paid Service

A paid service exists for convenience (Drive sync, team features).

**The service is strictly optional and never required for verification.**

Papers verified with ReproHash remain verifiable forever using only this 
free CLI, regardless of whether the service exists.

---

## Architecture

### Three Verification Layers

1. **Component seals** - Individual content hashes
   - Snapshots: `content_hash` over file manifest
   - RunRecords: `runrecord_hash` over execution details

2. **File integrity** - Component file checksums
   - Bundle manifest lists all component files
   - SHA-256 hash for each file

3. **Bundle binding** - Complete artifact coherence
   - `bundle_hash` cryptographically binds components
   - Includes `verification_profile` for semantic stability

### Verification Workflow

```
verify_bundle()
  ├── Bundle seal integrity (manifest not modified)
  ├── Component file integrity (JSON files match hashes)
  ├── Snapshot seal verification (content_hash valid)
  ├── RunRecord seal verification (runrecord_hash valid)
  ├── Provenance chain consistency (input → run → output)
  └── Optional: Data verification (files match snapshot)
```

Complete semantic verification, not just coherence.

---

## Documentation

### Core Documentation
- [PHILOSOPHY.md](docs/PHILOSOPHY.md) - Design principles and patterns
- [GOVERNANCE.md](docs/GOVERNANCE.md) - Versioning and compatibility
- [LIMITATIONS.md](docs/LIMITATIONS.md) - Honest limitations
- [FOR_REVIEWERS.md](docs/FOR_REVIEWERS.md) - Reviewer guide

### Specifications
- [hash-scope-v1.yaml](spec/hash-scope-v1.yaml) - Hash scope specification
- [canonical-json-v1.yaml](spec/canonical-json-v1.yaml) - Canonicalization rules

### Boundaries
- [WHAT_THIS_IS_NOT.md](docs/WHAT_THIS_IS_NOT.md) - Explicit non-goals
- [PROVENANCE_SPEC.md](docs/PROVENANCE_SPEC.md) - Linear chains only

---

## Examples

### Python API

```python
from reprohash import (
    create_snapshot, 
    RunRecord, 
    ZenodoBundle,
    ReproducibilityClass
)

# Create input snapshot
input_snapshot = create_snapshot("data/")
print(f"Input hash: {input_snapshot.content_hash}")

# Create run record
runrecord = RunRecord(
    input_snapshot.content_hash,
    "python train.py --epochs 100",
    ReproducibilityClass.DETERMINISTIC
)

runrecord.started = time.time()
# ... run computation ...
runrecord.ended = time.time()
runrecord.exit_code = 0

# Snapshot outputs
output_snapshot = create_snapshot("results/")
runrecord.bind_output(output_snapshot.content_hash)

# Seal runrecord (REQUIRED before archival)
runrecord.seal()

# Create bundle for publication
bundle = ZenodoBundle(input_snapshot, runrecord, output_snapshot)
bundle_hash = bundle.create_bundle("bundle/")
print(f"Bundle hash: {bundle_hash}")
```

### Verification

```python
from reprohash.bundle import verify_bundle

# Verify complete bundle
result = verify_bundle("bundle/", data_dir="data/")

print(f"Outcome: {result.outcome.value}")
# Outputs: PASS_INPUT_INTEGRITY, FAIL, or INCONCLUSIVE

if result.errors:
    for err in result.errors:
        print(f"Error: {err}")

if result.outcome.value == "PASS_INPUT_INTEGRITY":
    print("✓ All integrity checks passed")
```

---
## Development Setup
```bash
# Clone repository
git clone https://github.com/reprohash/reprohash-core.git
cd reprohash-core

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v --cov=reprohash

# Run conformance tests
pytest tests/test_vectors/ -v
```

## Contributing

1. Read PHILOSOPHY.md and GOVERNANCE.md
2. Check LIMITATIONS.md for scope
3. Add tests for new features
4. Maintain 95%+ coverage
5. Follow existing code style
6. Update documentation

## Running Conformance Tests
```bash
# Verify implementation conforms to profile
python -m reprohash.conformance tests/test_vectors/v2.1/
```
---

## Testing

Run the complete test suite:

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests with coverage
pytest tests/ -v --cov=reprohash --cov-report=term-missing

```

---

## Requirements

### Runtime
- Python 3.8+
- **Zero dependencies** (stdlib only)

### Development  
- pytest (testing)
- pytest-cov (coverage)
- black (formatting)
- mypy (type checking)

---

## Citation

```bibtex
@software{reprohash2025,
  title = {ReproHash: Cryptographic Input State Verification},
  author = {ReproHash Contributors},
  year = {2025},
  version = {2.1.8},
  url = {https://github.com/reprohash/reprohash-core},
  license = {Apache-2.0}
}
```

Paper submission pending.

---

## Contributing

We welcome contributions! Please:

1. Read [PHILOSOPHY.md](docs/PHILOSOPHY.md) for design principles
2. Check [GOVERNANCE.md](docs/GOVERNANCE.md) for compatibility rules
3. Add tests for new features
4. Maintain 95%+ coverage
5. Follow existing code style

### Areas for Contribution
- Additional language implementations (following spec)
- Improved documentation
- Additional test cases
- Bug reports with minimal reproducible examples

---

## Support

### Questions
- **Technical**: opensource@reproledger.com
- **Governance**: governance@reproledger.com  
- **Reviewers**: reviewers@reproledger.com

### Resources
- **Documentation**: https://docs.reproledger.com
- **Issues**: https://github.com/reprohash/reprohash-core/issues
- **Discussions**: https://github.com/reprohash/reprohash-core/discussions

**Reviewer support**: <24h response time guarantee

---

## License

Apache License 2.0

```
Copyright 2025 ReproHash Contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

---

## Status

**Dependencies**: Zero (stdlib only)  


### Roadmap
- [ ] submission
- [ ] Public service beta  
- [ ] Additional language implementations (Rust, Go)
- [ ] Formal specification (TLA+/Coq) - future work

---



[![Tests](https://github.com/reprohash/reprohash-core/workflows/Tests/badge.svg)](https://github.com/reprohash/reprohash-core/actions)
[![Coverage](https://codecov.io/gh/reprohash/reprohash-core/branch/main/graph/badge.svg)](https://codecov.io/gh/reprohash/reprohash-core)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

---

*License: Apache 2.0*
