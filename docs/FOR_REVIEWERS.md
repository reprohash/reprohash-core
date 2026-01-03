# Design Philosophy

## Core Principles

### 1. Mechanical Enforcement Within Reference Implementation

Correctness is enforced by code structure, not discipline or documentation.

**Examples**:
- Hash scope: `HashableManifest` dataclass excludes annotations structurally
- Finalization: `RuntimeError` if hash accessed before finalize()
- Sealing: `RuntimeError` if unsealed record exported
- Linearity: Constructor signature enforces single input/output
- Verification: Full cryptographic check (no warnings for normative requirements)
- Bundle binding: Manifest hash cryptographically binds all components

**Important**: Enforcement is within the Python reference implementation.
A language-independent formal specification is provided in `spec/hash-scope-v1.yaml`.

### 2. Epistemically Honest Verification

Verification has THREE outcomes (proper scientific epistemology):

- **PASS_INPUT_INTEGRITY**: Verification completed successfully, all checks passed
- **FAIL**: Verification completed, found integrity violations
- **INCONCLUSIVE**: Verification could not be completed

**CRITICAL DISTINCTION**:
- FAIL = "integrity claim is false" (files changed, missing, or corrupted)
- INCONCLUSIVE = "integrity claim not evaluable" (verification infrastructure unavailable)

**Rationale**: Scientific reviewers must distinguish claims that are FALSE from claims that are NOT EVALUATED.

**Examples**:
- File hash mismatch → FAIL (claim is false)
- Manifest corrupted → FAIL (claim is false)
- Snapshot file not found → INCONCLUSIVE (claim not evaluated)
- Permission denied → INCONCLUSIVE (claim not evaluated)

This is **fail-fast with epistemic precision**: we fail decisively when we can evaluate, and we're honest when we cannot.

### 3. Honest Boundaries

Explicitly state what we do NOT do.

**Examples**:
- Not a workflow manager
- Not reproducibility guarantee
- Not authentication system
- Not defending against fraud

See [WHAT_THIS_IS_NOT.md](WHAT_THIS_IS_NOT.md)

### 4. Linear Provenance (Enforced by Convention)

Linear provenance enforced by:
- Constructor signature (single input)
- `bind_output()` semantics (single output, overwrites)
- Schema structure (not arrays)
- Documentation

**Note**: Enforcement is by convention, not type system. Python's mutability allows:
```python
rr.output_snapshot_hash = "another_hash"  # Overwrites, doesn't append
```

This is acceptable because:
- Constructor prevents accidental multi-parent creation
- Schema clearly documents single-parent structure
- Intentional violation requires bypassing normal API

**Not supported** (by design):
- Multi-parent structures
- Multi-output structures
- Branching workflows
- Parameter sweeps

### 5. Service-Independent Verification

Verification does not depend on:
- Internet access
- API availability
- Service existence
- Account credentials
- Trust in service operator

**But**: Assumes good-faith authorship (not adversarial model).

CLI works offline, permanently.

### 6. Minimal Environment Capture

Capture only what's reliable:
- Python version
- Platform string

**Explicitly NOT captured**:
- OS kernel details
- Hardware specs
- Library versions (unless in container)

**Sealing rationale**: Environment is sealed to prevent post-hoc narrative 
editing, not to assert completeness or reproducibility.

### 7. Bundle-Level Coherence with Semantic Binding

**Publication artifacts are cryptographically AND semantically bound.**

Three levels of binding:

1. **Component identity**: content_hash, runrecord_hash
2. **File integrity**: SHA-256 of JSON files
3. **Semantic verification**: verification_profile declares interpretation rules

**Verification Profile: Declarative, Not Executable**

IMPORTANT: `verification_profile` is a **declaration**, not executable policy.

What this means:
- Profile states what verification should do
- Implementation ensures those semantics
- Compatibility maintained via **governance and testing**, not runtime parsing

**Why this design**:
- Avoids self-referential complexity
- Keeps codebase maintainable
- Relies on version discipline + test vectors

**Trade-off acknowledged**: Profile compatibility requires implementation 
discipline, not mechanical enforcement. This is **delegated trust** to 
maintainers, documented in GOVERNANCE.md.

### 8. Delegated Verification (Design Choice)

**Bundle verification delegates to component verifiers.**

Pattern:
```python
# Bundle verifies:
verify_runrecord(runrecord_file)  # Delegates to runrecord verifier
# Rather than:
# reimplement_runrecord_verification()  # Reimplements semantics
```

**Why this design**:
- Single source of truth (component verifiers)
- Avoids semantic drift
- Maintains consistency

