# Environment Plugin Interface Specification

## Requirements

All environment plugins MUST satisfy:

1. **Output is sealed**: Plugin data cryptographically bound in RunRecord
2. **Cannot affect verification**: Never changes PASS/FAIL/INCONCLUSIVE
3. **Declares capture method**: Documents what it captures
4. **Versioned**: Plugin version recorded
5. **Completeness disclaimer**: States what it does NOT capture

## Reference Implementation

See: reprohash/env_plugins.py - class PipEnvironmentPlugin

## Conformance

Plugins must:
- Inherit from EnvironmentPlugin
- Implement capture() → Dict[str, Any]
- Return JSON-serializable data only
- Be deterministic (same env → same output)
- Not execute user code
- Not modify environment
