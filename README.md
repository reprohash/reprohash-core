# ReproHash - Cryptographic Input State Verification

**Version**: 2.1.9  
**License**: Apache 2.0  
**Status**: Submission-ready within declared constraints

## What ReproHash Does

Creates cryptographic snapshots of computational input states and enables 
verification without re-execution.

### Verifies ✅
- Input file integrity (SHA-256 hashes)
- Snapshot manifest consistency (mechanically enforced scope)
- Run record tamper-evidence (sealed provenance)
- Bundle coherence (component binding)

### Does NOT Verify ❌
- Numerical reproducibility (requires re-execution)
- Environment equivalence (minimal capture only)
- Execution correctness (not validated)
- Author authenticity (provides integrity, not authentication)

See [WHAT_THIS_IS_NOT.md](docs/WHAT_THIS_IS_NOT.md) for complete boundaries.

## Design Principles

**Fail-Fast**: Binary outcomes (PASS/FAIL/INCONCLUSIVE)  
**Mechanical Enforcement**: Within reference implementation  
**Honest Boundaries**: Explicit about limitations  
**Governance**: Documented versioning and compatibility  

See [PHILOSOPHY.md](docs/PHILOSOPHY.md) and [GOVERNANCE.md](docs/GOVERNANCE.md)

## Guarantees and Constraints

**What we guarantee** (within declared constraints):
- 10-year free CLI verification minimum
- Verification profile stability
- Offline verification forever
- Open source (Apache 2.0)

**What we cannot guarantee**:
- Language-independent implementation (Python-specific semantics)
- Semantic enforcement via profile parsing (declarative only)
- Future proof against all specification changes

See GOVERNANCE.md for complete versioning and compatibility commitments.

[... rest of README ...]