**What this means**:
- Bundle trusts snapshot.verify_hash()
- Bundle trusts runrecord.verify_seal()
- Bundle checks provenance consistency, not component internals

This is **compositional verification**, not monolithic re-derivation.

**Trade-off**: Changes to component verification logic affect bundle 
verification (but this is intended - we want consistency).

### 9. Bounded Implementation Independence

**Canonical JSON fully specified WITHIN CONSTRAINTS.**

What's specified:
- Key ordering (lexicographic)
- Separators (compact)
- Encoding (UTF-8)
- Safe types (strings, integers)

What's constrained:
- Float precision (Python default)
- Unicode normalization (assumed NFC)
- Implementation (Python json module)

**Design choice**: Accept Python-specific semantics rather than attempt 
impossible implementation-independence.

**Mitigation**: Use only safe types (strings, integers), documented in 
spec/canonical-json-v1.yaml.

**Future**: Language-independent formal spec is possible but requires 
significant additional work (IEEE 754 float control, explicit Unicode 
normalization, etc.). Current scope is **bounded independence** with 
explicit constraints.

## Implementation Patterns

### HashableManifest Pattern

```python
@dataclass
class HashableManifest:
    """ONLY fields that get hashed."""
    version: str
    source_type: str
    files: List[Dict]
```

Annotations stored separately → structurally excluded from hash.

### Finalization Barrier

```python
def finalize():
    # Sort + deep copy + compute hash
    self._content_hash = ...

@property
def content_hash():
    if not self._content_hash:
        raise RuntimeError("Must finalize first")
```

Cannot access hash before finalization → enforces workflow.

### Linear Provenance Enforcement

```python
def __init__(self, input_snapshot_hash: str):  # Single input
    self.input_snapshot_hash = input_snapshot_hash
    self.output_snapshot_hash: Optional[str] = None  # Single output
```

Type system enforces linearity → no multi-parent structures possible.

### Binary Verification Outcomes

```python
class VerificationOutcome(Enum):
    PASS_INPUT_INTEGRITY = "PASS_INPUT_INTEGRITY"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"
```

Three outcomes preserve scientific epistemology.

### Full Cryptographic Verification

```python
def verify_runrecord(runrecord_file):
    # Reconstruct sealed record
    # Recompute hash
    # Compare
    # Return PASS, FAIL, or INCONCLUSIVE
    # NO WARNINGS for normative requirements
```

If verification cannot be mechanical, return INCONCLUSIVE.

## Language Precision

### ✅ Use
- "Tamper-evident" (modifications detectable)
- "Mechanically enforced within reference implementation"
- "Service-independent verification"
- "Integrity, not authenticity"
- "PASS_INPUT_INTEGRITY" (scope-explicit outcome)
- "Epistemically honest" (three outcomes)
- "Within declared constraints"
- "Delegated verification" (compositional design)

### ❌ Avoid
- "Immutable" (technically incorrect)
- "Zero-trust" (implies adversarial model we don't have)
- "Provable by construction" (implies formal proof)
- "Guarantees reproducibility" (overclaim)
- "Perfect philosophical consistency" (absolute claim)
- "PASS" without scope qualifier (too coarse)
- "Unimpeachable" (overstates bounded guarantees)

## Threat Model

**Defends against**:
- Accidental file modifications
- Unintentional corruption
- Input state ambiguity
- Post-hoc narrative editing (via sealing)

**Does NOT defend against**:
- Malicious data fabrication
- Selective reporting
- Fraudulent authorship

Assumes good-faith actors.

## Machine-Readable Specification

`spec/hash-scope-v1.yaml` and `spec/canonical-json-v1.yaml` provide language-independent reference.

This enables:
- Independent implementations (within constraints)
- Verification across languages
- Formal specification reference

## Summary: Design Choices and Trade-Offs

**Mechanically enforced** (within reference implementation):
- Hash scope exclusion (HashableManifest)
- Finalization workflow (RuntimeError)
- Sealing requirements (RuntimeError)
- Bundle file integrity (cryptographic)

**Governance-enforced** (discipline + testing):
- Verification profile compatibility
- Semantic stability across versions
- Multi-language implementations

**Explicitly out of scope**:
- Workflow DAGs
- Full environment capture
- Author authentication
- Adversarial fraud detection

**Known limitations** (documented, accepted):
- Linearity by convention (not type system)
- Canonical JSON Python-specific (bounded independence)
- Verification profile declarative (not executable)
- Component verification delegated (compositional design)

These are not bugs - they are **design choices with documented rationale**.

See GOVERNANCE.md for versioning and compatibility commitments.

## Questions?

See [FOR_REVIEWERS.md](FOR_REVIEWERS.md) for reviewer-specific guidance.
