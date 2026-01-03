# What ReproHash Is NOT

## Critical Boundaries

This document explicitly states what ReproHash does NOT do, does NOT claim, 
and is NOT designed for.

---

## NOT a Workflow Manager

ReproHash does NOT:
- Orchestrate scientific computations
- Manage task dependencies
- Schedule pipeline steps
- Execute workflows

**Use instead**: Snakemake, Nextflow, Airflow, Prefect, Dagster

**What ReproHash does**: Snapshot inputs/outputs of workflows you run elsewhere

---

## NOT a Reproducibility Guarantee

ReproHash does NOT guarantee:
- Numerical reproducibility (requires re-execution)
- Bit-for-bit output matching
- Environment equivalence
- Correct science

**What ReproHash does**: Verify input data integrity only

---

## NOT a Platform

ReproHash is NOT:
- A hosting service
- A compute platform
- A data warehouse
- A collaboration platform

**What ReproHash is**: A tool with an optional convenience service layer

---

## NOT Handling Branching Workflows

ReproHash does NOT attempt to represent:
- Parameter sweeps
- Branching workflows
- Multiple execution paths
- Workflow DAGs with fan-out/fan-in

**Design decision**: We intentionally limit provenance to linear chains:
```
input_snapshot → run → output_snapshot
```

**For complex workflows**: Use workflow managers (Snakemake) for execution 
graph, use ReproHash to snapshot each stage's inputs/outputs.

**Example**:
```
# Parameter sweep: 100 runs
for params in sweep:
    input_snap = snapshot(f"inputs_{params}")
    run(params)
    output_snap = snapshot(f"outputs_{params}")
    # Create 100 separate linear provenance chains
```

---

## NOT a Container Registry

ReproHash does NOT:
- Store container images
- Manage container versions
- Build containers
- Verify container integrity

**What ReproHash does**: Record container digest if provided (annotation only)

---

## NOT Defending Against Malicious Authors

ReproHash assumes good faith. It does NOT:
- Detect fabricated data
- Prevent selective reporting
- Validate scientific correctness
- Replace peer review

**What ReproHash does**: Help honest authors avoid accidental irreproducibility

---

## NOT Capturing Full Environment

ReproHash does NOT control:
- Operating system kernel
- Hardware (CPU, GPU, drivers)
- System libraries
- Cluster scheduler state
- Network state
- Filesystem state

**What ReproHash does**: Capture minimal environment metadata (Python version, 
platform), with explicit note that full environment is not controlled

---

## NOT Real-Time or Event-Driven

The optional service's Drive monitoring is NOT:
- Real-time
- Guaranteed to capture all changes
- Event-complete
- Semantically precise

**What it is**: Best-effort convenience for triggering snapshots

---

## NOT Continuous Reproducibility

Scheduled integrity checks are NOT:
- Continuous reproducibility validation
- Ongoing execution monitoring
- Live reproducibility assurance

**What they are**: Periodic checks of input integrity only

---

## NOT a Version Control System

ReproHash does NOT:
- Track incremental changes (use Git)
- Support branching/merging
- Provide diff/patch
- Store history

**What ReproHash does**: Snapshot point-in-time states

---

## NOT a Data Repository

ReproHash does NOT:
- Store your data
- Provide data hosting
- Manage data access
- Backup your files

**What ReproHash does**: Snapshot data hashes and metadata; data remains yours

---

## NOT Commercial Lock-In

**Explicitly**:
- Open source core (Apache 2.0)
- Zero dependencies on paid service
- Free CLI works forever
- Papers remain verifiable if company disappears

---

## Summary: Correct Usage

### ✅ Use ReproHash For
- Verifying input data integrity
- Creating archival snapshots
- Enabling offline verification
- Documenting input provenance

### ❌ Do NOT Use ReproHash For
- Workflow orchestration (use Snakemake)
- Reproducibility guarantee (requires re-execution)
- Complex provenance graphs (we do linear chains only)
- Full environment capture (minimal only)
- Defense against fraud (assumes good faith)

---

## Questions?

If you're unsure whether ReproHash is appropriate for your use case, ask:

**"Does this require verifying input file integrity?"**
- Yes → ReproHash is appropriate
- No → You probably need a different tool

See [USAGE.md](USAGE.md) for proper usage examples.
