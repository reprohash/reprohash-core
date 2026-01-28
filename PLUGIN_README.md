# ReproHash Environment Plugin System

**Version:** 2.1  
**Status:** Production-ready  
**Design:** Minimal, non-normative, domain-agnostic

---

## What This Is

An **optional plugin architecture** for capturing execution environment metadata in ReproHash RunRecords.

### Key Principles

1. **Environment metadata never affects PASS/FAIL outcomes**
2. **Plugins are optional** - absence of environment metadata is always valid
3. **Plugins are non-normative** - they document, not verify
4. **Plugins are domain-specific** - different fields need different plugins
5. **Core verification stays filesystem-based**

---

## Quick Start

### Basic Usage

```bash
# Without environment capture (works as before)
reprohash run \
  --input-hash abc123... \
  --exec "python train.py" \
  -o runrecord.json

# With environment capture (NEW)
reprohash run \
  --input-hash abc123... \
  --exec "python train.py" \
  --env-plugin pip \
  -o runrecord.json
```

### What Gets Captured

When `--env-plugin pip` is used:

```json
{
  "environment_metadata": {
    "fingerprint_hash": "4a5b6c7d8e9f...",
    "captured_by": "pip",
    "summary": {
      "python": "3.10.14",
      "key_packages": {
        "torch": "2.9.1",
        "numpy": "2.2.6"
      }
    },
    "note": "Informational only. Not part of cryptographic verification."
  }
}
```

---

## Why This Matters

### Your Original Problem

You ran the **same code** in two environments:

- **ml-a1**: NumPy 1.26.x, Torch 2.7.0
- **ml-b**: NumPy 2.2.6, Torch 2.9.1

ReproHash correctly verified **input integrity** both times.

But reviewers will ask: *"Did the environment differ?"*

### What Environment Plugins Solve

```bash
# Run in ml-a1
reprohash run --input-hash $HASH --exec "python train.py" --env-plugin pip -o rr_a.json

# Run in ml-b  
reprohash run --input-hash $HASH --exec "python train.py" --env-plugin pip -o rr_b.json

# Compare
reprohash compare-environments rr_a.json rr_b.json
```

**Output:**

```
Environment Comparison:
  Python: 3.10.14 (both)
  torch: 2.7.0 → 2.9.1 ⚠ MAJOR VERSION CHANGE
  numpy: 1.26.4 → 2.2.6 ⚠ ABI INCOMPATIBILITY LIKELY

Note: Input integrity verified in both cases.
Environment differences are informational only.
```

Now it's **immediately obvious** what changed.

---

## Available Plugins

### Built-in: `pip`

Captures Python and pip package versions.

**Usage:**
```bash
reprohash run --input-hash $HASH --exec "..." --env-plugin pip -o runrecord.json
```

**What it captures:**
- Python version (e.g., "3.10.14")
- Implementation (e.g., "CPython")
- All installed packages (via `importlib.metadata`)

**What it does NOT capture:**
- CUDA versions
- System libraries
- Compiler versions
- Hardware details

This is intentional - we stay minimal.

### Future Plugins (Examples)

```bash
# Conda environments
--env-plugin conda

# Docker containers
--env-plugin docker

# R environments
--env-plugin renv

# Julia manifests
--env-plugin julia

# HPC modules
--env-plugin modules

# Custom plugins
--env-plugin custom:mylab.bioinformatics
```

---

## How It Works

### 1. Plugin Execution (During `reprohash run`)

```
User runs: reprohash run --env-plugin pip --exec "python train.py"

Timeline:
  1. Plugin executes (BEFORE command runs)
  2. Environment captured prospectively
  3. Fingerprint hash computed
  4. Command executes
  5. RunRecord sealed (environment does NOT affect seal)
  6. Metadata attached to RunRecord
```

### 2. What Gets Stored

#### In RunRecord JSON:
- Environment fingerprint hash
- Summary (human-readable)
- Plugin name/version

#### In Bundle:
- Full environment data (separate file)
- Complete package list
- All metadata

### 3. Verification Semantics

