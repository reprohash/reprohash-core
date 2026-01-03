"""
ReproHash - Cryptographic Input State Verification
Version 2.1.9 | License: Apache 2.0

Design principles:
- Mechanical enforcement within reference implementation
- Fail-fast with epistemic precision
- Honest boundaries (explicit non-goals)
- Governance-based compatibility
"""

__version__ = "2.1.9"
__author__ = "ReproHash Contributors"
__license__ = "Apache-2.0"

from .snapshot import Snapshot, create_snapshot, SourceType
from .verify import verify_snapshot, verify_runrecord, VerificationOutcome
from .runrecord import RunRecord, ReproducibilityClass
from .bundle import ZenodoBundle, verify_bundle

__all__ = [
    "Snapshot",
    "create_snapshot",
    "SourceType",
    "verify_snapshot",
    "verify_runrecord",
    "VerificationOutcome",
    "RunRecord",
    "ReproducibilityClass",
    "ZenodoBundle",
    "verify_bundle",
]
