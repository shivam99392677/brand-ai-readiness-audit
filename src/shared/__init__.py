"""Shared schemas and common data contracts."""

from src.shared.evidence_schema import (
    CanonicalEvidence,
    Evidence,
    EvidenceType,
    ExtractionError,
    ExtractionResult,
    Provenance,
)

__all__ = [
    "CanonicalEvidence",
    "Evidence",
    "EvidenceType",
    "ExtractionError",
    "ExtractionResult",
    "Provenance",
]
