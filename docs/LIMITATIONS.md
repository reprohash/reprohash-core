# Limitations of ReproHash

*Include this section in your paper's Methods or Supplementary Information*

## What ReproHash Verifies

ReproHash provides cryptographic verification of **input data integrity only**.

Specifically:
1. All input files match their recorded SHA-256 hashes
2. Snapshot manifest is cryptographically consistent
3. Run records are tamper-evident (sealed)

## What ReproHash Does NOT Verify

### 1. Author Authenticity
**CRITICAL LIMITATION**: ReproHash provides **integrity, not authentication**.

**What this means**:
- Seals detect tampering after creation
- Seals do NOT identify who created the record
- Anyone can fabricate a sealed RunRecord
- No cryptographic signatures or author binding

**Implication**: ReproHash assumes good-faith authorship. It defends against 
**accidental** modification, not **malicious fabrication**.

Peer review and institutional oversight remain essential.

### 2. Numerical Reproducibility
**Limitation**: ReproHash does not rerun computations.

**Implication**: Verification confirms input integrity but not numerical 
reproducibility, which requires independent re-execution.

### 3. Environment Completeness
**Limitation**: Captures minimal environment (Python version, platform) but 
does NOT control or fully document:
- OS kernel
- Hardware (CPU, GPU, drivers)
- System libraries
- Scheduler state

**Why environment is sealed despite being incomplete**:
Environment metadata is sealed to prevent **post-hoc narrative editing**, 
not to assert **completeness** or **reproducibility**.

The seal provides tamper-evidence of what was recorded at runtime, protecting 
against later modification of the environment claim. However, the seal does 
NOT validate that the environment was sufficient for reproducibility.

**Implication**: Identical inputs may produce different outputs due to 
environment differences not captured by ReproHash.

### 4. Execution Correctness
**Limitation**: Does not validate scientific correctness.

### 5. Defense Against Malicious Authors
**Limitation**: Assumes good faith.

### 6. Container Completeness
**Limitation**: Container digest (if provided) pins userland but not host 
substrate.

### 7. Branching Workflows
**Limitation**: ReproHash does not represent branching workflows, parameter 
sweeps, or complex execution DAGs.

**Scope**: We intentionally handle linear provenance chains only:
```
input → run → output
```

**Implication**: For parameter sweeps or branching workflows, create separate 
linear chains for each execution path. Workflow structure is documented 
via workflow managers (Snakemake, Nextflow), not ReproHash.

### 8. Unsealed RunRecords
**Normative requirement**: Unsealed RunRecords MUST NOT be cited, exported, 
or archived.

**Implication**: Only sealed RunRecords are archival objects. Papers must 
cite sealed records only.

### 9. Language-Independent Verification
**Limitation**: Mechanical enforcement relies on Python reference implementation.

**Implication**: Hash scope guarantees are mechanically enforced in Python 
and formally specified for other languages.

**Future work**: A fully language-independent formal specification is future work.

## Design Philosophy: Strict Fail-Fast

ReproHash verification has exactly three outcomes:
- **PASS_INPUT_INTEGRITY**: All checks passed
- **FAIL**: Any check failed OR verification couldn't complete
- **INCONCLUSIVE**: Verification could not be completed

**Rationale**:
- "Couldn't verify" is not philosophically different from "found problems"
- Both mean the integrity claim cannot be validated
- Binary outcomes eliminate ambiguity

If verification cannot be done rigorously, ReproHash fails explicitly:
- Missing files: FAIL
- Corrupted manifest: FAIL
- Unreadable snapshot: INCONCLUSIVE
- Seal verification error: FAIL or INCONCLUSIVE

No partial success. No uncertain outcomes. Clear binary result.

## Hash Scope Verification

The hash scope (what is and isn't included in the content_hash) is 
**mechanically enforced within the reference implementation** via the 
`HashableManifest` dataclass in `reprohash/snapshot.py`.

This provides enforcement of:
- Annotation exclusion
- Deterministic file ordering
- Manifest immutability

Note: Enforcement relies on the Python reference implementation's 
object semantics. A language-independent formal specification is provided 
in spec/hash-scope-v1.yaml.

## Recommended Additional Validation

For full reproducibility claims:
1. Re-execution in equivalent environment
2. Complete environment documentation
3. Code review
4. Output verification
5. Statistical validation

## Appropriate Claims in Papers

### ✅ Appropriate
> "We provide cryptographic verification of input data integrity using 
> ReproHash (DOI: XXX). The input snapshot hash abc123... uniquely 
> identifies our input files. Reviewers can verify data integrity without 
> re-downloading the dataset."

### ❌ Inappropriate
> "Our results are cryptographically proven reproducible."

### ✅ Appropriate
> "Input integrity was verified using ReproHash. Numerical reproducibility 
> was additionally confirmed by re-running on a separate system (Appendix S1)."

### ❌ Inappropriate
> "ReproHash prevents scientific fraud."

### ✅ Appropriate
> "Environment metadata was sealed to prevent post-hoc editing, but does not 
> constitute complete environment documentation."

### ❌ Inappropriate
> "ReproHash captured the complete computational environment."

## Contact

Questions: limitations@reprohash.org