```python
# Environment metadata is verified for INTEGRITY
if env_fingerprint_hash != recomputed_hash:
    return FAIL  # Metadata was tampered with

# But environment DIFFERENCES are just warnings
if env_hash_a != env_hash_b:
    add_warning("Environment differs")
    # Still returns PASS_INPUT_INTEGRITY
```

---

## Creating Custom Plugins

### Minimal Plugin Example

```python
from reprohash.env_plugins import EnvironmentPlugin, PluginRegistry

class BiocondaPlugin(EnvironmentPlugin):
    PLUGIN_NAME = "bioconda"
    PLUGIN_VERSION = "1.0"
    
    def capture(self) -> Dict[str, Any]:
        """Capture Bioconda environment."""
        import subprocess
        
        # Get conda environment export
        result = subprocess.run(
            ['conda', 'env', 'export'],
            capture_output=True,
            text=True
        )
        
        return {
            "conda_export": result.stdout,
            "key_tools": {
                "bwa": self._get_version("bwa"),
                "samtools": self._get_version("samtools")
            }
        }
    
    def _get_version(self, tool: str) -> str:
        """Get tool version."""
        # Implementation details...
        pass

# Register plugin
PluginRegistry.register(BiocondaPlugin)
```

### Plugin Requirements

1. **Must inherit from `EnvironmentPlugin`**
2. **Must implement `capture()` method**
3. **Must return JSON-serializable dict**
4. **Must be deterministic** (same environment → same output)
5. **Must not execute user code**
6. **Must not modify environment**

---

## Verification Examples

### Example 1: Same Environment

```bash
$ reprohash verify-bundle bundle/ -d data/

============================================================
Outcome: PASS_INPUT_INTEGRITY
============================================================

Environment Info:
  Plugin: pip
  Fingerprint: 4a5b6c7d8e9f...
  Python: 3.10.14
  Key packages:
    • torch: 2.9.1
    • numpy: 2.2.6

✓ All checks passed
```

### Example 2: Different Environment

```bash
$ reprohash verify-bundle bundle/ -d data/

============================================================
Outcome: PASS_INPUT_INTEGRITY
============================================================

⚠ Warnings:
  • Environment differs from original run:
    - torch: 2.9.1 vs 2.7.0
    - numpy: 2.2.6 vs 1.26.4

✓ Input integrity verified
  (environment differences are informational)
```

### Example 3: No Environment Metadata

```bash
$ reprohash verify-bundle bundle/ -d data/

============================================================
Outcome: PASS_INPUT_INTEGRITY
============================================================

⚠ Warnings:
  • No environment metadata present (this is valid)

✓ All checks passed
```

---

## Design Philosophy

### What We Do NOT Claim

- ❌ "Environment capture guarantees reproducibility"
- ❌ "We solve the dependency problem"
- ❌ "This works across all domains"
- ❌ "Environment is cryptographically verified"

### What We Actually Provide

- ✅ "Environment is captured as structured metadata"
- ✅ "Metadata integrity is cryptographically verified"
- ✅ "Differences are surfaced to reviewers"
- ✅ "Plugin architecture allows domain-specific extensions"

### Why This Is Honest

Computational environments are **domain-specific**:

| Domain | Environment Complexity |
|--------|----------------------|
| Python/ML | pip packages, CUDA |
| Bioinformatics | conda, compiled tools, reference genomes |
| Materials Science | VASP, pseudopotentials, MPI stacks |
| Astrophysics | FORTRAN + modules + calibration files |

No single system can solve all of these.

But we can provide:
- A **plugin interface** (extensible)
- A **reference implementation** (Python/pip)
- A **verification pattern** (integrity without interpretation)

---

## Integration with Existing Workflow

### Before (v2.0)

```bash
reprohash snapshot data/ -o snapshot.json
reprohash run --input-hash $HASH --exec "python train.py" -o rr.json
reprohash create-bundle --input-snapshot snapshot.json --runrecord rr.json -o bundle/
```

### After (v2.1)

