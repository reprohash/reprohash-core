# ReproHash Python API Reference

## Core Functions

### Snapshot Creation
```python
from reprohash import create_snapshot, SourceType

# Create snapshot
snapshot = create_snapshot("data/", SourceType.POSIX)
print(f"Hash: {snapshot.content_hash}")

# Export to JSON
with open("snapshot.json", "w") as f:
    json.dump(snapshot.to_dict(), f)
```

### Verification
```python
from reprohash import verify_snapshot

result = verify_snapshot("snapshot.json", "data/")

if result.outcome.value == "PASS_INPUT_INTEGRITY":
    print("✓ Verified")
elif result.outcome.value == "FAIL":
    print("✗ Failed:", result.errors)
else:
    print("? Inconclusive:", result.inconclusive_reasons)
```

### RunRecord Creation
```python
from reprohash import RunRecord, ReproducibilityClass
import time

# Create run record
rr = RunRecord(
    snapshot.content_hash,
    "python train.py",
    ReproducibilityClass.DETERMINISTIC,
    env_plugins=["pip"]  # Optional
)

# Execute and record
rr.started = time.time()
# ... run your computation ...
rr.ended = time.time()
rr.exit_code = 0

# Seal (required before archival)
rr.seal()

# Export
with open("runrecord.json", "w") as f:
    json.dump(rr.to_dict(), f)
```

### Bundle Creation
```python
from reprohash import ZenodoBundle

bundle = ZenodoBundle(input_snapshot, runrecord, output_snapshot)
bundle_hash = bundle.create_bundle("bundle/")
```

## See Also

- Complete examples: examples/
- CLI reference: reprohash --help
- Advanced workflows: docs/ADVANCED.md
