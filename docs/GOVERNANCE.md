# Governance and Versioning

## Purpose

This document defines how ReproHash maintains compatibility across versions 
and how verification semantics remain stable over time.

## Verification Profile Governance

### Profile Identity

Each bundle includes a `verification_profile`:
```json
{
  "verification_profile": {
    "id": "reprohash-v2.1-strict",
    "semantics": "strict",
    "verification_rules": {...}
  }
}
```

### Profile Nature: Declarative, Not Executable

**IMPORTANT**: The verification profile is **declarative**, not mechanically 
enforced by profile parsing.

What this means:
- Profile declares what verification should do
- Implementation ensures it does those things
- Profile compatibility is **governance**, not automatic

**Why this design**:
- Avoids self-referential complexity (profile executing itself)
- Keeps implementation maintainable
- Relies on versioning + testing, not runtime interpretation

**Consequence**: Future versions must honor profile semantics via discipline 
and testing, not mechanical enforcement.

This is **delegated trust** to the implementation maintainers, acknowledged 
as a limitation.

### Profile Compatibility Rules

**MUST maintain compatibility**:
- Outcome model (PASS/FAIL/INCONCLUSIVE semantics)
- Verification checks (bundle seal, component seals, provenance)
- Failure conditions (what triggers FAIL vs INCONCLUSIVE)

**MAY change without new profile**:
- Performance optimizations
- Error message wording
- Internal implementation details
- Additional warnings (non-normative)

**MUST create new profile if**:
- Outcome semantics change
- Verification rules change
- Failure conditions change

### Profile Evolution

**Current profiles**:
- `reprohash-v2.1-strict`: Current production

**Future profiles** (examples):
- `reprohash-v2.2-strict`: Version 2.2 semantics
- `reprohash-v3.0-strict`: Major version change

**Backward compatibility**:
- Older bundles remain verifiable with original profile
- Verifiers SHOULD warn when profile doesn't match
- Verifiers MUST NOT silently reinterpret

### Version String Semantics

**Version format**: `MAJOR.MINOR.PATCH`

**Compatibility guarantees**:
- Same MAJOR.MINOR: Full compatibility
- Different MAJOR: Profile change required
- Different MINOR: Should be compatible if profile unchanged

**Example**:
- v2.1.8 can verify v2.1.0 bundles (same profile)
- v3.0.0 would use new profile (breaking change)

## Bundle Longevity Guarantees

### 10-Year Promise

**What we guarantee**:
- Free CLI verification for 10 years minimum
- Profile semantics stable (documented breaking changes only)
- Older bundles remain verifiable

**What we cannot guarantee**:
- Specific implementation availability (but spec enables reimplementation)
- Service availability (but verification is offline)
- Hardware compatibility (but code is pure Python)

### After 10 Years

**If ReproHash project ends**:
- Open source code remains (Apache 2.0)
- Spec remains normative reference
- Community can maintain/fork
- Verification continues offline

**If implementation needs updates**:
- New profile created
- Old profile semantics documented
- Verification rules preserved

## Implementation Governance

### Who Can Change Semantics

**Semantic changes** (require new profile):
- Core maintainers only
- Via RFC process
- With community review

**Non-semantic changes** (same profile):
- Contributors via PR
- Test suite validates compatibility
- Maintainer review required

### Compatibility Testing

**Required tests**:
- All v2.1.x bundles verify identically
- Profile warnings trigger when expected
- No silent semantic drift

**Test bundles**:
- Reference bundles in `test-vectors/`
- Must pass on all v2.1.x versions
- Establish normative behavior

## Language-Independent Verification

### Current State

**What's specified**:
- Hash scope (spec/hash-scope-v1.yaml)
- Canonical JSON (spec/canonical-json-v1.yaml)
- Verification profile (above)

**What's Python-specific**:
- Canonical JSON float handling
- Unicode normalization assumptions
- Implementation details

**Known constraints**:
- Reference implementation is Python
- Other languages must match Python semantics
- Test vectors establish ground truth

### Future Multi-Language Support

**Requirements for new implementation**:
1. Must match canonical JSON behavior
2. Must produce identical hashes
3. Must pass conformance test suite
4. Must respect verification profiles
5. Must document any deviations

**Governance**:
- Python implementation remains normative
- Deviations documented explicitly
- Community consensus for spec changes

## Dispute Resolution

### If Implementations Disagree

**Priority order**:
1. Test vectors (ground truth)
2. YAML specs (normative)
3. Python reference implementation (authoritative)
4. Documentation (interpretive)

### If Profile Semantics Unclear

**Process**:
1. Check test vectors
2. Review governance docs
3. Consult RFC history
4. Ask maintainers (last resort)

## Future Governance Evolution

**This governance model may evolve**, but changes require:
- RFC with rationale
- Community input period (30 days minimum)
- Supermajority approval (3/4 maintainers)
- Backward compatibility plan

## Questions?

**Governance questions**: governance@reprohash.org  
**Technical questions**: opensource@reprohash.org
