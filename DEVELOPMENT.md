# Development Documentation

**INTERNAL DOCUMENT**

## Current Status (v2.1.9)

**Structural completeness**: All identified gaps closed  
**Technical correctness**: No known bugs within stated scope  
**Governance**: Complete versioning and compatibility model  
**Documentation**: Honest about constraints and limitations  

### Known Limitations (By Design, Documented)

**Mechanical enforcement limitations**:
- Linearity: By convention, not type system
- Verification profile: Declarative, not executable
- Canonical JSON: Python-specific semantics

**Architectural choices**:
- Component verification: Delegated (compositional)
- Profile compatibility: Governance-based (not automated)
- Implementation reference: Python (bounded independence)

These are **design choices** with documented rationale, not bugs.

### What "Within Declared Constraints" Means

We claim:
- "Submission-ready within declared constraints"
- NOT "perfect"
- NOT "unimpeachable"
- NOT "implementation-independent" (we say "bounded independence")

**Why**: Our constraints are documented. Claims match documentation. 
Honest assessment rather than absolute statements.

## Governance Model

See GOVERNANCE.md for:
- Verification profile evolution
- Version compatibility rules
- Breaking change process
- Multi-language implementation requirements

## Testing Philosophy

**Test what we claim**:
- Hash scope exclusion (mechanical)
- Finalization barriers (mechanical)
- Sealing requirements (mechanical)
- Bundle coherence (cryptographic)

**Test what we govern**:
- Profile compatibility (regression tests)
- Canonical JSON conformance (test vectors)
- Version stability (integration tests)

**Don't test what we disclaim**:
- Numerical reproducibility (out of scope)
- Full environment capture (explicitly minimal)
- Author authentication (explicitly not provided)

## Future Work (Acknowledged, Not Current Scope)

**Possible improvements**:
- Executable verification profiles (significant complexity)
- IEEE 754 float specification (canonical JSON)
- Explicit Unicode normalization (canonical JSON)
- Type-system linearity enforcement (Rust rewrite?)
- Formal specification language (TLA+, Coq)

**Current assessment**: Cost/benefit doesn't justify for current use case.

**Governance commitment**: If attempted, requires new profile + RFC process.

## Questions & Discussion

**Internal development**: Use GitHub Issues  
**Design philosophy**: Use GitHub Discussions  
**Governance questions**: governance@reproledger.com

---

*This document tracks engineering reality, not marketing claims.*