```bash
reprohash snapshot data/ -o snapshot.json
reprohash run --input-hash $HASH --exec "python train.py" --env-plugin pip -o rr.json
reprohash create-bundle --input-snapshot snapshot.json --runrecord rr.json -o bundle/
```

**Change:** Just add `--env-plugin pip`. Everything else stays the same.

---

## Commercial Service Layer

### Open Source (Free Forever)
- Plugin execution
- Raw metadata capture
- Environment fingerprint hashing
- CLI comparison

### Paid Service (Optional)
- Automatic environment capture
- Known incompatibility warnings ("NumPy <2 → ≥2: ABI break likely")
- Policy enforcement ("Reject runs unless environment matches")
- Visual diff explanations
- Cross-run analytics
- Drive sidebar integration

---

## Versioning and Compatibility

### Schema Version: `reprohash.env.v1`

This is the envelope schema. All plugins use it.

### Plugin Versions

Each plugin has its own version:
- `pip` v1.0
- `conda` v1.0
- etc.

### Backwards Compatibility

- Old RunRecords (without environment metadata) remain valid
- New RunRecords (with environment metadata) are backwards-compatible
- Seal hash computation **unchanged** (environment does NOT affect it)

---

## Testing

### Basic Test

```bash
# Create RunRecord with environment
reprohash run \
  --input-hash abc123 \
  --exec "python train.py" \
  --env-plugin pip \
  -o runrecord.json

# Verify it worked
python -c "
import json
with open('runrecord.json') as f:
    rr = json.load(f)
    assert 'environment_metadata' in rr
    print('✓ Environment metadata present')
    print(f\"  Fingerprint: {rr['environment_metadata']['fingerprint_hash'][:16]}...\")
"
```

### Environment Comparison Test

```bash
# Run in two different environments
conda activate ml-env-a
reprohash run --input-hash $HASH --exec "python test.py" --env-plugin pip -o rr_a.json

conda activate ml-env-b  
reprohash run --input-hash $HASH --exec "python test.py" --env-plugin pip -o rr_b.json

# Compare
reprohash compare-environments rr_a.json rr_b.json
```

---

## FAQ

### Q: Is environment metadata required?

**No.** It's completely optional. RunRecords without environment metadata are valid.

### Q: Does environment affect PASS/FAIL?

**No.** Environment differences generate warnings, never FAIL.

### Q: Can I verify bundles without environment plugins installed?

**Yes.** Environment metadata verification only checks hash integrity, not semantics.

### Q: What if my domain isn't supported?

Write a custom plugin (see "Creating Custom Plugins" above).

### Q: Does this solve the reproducibility problem?

**No.** This makes environment **visible**, not **reproducible**. Reproducibility requires re-execution in controlled environments.

### Q: Why not just use containers?

Containers are great! But they:
- Don't capture host kernel/drivers
- Don't guarantee reproducibility
- Are another plugin target (`--env-plugin docker`)

---

## Paper Language

Use this in your Methods section:

> "We treat execution environments as first-class metadata objects, captured prospectively at runtime via a plugin architecture. Environment metadata is cryptographically bound to run records but is explicitly non-normative: it does not affect verification outcomes. This design reflects the domain-specific nature of computational environments while allowing reviewers and readers to identify potential sources of variability, such as library or compiler versions."

---

## Summary

### What This System Provides

| Feature | Status |
|---------|--------|
| Environment capture | ✅ Optional |
| Metadata integrity | ✅ Cryptographic |
| Domain-agnostic interface | ✅ Plugin architecture |
| Python/ML support | ✅ Built-in (pip plugin) |
| Verification impact | ⚠️ Informational only |
| Backwards compatibility | ✅ Full |

### What Happens Next

1. Use `--env-plugin pip` for your ML workflows
2. Surface environment differences in comparisons
3. Document this in your Nature Methods paper
4. Extend with domain-specific plugins as needed

---

## Contact

- **Technical**: opensource@reproledger.com
- **Plugin Development**: plugins@reproledger.com
- **Paper Questions**: reviewers@reproledger.com

---

*Last Updated: 2026-01-20*  
*Version: 2.1.0*  
*License: Apache 2.0*
