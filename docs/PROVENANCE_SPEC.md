# Provenance Specification

## Design Philosophy

ReproHash provenance is **intentionally minimal**.

We represent **linear chains** only:
```
input_snapshot → run → output_snapshot
```

## What We Do NOT Support

ReproHash does NOT handle:
- ❌ Branching workflows
- ❌ Parameter sweeps
- ❌ Fan-out/fan-in patterns
- ❌ Multiple execution paths
- ❌ Workflow DAGs

**This is by design.**

## Why Linear Chains Only?

### 1. Simplicity
Complex provenance graphs introduce:
- Ambiguous semantics
- Version explosion
- Query complexity
- Maintenance burden

### 2. Scope Focus
We verify **input integrity**, not **workflow structure**.

Workflow structure is handled by:
- Snakemake
- Nextflow
- Airflow
- CWL

### 3. Reviewer Clarity
A linear chain is trivially verifiable:
- Reviewer downloads input snapshot
- Verifies files match hash
- Done

Complex DAGs require workflow execution engines.

## Provenance Objects

### Snapshot
```json
{
  "content_hash": "abc123...",
  "files": [...]
}
```

### RunRecord
```json
{
  "run_id": "xyz789...",
  "runrecord_hash": "def456...",
  "provenance": {
    "input_snapshot": "abc123...",
    "output_snapshot": "ghi789..."
  }
}
```

### Provenance Chain
```
input_hash → run_id → output_hash
```

That's it. Simple. Verifiable. Archival.

## Handling Complex Workflows

### Parameter Sweep Example
```python
# Wrong: Try to represent sweep in one provenance graph
# ReproHash doesn't do this

# Right: Create separate chains for each run
for params in sweep:
    input_snap = create_snapshot(f"inputs/{params}")
    
    runrecord = RunRecord(input_snap.content_hash, f"train.py {params}")
    runrecord.started = time.time()
    # ... execute ...
    runrecord.ended = time.time()
    
    output_snap = create_snapshot(f"outputs/{params}")
    runrecord.bind_output(output_snap.content_hash)
    runrecord.seal()
    
    # Each parameter setting gets its own linear chain
```

### Branching Workflow Example
```python
# Snakemake manages branches
# ReproHash snapshots each stage

# Stage 1: Data prep
prep_input = create_snapshot("raw_data/")
# ... run prep ...
prep_output = create_snapshot("prep_data/")

# Stage 2a: Model A
model_a_input = create_snapshot("prep_data/")  # Same as prep output
# ... train model A ...
model_a_output = create_snapshot("model_a/")

# Stage 2b: Model B
model_b_input = create_snapshot("prep_data/")  # Same as prep output
# ... train model B ...
model_b_output = create_snapshot("model_b/")

# Each branch gets its own linear chain
# Snakemake DAG represents branch structure
# ReproHash verifies inputs at each stage
```

## Provenance Verification

Given a paper with:
- Input snapshot hash: `abc123`
- RunRecord ID: `xyz789`
- Output snapshot hash: `ghi789`

Reviewer can verify:
```bash
# 1. Verify input integrity
reprohash verify input_snapshot.json -d data/

# 2. Verify runrecord seal
reprohash verify-runrecord runrecord.json

# 3. Verify output integrity
reprohash verify output_snapshot.json -d output_data/

# Or all at once:
reprohash verify-bundle bundle/ -d data/
```

No graph traversal. No complex queries. Just hash verification.

## Why This Is Sufficient

For scientific papers, reviewers care about:
1. Can I get the exact inputs?
2. Were they modified?
3. What command was run?

A linear chain answers all three.

Workflow structure is documented elsewhere (Snakemake file, paper Methods).

## Questions?

**Q**: How do I represent multiple reruns?  
**A**: Create separate RunRecords for each. They share the same input snapshot hash.

**Q**: How do I represent ensemble models?  
**A**: Each model gets its own chain. Input hash can be identical.

**Q**: What about intermediate steps?  
**A**: Snapshot each step's output. Chain: `A → B → C`, represented as two chains: `A → B` and `B → C`.

---

## Summary

ReproHash provenance is:
- **Linear chains only** (by design)
- **Simple** (hash verification only)
- **Reviewer-friendly** (no graph traversal)
- **Sufficient** (for input integrity verification)

For complex workflow provenance, use workflow managers.
ReproHash snapshots the stages.
